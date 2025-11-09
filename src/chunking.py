# src/chunking.py
import re
from typing import List

def chunk_markdown(md: str, chunk_size: int = 2000, overlap: int = 300) -> List[str]:
    """
    Paragraph-aware recursive splitter without external deps.
    - First split on blank lines to respect paragraphs/sections.
    - If a piece is too big, hard-split with overlap.
    """
    text = md.strip()
    if not text:
        return []

    parts = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    buf = ""

    def flush_buffer():
        nonlocal buf
        if buf:
            chunks.append(buf)
            if overlap > 0 and len(buf) > overlap:
                buf = buf[-overlap:]
            else:
                buf = ""

    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 2 <= chunk_size:
            buf = (buf + ("\n\n" if buf else "") + p)
        else:
            flush_buffer()
            # If this paragraph itself is huge, hard-split with overlap windows
            i = 0
            while i < len(p):
                end = i + chunk_size
                seg = p[i:end]
                chunks.append(seg)
                if end >= len(p):
                    buf = ""
                else:
                    # back up by overlap for the next window
                    i = end - overlap
                i = max(i, end)
    flush_buffer()
    return chunks
