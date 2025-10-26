"""Utility functions for PDF Translator."""

import logging
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


@dataclass
class BoundingBox:
    """Represents a bounding box with coordinates."""
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float:
        """Get width of bounding box."""
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        """Get height of bounding box."""
        return self.y1 - self.y0
    
    @property
    def area(self) -> float:
        """Get area of bounding box."""
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of bounding box."""
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        """Convert to tuple format."""
        return (self.x0, self.y0, self.x1, self.y1)
    
    @classmethod
    def from_tuple(cls, bbox: Tuple[float, float, float, float]) -> 'BoundingBox':
        """Create from tuple format."""
        return cls(bbox[0], bbox[1], bbox[2], bbox[3])
    
    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if this bounding box overlaps with another."""
        return not (self.x1 < other.x0 or self.x0 > other.x1 or 
                   self.y1 < other.y0 or self.y0 > other.y1)
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside bounding box."""
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1


@dataclass
class TextBlock:
    """Represents a text block extracted from PDF."""
    text: str
    bbox: BoundingBox
    font: str
    size: float
    color: Tuple[float, float, float]
    page: int
    translated_text: str = ""
    
    def __repr__(self) -> str:
        """String representation."""
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"TextBlock(page={self.page}, font={self.font}, size={self.size:.1f}, text='{preview}')"


@dataclass
class ImageBlock:
    """Represents an image extracted from PDF."""
    image_data: bytes
    bbox: BoundingBox
    page: int
    format: str
    xref: int  # Reference number in PDF
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ImageBlock(page={self.page}, format={self.format}, size={len(self.image_data)} bytes)"


@dataclass
class PageInfo:
    """Information about a PDF page."""
    page_number: int
    width: float
    height: float
    rotation: int = 0
    
    def __repr__(self) -> str:
        """String representation."""
        return f"PageInfo(page={self.page_number}, size={self.width:.1f}x{self.height:.1f}, rotation={self.rotation})"


def normalize_font_name(font_name: str) -> str:
    """Normalize font name by removing prefixes and suffixes."""
    # Remove common prefixes
    for prefix in ['ABCDEE+', 'BCDFEE+', 'CDFGHI+']:
        if font_name.startswith(prefix):
            font_name = font_name[len(prefix):]
    
    # Remove style suffixes for base font name
    base_name = font_name.split(',')[0].split('-')[0]
    
    return base_name


def estimate_text_width(text: str, font_size: float, avg_char_width: float = 0.5) -> float:
    """Estimate text width in points."""
    return len(text) * font_size * avg_char_width


def split_text_to_fit(text: str, max_width: float, font_size: float, 
                      avg_char_width: float = 0.5) -> List[str]:
    """Split text into multiple lines to fit within max width."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if estimate_text_width(test_line, font_size, avg_char_width) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Word is too long, add it anyway
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def rgb_to_float(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Convert RGB from 0-255 to 0-1 range."""
    return (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)


def float_to_rgb(rgb: Tuple[float, float, float]) -> Tuple[int, int, int]:
    """Convert RGB from 0-1 to 0-255 range."""
    return (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

