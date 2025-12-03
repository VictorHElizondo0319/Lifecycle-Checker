"""
Excel API Routes - Handle Excel file upload and parsing
"""
from flask import Blueprint, request, jsonify
import sys
import os
# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from services.excel_service import parse_excel_file
import os

excel_bp = Blueprint('excel', __name__)


@excel_bp.route('/upload', methods=['POST'])
def upload_excel():
    """
    Upload and parse Excel file
    POST /api/excel/upload
    
    Request:
        - multipart/form-data with 'file' field
        
    Response:
        {
            "success": true,
            "products": [
                {
                    "manufacturer": "BANNER",
                    "part_number": "45136",
                    "row_index": 1
                },
                ...
            ],
            "total": 10
        }
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Check file extension
        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            return jsonify({"error": "Invalid file type. Please upload .xlsx or .xls file"}), 400
        
        # Read file content
        file_content = file.read()
        filename = file.filename
        
        # Parse Excel file
        products = parse_excel_file(file_content, filename)
        
        if not products:
            return jsonify({
                "success": False,
                "error": "No products found in Excel file"
            }), 400
        
        return jsonify({
            "success": True,
            "products": products,
            "total": len(products)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

