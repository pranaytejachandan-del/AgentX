import math
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.config import settings

logger = logging.getLogger("agentx.embedding_service")

EMBEDDING_DIM = 1536


def generate_product_text(
    name: str,
    category: str,
    description: Optional[str] = None,
    specifications: Optional[Dict[str, Any]] = None,
    certifications: Optional[List[str]] = None
) -> str:
    """Construct composite textual representation of product for embedding generation."""
    parts = [f"Product: {name}", f"Category: {category}"]
    if description:
        parts.append(f"Description: {description}")
    if specifications:
        specs_str = ", ".join(f"{k}: {v}" for k, v in specifications.items())
        parts.append(f"Specifications: {specs_str}")
    if certifications:
        certs_str = ", ".join(certifications)
        parts.append(f"Certifications: {certs_str}")
    return " | ".join(parts)


class EmbeddingProvider(ABC):
    """Abstract Base Class for generating vector embeddings."""

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate a 1536-dimensional vector embedding for text."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic Mock Vector Generator for offline execution and testing."""

    def generate_embedding(self, text: str) -> List[float]:
        lowered = text.lower()
        # Seed vector using hash of text
        vec = [0.0] * EMBEDDING_DIM
        h = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        
        # Populate base pseudo-random components
        for i in range(EMBEDDING_DIM):
            val = math.sin(h + i * 0.1)
            vec[i] = val

        # Project key domain keywords onto specific embedding dimensions for semantic alignment
        keywords = {
            "chair": 10, "mesh": 20, "ergonomic": 30, "executive": 40,
            "desk": 50, "standing": 60, "table": 70, "cabinet": 80,
            "bifma": 90, "iso": 100, "leather": 110, "stool": 120,
            "acoustic": 130, "pod": 140, "furniture": 150,
            "laptop": 160, "electronics": 170, "16gb": 180, "ram": 190, "computer": 200
        }
        for kw, idx in keywords.items():
            if kw in lowered:
                vec[idx] += 5.0
                vec[idx + 1] += 3.0

        # Normalize vector to unit length (L2 norm = 1.0)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Text Embedding Provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("openai package is required for OpenAIEmbeddingProvider.")

    def generate_embedding(self, text: str) -> List[float]:
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {str(e)}. Falling back to MockEmbeddingProvider.")
            return MockEmbeddingProvider().generate_embedding(text)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini Text Embedding Provider."""

    def __init__(self, api_key: str, model: str = "models/text-embedding-004"):
        try:
            import google.generativeai as genai
            getattr(genai, "configure")(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("google-generativeai package is required for GeminiEmbeddingProvider.")

    def generate_embedding(self, text: str) -> List[float]:
        try:
            import google.generativeai as genai
            embed_fn = getattr(genai, "embed_content")
            res = embed_fn(
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            emb = res['embedding']
            # Resize if necessary to match 1536 dims
            if len(emb) < EMBEDDING_DIM:
                emb = emb + [0.0] * (EMBEDDING_DIM - len(emb))
            return emb[:EMBEDDING_DIM]
        except Exception as e:
            logger.error(f"Gemini embedding generation failed: {str(e)}. Falling back to MockEmbeddingProvider.")
            return MockEmbeddingProvider().generate_embedding(text)


def get_embedding_service() -> EmbeddingProvider:
    """Factory function returning configured EmbeddingProvider instance."""
    provider_type = settings.EMBEDDING_PROVIDER.lower()

    if provider_type == "openai" and settings.OPENAI_API_KEY:
        logger.info("Initializing OpenAIEmbeddingProvider")
        return OpenAIEmbeddingProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_EMBEDDING_MODEL)
    elif provider_type == "gemini" and settings.GEMINI_API_KEY:
        logger.info("Initializing GeminiEmbeddingProvider")
        return GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_EMBEDDING_MODEL)
    else:
        if provider_type not in ["mock", "test"]:
            logger.warning(f"API key missing for embedding provider '{provider_type}'. Using MockEmbeddingProvider fallback.")
        return MockEmbeddingProvider()
