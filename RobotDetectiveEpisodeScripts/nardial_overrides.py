"""Project-local runtime patches for nardial behavior.

These overrides keep episode behavior stable even if the installed package is updated.
"""

from nardial.conversation_agent import ConversationAgent


_PATCH_APPLIED = False


def apply_nardial_overrides() -> None:
    """Apply runtime monkey patches used by Robot Detective episodes."""
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return

    original_ask_yesno = ConversationAgent.ask_yesno

    def ask_yesno_with_text_fallback(self, question, max_attempts=1):
        attempts = 0
        while attempts < max_attempts:
            self.say(question)
            reply, intent = self.orchestrator.listen()

            if intent:
                print(f"context: answer_yesno, recognized_intent: {str(intent)}")
                if intent == "yesno_yes":
                    return "yes"
                if intent == "yesno_no":
                    return "no"
                if intent == "yesno_dontknow":
                    return "dontknow"

            # Keyboard mode returns text without intent, so parse common variants.
            if reply:
                normalized = str(reply).strip().lower()
                yes_values = {
                    "yes", "y", "yeah", "yep", "sure", "ok", "okay",
                    "ja", "jazeker", "zeker", "jawel",
                }
                no_values = {
                    "no", "n", "nope",
                    "nee", "neen",
                }
                dontknow_values = {
                    "dontknow", "don't know", "do not know", "idk", "not sure",
                    "weet niet", "ik weet het niet", "geen idee", "misschien",
                }

                if normalized in yes_values:
                    return "yes"
                if normalized in no_values:
                    return "no"
                if normalized in dontknow_values:
                    return "dontknow"

            attempts += 1

        return None

    ConversationAgent.ask_yesno = ask_yesno_with_text_fallback
    ConversationAgent._robot_detective_original_ask_yesno = original_ask_yesno
    _PATCH_APPLIED = True

