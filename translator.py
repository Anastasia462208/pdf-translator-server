"""Improved translation module with better prompts and context handling."""

import time
from typing import List, Dict, Optional, Tuple
from openai import OpenAI

from utils import TextBlock, get_logger
from config import TranslatorConfig


logger = get_logger(__name__)


class TextTranslator:
    """Handles text translation using OpenAI API with improved prompts."""
    
    def __init__(self, config: TranslatorConfig):
        """
        Initialize translator.
        
        Args:
            config: TranslatorConfig object
        """
        self.config = config
        self.client = OpenAI()  # API key from environment
        self.translation_cache = {}
        logger.info(f"Initialized translator with model: {config.translation_model}")
    
    def translate_text(self, text: str, source_lang: str, target_lang: str,
                      context: Optional[str] = None) -> str:
        """
        Translate a single text string.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context for better translation
            
        Returns:
            Translated text
        """
        if not text.strip():
            return text
        
        # Check cache first
        cache_key = f"{text}:{source_lang}:{target_lang}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]
        
        try:
            # Create improved prompt
            prompt = self._create_translation_prompt(text, source_lang, target_lang, context)
            
            # Make API call
            response = self.client.chat.completions.create(
                model=self.config.translation_model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(source_lang, target_lang)},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=2000
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # Cache the result
            self.translation_cache[cache_key] = translated_text
            
            logger.debug(f"Translated: '{text[:50]}...' -> '{translated_text[:50]}...'")
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation failed for text '{text[:50]}...': {e}")
            return text  # Return original text on failure
    
    def translate_text_blocks(self, text_blocks: List[TextBlock],
                            source_lang: str, target_lang: str) -> List[TextBlock]:
        """
        Translate multiple text blocks with context awareness.
        
        Args:
            text_blocks: List of TextBlock objects
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            List of TextBlock objects with translated text
        """
        logger.info(f"Translating {len(text_blocks)} text blocks...")
        
        # Group blocks by page for context
        pages = {}
        for block in text_blocks:
            if block.page not in pages:
                pages[block.page] = []
            pages[block.page].append(block)
        
        # Process each page
        translated_blocks = []
        for page_num, page_blocks in pages.items():
            logger.info(f"Translating page {page_num + 1} ({len(page_blocks)} blocks)")
            page_translated = self._translate_page_blocks(page_blocks, source_lang, target_lang)
            translated_blocks.extend(page_translated)
        
        logger.info(f"Translation complete: {len(translated_blocks)} blocks")
        return translated_blocks
    
    def _translate_page_blocks(self, page_blocks: List[TextBlock],
                             source_lang: str, target_lang: str) -> List[TextBlock]:
        """
        Translate blocks from a single page with context.
        
        Args:
            page_blocks: List of TextBlock objects from one page
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            List of translated TextBlock objects
        """
        # Sort blocks by position (top to bottom, left to right)
        sorted_blocks = sorted(page_blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))
        
        # Process in batches with context
        batch_size = self.config.batch_size
        translated_blocks = []
        
        for i in range(0, len(sorted_blocks), batch_size):
            batch = sorted_blocks[i:i + batch_size]
            
            # Create context from surrounding text
            context = self._build_context(sorted_blocks, i, batch_size)
            
            # Translate batch
            batch_translated = self._translate_batch_with_context(
                batch, source_lang, target_lang, context
            )
            translated_blocks.extend(batch_translated)
            
            logger.info(f"Translated batch {i//batch_size + 1}/{(len(sorted_blocks) + batch_size - 1)//batch_size}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        return translated_blocks
    
    def _translate_batch_with_context(self, batch: List[TextBlock],
                                    source_lang: str, target_lang: str,
                                    context: str) -> List[TextBlock]:
        """
        Translate a batch of text blocks with context.
        
        Args:
            batch: List of TextBlock objects to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Context information
            
        Returns:
            List of translated TextBlock objects
        """
        try:
            # Prepare texts for batch translation
            texts = [block.text for block in batch if block.text.strip()]
            if not texts:
                return batch
            
            # Create batch translation prompt
            prompt = self._create_batch_translation_prompt(texts, source_lang, target_lang, context)
            
            # Make API call
            response = self.client.chat.completions.create(
                model=self.config.translation_model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(source_lang, target_lang)},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=4000
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            translations = self._parse_batch_response(response_text, len(texts))
            
            # Apply translations to blocks
            text_index = 0
            for block in batch:
                if block.text.strip():
                    if text_index < len(translations):
                        block.translated_text = translations[text_index]
                        # Cache individual translation
                        cache_key = f"{block.text}:{source_lang}:{target_lang}"
                        self.translation_cache[cache_key] = translations[text_index]
                        text_index += 1
                    else:
                        block.translated_text = block.text  # Fallback
                else:
                    block.translated_text = block.text
            
            logger.debug(f"Batch translated {len(texts)} texts")
            return batch
            
        except Exception as e:
            logger.error(f"Batch translation failed: {e}")
            # Fallback to individual translation
            return self._translate_batch_individually(batch, source_lang, target_lang)
    
    def _translate_batch_individually(self, batch: List[TextBlock],
                                    source_lang: str, target_lang: str) -> List[TextBlock]:
        """
        Fallback method to translate each block individually.
        
        Args:
            batch: List of TextBlock objects
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            List of translated TextBlock objects
        """
        for block in batch:
            block.translated_text = self.translate_text(block.text, source_lang, target_lang)
        return batch
    
    def _build_context(self, all_blocks: List[TextBlock], current_index: int, batch_size: int) -> str:
        """
        Build context from surrounding text blocks.
        
        Args:
            all_blocks: All text blocks from the page
            current_index: Index of current batch start
            batch_size: Size of current batch
            
        Returns:
            Context string
        """
        context_parts = []
        
        # Add previous text for context (up to 3 blocks)
        start_context = max(0, current_index - 3)
        for i in range(start_context, current_index):
            if all_blocks[i].text.strip():
                context_parts.append(all_blocks[i].text.strip())
        
        # Add following text for context (up to 3 blocks)
        end_context = min(len(all_blocks), current_index + batch_size + 3)
        for i in range(current_index + batch_size, end_context):
            if all_blocks[i].text.strip():
                context_parts.append(all_blocks[i].text.strip())
        
        return " ".join(context_parts) if context_parts else ""
    
    def _get_system_prompt(self, source_lang: str, target_lang: str) -> str:
        """
        Get system prompt for translation.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            System prompt string
        """
        lang_names = {
            'en': 'English', 'ru': 'Russian', 'es': 'Spanish', 'fr': 'French',
            'de': 'German', 'it': 'Italian', 'pt': 'Portuguese', 'zh': 'Chinese',
            'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic', 'hi': 'Hindi',
            'tr': 'Turkish', 'pl': 'Polish', 'nl': 'Dutch', 'sv': 'Swedish',
            'no': 'Norwegian', 'da': 'Danish', 'fi': 'Finnish', 'cs': 'Czech',
            'el': 'Greek', 'he': 'Hebrew', 'th': 'Thai', 'vi': 'Vietnamese',
            'id': 'Indonesian', 'ms': 'Malay', 'uk': 'Ukrainian'
        }
        
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)
        
        return f"""You are a professional translator specializing in document translation from {source_name} to {target_name}.

Your task is to provide accurate, natural, and contextually appropriate translations that:
1. Preserve the original meaning and tone
2. Use natural, fluent language in the target language
3. Maintain technical terminology accuracy
4. Respect formatting and structure
5. Consider the document context and domain

Guidelines:
- Translate text naturally, not word-for-word
- Preserve proper nouns, brand names, and technical terms when appropriate
- Maintain the same level of formality as the original
- Keep numbers, dates, and measurements in their original format unless localization is needed
- For headings and titles, use appropriate capitalization for the target language
- If text appears to be a heading, title, or label, translate accordingly

Always provide only the translation without explanations or additional text."""
    
    def _create_translation_prompt(self, text: str, source_lang: str, target_lang: str,
                                 context: Optional[str] = None) -> str:
        """
        Create translation prompt for single text.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Optional context
            
        Returns:
            Translation prompt
        """
        prompt = f"Translate the following text from {source_lang} to {target_lang}:\n\n{text}"
        
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        
        return prompt
    
    def _create_batch_translation_prompt(self, texts: List[str], source_lang: str,
                                       target_lang: str, context: str) -> str:
        """
        Create batch translation prompt.
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            context: Context information
            
        Returns:
            Batch translation prompt
        """
        prompt = f"Translate the following {len(texts)} text segments from {source_lang} to {target_lang}.\n"
        prompt += "Provide translations in the same order, separated by '---' on a new line.\n"
        
        if context:
            prompt += f"\nContext: {context}\n"
        
        prompt += "\nTexts to translate:\n\n"
        
        for i, text in enumerate(texts, 1):
            prompt += f"{i}. {text}\n"
        
        prompt += "\nProvide only the translations, separated by '---':"
        
        return prompt
    
    def _parse_batch_response(self, response: str, expected_count: int) -> List[str]:
        """
        Parse batch translation response.
        
        Args:
            response: API response text
            expected_count: Expected number of translations
            
        Returns:
            List of translated texts
        """
        # Split by separator
        parts = response.split('---')
        
        # Clean up translations
        translations = []
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                # Remove numbering if present
                if cleaned.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    cleaned = cleaned[2:].strip()
                translations.append(cleaned)
        
        # Ensure we have the right number of translations
        while len(translations) < expected_count:
            translations.append("")  # Add empty strings for missing translations
        
        return translations[:expected_count]
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.translation_model,
                messages=[
                    {"role": "system", "content": "You are a language detection expert. Respond with only the ISO 639-1 language code (e.g., 'en', 'ru', 'es', 'fr', 'de')."},
                    {"role": "user", "content": f"Detect the language of this text: {text[:500]}"}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            detected_lang = response.choices[0].message.content.strip().lower()
            logger.info(f"Detected language: {detected_lang}")
            return detected_lang
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en"  # Default to English


def test_translator():
    """Test the translator with sample text."""
    from config import TranslatorConfig
    
    config = TranslatorConfig()
    translator = TextTranslator(config)
    
    # Test single translation
    text = "Hello, this is a test document."
    translated = translator.translate_text(text, "en", "ru")
    print(f"Original: {text}")
    print(f"Translated: {translated}")
    
    # Test language detection
    detected = translator.detect_language(text)
    print(f"Detected language: {detected}")


if __name__ == "__main__":
    test_translator()
