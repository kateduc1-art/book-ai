"""
Database initialization script.
Run this once to create all tables and enable pgvector extension.

Usage:
    python scripts/create_db.py
"""
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import init_db
from app.core.logging import get_logger

logger = get_logger("create_db")


def main():
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
