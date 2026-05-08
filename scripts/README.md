# Database Scripts

This directory contains scripts for managing the Agentic AI Fraud Investigator database.

## Scripts

### `create_tables.py`
Creates all necessary database tables for the fraud investigation system.

**Usage:**
```bash
python scripts/create_tables.py
```

**Features:**
- Creates database if it doesn't exist (PostgreSQL)
- Creates all tables with proper relationships
- Adds performance indexes
- Verifies table creation
- Comprehensive logging

### `drop_tables.py`
Drops all database tables. ⚠️ **WARNING: Deletes all data!**

**Usage:**
```bash
python scripts/drop_tables.py
```

**Safety:**
- Requires explicit confirmation
- Only for development/testing purposes

## Database Schema

The system uses the following tables:

### Core Tables
- **`alerts`** - Fraud alerts from various sources
- **`cases`** - Investigation cases created from alerts
- **`investigations`** - Detailed investigation records
- **`evidence`** - Evidence collected for investigations
- **`audit_logs`** - System activity audit trail

### Key Features
- **Timestamp tracking** on all records
- **JSON fields** for flexible data storage
- **Proper relationships** with foreign keys
- **Performance indexes** for common queries
- **Audit logging** for compliance

## Environment Setup

Make sure your `.env` file has the correct database configuration:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/fraud_investigator
DEBUG=false
```

## Running Scripts

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up database:**
   ```bash
   python scripts/create_tables.py
   ```

3. **Verify installation:**
   ```bash
   python -c "from app.models import Base; print('Models imported successfully')"
   ```

## Troubleshooting

### Connection Issues
- Check PostgreSQL is running
- Verify DATABASE_URL in `.env`
- Ensure database user has proper permissions

### Permission Errors
- Make scripts executable: `chmod +x scripts/*.py`
- Run with appropriate user permissions

### Table Creation Errors
- Check database connection
- Verify PostgreSQL version compatibility
- Review error logs for specific issues
