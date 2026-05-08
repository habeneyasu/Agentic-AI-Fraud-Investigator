#!/usr/bin/env python3
"""
Drop all database tables for Agentic AI Fraud Investigator.

⚠️  WARNING: This script will delete all data in the database!
Use only for development/testing purposes.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.logging import get_logger
from app.models import Base

logger = get_logger(__name__)


def drop_tables():
    """Drop all database tables."""
    try:
        logger.warning("Dropping all database tables...")
        
        # Create database engine
        engine = create_engine(
            settings.database_url,
            echo=settings.debug,
        )
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        
        logger.info("All tables dropped successfully")
        engine.dispose()
        
    except SQLAlchemyError as e:
        logger.error(f"Error dropping tables: {e}")
        raise


def main():
    """Main function to drop all tables."""
    try:
        print("⚠️  WARNING: This will delete ALL data in the database!")
        response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
        
        if response.lower() != 'yes':
            print("Operation cancelled.")
            return
        
        drop_tables()
        print("✅ All tables dropped successfully!")
        
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        print(f"❌ Failed to drop tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
