import os
import chromadb

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB_ROOT = os.path.join(_BASE_DIR, "database")
_COLLECTION_NAME = "chunks"


def _resolve_db_path(index_name: str, db_root: str | None = None) -> str:
	base = db_root if db_root else _DEFAULT_DB_ROOT
	return os.path.join(base, index_name)


def get_top1(
	prompt: str,
	index_name: str = "default",
	db_root: str | None = None,
	collection_name: str = _COLLECTION_NAME,
) -> dict:
	"""Retrieve the single most relevant record from a local Chroma index.

	Args:
		prompt: User query text.
		index_name: Index folder inside the database root.
		db_root: Optional custom database root. Defaults to material_collection/database.
		collection_name: Chroma collection name.

	Returns:
		A dictionary containing id, document, metadata, and distance for the top match.
	"""
	db_path = _resolve_db_path(index_name=index_name, db_root=db_root)
	if not os.path.isdir(db_path):
		raise FileNotFoundError(f"Local database path not found: {db_path}")

	client = chromadb.PersistentClient(path=db_path)
	collection = client.get_collection(name=collection_name)

	result = collection.query(
		query_texts=[prompt],
		n_results=1,
		include=["metadatas", "documents", "distances"],
	)

	ids = (result.get("ids") or [[]])[0]
	documents = (result.get("documents") or [[]])[0]
	metadatas = (result.get("metadatas") or [[]])[0]
	distances = (result.get("distances") or [[]])[0]

	if not ids:
		return {}

	return {
		"id": ids[0],
		"document": documents[0] if documents else "",
		"metadata": metadatas[0] if metadatas else {},
		"distance": distances[0] if distances else None,
	}


def fetch_all(
	index_name: str,
	db_root: str | None = None,
	collection_name: str = _COLLECTION_NAME,
	batch_size: int = 500,
) -> list[dict]:
	"""Fetch all records from a local Chroma index/collection.

	Args:
		index_name: Index folder inside the database root.
		db_root: Optional custom database root. Defaults to material_collection/database.
		collection_name: Chroma collection name.
		batch_size: Number of rows to fetch per call.

	Returns:
		List of dictionaries. Each item has id, document, and metadata.
	"""
	db_path = _resolve_db_path(index_name=index_name, db_root=db_root)
	if not os.path.isdir(db_path):
		raise FileNotFoundError(f"Local database path not found: {db_path}")

	client = chromadb.PersistentClient(path=db_path)
	collection = client.get_collection(name=collection_name)

	total = collection.count()
	rows: list[dict] = []

	for offset in range(0, total, batch_size):
		result = collection.get(
			include=["metadatas", "documents"],
			limit=batch_size,
			offset=offset,
		)
		ids = result.get("ids", []) or []
		documents = result.get("documents", []) or []
		metadatas = result.get("metadatas", []) or []

		for idx, item_id in enumerate(ids):
			rows.append(
				{
					"id": item_id,
					"document": documents[idx] if idx < len(documents) else "",
					"metadata": metadatas[idx] if idx < len(metadatas) else {},
				}
			)

	return rows

