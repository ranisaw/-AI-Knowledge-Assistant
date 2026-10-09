"""
Document Ingestion & Chunking Pipeline for AI Knowledge Assistant.
Supports:
- Markdown (.md)
- PDF (.pdf) via pypdf
- Word (.docx) via python-docx
- CSV (.csv) via csv/pandas

Normalizes text, strips noise, executes semantic chunking, and produces chunks.json.
"""
import os
import json
import csv
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.config import settings
from core.security import redact_pii


class DocumentParser:
    """Multi-format document reader and text extractor."""

    @staticmethod
    def parse_markdown(path: Path) -> str:
        """Parse markdown file."""
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def parse_docx(path: Path) -> str:
        """Extract text from Microsoft Word .docx files."""
        try:
            from docx import Document
            doc = Document(path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        full_text.append(row_text)
            return "\n\n".join(full_text)
        except Exception as e:
            # Fallback if python-docx fails or format is alternate
            try:
                txt_fallback = path.with_suffix(".txt")
                if txt_fallback.exists():
                    return txt_fallback.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
            return f"[Error parsing DOCX {path.name}: {str(e)}]"

    @staticmethod
    def parse_pdf(path: Path) -> str:
        """Extract text from PDF documents using pypdf."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pages_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages_text.append(text.strip())
            if pages_text:
                return "\n\n".join(pages_text)
        except Exception:
            pass

        # Native fallback: scan for standard PDF text streams
        try:
            content = path.read_bytes()
            extracted = []
            matches = re.findall(rb'\((.*?)\)\s*Tj', content)
            for m in matches:
                try:
                    decoded = m.decode("latin-1", errors="ignore").replace("\\(", "(").replace("\\)", ")")
                    if decoded.strip():
                        extracted.append(decoded.strip())
                except Exception:
                    continue
            if extracted:
                return "\n".join(extracted)
        except Exception as e:
            return f"[Error reading PDF {path.name}: {str(e)}]"

        return ""

    @staticmethod
    def parse_csv(path: Path) -> str:
        """Extract structured textual representations of CSV rows."""
        chunks = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for idx, row in enumerate(reader):
                    items = [f"{k}: {v}" for k, v in row.items() if v]
                    chunks.append(f"Row {idx + 1} -> " + " | ".join(items))
            return "\n\n".join(chunks)
        except Exception as e:
            return f"[Error parsing CSV {path.name}: {str(e)}]"


def clean_text(raw_text: str) -> str:
    """Normalize whitespace, remove control chars, and clean formatting."""
    if not raw_text:
        return ""
    # Normalize line endings
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip non-printable ascii characters (keep newlines and tabs)
    text = re.sub(r'[^\x20-\x7E\n\t]', ' ', text)
    # Strip trailing whitespace on each line
    lines = [line.strip() for line in text.split("\n")]
    cleaned = "\n".join(lines).strip()
    return cleaned


def chunk_text(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 100
) -> List[str]:
    """
    Split text into semantic chunks respecting paragraphs, headings, and sentences.
    """
    if len(text) <= chunk_size:
        return [text] if text else []

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If single paragraph exceeds chunk size, split by sentences
        if len(para) > chunk_size:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                    current_chunk = (current_chunk + " " + sentence).strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    # Start new chunk with overlap if possible
                    if len(current_chunk) > chunk_overlap:
                        overlap_seed = current_chunk[-chunk_overlap:].strip()
                        current_chunk = (overlap_seed + " " + sentence).strip()
                    else:
                        current_chunk = sentence
        else:
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(current_chunk) > chunk_overlap:
                    overlap_seed = current_chunk[-chunk_overlap:].strip()
                    current_chunk = (overlap_seed + "\n\n" + para).strip()
                else:
                    current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def load_metadata_for_file(file_path: Path) -> Dict[str, Any]:
    """Load metadata sidecar (.meta.json) if present."""
    meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
    if not meta_path.exists():
        meta_path = file_path.with_name(f"{file_path.stem}.meta.json")
    
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Default metadata based on filename
    title = file_path.stem.replace("_", " ").title()
    return {
        "title": title,
        "tags": [file_path.suffix.lstrip(".").lower()],
        "type": "document",
        "date": "2026-01-01",
        "author": "System",
        "classification": "Internal"
    }


def ingest_documents(
    raw_dir: Optional[Path] = None,
    output_file: Optional[Path] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Ingest all documents from raw directory, extract text, split into chunks,
    and save to chunks.json.
    """
    source_dir = raw_dir or settings.raw_data_dir
    dest_file = output_file or settings.chunks_file
    c_size = chunk_size or settings.chunk_size
    c_overlap = chunk_overlap or settings.chunk_overlap

    if not source_dir.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {source_dir}")

    all_chunks: List[Dict[str, Any]] = []
    supported_extensions = {".md", ".pdf", ".docx", ".csv"}
    
    files = [p for p in source_dir.iterdir() if p.suffix.lower() in supported_extensions and not p.name.endswith(".meta.json")]

    for file_path in sorted(files, key=lambda x: x.name):
        ext = file_path.suffix.lower()
        if ext == ".md":
            raw_text = DocumentParser.parse_markdown(file_path)
        elif ext == ".pdf":
            raw_text = DocumentParser.parse_pdf(file_path)
        elif ext == ".docx":
            raw_text = DocumentParser.parse_docx(file_path)
        elif ext == ".csv":
            raw_text = DocumentParser.parse_csv(file_path)
        else:
            continue

        cleaned = clean_text(raw_text)
        if not cleaned:
            continue

        # Optional PII redaction during ingestion
        sanitized_text, _ = redact_pii(cleaned)

        metadata = load_metadata_for_file(file_path)
        doc_chunks = chunk_text(sanitized_text, chunk_size=c_size, chunk_overlap=c_overlap)

        file_hash = hashlib.md5(file_path.name.encode()).hexdigest()[:8]

        for idx, chunk in enumerate(doc_chunks):
            chunk_id = f"{file_hash}_{idx:03d}"
            record = {
                "id": chunk_id,
                "text": chunk,
                "source": file_path.name,
                "title": metadata.get("title", file_path.stem),
                "doc_type": metadata.get("type", "document"),
                "tags": metadata.get("tags", []),
                "chunk_index": idx,
                "total_chunks": len(doc_chunks),
                "date": metadata.get("date", ""),
                "author": metadata.get("author", "Unknown"),
                "token_estimate": len(chunk.split())
            }
            all_chunks.append(record)

    # Save to chunks.json
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"Ingested {len(files)} files into {len(all_chunks)} chunks -> {dest_file}")
    return all_chunks


if __name__ == "__main__":
    ingest_documents()
