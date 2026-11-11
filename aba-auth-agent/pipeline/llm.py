"""Shared model choices and response handling for every Claude call in the pipeline.

Keeping model IDs in one place means a retired model is a one-line fix instead of a hunt
through the pipeline.
"""

# Sonnet-tier model for extraction, template analysis and narrative generation.
MAIN_MODEL = "claude-sonnet-5-5"
# Haiku-tier model for the cheap post-generation cross-check.
CHECK_MODEL = "claude-haiku-5-5"

# These models think by default and reject custom temperature. Effort is the control:
# structured extraction and drafting from supplied data need little deep reasoning.
EFFORT_EXTRACT = "medium"
EFFORT_GENERATE = "medium"
EFFORT_LIGHT = "low"

# Thinking tokens count toward max_tokens, so leave room beyond the visible JSON.
MAX_TOKENS_LARGE = 16000
MAX_TOKENS_SMALL = 8000


class LLMError(RuntimeError):
    """A model call finished without usable text."""


def response_text(message) -> str:
    """The text of a response, ignoring thinking blocks.

    Raises LLMError, with a message fit to show a user, if the model declined or ran out
    of room, instead of failing later on missing or half-written JSON.
    """
    if message.stop_reason == "refusal":
        raise LLMError("The AI declined to process this request. Review the document, or try again.")
    if message.stop_reason == "max_tokens":
        raise LLMError("The AI's response was cut off before it finished. Try again, or use a shorter document.")

    text = "".join(block.text for block in message.content if block.type == "text").strip()
    if not text:
        raise LLMError("The AI returned an empty response. Please try again.")
    return text
