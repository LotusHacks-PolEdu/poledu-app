import asyncio
import os
import json
import re
from llama_parse import LlamaParse

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _semantic_split_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Split text into sentence-aware chunks with light overlap for retrieval continuity."""
    cleaned = _normalize_whitespace(text)
    if not cleaned:
        return []

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if not sentences:
        return [cleaned]

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(sentence), chunk_size):
                piece = sentence[start:start + chunk_size].strip()
                if piece:
                    chunks.append(piece)
            continue

        if not current:
            current = sentence
            continue

        candidate = f"{current} {sentence}"
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current.strip())
            if overlap > 0 and len(current) > overlap:
                current = f"{current[-overlap:].strip()} {sentence}".strip()
            else:
                current = sentence

    if current.strip():
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


async def parse_pdf(pdf_path: str, chunk_size: int = 1200, overlap: int = 150) -> list[dict]:
    """Parse a PDF file and return semantically chunked text payloads.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of chunk dicts with chunk_id, page_label, and text.
    """
    # Load API key from credentials.json
    creds_path = os.path.join(_BASE_DIR, "credentials.json")
    with open(creds_path, "r", encoding="utf-8") as f:
        creds = json.load(f)

    parser = LlamaParse(
        api_key=creds["llama_parse"],
        result_type="markdown",
        split_by_page=True,
        verbose=True,
    )

    documents = await parser.aload_data(pdf_path)

    chunks: list[dict] = []
    chunk_id = 0
    for page_index, page in enumerate(documents, start=1):
        page_text = page.text if hasattr(page, "text") else str(page)
        for chunk_text in _semantic_split_text(page_text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "page_label": page_index,
                    "text": chunk_text,
                }
            )
            chunk_id += 1

    return chunks


if __name__ == "__main__":
    result = asyncio.run(parse_pdf("sample.pdf"))
    print(f"Parsed into {len(result)} semantic chunks")
