"""
TTS text sanitization utilities.

Strips markdown formatting and other markup that TTS engines
would otherwise read aloud (e.g. "**" spoken as "star star").
"""

import re


def sanitize_for_tts(text: str) -> str:
    """Remove markdown formatting so text reads naturally through TTS.

    Args:
        text: Raw text that may contain markdown formatting.

    Returns:
        Cleaned plain text suitable for TTS processing.

    Examples:
        >>> sanitize_for_tts("This is **bold** text")
        'This is bold text'
        >>> sanitize_for_tts("Visit [Google](https://google.com) now")
        'Visit Google now'
    """
    if not text:
        return text

    # --- block-level elements (order matters) ---

    # Fenced code blocks → remove entirely
    text = re.sub(r"```[\s\S]*?```", "", text)

    # Horizontal rules (---, ***, ___) on their own line
    text = re.sub(r"^[ \t]*[-*_]{3,}[ \t]*$", "", text, flags=re.MULTILINE)

    # Headers (# … ######)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Block quotes
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

    # Unordered list markers (- or *)
    text = re.sub(r"^[ \t]*[-*]\s+", "", text, flags=re.MULTILINE)

    # Ordered list markers (1. 2. …)
    text = re.sub(r"^[ \t]*\d+\.\s+", "", text, flags=re.MULTILINE)

    # --- inline elements ---

    # Bold (**text** and __text__)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)

    # Italic (*text* and _text_) — avoid matching already-handled bold
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", text)

    # Strikethrough
    text = re.sub(r"~~(.+?)~~", r"\1", text)

    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Links [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Leftover standalone asterisks / underscores (any orphans)
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"(?<!\w)_+(?!\w)", "", text)

    # --- whitespace cleanup ---
    text = re.sub(r"\s+", " ", text)

    return text.strip()
