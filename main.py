import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from services.rag_service import index_documents_async
        result = await index_documents_async()
        logger.info(f"Startup document indexing: {result}")
    except Exception as e:
        logger.warning(f"Startup document indexing failed (non-fatal): {e}")
    yield


app = FastAPI(title="Scube AI Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/")
async def root():
    return {"message": "Scube AI Backend is running"}
