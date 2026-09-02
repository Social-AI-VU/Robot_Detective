"""Runtime compatibility and resiliency patches for Robot Detective."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path


def _install_nardial_tts_manager_shim() -> None:
    module_name = "nardial.tts_manager"
    if module_name in sys.modules:
        return
    try:
        from sic_framework.services.elevenlabs_tts.elevenlabs_tts import (  # type: ignore
            ElevenLabsTTS,
            ElevenLabsTTSConf,
            GetElevenLabsSpeechRequest,
        )
    except Exception:
        return

    shim = types.ModuleType(module_name)
    shim.ElevenLabsTTS = ElevenLabsTTS
    shim.ElevenLabsTTSConf = ElevenLabsTTSConf
    shim.GetElevenLabsSpeechRequest = GetElevenLabsSpeechRequest
    sys.modules[module_name] = shim


def _install_rag_timeout_and_fallback_patch() -> None:
    try:
        import sic_framework.services.datastore.redis_datastore as rd  # type: ignore
    except Exception:
        return

    try:
        timeout_sec = float(os.getenv("OPENAI_EMBED_TIMEOUT_SEC", "20"))
    except Exception:
        timeout_sec = 20.0

    def _openai_embed_texts_with_timeout(texts: list[str], *, model: str, api_key: str) -> list[list[float]]:
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency: openai.\n"
                "Install it with: pip install openai\n"
                "Original import error: {}".format(e)
            ) from e
        if not api_key:
            raise RuntimeError("openai_api_key parameter is required")

        client = OpenAI(api_key=api_key, timeout=timeout_sec)
        resp = client.embeddings.create(model=model, input=texts)
        data = sorted(resp.data, key=lambda d: d.index)
        return [d.embedding for d in data]

    rd._openai_embed_texts = _openai_embed_texts_with_timeout

    original_handle = rd.RedisDatastoreComponent.handle_datastore_actions

    def _safe_handle(self, request):
        try:
            return original_handle(self, request)
        except Exception as exc:
            if rd.is_sic_instance(request, rd.QueryVectorDBRequest):
                self.logger.error("QueryVectorDBRequest failed: {}".format(exc))
                index_name = rd.sanitize_index_name(getattr(request, "index_name", "index"))
                return rd.VectorDBResultsMessage(
                    payload={
                        "index": index_name,
                        "total": 0,
                        "results": [],
                        "error": str(exc),
                    }
                )
            raise

    rd.RedisDatastoreComponent.handle_datastore_actions = _safe_handle


def _install_connector_rag_timeout_patch() -> None:
    """
    Guard client-side RAG requests so the interview loop does not block when datastore
    replies are missing or delayed.
    """
    try:
        from sic_framework.core.connector import SICConnector  # type: ignore
        from sic_framework.services.datastore.redis_datastore import VectorDBResultsMessage  # type: ignore
    except Exception:
        return

    original_request = SICConnector.request

    try:
        rag_timeout_sec = float(os.getenv("RAG_QUERY_TIMEOUT_SEC", "12"))
    except Exception:
        rag_timeout_sec = 12.0

    def _safe_request(self, request, timeout=100.0, block=True):
        is_rag_query = request.__class__.__name__ == "QueryVectorDBRequest"
        if not is_rag_query:
            return original_request(self, request, timeout=timeout, block=block)

        effective_timeout = min(float(timeout), rag_timeout_sec)
        try:
            return original_request(self, request, timeout=effective_timeout, block=block)
        except TimeoutError as exc:
            self.logger.error("RAG query timed out after {}s: {}".format(effective_timeout, exc))
            return VectorDBResultsMessage(
                payload={
                    "index": getattr(request, "index_name", ""),
                    "total": 0,
                    "results": [],
                    "error": "rag_query_timeout",
                }
            )
        except Exception as exc:
            self.logger.error("RAG query failed: {}".format(exc))
            return VectorDBResultsMessage(
                payload={
                    "index": getattr(request, "index_name", ""),
                    "total": 0,
                    "results": [],
                    "error": str(exc),
                }
            )

    SICConnector.request = _safe_request


def _install_vector_store_quality_patch() -> None:
    """Improve RAG snippet quality to reduce prompt-echo behavior."""
    try:
        from nardial.providers.vector_store.redis_store import RedisVectorStoreProvider  # type: ignore
        from sic_framework.services.datastore.redis_datastore import (  # type: ignore
            QueryVectorDBRequest,
            VectorDBResultsMessage,
        )
    except Exception:
        return

    def _is_low_signal_query(text: str) -> bool:
        normalized = " ".join((text or "").strip().lower().split())
        if not normalized:
            return True
        greetings = {"hoi", "hallo", "hey", "yo", "oke", "ok", "hi", "goedemorgen", "goedemiddag"}
        if normalized in greetings:
            return True
        return len(normalized.split()) <= 2 and "?" not in normalized

    def _clean_snippet(content: str) -> str:
        heading_drops = {
            "personal history trudy",
            "personal relationships trudy",
            "mystery knowlegde",
            "ep1 mystery knowledge trudy",
            "conversation guidelines",
        }
        lines = []
        for raw in (content or "").replace("\ufeff", "").splitlines():
            line = raw.strip()
            if not line:
                continue
            low = line.lower()
            if low in heading_drops:
                continue
            if "haal dit uit de rag" in low:
                continue
            lines.append(line)
        cleaned = " ".join(lines).strip()
        if len(cleaned) > 420:
            cleaned = cleaned[:420].rsplit(" ", 1)[0] + "..."
        return cleaned

    def _query(self, text: str, index_name: str | None = None, k: int = 5) -> list[str]:
        user_text = str(text or "").strip()
        if _is_low_signal_query(user_text):
            return []

        query_index = index_name or self._index_name
        if not query_index:
            raise ValueError("RedisVectorStoreProvider.query requires an index name")

        result = self._datastore.request(
            QueryVectorDBRequest(
                index_name=query_index,
                query_text=user_text,
                openai_api_key=self._openai_api_key,
                k=max(1, min(int(k), 3)),
                partition="default",
                embedding_model=self._embedding_model,
            )
        )

        if not isinstance(result, VectorDBResultsMessage):
            return []

        snippets = []
        for idx, item in enumerate(result.payload.get("results", []), start=1):
            cleaned = _clean_snippet(item.get("content") or "")
            if not cleaned:
                continue
            source = Path(item.get("doc_path") or "unknown").name
            snippets.append(f"[{idx}] Source: {source}\nFacts: {cleaned}")
            if len(snippets) >= 3:
                break
        return snippets

    RedisVectorStoreProvider.query = _query


def apply_runtime_patches() -> None:
    _install_nardial_tts_manager_shim()
    _install_rag_timeout_and_fallback_patch()
    _install_connector_rag_timeout_patch()
    _install_vector_store_quality_patch()
