"""
Main Flask Application
"""
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import sys
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Track database initialization status
db_initialized = False

# Initialize database on startup
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from database.db_config import init_db
    print("Attempting to initialize database...")
    result = init_db()
    if result:
        db_initialized = True
        print("[OK] Database initialized successfully!")
    else:
        db_initialized = False
        print("[WARNING] Database initialization skipped - MySQL server not available or not configured.")
        print("  Application will continue without database features.")
except ImportError as e:
    print(f"[WARNING] Warning: Database module not found: {e}")
    print("  Database features will be disabled.")
    db_initialized = False
except Exception as e:
    import traceback
    print(f"[WARNING] Warning: Unexpected error during database initialization: {e}")
    print(f"  Error details: {traceback.format_exc()}")
    print("  Application will continue without database features.")
    db_initialized = False


@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    GET /health or GET /api/health
    
    Returns:
        {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00",
            "database": "connected" | "disconnected" | "not_configured"
        }
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": "not_configured"
    }
    
    # Check database connectivity if initialized
    if db_initialized:
        try:
            from database.db_config import engine
            from sqlalchemy import text
            if engine is not None:
                # Test database connection
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                health_status["database"] = "connected"
            else:
                health_status["database"] = "disconnected"
        except Exception as e:
            health_status["database"] = "disconnected"
            health_status["database_error"] = str(e)
    
    status_code = 200
    if health_status["database"] == "disconnected" and db_initialized:
        # If database was expected but is disconnected, return 503
        status_code = 503
        health_status["status"] = "degraded"
    
    return jsonify(health_status), status_code


# Register blueprints
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.excel_routes import excel_bp
from api.analyze_routes import analyze_bp
from api.save_routes import save_bp
from api.parts_routes import parts_bp

app.register_blueprint(excel_bp, url_prefix='/api/excel')
app.register_blueprint(analyze_bp, url_prefix='/api')
app.register_blueprint(save_bp, url_prefix='/api')
app.register_blueprint(parts_bp, url_prefix='/api')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

