#!/usr/bin/env python3
"""
Create database tables for Agentic AI Fraud Investigator.

Uses SQLAlchemy ``Base.metadata.create_all`` (same models as the FastAPI ORM).
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Base

logger = get_logger(__name__)


def create_database():
    """Create database if it doesn't exist (PostgreSQL specific)."""
    try:
        db_url_parts = settings.database_url.rstrip("/").rsplit("/", 1)
        server_url = db_url_parts[0]
        db_name = db_url_parts[1] if len(db_url_parts) > 1 else "fraud_investigator"

        engine = create_engine(server_url)

        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            )

            if not result.fetchone():
                conn.execute(text("COMMIT"))
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.info(f"Database '{db_name}' already exists")

        engine.dispose()

    except SQLAlchemyError as e:
        logger.error(f"Error creating database: {e}")
        raise


def create_tables():
    """Create all ORM tables (indexes are declared on models)."""
    try:
        logger.info("Creating database tables...")
        engine = create_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
        )
        Base.metadata.create_all(bind=engine)
        tables = sorted(Base.metadata.tables.keys())
        logger.info(f"Successfully created/verified {len(tables)} tables: {', '.join(tables)}")
        engine.dispose()
        logger.info("Database setup completed successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error creating tables: {e}")
        raise


def verify_tables():
    """Verify that all expected ORM tables exist."""
    expected_tables = {
        "transactions",
        "kyc_profiles",
        "sanctions_watchlist",
        "country_risks",
        "alerts",
        "triage_assessments",
        "investigation_logs",
        "fraud_memory",
        "audit_trail",
    }
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            existing_tables = {row[0] for row in result}
        engine.dispose()

        missing_tables = expected_tables - existing_tables
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            return False
        logger.info("All tables verified successfully")
        return True

    except SQLAlchemyError as e:
        logger.error(f"Error verifying tables: {e}")
        return False


def main():
    """Main function to create database and tables."""
    try:
        logger.info("Starting database setup...")
        if "postgresql" in settings.database_url:
            create_database()
        create_tables()
        if verify_tables():
            logger.info("Database setup completed successfully!")
            print("✅ Database tables created successfully!")
        else:
            logger.error("Database setup verification failed!")
            print("❌ Database setup failed!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
