import os
import sys
import logging

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.connection import SessionLocal, check_db_connection
from app.models.product import Product
from app.services.embedding_service import get_embedding_service, generate_product_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentx.generate_embeddings")


def generate_all_product_embeddings(force: bool = False):
    """Generate vector embeddings for all products in the database."""
    if not check_db_connection():
        logger.error("PostgreSQL database is currently unavailable. Please start PostgreSQL server before running embedding generation.")
        return

    session = SessionLocal()
    try:
        embedding_service = get_embedding_service()
        
        if force:
            products = session.query(Product).all()
        else:
            products = session.query(Product).filter(Product.embedding.is_(None)).all()

        logger.info(f"Found {len(products)} products requiring embedding generation.")

        updated_count = 0
        for product in products:
            product_text = generate_product_text(
                name=product.name,
                category=product.category,
                description=product.description,
                specifications=product.specifications,
                certifications=product.certifications
            )
            
            vector = embedding_service.generate_embedding(product_text)
            product.embedding = vector
            updated_count += 1
            logger.info(f"Generated embedding for Product [{product.sku}] '{product.name}' ({len(vector)} dims)")

        session.commit()
        logger.info(f"Successfully updated embeddings for {updated_count} products!")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to generate product embeddings: {str(e)}")
    finally:
        session.close()


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    generate_all_product_embeddings(force=force_flag)
