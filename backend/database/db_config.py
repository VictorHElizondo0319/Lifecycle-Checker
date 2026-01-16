"""
Database Configuration and Connection
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError
import os
from dotenv import load_dotenv
import pymysql

load_dotenv()

# Database connection configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'lifecycle_checker')
DB_CHARSET = os.getenv('DB_CHARSET', 'utf8mb4')

# Base URL without database name (for creating database)
BASE_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}?charset={DB_CHARSET}"

# Construct database URL with database name
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={DB_CHARSET}"


def create_database_if_not_exists():
    """
    Create the database if it doesn't exist.
    Returns True if successful, False if connection failed (non-critical).
    """
    try:
        # Connect without specifying database
        temp_engine = create_engine(
            BASE_DATABASE_URL,
            connect_args={'connect_timeout': 5}  # Reduced timeout for faster failure
        )
        
        with temp_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(f"SHOW DATABASES LIKE '{DB_NAME}'"))
            if result.fetchone() is None:
                # Create database
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
                print(f"Database '{DB_NAME}' created successfully!")
            else:
                print(f"Database '{DB_NAME}' already exists.")
        
        temp_engine.dispose()
        return True
    except OperationalError as e:
        print(f"Warning: Could not connect to MySQL server at {DB_HOST}:{DB_PORT}")
        print(f"Please ensure MySQL is running and credentials in .env are correct.")
        print(f"Error: {e}")
        # Don't raise - allow app to continue without database
        return False
    except Exception as e:
        print(f"Error creating database: {e}")
        import traceback
        print(traceback.format_exc())
        # Don't raise - allow app to continue without database
        return False


# Create engine with connection pooling (will be initialized after database is created)
engine = None

# Create session factory (will be initialized after engine is created)
SessionLocal = None


def get_db_session():
    """
    Get a database session.
    Use in a context manager or ensure to close it:
    
    with get_db_session() as session:
        # Use session
        pass
    """
    if SessionLocal is None:
        # Try to initialize if not already initialized
        if engine is None:
            result = init_db()
            if not result:
                raise RuntimeError(
                    "Database not initialized. "
                    "Please check MySQL server is running and database credentials in .env are correct."
                )
        else:
            raise RuntimeError("Database session factory not initialized. Call init_db() first.")
    return SessionLocal()


def init_db():
    """
    Initialize database - create database and all tables if they don't exist.
    Automatically creates database and tables on first run.
    Returns True if successful, False if initialization failed (non-critical).
    This function is idempotent - safe to call multiple times.
    """
    global engine, SessionLocal
    
    # If already initialized, just verify connection
    if engine is not None and SessionLocal is not None:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            # Connection lost, reset and reinitialize
            engine = None
            SessionLocal = None
    
    try:
        # Step 1: Create database if it doesn't exist
        print(f"Connecting to MySQL server at {DB_HOST}:{DB_PORT}...")
        db_created = create_database_if_not_exists()
        if not db_created:
            print("Skipping database initialization - MySQL server not available.")
            return False
        
        # Step 2: Create engine with connection pooling
        try:
            print(f"Creating database engine for database '{DB_NAME}'...")
            engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before using
                echo=False,  # Set to True for SQL query logging
                connect_args={
                    'charset': DB_CHARSET,
                    'connect_timeout': 5  # Reduced timeout
                }
            )
            
            # Test the connection
            print("Testing database connection...")
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[OK] Database connection successful!")
            
            # Update SessionLocal to use the new engine
            SessionLocal = scoped_session(sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            ))
        except OperationalError as e:
            print(f"[ERROR] Warning: Could not connect to database '{DB_NAME}' at {DB_HOST}:{DB_PORT}")
            print(f"  Error: {e}")
            print("  Database features will be unavailable.")
            print("  Please check:")
            print(f"    - MySQL server is running")
            print(f"    - Database credentials in .env are correct")
            print(f"    - Database '{DB_NAME}' exists")
            engine = None
            SessionLocal = None
            return False
        
        # Step 3: Create all tables if they don't exist
        if engine is not None:
            print("Creating database tables if they don't exist...")
            from .models import Base
            Base.metadata.create_all(bind=engine)
            print("[OK] Database and tables initialized successfully!")
            return True
        else:
            return False
        
    except ImportError as e:
        print(f"[ERROR] Warning: Could not import database models: {e}")
        print("  Database features will be unavailable.")
        return False
    except Exception as e:
        import traceback
        print(f"[ERROR] Error initializing database: {e}")
        print(traceback.format_exc())
        print("  Database features will be unavailable.")
        engine = None
        SessionLocal = None
        return False


def close_db():
    """
    Close database connections.
    """
    global SessionLocal, engine
    if SessionLocal is not None:
        SessionLocal.remove()
    if engine is not None:
        engine.dispose()

