"""
Main Flask Application
"""
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Register blueprints
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.excel_routes import excel_bp
from api.analyze_routes import analyze_bp

app.register_blueprint(excel_bp, url_prefix='/api/excel')
app.register_blueprint(analyze_bp, url_prefix='/api')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

