"""Read and normalize source data."""
from pathlib import Path
import re
import unicodedata
import pypdf
from .models import DocumentPage


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC), remove excessive whitespaces, and preserve structure."""
    if not text:
        return ""
    # Normalize to Unicode NFC
    normalized = unicodedata.normalize("NFC", text)
    # Replace non-breaking spaces and unusual whitespace
    normalized = normalized.replace("\xa0", " ").replace("\u200b", "")
    # Normalize multiple horizontal whitespaces
    normalized = re.sub(r"[ \t]+", " ", normalized)
    # Normalize multiple newlines (keep at most 2 newlines for paragraph breaks)
    normalized = re.sub(r"\n\s*\n+", "\n\n", normalized)
    return normalized.strip()


def determine_section(physical_page: int) -> str:
    """Determine the document section based on physical page number.
    
    Phần 1: Giới thiệu Học viện (Trang 4 - 11)
    Phần 2: Sự cần thiết mở ngành (Trang 12 - 41)
    Phần 3: Chương trình đào tạo (Trang 42 - 43)
    Phần 4: Năng lực cơ sở đào tạo (Trang 44 - 55)
    Phần 5: Kết luận và kiến nghị (Trang 56 - 57)
    """
    if 4 <= physical_page <= 11:
        return "phan_1"
    elif 12 <= physical_page <= 41:
        return "phan_2"
    elif 42 <= physical_page <= 43:
        return "phan_3"
    elif 44 <= physical_page <= 55:
        return "phan_4"
    elif 56 <= physical_page <= 57:
        return "phan_5"
    return "other"


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each content page; keep page number, source, and metadata.
    
    Pages 1 (Cover) and 2-3 (Table of contents) are skipped as per manifest rules.
    """
    reader = pypdf.PdfReader(str(path))
    pages: list[DocumentPage] = []
    
    for idx, page_obj in enumerate(reader.pages):
        physical_page = idx + 1
        # Skip cover and table of contents
        if physical_page < 4:
            continue
        
        raw_text = page_obj.extract_text() or ""
        norm_text = normalize_text(raw_text)
        
        if not norm_text:
            print(f"[Warning] Empty page extracted at physical page {physical_page}")
            continue
            
        sec = determine_section(physical_page)
        metadata = {
            "section": sec,
            "physical_page": physical_page,
            "printed_page": physical_page - 3,
            "char_count": len(norm_text)
        }
        
        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=physical_page,
                text=norm_text,
                metadata=metadata
            )
        )
        
    return pages
