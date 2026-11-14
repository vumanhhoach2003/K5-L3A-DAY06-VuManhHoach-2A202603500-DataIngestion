"""Implement fixed-size and structure-aware chunking."""
import re
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split text into overlapping windows of fixed character length while preserving metadata."""
    text = page.text
    step = size - overlap
    if step <= 0:
        raise ValueError("size must be strictly greater than overlap")
    
    chunks: list[Chunk] = []
    chunk_idx = 0
    start = 0
    n = len(text)
    
    if n == 0:
        return []
    
    while start < n:
        end = min(start + size, n)
        chunk_text = text[start:end].strip()
        
        if chunk_text:
            c_id = f"{page.document_id}_p{page.page}_fix{chunk_idx:03d}"
            chunks.append(
                Chunk(
                    chunk_id=c_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata=dict(page.metadata)
                )
            )
            chunk_idx += 1
            
        if end >= n:
            break
        start += step
        
    return chunks


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    """Group paragraphs together without exceeding max_size, keeping cohesive units.
    
    Filters out isolated single-number page headers and merges short fragments.
    """
    text = page.text
    raw_paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    
    # Filter out standalone page numbers at top of page (e.g. '1', '2', '43')
    filtered_paras = []
    for idx, p in enumerate(raw_paras):
        if idx == 0 and p.isdigit() and len(p) <= 3:
            continue
        filtered_paras.append(p)
        
    if not filtered_paras:
        filtered_paras = [p.strip() for p in text.split("\n") if p.strip()]
        
    chunks: list[Chunk] = []
    chunk_idx = 0
    current_para_group: list[str] = []
    current_len = 0
    
    for para in filtered_paras:
        para_len = len(para)
        # If a single paragraph is abnormally large, split it into sentences
        if para_len > max_size:
            if current_para_group:
                c_text = "\n\n".join(current_para_group).strip()
                if c_text:
                    c_id = f"{page.document_id}_p{page.page}_para{chunk_idx:03d}"
                    chunks.append(
                        Chunk(
                            chunk_id=c_id,
                            document_id=page.document_id,
                            source=page.source,
                            page=page.page,
                            text=c_text,
                            metadata=dict(page.metadata)
                        )
                    )
                    chunk_idx += 1
                current_para_group = []
                current_len = 0
            
            sentences = re.split(r"(?<=[.!?])\s+", para)
            sent_buffer: list[str] = []
            sent_len = 0
            for sent in sentences:
                if sent_len + len(sent) + 1 > max_size and sent_buffer:
                    c_text = " ".join(sent_buffer).strip()
                    c_id = f"{page.document_id}_p{page.page}_para{chunk_idx:03d}"
                    chunks.append(
                        Chunk(
                            chunk_id=c_id,
                            document_id=page.document_id,
                            source=page.source,
                            page=page.page,
                            text=c_text,
                            metadata=dict(page.metadata)
                        )
                    )
                    chunk_idx += 1
                    sent_buffer = [sent]
                    sent_len = len(sent)
                else:
                    sent_buffer.append(sent)
                    sent_len += len(sent) + 1
            if sent_buffer:
                c_text = " ".join(sent_buffer).strip()
                c_id = f"{page.document_id}_p{page.page}_para{chunk_idx:03d}"
                chunks.append(
                    Chunk(
                        chunk_id=c_id,
                        document_id=page.document_id,
                        source=page.source,
                        page=page.page,
                        text=c_text,
                        metadata=dict(page.metadata)
                    )
                )
                chunk_idx += 1
            continue
            
        # Check if adding this paragraph exceeds max_size
        if current_len + para_len + 2 > max_size and current_para_group:
            c_text = "\n\n".join(current_para_group).strip()
            if c_text:
                c_id = f"{page.document_id}_p{page.page}_para{chunk_idx:03d}"
                chunks.append(
                    Chunk(
                        chunk_id=c_id,
                        document_id=page.document_id,
                        source=page.source,
                        page=page.page,
                        text=c_text,
                        metadata=dict(page.metadata)
                    )
                )
                chunk_idx += 1
            current_para_group = [para]
            current_len = para_len
        else:
            current_para_group.append(para)
            current_len += para_len + 2
            
    # Flush remaining
    if current_para_group:
        c_text = "\n\n".join(current_para_group).strip()
        if c_text:
            c_id = f"{page.document_id}_p{page.page}_para{chunk_idx:03d}"
            chunks.append(
                Chunk(
                    chunk_id=c_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=c_text,
                    metadata=dict(page.metadata)
                )
            )
            chunk_idx += 1
            
    return chunks
