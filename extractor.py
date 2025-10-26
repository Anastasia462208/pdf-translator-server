"""PDF extraction module using PyMuPDF."""

import fitz  # PyMuPDF
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from utils import (
    TextBlock, ImageBlock, PageInfo, BoundingBox,
    get_logger, normalize_font_name
)


logger = get_logger(__name__)


class PDFExtractor:
    """Extracts text, images, and layout information from PDF files."""
    
    def __init__(self, pdf_path: str):
        """
        Initialize PDF extractor.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.doc = fitz.open(str(self.pdf_path))
        self.page_count = len(self.doc)
        logger.info(f"Opened PDF: {self.pdf_path.name} ({self.page_count} pages)")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def close(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            logger.info(f"Closed PDF: {self.pdf_path.name}")
    
    def get_page_info(self, page_num: int) -> PageInfo:
        """
        Get information about a specific page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            PageInfo object with page dimensions and properties
        """
        page = self.doc[page_num]
        rect = page.rect
        
        return PageInfo(
            page_number=page_num,
            width=rect.width,
            height=rect.height,
            rotation=page.rotation
        )
    
    def extract_text_blocks(self, page_num: int) -> List[TextBlock]:
        """
        Extract text blocks with formatting information from a page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            List of TextBlock objects
        """
        page = self.doc[page_num]
        text_blocks = []
        
        # Get text in dictionary format for detailed information
        text_dict = page.get_text("dict")
        
        # Process each block
        for block in text_dict.get("blocks", []):
            # Skip image blocks
            if block.get("type") != 0:
                continue
            
            # Process each line in the block
            for line in block.get("lines", []):
                line_text = ""
                line_bbox = None
                line_font = None
                line_size = None
                line_color = None
                
                # Process each span (text with same formatting)
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    if not span_text.strip():
                        continue
                    
                    line_text += span_text
                    
                    # Get formatting information from first span
                    if line_font is None:
                        line_font = normalize_font_name(span.get("font", "Arial"))
                        line_size = span.get("size", 12.0)
                        # Color is in RGB 0-1 range
                        color_int = span.get("color", 0)
                        line_color = self._int_to_rgb(color_int)
                    
                    # Expand bounding box
                    span_bbox = span.get("bbox")
                    if span_bbox:
                        if line_bbox is None:
                            line_bbox = list(span_bbox)
                        else:
                            line_bbox[0] = min(line_bbox[0], span_bbox[0])
                            line_bbox[1] = min(line_bbox[1], span_bbox[1])
                            line_bbox[2] = max(line_bbox[2], span_bbox[2])
                            line_bbox[3] = max(line_bbox[3], span_bbox[3])
                
                # Create text block if we have text
                if line_text.strip() and line_bbox:
                    text_block = TextBlock(
                        text=line_text,
                        bbox=BoundingBox.from_tuple(tuple(line_bbox)),
                        font=line_font or "Arial",
                        size=line_size or 12.0,
                        color=line_color or (0.0, 0.0, 0.0),
                        page=page_num
                    )
                    text_blocks.append(text_block)
        
        logger.info(f"Extracted {len(text_blocks)} text blocks from page {page_num}")
        return text_blocks
    
    def extract_images(self, page_num: int) -> List[ImageBlock]:
        """
        Extract images from a page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            List of ImageBlock objects
        """
        page = self.doc[page_num]
        image_blocks = []
        
        # Get list of images on the page
        image_list = page.get_images(full=True)
        
        for img_index, img_info in enumerate(image_list):
            try:
                xref = img_info[0]  # Image reference number
                
                # Get image bounding box
                # This is approximate - we need to find the actual position
                img_rects = page.get_image_rects(xref)
                if not img_rects:
                    continue
                
                # Use first rectangle (images can appear multiple times)
                img_rect = img_rects[0]
                
                # Extract image data
                base_image = self.doc.extract_image(xref)
                image_data = base_image["image"]
                image_format = base_image["ext"]
                
                image_block = ImageBlock(
                    image_data=image_data,
                    bbox=BoundingBox(
                        x0=img_rect.x0,
                        y0=img_rect.y0,
                        x1=img_rect.x1,
                        y1=img_rect.y1
                    ),
                    page=page_num,
                    format=image_format,
                    xref=xref
                )
                image_blocks.append(image_block)
                
            except Exception as e:
                logger.warning(f"Failed to extract image {img_index} from page {page_num}: {e}")
                continue
        
        logger.info(f"Extracted {len(image_blocks)} images from page {page_num}")
        return image_blocks
    
    def extract_all(self) -> Dict[str, any]:
        """
        Extract all content from the PDF.
        
        Returns:
            Dictionary containing:
                - pages: List of PageInfo objects
                - text_blocks: List of all TextBlock objects
                - images: List of all ImageBlock objects
        """
        logger.info(f"Starting full extraction of {self.pdf_path.name}")
        
        pages = []
        all_text_blocks = []
        all_images = []
        
        for page_num in range(self.page_count):
            # Get page info
            page_info = self.get_page_info(page_num)
            pages.append(page_info)
            
            # Extract text blocks
            text_blocks = self.extract_text_blocks(page_num)
            all_text_blocks.extend(text_blocks)
            
            # Extract images
            images = self.extract_images(page_num)
            all_images.extend(images)
        
        logger.info(f"Extraction complete: {len(all_text_blocks)} text blocks, "
                   f"{len(all_images)} images across {len(pages)} pages")
        
        return {
            'pages': pages,
            'text_blocks': all_text_blocks,
            'images': all_images,
            'metadata': self.get_metadata()
        }
    
    def get_metadata(self) -> Dict[str, any]:
        """
        Get PDF metadata.
        
        Returns:
            Dictionary with metadata
        """
        metadata = self.doc.metadata
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'page_count': self.page_count
        }
    
    def _int_to_rgb(self, color_int: int) -> Tuple[float, float, float]:
        """
        Convert integer color to RGB tuple (0-1 range).
        
        Args:
            color_int: Color as integer
            
        Returns:
            RGB tuple with values in 0-1 range
        """
        # Extract RGB components
        r = ((color_int >> 16) & 0xFF) / 255.0
        g = ((color_int >> 8) & 0xFF) / 255.0
        b = (color_int & 0xFF) / 255.0
        return (r, g, b)
    
    def get_fonts_used(self) -> Dict[str, int]:
        """
        Get list of fonts used in the document.
        
        Returns:
            Dictionary mapping font names to usage count
        """
        fonts = {}
        
        for page_num in range(self.page_count):
            text_blocks = self.extract_text_blocks(page_num)
            for block in text_blocks:
                font_name = block.font
                fonts[font_name] = fonts.get(font_name, 0) + 1
        
        return fonts
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about the PDF.
        
        Returns:
            Dictionary with various statistics
        """
        data = self.extract_all()
        
        total_chars = sum(len(block.text) for block in data['text_blocks'])
        total_words = sum(len(block.text.split()) for block in data['text_blocks'])
        
        fonts_used = {}
        for block in data['text_blocks']:
            fonts_used[block.font] = fonts_used.get(block.font, 0) + 1
        
        return {
            'page_count': len(data['pages']),
            'text_block_count': len(data['text_blocks']),
            'image_count': len(data['images']),
            'total_characters': total_chars,
            'total_words': total_words,
            'fonts_used': len(fonts_used),
            'font_list': list(fonts_used.keys())
        }


def test_extractor(pdf_path: str):
    """Test the PDF extractor with a sample file."""
    with PDFExtractor(pdf_path) as extractor:
        # Get statistics
        stats = extractor.get_statistics()
        print("\n=== PDF Statistics ===")
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # Extract first page
        print("\n=== First Page Text Blocks ===")
        text_blocks = extractor.extract_text_blocks(0)
        for i, block in enumerate(text_blocks[:5]):  # Show first 5
            print(f"\nBlock {i+1}:")
            print(f"  Text: {block.text[:100]}...")
            print(f"  Font: {block.font}, Size: {block.size}")
            print(f"  Position: ({block.bbox.x0:.1f}, {block.bbox.y0:.1f})")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_extractor(sys.argv[1])
    else:
        print("Usage: python extractor.py <pdf_file>")

