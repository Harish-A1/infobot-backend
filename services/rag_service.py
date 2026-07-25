import asyncio
import hashlib
import logging
import shutil
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CHROMA_DIR = Path(__file__).parent.parent / ".chroma"
VENDORED_MODEL_DIR = Path(__file__).parent.parent / "models" / "all-MiniLM-L6-v2" / "onnx"

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

DOCUMENTS_BASE_URL = "https://infobot-backend-k83x.onrender.com/documents"

# Maps each processed/*.txt file to the raw PDF in data/ it was derived from,
# so retrieved chunks can link back to the actual document users can open.
SOURCE_PDF = {
    "shameerpet_broucher.txt": "Shameerpet_Broucher.pdf",
    "lakeside_manor_booklet.txt": "Proof - Lake Side Manore Booklet.pdf",
}


def _document_link(processed_filename: str) -> str:
    pdf_name = SOURCE_PDF.get(processed_filename)
    return f"{DOCUMENTS_BASE_URL}/{quote(pdf_name)}" if pdf_name else ""


_collection = None


def _seed_embedding_model_cache() -> None:
    """Pre-populate chromadb's ONNX embedding model cache from the vendored copy in
    models/, so it never has to fetch it from chroma-onnx-models.s3.amazonaws.com
    at runtime (that download otherwise repeats on every cold start)."""
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

    target_dir = Path(ONNXMiniLM_L6_V2.DOWNLOAD_PATH) / ONNXMiniLM_L6_V2.EXTRACTED_FOLDER_NAME
    if not VENDORED_MODEL_DIR.is_dir():
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    for src in VENDORED_MODEL_DIR.iterdir():
        dest = target_dir / src.name
        if not dest.exists():
            shutil.copy2(src, dest)
    logger.info(f"Seeded embedding model cache from {VENDORED_MODEL_DIR} into {target_dir}")


def _get_collection():
    global _collection
    if _collection is None:
        _seed_embedding_model_cache()
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


def _prune_stale_sources(collection, current_names: set[str]) -> None:
    existing = collection.get()
    stale_sources = {
        m.get("source") for m in existing["metadatas"]
        if m.get("source") not in current_names and m.get("source") != "__sentinel__"
    }
    for source in stale_sources:
        collection.delete(where={"source": source})
        collection.delete(ids=[f"__sentinel__{source}"])
        logger.info(f"Pruned stale indexed file no longer in data/processed/: {source}")


def index_documents() -> dict:
    collection = _get_collection()
    files = list(PROCESSED_DIR.glob("*.txt"))

    _prune_stale_sources(collection, {f.name for f in files})

    if not files:
        logger.info("No documents found in data/processed/ folder.")
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

        text = file_path.read_text(encoding="utf-8", errors="ignore")
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


def retrieve(query: str, top_k: int = 5) -> list[dict]:
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
        if not results["documents"]:
            return []
        return [
            {
                "text": doc,
                "source": SOURCE_PDF.get(meta.get("source", ""), meta.get("source", "")),
                "link": _document_link(meta.get("source", "")),
            }
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ]
    except Exception as e:
        logger.warning(f"RAG query failed: {e}")
        return []


async def retrieve_async(query: str, top_k: int = 5) -> list[dict]:
    return await asyncio.to_thread(retrieve, query, top_k)


def format_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        header = f"[Source: {c['source']}"
        header += f" | link: {c['link']}]" if c["link"] else "]"
        parts.append(f"{header}\n{c['text']}")
    return "\n\n---\n\n".join(parts)
