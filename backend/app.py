"""
Main Flask Application
"""
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize database on startup
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from database.db_config import init_db
    init_db()
except ImportError:
    print("Warning: Database module not found. Database features will be disabled.")
except Exception as e:
    print(f"Warning: Could not initialize database: {e}")
    print("Application will continue without database features.")

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
    app.run(host="0.0.0.0", port=5000, debug=True)

