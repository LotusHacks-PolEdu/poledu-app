import os
import shutil
import re
import time
import chromadb

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB_ROOT = os.path.join(_BASE_DIR, "database")
_COLLECTION_NAME = "chunks"


def _parse_chunks_file(chunks_file: str) -> list[dict]:
    """Parse the chunkz file into normalized chunk payloads."""
    with open(chunks_file, "r", encoding="utf-8") as f:
        content = f.read()

    parts = re.split(r'--- Chunk (\d+) \(Length: \d+ \| Page (\d+)\) ---', content)
    parsed_chunks = []
    for i in range(1, len(parts), 3):
        chunk_id = int(parts[i])
        page_num = int(parts[i + 1])
        chunk_text = parts[i + 2].strip()
        parsed_chunks.append(
            {
                "chunk_id": chunk_id,
                "page_label": page_num,
                "text": chunk_text,
            }
        )
    return parsed_chunks


def _resolve_db_path(index_name: str, db_root: str | None = None) -> str:
    base = db_root if db_root else _DEFAULT_DB_ROOT
    return os.path.join(base, index_name)


def _normalize_chunks(chunks_input) -> list[dict]:
    """Support legacy chunk file input and new in-memory chunk payloads."""
    if isinstance(chunks_input, str):
        return _parse_chunks_file(chunks_input)

    if isinstance(chunks_input, list):
        normalized = []
        for i, chunk in enumerate(chunks_input):
            if not isinstance(chunk, dict):
                continue
            text = str(chunk.get("text", "")).strip()
            if not text:
                continue
            normalized.append(
                {
                    "chunk_id": int(chunk.get("chunk_id", i)),
                    "page_label": chunk.get("page_label", "?"),
                    "text": text,
                }
            )
        return normalized

    raise TypeError("chunks_input must be a chunk file path (str) or list[dict].")


def store_chunks(chunks_input, index_name: str = "lecture3", db_root: str | None = None):
    """Store chunks in a local Chroma database.

    Args:
        chunks_input: Chunk file path (legacy) or list of chunk dicts.
        index_name: Namespace for this run (usually process_code).
        db_root: Optional root directory for local database folders.
    """
    chunks = _normalize_chunks(chunks_input)
    if not chunks:
        print("No chunks found to store.")
        return 0

    db_path = _resolve_db_path(index_name=index_name, db_root=db_root)
    os.makedirs(db_path, exist_ok=True)

    client = chromadb.PersistentClient(path=db_path)

    # Replace collection on re-run to avoid duplicate vectors for same process code.
    try:
        client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(name=_COLLECTION_NAME)

    texts = [chunk["text"] for chunk in chunks]

    ids = [f"chunk-{chunk['chunk_id']}" for chunk in chunks]
    metadatas = [
        {
            "chunk_id": chunk["chunk_id"],
            "page_label": chunk["page_label"],
            "text": chunk["text"],
            "project": index_name.capitalize(),
        }
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
    )

    print(f"Successfully stored {len(chunks)} chunks locally in {db_path}")
    return len(chunks)


def fetch_all_chunks_local(index_name: str, db_root: str | None = None, batch_size: int = 200) -> list[dict]:
    """Fetch all locally stored chunks for a process code in chunk_id order."""
    db_path = _resolve_db_path(index_name=index_name, db_root=db_root)
    if not os.path.isdir(db_path):
        raise FileNotFoundError(f"Local database path not found: {db_path}")

    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(_COLLECTION_NAME)

    total = collection.count()
    chunks = []
    for offset in range(0, total, batch_size):
        result = collection.get(
            include=["metadatas", "documents"],
            limit=batch_size,
            offset=offset,
        )
        metadatas = result.get("metadatas", []) or []
        documents = result.get("documents", []) or []
        for metadata, doc in zip(metadatas, documents):
            meta = metadata or {}
            chunks.append(
                {
                    "chunk_id": int(meta.get("chunk_id", 0)),
                    "page_label": meta.get("page_label", "?"),
                    "text": meta.get("text") or doc or "",
                }
            )

    chunks.sort(key=lambda x: x["chunk_id"])
    return chunks


def cleanup_expired_local_dbs(db_root: str | None = None, ttl_days: int = 1) -> list[str]:
    """Delete database/<process_code> folders older than ttl_days."""
    base = db_root if db_root else _DEFAULT_DB_ROOT
    os.makedirs(base, exist_ok=True)

    deleted_paths = []
    now = time.time()
    ttl_seconds = max(ttl_days, 0) * 24 * 60 * 60

    for child in os.listdir(base):
        candidate = os.path.join(base, child)
        if not os.path.isdir(candidate):
            continue
        age_seconds = now - os.path.getmtime(candidate)
        if age_seconds > ttl_seconds:
            shutil.rmtree(candidate, ignore_errors=True)
            deleted_paths.append(candidate)

    return deleted_paths


if __name__ == "__main__":
    # Default standalone usage
    default_chunks = r"C:\Users\ADMIN\Downloads\rag_project\rag_project\fact_check\chunkz.txt"
    store_chunks(default_chunks)