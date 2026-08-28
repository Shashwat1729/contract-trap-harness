"""
Ingest — production: PDF/DOCX -> page-preserving text.

Contract redlining requires native .docx tracked changes in Harbor,
but for harness eval we operate on text with page:line provenance.
This module preserves provenance without hallucination.
"""
from __future__ import annotations

import io
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Page:
    num: int
    text: str
    start: int  # char offset in full text
    end: int


def extract_text_with_pages(path: str | Path, chars_per_page: int = 2500) -> tuple[str, list[Page]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return _from_pdf(p)
    if suffix in (".docx", ".doc"):
        return _from_docx(p)
    # fallback plain text
    text = p.read_text(encoding="utf-8", errors="ignore")
    return _paginate(text, chars_per_page)


def _from_pdf(p: Path) -> tuple[str, list[Page]]:
    from pypdf import PdfReader
    reader = PdfReader(str(p))
    pages: list[Page] = []
    full = []
    offset = 0
    for i, page in enumerate(reader.pages, start=1):
        t = page.extract_text() or ""
        # Normalize: keep newlines, collapse form feeds
        t = t.replace("\x0c", "\n")
        if not t.endswith("\n"):
            t += "\n"
        pages.append(Page(num=i, text=t, start=offset, end=offset + len(t)))
        full.append(t)
        offset += len(t)
    return "".join(full), pages


def _from_docx(p: Path) -> tuple[str, list[Page]]:
    from docx import Document
    doc = Document(str(p))
    # Reconstruct text paragraph by paragraph, preserving page breaks approx.
    # python-docx has no real pagination; we paginate by chars_per_page as proxy
    # but we add w:pageBreak handling if present in XML.
    parts: list[str] = []
    for para in doc.paragraphs:
        t = para.text
        # Detect page break in paragraph XML
        if para._element is not None:
            # If <w:br w:type="page"/> present, treat as page boundary
            xml = para._element.xml
            if 'w:type="page"' in xml:
                parts.append("\n---PAGE_BREAK---\n")
        parts.append(t + "\n")
    # Tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(c.text for c in row.cells)
            parts.append(row_text + "\n")
    text = "".join(parts)
    return _paginate(text, chars_per_page=2500)


def _paginate(text: str, chars_per_page: int = 2500) -> tuple[str, list[Page]]:
    pages: list[Page] = []
    for i in range(0, len(text), chars_per_page):
        num = i // chars_per_page + 1
        chunk = text[i: i + chars_per_page]
        pages.append(Page(num=num, text=chunk, start=i, end=i + len(chunk)))
    if not pages:
        pages.append(Page(num=1, text=text, start=0, end=len(text)))
    return text, pages


def offset_to_page_line(offset: int, pages: list[Page], full_text: str) -> tuple[int, int]:
    for pg in pages:
        if pg.start <= offset < pg.end:
            line = full_text[pg.start:offset].count("\n") + 1
            return pg.num, line
    return pages[-1].num if pages else 1, 1
