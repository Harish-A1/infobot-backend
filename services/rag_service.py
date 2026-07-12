import asyncio
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CHROMA_DIR = Path(__file__).parent.parent / ".chroma"

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

_collection = None


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_or_create_collection(
            name="documents",
            embedding_function=DefaultEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + CHUNK_SIZE
        chunks.append(" ".join(words[start:end]))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if c.strip()]


def _file_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def index_documents() -> dict:
    collection = _get_collection()
    files = list(DATA_DIR.glob("*.pdf")) + list(DATA_DIR.glob("*.txt"))

    if not files:
        logger.info("No documents found in data/ folder.")
        return {"indexed": 0, "skipped": 0}

    indexed = 0
    skipped = 0

    for file_path in files:
        file_hash = _file_md5(file_path)
        sentinel_id = f"__sentinel__{file_path.name}"

        existing = collection.get(ids=[sentinel_id])
        if existing["ids"] and existing["metadatas"][0].get("hash") == file_hash:
            logger.info(f"Skipping unchanged file: {file_path.name}")
            skipped += 1
            continue

        try:
            collection.delete(where={"source": file_path.name})
        except Exception:
            pass
        try:
            collection.delete(ids=[sentinel_id])
        except Exception:
            pass

        text = _extract_text(file_path)
        chunks = _chunk_text(text)
        if not chunks:
            skipped += 1
            continue

        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            ids = [f"{file_path.name}__chunk_{i + j}" for j in range(len(batch))]
            metadatas = [{"source": file_path.name, "chunk_index": i + j} for j in range(len(batch))]
            collection.add(ids=ids, documents=batch, metadatas=metadatas)

        collection.add(
            ids=[sentinel_id],
            documents=[file_path.name],
            metadatas=[{"source": "__sentinel__", "hash": file_hash}],
        )

        indexed += 1
        logger.info(f"Indexed {file_path.name}: {len(chunks)} chunks")

    return {"indexed": indexed, "skipped": skipped}


async def index_documents_async() -> dict:
    return await asyncio.to_thread(index_documents)


def retrieve(query: str, top_k: int = 5) -> list[str]:
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, total),
            where={"source": {"$ne": "__sentinel__"}},
        )
        return results["documents"][0] if results["documents"] else []
    except Exception as e:
        logger.warning(f"RAG query failed: {e}")
        return []


async def retrieve_async(query: str, top_k: int = 5) -> list[str]:
    return await asyncio.to_thread(retrieve, query, top_k)
