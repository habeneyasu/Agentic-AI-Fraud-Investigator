#!/usr/bin/env python3
"""
Create database tables for Agentic AI Fraud Investigator.

This script creates all necessary database tables for the fraud investigation system.
"""

import sys
import os
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
        # Connect to PostgreSQL server (without specifying database)
        db_url_parts = settings.database_url.rstrip('/').rsplit('/', 1)
        server_url = db_url_parts[0]
        db_name = db_url_parts[1] if len(db_url_parts) > 1 else 'fraud_investigator'
        
        engine = create_engine(server_url)
        
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            )
            
            if not result.fetchone():
                # Create database
                conn.execute(text("COMMIT"))  # End any transaction
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.info(f"Database '{db_name}' already exists")
                
        engine.dispose()
        
    except SQLAlchemyError as e:
        logger.error(f"Error creating database: {e}")
        raise


def create_tables():
    """Create all database tables."""
    try:
        logger.info("Creating database tables...")
        
        # Create database engine
        engine = create_engine(
            settings.database_url,
            echo=settings.debug,  # Log SQL statements in debug mode
            pool_pre_ping=True,   # Verify connections before use
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Log created tables
        tables = Base.metadata.tables.keys()
        logger.info(f"Successfully created {len(tables)} tables: {', '.join(tables)}")
        
        # Create indexes for performance
        create_indexes(engine)
        
        engine.dispose()
        logger.info("Database setup completed successfully")
        
    except SQLAlchemyError as e:
        logger.error(f"Error creating tables: {e}")
        raise


def create_indexes(engine):
    """Create additional indexes for performance optimization."""
    try:
        with engine.connect() as conn:
            # Alert indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_alerts_status_type ON alerts(status, alert_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_alerts_priority ON alerts(priority_score DESC)"))
            
            # Case indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cases_status_priority ON cases(status, priority)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cases_assigned_to ON cases(assigned_to)"))
            
            # Investigation indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_investigations_assigned_to ON investigations(assigned_to)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_investigations_case_id ON investigations(case_id)"))
            
            # Evidence indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON evidence(case_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence(evidence_type)"))
            
            # Audit log indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)"))
            
            logger.info("Performance indexes created successfully")
            
    except SQLAlchemyError as e:
        logger.warning(f"Error creating indexes: {e}")


def verify_tables():
    """Verify that all tables were created successfully."""
    try:
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # Check if all expected tables exist
            expected_tables = {
                'alerts', 'cases', 'investigations', 
                'evidence', 'audit_logs'
            }
            
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ))
            existing_tables = {row[0] for row in result}
            
            missing_tables = expected_tables - existing_tables
            
            if missing_tables:
                logger.error(f"Missing tables: {missing_tables}")
                return False
            else:
                logger.info("All tables verified successfully")
                return True
                
        engine.dispose()
        
    except SQLAlchemyError as e:
        logger.error(f"Error verifying tables: {e}")
        return False


def main():
    """Main function to create database and tables."""
    try:
        logger.info("Starting database setup...")
        
        # Create database (PostgreSQL specific)
        if "postgresql" in settings.database_url:
            create_database()
        
        # Create tables
        create_tables()
        
        # Verify tables
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
