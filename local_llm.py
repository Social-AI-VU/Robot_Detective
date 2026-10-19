"""
Choose the language model for the chats, interviews and Robin's summaries: OpenAI (default) or a
local model served by Ollama or LM Studio (both speak the OpenAI chat protocol).

The launcher asks which one to use. Without the launcher, set it in conf/.env:
    LLM_BACKEND=openai_direct                  # any OpenAI model, straight from the episode (no GPT service):
    OPENAI_MODEL=gpt-5.4-mini                  #   e.g. gpt-5.4-mini, gpt-5.4-nano, gpt-4o
    OPENAI_REASONING_EFFORT=none               #   GPT-5 only: how long it thinks first; "none" is fastest
    LLM_BACKEND=local                          # "openai" (default, gpt-4o-mini via the GPT service) or "local"
    LOCAL_LLM_URL=http://localhost:11434/v1    # Ollama; LM Studio is http://localhost:1234/v1
    LOCAL_LLM_MODEL=qwen2.5:3b                 # the model name as the server knows it (`ollama list`)
    LOCAL_LLM_TEMPERATURE=0.7                  # optional, same as OpenAI
    LOCAL_LLM_MAX_TOKENS=150                   # optional; answers are 1-3 short sentences
    LOCAL_LLM_TIMEOUT=60                       # optional, seconds per answer before giving up

With the local backend the GPT service is not needed. The knowledge search (RAG) still uses
OpenAI embeddings, so OPENAI_API_KEY stays needed for that.

Try a model before a session:
    python utils/test_local_llm.py
"""
import os
import re
import time

THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class LocalLLMProvider:
    """nardial LLM provider for any OpenAI-compatible server (Ollama, LM Studio, llama.cpp, vLLM)."""

    def __init__(self, base_url: str, model: str, temperature: float = 0.7, max_tokens: int = 150,
                 timeout: float = 60, api_key: str | None = None, reasoning_effort: str = "none"):
        from openai import OpenAI

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        # Local servers ignore the key, but the client needs one.
        self._client = OpenAI(base_url=base_url, api_key=api_key or os.getenv("LOCAL_LLM_API_KEY", "local"),
                              timeout=timeout, max_retries=0)

    def complete(self, messages, system_prompt: str = "") -> str:
        if not messages:
            return ""
        chat = [{"role": "system", "content": system_prompt}] if system_prompt else []
        chat += [{"role": m.role, "content": m.content} for m in messages]
        started = time.monotonic()
        if self.model.startswith("gpt-5"):
            # GPT-5 models only take max_completion_tokens, no temperature, and think first unless told not to.
            try:
                resp = self._client.chat.completions.create(
                    model=self.model, messages=chat, max_completion_tokens=self.max_tokens,
                    reasoning_effort=self.reasoning_effort,
                )
            except Exception as exc:
                if "reasoning_effort" not in str(exc) or self.reasoning_effort == "minimal":
                    raise
                self.reasoning_effort = "minimal"  # older GPT-5 models (gpt-5, gpt-5-mini) have no "none"
                resp = self._client.chat.completions.create(
                    model=self.model, messages=chat, max_completion_tokens=self.max_tokens,
                    reasoning_effort=self.reasoning_effort,
                )
        else:
            resp = self._client.chat.completions.create(
                model=self.model, messages=chat, temperature=self.temperature, max_tokens=self.max_tokens,
            )
        text = resp.choices[0].message.content or ""
        # Reasoning models (deepseek-r1, qwen3, ...) put their thinking between <think> tags.
        text = THINK_BLOCK.sub("", text).strip()
        print(f"[LLM] {self.model}: {time.monotonic() - started:.1f} s", flush=True)
        return text


def preload_ollama(url: str, model: str, keep_alive: str = "3h") -> None:
    """Load the model now and keep it in memory for the whole session.

    Ollama unloads a model after 5 idle minutes, so after a long pause the next answer would
    have to wait for loading again (~10 s on a laptop). Other servers are left alone."""
    import json
    import urllib.request

    base = url.rstrip("/").removesuffix("/v1")
    request = urllib.request.Request(
        f"{base}/api/generate", data=json.dumps({"model": model, "keep_alive": keep_alive}).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=180) as resp:
            resp.read()
        print(f"[LLM] {model} loaded in {time.monotonic() - started:.0f} s; kept in memory for {keep_alive}", flush=True)
    except Exception as exc:
        print(f"[LLM] Could not load {model} in Ollama ({exc}). Is Ollama running, and is the model "
              f"downloaded (`ollama pull {model}`)?", flush=True)


def make_llm_provider():
    """The LLM provider the episode runners use, chosen by LLM_BACKEND (launcher or conf/.env)."""
    backend = os.getenv("LLM_BACKEND", "openai").strip().lower()
    if backend == "local":
        url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
        model = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:3b")
        print(f"[LLM] Local model {model} at {url}", flush=True)
        if ":11434" in url:  # Ollama
            preload_ollama(url, model)
        return LocalLLMProvider(
            base_url=url,
            model=model,
            temperature=float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LOCAL_LLM_MAX_TOKENS", "150")),
            timeout=float(os.getenv("LOCAL_LLM_TIMEOUT", "60")),
        )
    if backend == "openai_direct":
        model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip()
        print(f"[LLM] OpenAI {model}, directly (no GPT service)", flush=True)
        return LocalLLMProvider(
            base_url="https://api.openai.com/v1",
            model=model,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "150")),
            timeout=float(os.getenv("OPENAI_TIMEOUT", "30")),
            reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "none").strip(),
        )
    if backend != "openai":
        print(f"[LLM] Unknown LLM_BACKEND={backend!r}; using OpenAI", flush=True)
    from nardial.providers.llm.openai_gpt import OpenAIGPTProvider

    return OpenAIGPTProvider(api_key=os.getenv("OPENAI_API_KEY"))
