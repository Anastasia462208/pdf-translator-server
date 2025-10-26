"""PDF reconstruction module - SIDE-BY-SIDE with batch processing."""

import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import io
import os

from utils import TextBlock, ImageBlock, PageInfo, get_logger
from config import TranslatorConfig


logger = get_logger(__name__)


class PDFReconstructor:
    """Reconstructs PDF with side-by-side comparison and batch processing."""
    
    def __init__(self, config: TranslatorConfig):
        """
        Initialize PDF reconstructor.
        
        Args:
            config: TranslatorConfig object
        """
        self.config = config
        self.doc = None
        self.unicode_font = None
        self._load_unicode_font()
        logger.info("Initialized PDF reconstructor for side-by-side mode")
    
    def _load_unicode_font(self):
        """Load a Unicode-capable font for text rendering."""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    with open(font_path, 'rb') as f:
                        font_data = f.read()
                    self.unicode_font = font_path
                    logger.info(f"Loaded Unicode font: {font_path}")
                    return
                except Exception as e:
                    logger.debug(f"Could not load font {font_path}: {e}")
        
        logger.warning("No Unicode font found, using built-in fonts")
    
    def create_side_by_side_pdf(self, original_pdf_path: str,
                               pages: List[PageInfo],
                               text_blocks: List[TextBlock],
                               images: List[ImageBlock],
                               output_path: str,
                               page_range: Optional[Tuple[int, int]] = None):
        """
        Create side-by-side comparison PDF (original | translation).
        
        Args:
            original_pdf_path: Path to original PDF
            pages: List of PageInfo objects
            text_blocks: List of TextBlock objects with translated text
            images: List of ImageBlock objects
            output_path: Path to save the output PDF
            page_range: Optional (start, end) tuple for batch processing
        """
        # Open original PDF
        original_doc = fitz.open(original_pdf_path)
        
        # Determine page range
        if page_range:
            start_page, end_page = page_range
            pages_to_process = [p for p in pages if start_page <= p.page_number < end_page]
            logger.info(f"Processing pages {start_page} to {end_page-1}")
        else:
            pages_to_process = pages
            logger.info(f"Processing all {len(pages)} pages")
        
        # Create new PDF document
        self.doc = fitz.open()
        
        # Process each page
        for page_info in pages_to_process:
            page_num = page_info.page_number
            
            # Create new page with double width + separator
            separator_width = 10
            new_width = page_info.width * 2 + separator_width
            new_height = page_info.height
            
            page = self.doc.new_page(width=new_width, height=new_height)
            
            # === LEFT SIDE: Original (unchanged) ===
            original_page = original_doc[page_num]
            page.show_pdf_page(
                fitz.Rect(0, 0, page_info.width, page_info.height),
                original_doc,
                page_num
            )
            
            # === SEPARATOR LINE ===
            sep_x = page_info.width + separator_width / 2
            page.draw_line(
                (sep_x, 0),
                (sep_x, page_info.height),
                color=(0.7, 0.7, 0.7),
                width=2
            )
            
            # Add "Original" and "Translation" labels at top
            label_font_size = 10
            page.insert_text(
                (page_info.width / 2 - 30, 15),
                "Original",
                fontsize=label_font_size,
                color=(0.5, 0.5, 0.5)
            )
            page.insert_text(
                (page_info.width + separator_width + page_info.width / 2 - 30, 15),
                "Translation",
                fontsize=label_font_size,
                color=(0.5, 0.5, 0.5)
            )
            
            # === RIGHT SIDE: Translation ===
            # Show original as background (lighter)
            page.show_pdf_page(
                fitz.Rect(page_info.width + separator_width, 0, new_width, page_info.height),
                original_doc,
                page_num
            )
            
            # Filter blocks for this page
            page_text_blocks = [b for b in text_blocks if b.page == page_num]
            page_text_blocks.sort(key=lambda b: (b.bbox.y0, b.bbox.x0))
            
            # Calculate offset for right side
            offset_x = page_info.width + separator_width
            
            # Add white rectangles and translated text
            for text_block in page_text_blocks:
                # Create white background rectangle
                rect = fitz.Rect(
                    text_block.bbox.x0 + offset_x - 1,
                    text_block.bbox.y0 - 1,
                    text_block.bbox.x1 + offset_x + 1,
                    text_block.bbox.y1 + 1
                )
                page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)
                
                # Shift text block coordinates
                import copy
                shifted_block = copy.deepcopy(text_block)
                shifted_block.bbox.x0 += offset_x
                shifted_block.bbox.x1 += offset_x
                
                # Add translated text
                self._add_translated_text(page, shifted_block)
            
            logger.debug(f"Processed page {page_num + 1} with {len(page_text_blocks)} translations")
        
        # Save the document
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.config.compression:
            self.doc.save(str(output_path), garbage=4, deflate=True, clean=True)
        else:
            self.doc.save(str(output_path))
        
        self.doc.close()
        original_doc.close()
        
        logger.info(f"Side-by-side PDF saved to: {output_path}")
    
    def _add_translated_text(self, page: fitz.Page, text_block: TextBlock):
        """
        Add translated text with proper formatting.
        
        Args:
            page: PyMuPDF Page object
            text_block: TextBlock with translated text
        """
        text = text_block.translated_text or text_block.text
        if not text.strip():
            return
        
        font_size = text_block.size
        color = text_block.color
        bbox = text_block.bbox
        
        # Adjust font size if needed
        if self.config.adjust_font_size:
            font_size = self._calculate_font_size(text, bbox, font_size)
        
        # Calculate insertion point
        insert_y = bbox.y0 + (font_size * 0.75)
        insert_point = (bbox.x0 + 1, insert_y)
        
        try:
            if self.unicode_font:
                # Use Unicode font for Cyrillic
                font = fitz.Font(fontfile=self.unicode_font)
                
                # Wrap text if too long
                max_width = bbox.width - 2
                lines = self._wrap_text(text, font, font_size, max_width)
                
                y_offset = insert_point[1]
                line_height = font_size * 1.2
                
                for line in lines:
                    if y_offset > bbox.y1:
                        break
                    
                    writer = fitz.TextWriter(page.rect)
                    writer.append(
                        pos=(insert_point[0], y_offset),
                        text=line,
                        font=font,
                        fontsize=font_size
                    )
                    writer.write_text(page, color=color)
                    y_offset += line_height
                
            else:
                # Fallback
                page.insert_text(
                    point=insert_point,
                    text=text,
                    fontsize=font_size,
                    color=color,
                    fontname="helv"
                )
                
        except Exception as e:
            logger.error(f"Failed to add text: {e}")
    
    def _wrap_text(self, text: str, font, font_size: float, max_width: float) -> List[str]:
        """Wrap text to fit within max width."""
        if not text.strip():
            return []
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            estimated_width = len(test_line) * font_size * 0.55
            
            if estimated_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines if lines else [text]
    
    def _calculate_font_size(self, text: str, bbox, original_size: float) -> float:
        """Calculate appropriate font size to fit text."""
        if not text.strip():
            return original_size
        
        try:
            avg_char_width = 0.55
            estimated_width = len(text) * original_size * avg_char_width
            estimated_height = original_size * 1.2
            
            available_width = bbox.width * 0.95
            available_height = bbox.height * 0.90
            
            if estimated_width <= available_width and estimated_height <= available_height:
                return original_size
            
            width_scale = available_width / estimated_width if estimated_width > 0 else 1.0
            height_scale = available_height / estimated_height if estimated_height > 0 else 1.0
            
            scale = min(width_scale, height_scale, 1.0)
            scale = max(scale, self.config.max_font_reduction)
            
            new_size = original_size * scale
            new_size = max(new_size, self.config.min_font_size)
            
            return new_size
            
        except Exception as e:
            logger.warning(f"Font size calculation failed: {e}")
            return original_size
    
    def create_pdf(self, pages: List[PageInfo], text_blocks: List[TextBlock],
                   images: List[ImageBlock], output_path: str,
                   metadata: Optional[Dict] = None,
                   original_pdf_path: Optional[str] = None):
        """
        Create PDF - wrapper для совместимости со старым API.
        
        Args:
            pages: List of PageInfo objects
            text_blocks: List of TextBlock objects with translated text
            images: List of ImageBlock objects
            output_path: Path to save the output PDF
            metadata: Optional metadata dictionary
            original_pdf_path: Path to original PDF (REQUIRED for side-by-side)
        """
        if original_pdf_path is None:
            logger.error("="*60)
            logger.error("ОШИБКА: Не указан original_pdf_path!")
            logger.error("="*60)
            logger.error("Для side-by-side режима требуется оригинальный PDF файл")
            logger.error("")
            logger.error("Решение: Добавьте параметр original_pdf_path при вызове")
            logger.error("="*60)
            
            raise ValueError(
                "original_pdf_path is required for side-by-side mode. "
                "Please provide the path to the original PDF file."
            )
        
        # Вызываем side-by-side метод
        logger.info("Using side-by-side mode (wrapper compatibility)")
        return self.create_side_by_side_pdf(
            original_pdf_path=original_pdf_path,
            pages=pages,
            text_blocks=text_blocks,
            images=images,
            output_path=output_path,
            page_range=None
        )
    
    def process_large_pdf_in_batches(self, original_pdf_path: str,
                                    pages: List[PageInfo],
                                    text_blocks: List[TextBlock],
                                    images: List[ImageBlock],
                                    output_dir: str,
                                    pages_per_batch: int = 5):
        """
        Process large PDF in batches to avoid memory issues.
        
        Args:
            original_pdf_path: Path to original PDF
            pages: List of all PageInfo objects
            text_blocks: List of all TextBlock objects
            images: List of all ImageBlock objects
            output_dir: Directory to save batch PDFs
            pages_per_batch: Number of pages per batch (default: 5)
            
        Returns:
            List of output file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        total_pages = len(pages)
        num_batches = (total_pages + pages_per_batch - 1) // pages_per_batch
        
        logger.info(f"Processing {total_pages} pages in {num_batches} batches ({pages_per_batch} pages each)")
        
        output_files = []
        
        for batch_idx in range(num_batches):
            start_page = batch_idx * pages_per_batch
            end_page = min(start_page + pages_per_batch, total_pages)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"BATCH {batch_idx + 1}/{num_batches}: Pages {start_page + 1}-{end_page}")
            logger.info(f"{'='*60}")
            
            # Create output filename
            output_filename = f"translated_pages_{start_page + 1:03d}-{end_page:03d}.pdf"
            output_path = output_dir / output_filename
            
            # Process this batch
            try:
                self.create_side_by_side_pdf(
                    original_pdf_path=original_pdf_path,
                    pages=pages,
                    text_blocks=text_blocks,
                    images=images,
                    output_path=str(output_path),
                    page_range=(start_page, end_page)
                )
                
                output_files.append(str(output_path))
                logger.info(f"✓ Batch {batch_idx + 1} saved: {output_filename}")
                
            except Exception as e:
                logger.error(f"✗ Batch {batch_idx + 1} failed: {e}")
                continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"COMPLETE: Created {len(output_files)} batch files")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"{'='*60}\n")
        
        return output_files
    
    def merge_batch_pdfs(self, batch_files: List[str], final_output_path: str):
        """
        Merge multiple batch PDF files into one.
        
        Args:
            batch_files: List of PDF file paths to merge
            final_output_path: Path for final merged PDF
        """
        logger.info(f"Merging {len(batch_files)} PDF files...")
        
        final_doc = fitz.open()
        
        for idx, pdf_file in enumerate(batch_files):
            try:
                doc = fitz.open(pdf_file)
                final_doc.insert_pdf(doc)
                doc.close()
                logger.info(f"  Merged file {idx + 1}/{len(batch_files)}: {Path(pdf_file).name}")
            except Exception as e:
                logger.error(f"  Failed to merge {pdf_file}: {e}")
        
        # Save merged file
        final_output_path = Path(final_output_path)
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.config.compression:
            final_doc.save(str(final_output_path), garbage=4, deflate=True, clean=True)
        else:
            final_doc.save(str(final_output_path))
        
        final_doc.close()
        
        logger.info(f"✓ Final merged PDF saved: {final_output_path}")
        logger.info(f"  Total pages: {len(final_doc)}")
    
    def _set_metadata(self, metadata: Dict):
        """Set PDF metadata."""
        try:
            self.doc.set_metadata({
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': 'PDF Translator (Side-by-Side)',
                'producer': 'PDF Translator using PyMuPDF',
            })
        except Exception as e:
            logger.warning(f"Could not set metadata: {e}")
    
    def create_translation_only_pdf(self, original_pdf_path: str,
                                    pages: List[PageInfo],
                                    text_blocks: List[TextBlock],
                                    images: List[ImageBlock],
                                    output_path: str):
        """
        Create PDF with ONLY translated text (no original).
        Uses original PDF as background, overlays white boxes with translations.
        
        Args:
            original_pdf_path: Path to original PDF
            pages: List of PageInfo objects
            text_blocks: List of TextBlock objects with translated text
            images: List of ImageBlock objects
            output_path: Path to save the output PDF
        """
        logger.info("Creating translation-only PDF (overlay mode)")
        
        # Open original PDF
        original_doc = fitz.open(original_pdf_path)
        
        # Create new PDF document
        self.doc = fitz.open()
        
        # Process each page
        for page_info in pages:
            page_num = page_info.page_number
            
            # Create new page with same dimensions
            page = self.doc.new_page(
                width=page_info.width,
                height=page_info.height
            )
            
            # Copy original page as background
            original_page = original_doc[page_num]
            page.show_pdf_page(
                fitz.Rect(0, 0, page_info.width, page_info.height),
                original_doc,
                page_num
            )
            
            # Filter blocks for this page
            page_text_blocks = [b for b in text_blocks if b.page == page_num]
            page_text_blocks.sort(key=lambda b: (b.bbox.y0, b.bbox.x0))
            
            # Add white rectangles and translated text
            for text_block in page_text_blocks:
                # Create white background rectangle to cover original text
                rect = fitz.Rect(
                    text_block.bbox.x0 - 1,
                    text_block.bbox.y0 - 1,
                    text_block.bbox.x1 + 1,
                    text_block.bbox.y1 + 1
                )
                page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)
                
                # Add translated text on top
                self._add_translated_text(page, text_block)
            
            logger.debug(f"Processed page {page_num + 1} with {len(page_text_blocks)} translations")
        
        # Save the document
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.config.compression:
            self.doc.save(str(output_path), garbage=4, deflate=True, clean=True)
        else:
            self.doc.save(str(output_path))
        
        self.doc.close()
        original_doc.close()
        
        logger.info(f"Translation-only PDF saved to: {output_path}")


def test_side_by_side():
    """Test side-by-side PDF creation."""
    print("\n" + "="*60)
    print("PDF TRANSLATOR - SIDE-BY-SIDE MODE TEST")
    print("="*60 + "\n")
    
    # This test assumes you have a PDF file to test with
    test_pdf = "quarto_ceramics.pdf"
    
    if not Path(test_pdf).exists():
        print(f"❌ Test file not found: {test_pdf}")
        print("Please provide a PDF file for testing.")
        return
    
    print(f"✓ Found test file: {test_pdf}\n")
    
    # Import necessary modules
    from config import TranslatorConfig
    from extractor import PDFExtractor
    from translator import TextTranslator
    
    # Create config
    config = TranslatorConfig(
        source_language='en',
        target_language='ru',
        batch_size=5
    )
    
    print("Step 1: Extracting PDF content...")
    with PDFExtractor(test_pdf) as extractor:
        data = extractor.extract_all()
    
    pages = data['pages']
    text_blocks = data['text_blocks']
    images = data['images']
    
    print(f"  ✓ Extracted {len(pages)} pages")
    print(f"  ✓ Extracted {len(text_blocks)} text blocks")
    print(f"  ✓ Extracted {len(images)} images\n")
    
    print("Step 2: Translating text...")
    translator = TextTranslator(config)
    translated_blocks = translator.translate_text_blocks(text_blocks, 'en', 'ru')
    print(f"  ✓ Translated {len(translated_blocks)} blocks\n")
    
    print("Step 3: Creating side-by-side PDF...")
    reconstructor = PDFReconstructor(config)
    
    output_path = "test_side_by_side.pdf"
    reconstructor.create_side_by_side_pdf(
        original_pdf_path=test_pdf,
        pages=pages,
        text_blocks=translated_blocks,
        images=images,
        output_path=output_path
    )
    
    print(f"\n✓ SUCCESS! Created: {output_path}")
    print("\nOpen the PDF to see:")
    print("  - Left side: Original English")
    print("  - Right side: Russian translation")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_side_by_side()
