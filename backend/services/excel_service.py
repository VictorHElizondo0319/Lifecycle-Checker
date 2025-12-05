"""
Excel Service - Handles Excel file parsing and product list extraction
"""
import pandas as pd
from typing import List, Dict, Any
import io
import re


def parse_excel_file(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Parse Excel file and return product list
    
    Args:
        file_content: Binary content of the Excel file
        filename: Original filename
        
    Returns:
        List of dictionaries containing product information
        Each dict should have at least 'manufacturer' and 'part_number' keys
    """
    try:
        # Read Excel file from bytes
        excel_file = io.BytesIO(file_content)
        
        # Try to read the Excel file
        # Support both .xlsx and .xls formats
        if filename.endswith('.xlsx'):
            df = pd.read_excel(excel_file, engine='openpyxl')
        elif filename.endswith('.xls'):
            df = pd.read_excel(excel_file, engine='xlrd')
        else:
            # Default to openpyxl
            df = pd.read_excel(excel_file, engine='openpyxl')
        
        # Convert DataFrame to list of dictionaries
        products = []
        
        # Normalize column names (strip whitespace)
        df.columns = df.columns.str.strip()
        print(df.columns.tolist())
        # Integer fields that should not show .0
        integer_fields = {
            'Original Order': 'original_order',
            'Machine Equipment Number': 'machine_equipment_number',
            'Equipment Alias': 'equipment_alias',
            'CSPL Line Number': 'cspl_line_number',
            'Qty.on Machine': 'qty_on_machine',
            'Gore Stock Number': 'gore_stock_number',
        }
        
        # Helper function to normalize whitespace in strings (collapse multiple spaces to single)
        def normalize_whitespace(text):
            """Normalize whitespace by collapsing multiple spaces to single space"""
            return re.sub(r'\s+', ' ', str(text).strip())
        
        # Helper function to find column name with flexible matching
        def find_column(column_name):
            """Find column in dataframe with flexible matching (handles whitespace variations)"""
            # First try exact match
            if column_name in df.columns:
                return column_name
            
            # Try with normalized whitespace
            normalized_search = normalize_whitespace(column_name)
            for col in df.columns:
                if normalize_whitespace(col) == normalized_search:
                    return col
            
            # Try case-insensitive match with normalized whitespace
            normalized_search_lower = normalized_search.lower()
            for col in df.columns:
                if normalize_whitespace(col).lower() == normalized_search_lower:
                    return col
            
            return None
        
        # Helper function to format integer values (remove .0)
        def format_integer_value(val):
            """Convert float values like 30.0 to integer strings like '30'"""
            try:
                # Try to convert to float first
                float_val = float(val)
                # If it's a whole number, return as integer string
                if float_val.is_integer():
                    return str(int(float_val))
                return str(float_val)
            except (ValueError, TypeError):
                # If conversion fails, return original value
                return str(val)
        
        # Helper function to get value from row with fallback
        def get_value(row, col_name, default="", is_integer=False):
            # Try to find the column with flexible matching
            actual_col_name = find_column(col_name)
            if actual_col_name and actual_col_name in df.columns and pd.notna(row[actual_col_name]):
                val = row[actual_col_name]
                # For integer fields, format the value
                if is_integer:
                    val = format_integer_value(val)
                else:
                    val = str(val).strip()
                return val if val != 'nan' else default
            return default
        
        # Extract products - map all columns from the Excel file
        for index, row in df.iterrows():
            product = {
                'original_order': get_value(row, 'Original Order', is_integer=True),
                'parent_folder': get_value(row, 'Parent Folder'),
                'machine_equipment_number': get_value(row, 'Machine Equipment Number', is_integer=True),
                'equipment_number': get_value(row, 'Equipment Number', get_value(row, 'Machine Equipment Number', is_integer=True), is_integer=True),  # Fallback to Machine Equipment Number
                'equipment_alias': get_value(row, 'Equipment Alias', is_integer=True),
                'machine_description': get_value(row, 'Machine Description'),
                'group_responsibility': get_value(row, 'Group Responsibility'),
                'plant': get_value(row, 'Plant'),
                'initiator': get_value(row, 'Initiator'),
                'cspl_line_number': get_value(row, 'CSPL Line Number', is_integer=True),
                'part_description': get_value(row, 'Part Description'),
                'part_manufacturer': get_value(row, 'Part Manufacturer'),
                'manufacturer_part_number': get_value(row, 'Manufacturer Part # or Gore Part # or MD Drawing #'),
                'qty_on_machine': get_value(row, 'Qty.on Machine', is_integer=True),
                'suggested_supplier': get_value(row, 'Suggested Supplier (when applicable)'),
                'supplier_part_number': get_value(row, 'Supplier PartNumber (when applicable)'),
                'gore_stock_number': get_value(row, 'Gore Stock Number', is_integer=True),
                'is_part_likely_to_fail': get_value(row, 'Is Part likely to fail?'),
                'will_failures_stop_machine': get_value(row, 'Will Failures stop machine from supporting production'),
                'stocking_decision': get_value(row, 'Stocking Decision'),
                'min_qty_to_stock': get_value(row, 'Min Qty to Stock for this Machine'),
                'part_preplacement_line_number': get_value(row, 'Part Preplacement Line #'),
                'notes': get_value(row, 'Notes'),
                'part_number_ai_modified': get_value(row, 'Part# (AI Modified)'),
                'manufacturer': get_value(row, 'Manufacturer'),
                'ai_status': get_value(row, 'AI Status'),
                'notes_by_ai': get_value(row, 'Notes By AI'),
                'ai_confidence': get_value(row, 'AI Confidence'),
                'ai_confidence_confirmed': get_value(row, 'AI Confidence Confirmed'),
                'will_notes': get_value(row, 'Will Notes'),
                'nejat_notes': get_value(row, 'Nejat Notes'),
                'kc_notes': get_value(row, 'KC Notes'),
                'initial_email_communication': get_value(row, 'Initial Email Communication'),
                'follow_up_email_communication_date': get_value(row, 'Follow up Email Communication Date'),
                'ricky_notes': get_value(row, "Ricky's Notes"),
                'stephanie_notes': get_value(row, 'Stephanie Notes'),
                'pit_notes': get_value(row, 'PIT Notes'),
                'row_index': index + 1  # 1-based index for reference
            }
            
            # Skip completely empty rows (no part manufacturer or part number)
            if not product['part_manufacturer'] and not product['manufacturer_part_number']:
                continue
            
            products.append(product)
        
        return products
        
    except Exception as e:
        raise Exception(f"Error parsing Excel file: {str(e)}")


def split_products_into_chunks(products: List[Dict[str, Any]], chunk_size: int = 30) -> List[List[Dict[str, Any]]]:
    """
    Split products list into chunks for parallel processing
    
    Args:
        products: List of product dictionaries
        chunk_size: Number of products per chunk (default: 30)
        
    Returns:
        List of product chunks
    """
    chunks = []
    for i in range(0, len(products), chunk_size):
        chunks.append(products[i:i + chunk_size])
    return chunks

