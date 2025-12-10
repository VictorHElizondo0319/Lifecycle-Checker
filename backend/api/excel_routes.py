"""
Excel API Routes - Handle Excel file upload and parsing
"""
from flask import Blueprint, request, jsonify, send_file
import sys
import os
# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from services.excel_service import parse_excel_file, parse_excel_file_complete, extract_general_information, extract_products_from_row_18, export_products_to_excel
from flask import send_file
import os

excel_bp = Blueprint('excel', __name__)


# @excel_bp.route('/upload', methods=['POST'])
# def upload_excel():
#     """
#     Upload and parse Excel file
#     POST /api/excel/upload
    
#     Request:
#         - multipart/form-data with 'file' field
        
#     Response:
#         {
#             "success": true,
#             "products": [
#                 {
#                     "manufacturer": "BANNER",
#                     "part_number": "45136",
#                     "row_index": 1
#                 },
#                 ...
#             ],
#             "total": 10
#         }
#     """
#     try:
#         if 'file' not in request.files:
#             return jsonify({"error": "No file provided"}), 400
        
#         file = request.files['file']
        
#         if file.filename == '':
#             return jsonify({"error": "No file selected"}), 400
        
#         # Check file extension
#         if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
#             return jsonify({"error": "Invalid file type. Please upload .xlsx or .xls file"}), 400
        
#         # Read file content
#         file_content = file.read()
#         filename = file.filename
        
#         # Parse Excel file
#         products = parse_excel_file(file_content, filename)
        
#         if not products:
#             return jsonify({
#                 "success": False,
#                 "error": "No products found in Excel file"
#             }), 400
        
#         return jsonify({
#             "success": True,
#             "products": products,
#             "total": len(products)
#         })
        
#     except Exception as e:
#         return jsonify({
#             "success": False,
#             "error": str(e)
#         }), 500


@excel_bp.route('/upload', methods=['POST'])
def parse_complete():
    """
    Upload and parse Excel file with both general information and products
    POST /api/excel/upload
    
    Request:
        - multipart/form-data with 'file' field
        
    Response:
        {
            "success": true,
            "general_info": {
                "document_no": "...",
                "equipment_description": "...",
                "eam_equipment_id": "...",
                ...
            },
            "products": [...],
            "total_products": 10
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
        
        # Parse Excel file with both general info and products
        result = parse_excel_file_complete(file_content, filename)
        
        return jsonify({
            "success": True,
            **result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@excel_bp.route('/general-info', methods=['POST'])
def get_general_info():
    """
    Extract only general information from Excel file
    POST /api/excel/general-info
    
    Request:
        - multipart/form-data with 'file' field
        
    Response:
        {
            "success": true,
            "general_info": {
                "document_no": "...",
                "equipment_description": "...",
                "eam_equipment_id": "...",
                ...
            }
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
        
        # Extract general information
        general_info = extract_general_information(file_content, filename)
        
        return jsonify({
            "success": True,
            "general_info": general_info
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@excel_bp.route('/products', methods=['POST'])
def get_products():
    """
    Extract only products list from Excel file (starting from row 18)
    POST /api/excel/products
    
    Request:
        - multipart/form-data with 'file' field
        
    Response:
        {
            "success": true,
            "products": [...],
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
        
        # Extract products from row 18
        products = extract_products_from_row_18(file_content, filename)
        
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


@excel_bp.route('/export', methods=['POST'])
def export_excel():
    """
    Export products to Excel file
    POST /api/excel/export
    
    Request:
        {
            "cols": ["manufacturer", "part_number", ...],
            "products": [...]
        }
        
    Response:
        Excel file download (.xlsx)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        cols = data.get('cols', [])
        products = data.get('products', [])
        
        if not cols:
            return jsonify({"error": "No columns specified"}), 400
        
        if not products:
            return jsonify({"error": "No products to export"}), 400
        
        # Export to Excel
        excel_content = export_products_to_excel(products, cols)
        
        # Create BytesIO object for file download
        from io import BytesIO
        output = BytesIO(excel_content)
        output.seek(0)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'products_export_{timestamp}.xlsx'
        
        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

