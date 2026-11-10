"""Domain constants for Vocara Voice API Platform."""

# Canonical Khmer default script used for voice preview, instant cloning preview, and acoustic design preview
DEFAULT_PREVIEW_TEXT: str = "សួស្តី ខ្ញុំជាវូការា ជាអេអាយបម្លែងអក្សរទៅជាសម្លេង។"

# Canonical English default script for English voice previews
DEFAULT_PREVIEW_TEXT_EN: str = "Hello, I am Vocara, an AI text-to-speech converter."


def get_preview_text_for_language(
    language: str | None,
    km_default: str | None = None,
    en_default: str | None = None,
) -> str:
    """Return appropriate language preview script using configured overrides when provided."""
    if language and language.lower().startswith("en"):
        return en_default or DEFAULT_PREVIEW_TEXT_EN
    return km_default or DEFAULT_PREVIEW_TEXT

