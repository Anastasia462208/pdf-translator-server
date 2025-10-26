"""Configuration management for PDF Translator."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TranslatorConfig:
    """Configuration for PDF translation."""
    
    # Language settings
    source_language: str = 'auto'
    target_language: str = 'en'
    
    # Font settings
    preserve_fonts: bool = True
    font_fallback: str = 'Arial'
    adjust_font_size: bool = True
    max_font_reduction: float = 0.8  # Don't reduce below 80% of original
    min_font_size: float = 6.0  # Minimum font size in points
    
    # Translation settings
    translation_model: str = 'gpt-4.1-mini'
    batch_size: int = 10  # Number of text blocks to translate at once
    max_tokens: int = 4000
    temperature: float = 0.3  # Lower temperature for more consistent translation
    
    # Processing settings
    preserve_images: bool = True
    preserve_layout: bool = True
    extract_tables: bool = True
    
    # Output settings
    output_format: str = 'pdf'
    compression: bool = True
    
    # API settings
    openai_api_key: Optional[str] = None
    
    def __post_init__(self):
        """Initialize API key from environment if not provided."""
        if self.openai_api_key is None:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'TranslatorConfig':
        """Create config from dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})


# Language code mapping
LANGUAGE_CODES = {
    'english': 'en',
    'russian': 'ru',
    'spanish': 'es',
    'french': 'fr',
    'german': 'de',
    'italian': 'it',
    'portuguese': 'pt',
    'chinese': 'zh',
    'japanese': 'ja',
    'korean': 'ko',
    'arabic': 'ar',
    'hindi': 'hi',
    'turkish': 'tr',
    'polish': 'pl',
    'dutch': 'nl',
    'swedish': 'sv',
    'norwegian': 'no',
    'danish': 'da',
    'finnish': 'fi',
    'czech': 'cs',
    'greek': 'el',
    'hebrew': 'he',
    'thai': 'th',
    'vietnamese': 'vi',
    'indonesian': 'id',
    'malay': 'ms',
    'ukrainian': 'uk',
}

# Reverse mapping
LANGUAGE_NAMES = {v: k for k, v in LANGUAGE_CODES.items()}


def get_language_code(language: str) -> str:
    """Convert language name to code."""
    language_lower = language.lower()
    if language_lower in LANGUAGE_CODES:
        return LANGUAGE_CODES[language_lower]
    elif language in LANGUAGE_CODES.values():
        return language
    else:
        return language  # Return as-is if not found


def get_language_name(code: str) -> str:
    """Convert language code to name."""
    return LANGUAGE_NAMES.get(code, code)

