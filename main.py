#!/usr/bin/env python3
"""
PDF Translator - Main Application with Batch Processing

Translates PDF documents in batches for better memory management.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from config import TranslatorConfig, get_language_code, LANGUAGE_CODES
from extractor import PDFExtractor
from translator import TextTranslator
from reconstructor import PDFReconstructor
from utils import get_logger, format_file_size


logger = get_logger(__name__)


class PDFTranslatorApp:
    """Main application class for PDF translation with batch processing."""
    
    def __init__(self, config: TranslatorConfig):
        """
        Initialize the application.
        
        Args:
            config: TranslatorConfig object
        """
        self.config = config
        self.extractor = None
        self.translator = None
        self.reconstructor = None
        
        logger.info("PDF Translator initialized with batch processing support")
    
    def translate_pdf(self, input_path: str, output_path: str,
                     source_lang: Optional[str] = None,
                     target_lang: Optional[str] = None,
                     pages_per_batch: int = 5,
                     merge_batches: bool = True,
                     mode: str = 'side-by-side') -> bool:
        """
        Translate a PDF file with batch processing.
        
        Args:
            input_path: Path to input PDF
            output_path: Path to output PDF (or directory for batches)
            source_lang: Source language code (optional)
            target_lang: Target language code
            pages_per_batch: Number of pages to process per batch
            merge_batches: Whether to merge batch files into one PDF
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate input file
            input_path = Path(input_path)
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                return False
            
            if not input_path.suffix.lower() == '.pdf':
                logger.error(f"Input file is not a PDF: {input_path}")
                return False
            
            # Get file size
            file_size = input_path.stat().st_size
            logger.info(f"Processing PDF: {input_path.name} ({format_file_size(file_size)})")
            
            # ============================================
            # STEP 1: Extract content from PDF
            # ============================================
            logger.info("\n" + "="*60)
            logger.info("STEP 1/3: Extracting content from PDF")
            logger.info("="*60)
            
            with PDFExtractor(str(input_path)) as extractor:
                self.extractor = extractor
                
                # Get statistics
                stats = extractor.get_statistics()
                logger.info(f"  Pages: {stats['page_count']}")
                logger.info(f"  Text blocks: {stats['text_block_count']}")
                logger.info(f"  Images: {stats['image_count']}")
                logger.info(f"  Words: {stats['total_words']}")
                logger.info(f"  Fonts: {', '.join(stats['font_list'][:5])}")
                
                # Extract all content
                extracted_data = extractor.extract_all()
            
            pages = extracted_data['pages']
            text_blocks = extracted_data['text_blocks']
            images = extracted_data['images']
            metadata = extracted_data['metadata']
            
            total_pages = len(pages)
            
            # ============================================
            # STEP 2: Translate text
            # ============================================
            logger.info("\n" + "="*60)
            logger.info("STEP 2/3: Translating text")
            logger.info("="*60)
            
            self.translator = TextTranslator(self.config)
            
            # Use provided languages or config defaults
            src_lang = source_lang or self.config.source_language
            tgt_lang = target_lang or self.config.target_language
            
            # Auto-detect source language if needed
            if src_lang == 'auto' and text_blocks:
                sample_text = ' '.join([b.text for b in text_blocks[:5]])
                src_lang = self.translator.detect_language(sample_text)
                logger.info(f"  Detected source language: {src_lang}")
            
            logger.info(f"  Translating from {src_lang} to {tgt_lang}...")
            logger.info(f"  Model: {self.config.translation_model}")
            
            # Translate all text blocks
            translated_blocks = self.translator.translate_text_blocks(
                text_blocks, src_lang, tgt_lang
            )
            
            # ============================================
            # STEP 3: Create side-by-side PDF
            # ============================================
            logger.info("\n" + "="*60)
            logger.info("STEP 3/3: Creating side-by-side comparison PDF")
            logger.info("="*60)
            
            self.reconstructor = PDFReconstructor(self.config)
            
            # Decide on batch processing
            if total_pages > pages_per_batch:
                logger.info(f"Large PDF detected ({total_pages} pages)")
                logger.info(f"Will process in batches of {pages_per_batch} pages")
                
                # Create output directory for batches
                output_path_obj = Path(output_path)
                if output_path_obj.suffix == '.pdf':
                    # User provided a filename, create directory next to it
                    batch_dir = output_path_obj.parent / f"{output_path_obj.stem}_batches"
                else:
                    # User provided a directory
                    batch_dir = output_path_obj
                
                # Process in batches
                batch_files = self.reconstructor.process_large_pdf_in_batches(
                    original_pdf_path=str(input_path),
                    pages=pages,
                    text_blocks=translated_blocks,
                    images=images,
                    output_dir=str(batch_dir),
                    pages_per_batch=pages_per_batch
                )
                
                if not batch_files:
                    logger.error("No batch files were created!")
                    return False
                
                # Merge batches if requested
                if merge_batches:
                    logger.info("\nMerging batch files...")
                    final_output = output_path if Path(output_path).suffix == '.pdf' else str(Path(output_path) / "translated_complete.pdf")
                    
                    self.reconstructor.merge_batch_pdfs(
                        batch_files=batch_files,
                        final_output_path=final_output
                    )
                    
                    logger.info(f"\n✓ Final merged PDF: {final_output}")
                    logger.info(f"✓ Batch files kept in: {batch_dir}")
                else:
                    logger.info(f"\n✓ Created {len(batch_files)} batch files")
                    logger.info(f"✓ Output directory: {batch_dir}")
                    for bf in batch_files:
                        logger.info(f"    - {Path(bf).name}")
            
            else:
                # Small PDF, process all at once
                logger.info(f"Processing all {total_pages} pages at once")
                
                # ВАЖНО: Всегда используем side-by-side режим
                self.reconstructor.create_side_by_side_pdf(
                    original_pdf_path=str(input_path),
                    pages=pages,
                    text_blocks=translated_blocks,
                    images=images,
                    output_path=output_path,
                    page_range=None  # Все страницы
                )
                
                # Get output file size
                output_size = Path(output_path).stat().st_size
                logger.info(f"\n✓ Translation complete!")
                logger.info(f"✓ Output: {output_path}")
                logger.info(f"✓ Size: {format_file_size(output_size)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Translation failed: {e}", exc_info=True)
            return False
    
    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        Get information about a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with PDF information
        """
        try:
            with PDFExtractor(pdf_path) as extractor:
                stats = extractor.get_statistics()
                metadata = extractor.get_metadata()
                return {
                    'statistics': stats,
                    'metadata': metadata
                }
        except Exception as e:
            logger.error(f"Failed to get PDF info: {e}")
            return {}


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='PDF Translator - Side-by-side translation with batch processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate small PDF (auto batch size)
  python main.py input.pdf -o output.pdf -t ru
  
  # Translate large PDF with custom batch size
  python main.py large_book.pdf -o translated/ -t ru --batch-pages 3
  
  # Don't merge batches (keep separate files)
  python main.py book.pdf -o output/ -t es --no-merge
  
  # Get PDF information
  python main.py input.pdf --info
  
Supported languages:
  en (English), ru (Russian), es (Spanish), fr (French), de (German),
  it (Italian), pt (Portuguese), zh (Chinese), ja (Japanese), ko (Korean),
  ar (Arabic), hi (Hindi), tr (Turkish), pl (Polish), and more...

Batch Processing:
  - PDFs with more than --batch-pages pages are split into batches
  - Each batch is processed and saved separately
  - By default, batches are merged into final PDF
  - Use --no-merge to keep batch files separate
        """
    )
    
    parser.add_argument('input', help='Input PDF file')
    parser.add_argument('-o', '--output', help='Output PDF file or directory')
    parser.add_argument('-s', '--source-lang', default='auto',
                       help='Source language code (default: auto-detect)')
    parser.add_argument('-t', '--target-lang', default='ru',
                       help='Target language code (default: ru)')
    parser.add_argument('--batch-pages', type=int, default=5,
                       help='Pages per batch for large PDFs (default: 5)')
    parser.add_argument('--no-merge', action='store_true',
                       help='Keep batch files separate (don\'t merge)')
    parser.add_argument('--mode', choices=['side-by-side', 'overlay'], default='side-by-side',
                       help='Output mode: side-by-side (оригинал|перевод) or overlay (только перевод)')
    parser.add_argument('--model', default='gpt-4.1-mini',
                       choices=['gpt-4.1-mini', 'gpt-4.1-nano', 'gemini-2.5-flash'],
                       help='Translation model to use (default: gpt-4.1-mini)')
    parser.add_argument('--no-images', action='store_true',
                       help='Do not include images in output')
    parser.add_argument('--no-font-adjust', action='store_true',
                       help='Do not adjust font size for translated text')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Text blocks to translate at once (default: 10)')
    parser.add_argument('--info', action='store_true',
                       help='Show PDF information and exit')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Show info and exit
    if args.info:
        app = PDFTranslatorApp(TranslatorConfig())
        info = app.get_pdf_info(args.input)
        
        if info:
            print("\n" + "="*60)
            print("PDF INFORMATION")
            print("="*60)
            
            print("\nMetadata:")
            for key, value in info['metadata'].items():
                if value:
                    print(f"  {key}: {value}")
            
            print("\nStatistics:")
            for key, value in info['statistics'].items():
                if key != 'font_list':
                    print(f"  {key}: {value}")
                else:
                    fonts = ', '.join(value[:10])
                    if len(value) > 10:
                        fonts += f" ... (+{len(value)-10} more)"
                    print(f"  {key}: {fonts}")
            
            # Estimate processing
            pages = info['statistics']['page_count']
            batch_size = args.batch_pages
            num_batches = (pages + batch_size - 1) // batch_size
            
            print(f"\nProcessing Estimate:")
            print(f"  Total pages: {pages}")
            print(f"  Batch size: {batch_size} pages")
            print(f"  Number of batches: {num_batches}")
            
            print("="*60 + "\n")
        
        return 0
    
    # Validate arguments
    if not args.output:
        parser.error("Output file is required (use -o/--output)")
    
    # Normalize language codes
    source_lang = get_language_code(args.source_lang)
    target_lang = get_language_code(args.target_lang)
    
    # Create configuration
    config = TranslatorConfig(
        source_language=source_lang,
        target_language=target_lang,
        translation_model=args.model,
        preserve_images=not args.no_images,
        adjust_font_size=not args.no_font_adjust,
        batch_size=args.batch_size
    )
    
    # Create application
    app = PDFTranslatorApp(config)
    
    # Print header
    print("\n" + "="*60)
    print("PDF TRANSLATOR - SIDE-BY-SIDE MODE")
    print("="*60)
    print(f"\nInput:  {args.input}")
    print(f"Output: {args.output}")
    print(f"Source language: {source_lang}")
    print(f"Target language: {target_lang}")
    print(f"Translation model: {args.model}")
    print(f"Batch size: {args.batch_pages} pages")
    print(f"Merge batches: {'Yes' if not args.no_merge else 'No'}")
    print()
    
    # Translate PDF
    success = app.translate_pdf(
        args.input,
        args.output,
        source_lang,
        target_lang,
        pages_per_batch=args.batch_pages,
        merge_batches=not args.no_merge
    )
    
    if success:
        print("\n" + "="*60)
        print("✓ TRANSLATION SUCCESSFUL!")
        print("="*60)
        print("\nYour translated PDF shows:")
        print("  • LEFT SIDE:  Original text (unchanged)")
        print("  • RIGHT SIDE: Translated text")
        print("\nThis makes it easy to compare and verify translations!")
        print("="*60 + "\n")
        return 0
    else:
        print("\n" + "="*60)
        print("✗ TRANSLATION FAILED")
        print("="*60)
        print("\nCheck the logs above for error details.")
        print("="*60 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())