"""Domain constants for Vocara Voice API Platform."""

# Canonical Khmer default script used for voice preview, instant cloning preview, and acoustic design preview
DEFAULT_PREVIEW_TEXT: str = "សួស្តី ខ្ញុំជាវូការា ជាអេអាយបម្លែងអក្សរទៅជាសម្លេង។"

# Canonical English default script for English voice previews
DEFAULT_PREVIEW_TEXT_EN: str = "Hello, I am Vocara, an AI text-to-speech converter."


def get_preview_text_for_language(language: str | None) -> str:
    """Return appropriate language preview script."""
    if language and language.lower().startswith("en"):
        return DEFAULT_PREVIEW_TEXT_EN
    return DEFAULT_PREVIEW_TEXT

