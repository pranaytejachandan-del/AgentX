import logging
import sys
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routes import health, procurement, discovery, negotiation, payments
from app.database.connection import check_db_connection
from app.exceptions.intent_exceptions import IntentParserException

from io import TextIOWrapper

# Configure structured logging with UTF-8 stream handler
stream_handler = logging.StreamHandler(sys.stdout)
if isinstance(sys.stdout, TextIOWrapper):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[stream_handler]
)

logger = logging.getLogger("agentx.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} Backend Services (LLM: {settings.LLM_PROVIDER}, Embedding: {settings.EMBEDDING_PROVIDER})...")
    db_status = "connected" if check_db_connection() else "disconnected/unavailable"
    logger.info(f"Database initial status: {db_status}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME} Backend Services...")


app = FastAPI(
    title="AgentX Orchestrator API",
    description="Autonomous B2B/B2C Purchasing & Negotiation Agents Core Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Intent Parser exception handler
@app.exception_handler(IntentParserException)
async def intent_parser_exception_handler(request: Request, exc: IntentParserException):
    logger.warning(f"IntentParserException on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )

# Global unhandled exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."}
    )

# Register routers
app.include_router(health.router)
app.include_router(procurement.router)
app.include_router(discovery.router)
app.include_router(negotiation.router)
app.include_router(payments.router)
