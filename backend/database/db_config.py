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
    """
    try:
        # Connect without specifying database
        temp_engine = create_engine(
            BASE_DATABASE_URL,
            connect_args={'connect_timeout': 10}
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
    except OperationalError as e:
        print(f"Warning: Could not connect to MySQL server. Please ensure MySQL is running and credentials are correct.")
        print(f"Error: {e}")
        raise
    except Exception as e:
        print(f"Error creating database: {e}")
        raise


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
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return SessionLocal()


def init_db():
    """
    Initialize database - create database and all tables if they don't exist.
    Automatically creates database and tables on first run.
    """
    global engine
    
    try:
        # Step 1: Create database if it doesn't exist
        create_database_if_not_exists()
        
        # Step 2: Create engine with connection pooling
        if engine is None:
            engine = create_engine(
                DATABASE_URL,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before using
                echo=False,  # Set to True for SQL query logging
                connect_args={
                    'charset': DB_CHARSET,
                    'connect_timeout': 10
                }
            )
            
            # Update SessionLocal to use the new engine
            global SessionLocal
            SessionLocal = scoped_session(sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine
            ))
        
        # Step 3: Create all tables if they don't exist
        from .models import Base
        Base.metadata.create_all(bind=engine)
        print("Database and tables initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise


def close_db():
    """
    Close database connections.
    """
    global SessionLocal, engine
    if SessionLocal is not None:
        SessionLocal.remove()
    if engine is not None:
        engine.dispose()

