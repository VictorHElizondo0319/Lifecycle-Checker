"""
Excel Service - Handles Excel file parsing and product list extraction
"""
import pandas as pd
from typing import List, Dict, Any
import io
import re


def extract_general_information(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Extract general information from the Excel file
    
    Args:
        file_content: Binary content of the Excel file
        filename: Original filename
        
    Returns:
        Dictionary containing general information
    """
    try:
        # Read Excel file from bytes
        excel_file = io.BytesIO(file_content)
        
        # Try to read the Excel file
        if filename.endswith('.xlsx'):
            df = pd.read_excel(excel_file, engine='openpyxl', header=None)
        elif filename.endswith('.xls'):
            df = pd.read_excel(excel_file, engine='xlrd', header=None)
        else:
            df = pd.read_excel(excel_file, engine='openpyxl', header=None)
        
        # Helper function to safely get cell value
        def get_cell_value(row_idx, col_idx, default=""):
            try:
                val = df.iloc[row_idx, col_idx]
                if pd.isna(val):
                    return default
                return str(val).strip()
            except (IndexError, KeyError):
                return default
        
        # Extract document information (rows 2-4)
        document_no = get_cell_value(2, 0)  # Row 3 (0-indexed: 2)
        revision_no = get_cell_value(2, 1) if len(df.columns) > 1 else ""
        title = get_cell_value(3, 0)  # Row 4
        
        # Extract general information (row 6, 0-indexed: 5)
        equipment_description = get_cell_value(7, 1)
        eam_equipment_id = get_cell_value(7, 3)
        alias = get_cell_value(7, 5)
        plant = get_cell_value(7, 7)
        group_responsible = get_cell_value(7, 9)
        
        # Extract participating associates (around row 7-8)
        # Try to find "Initiator" or "Role" row
        initiator_name = get_cell_value(7, 11)
        initiator_id = get_cell_value(7, 12)
        pe_name = get_cell_value(8, 11)
        pe_id = get_cell_value(8, 12)
        d_and_a_name = get_cell_value(9, 11)
        d_and_a_id = get_cell_value(9, 12)
        maintenance_tech_name = get_cell_value(10, 11)
        maintenance_tech_id = get_cell_value(10, 12)
        indirect_procurement_name = get_cell_value(11, 11)
        indirect_procurement_id = get_cell_value(11, 12)
        
        return {
            'document_no': document_no,
            'revision_no': revision_no,
            'title': title,
            'equipment_description': equipment_description,
            'eam_equipment_id': eam_equipment_id,
            'alias': alias,
            'plant': plant,
            'group_responsible': group_responsible,
            'participating_associates': {
                'initiator': {
                    'name': initiator_name,
                    'id': initiator_id
                },
                'pe': {
                    'name': pe_name,
                    'id': pe_id
                },
                'd_and_a': {
                    'name': d_and_a_name,
                    'id': d_and_a_id
                },
                'maintenance_tech': {
                    'name': maintenance_tech_name,
                    'id': maintenance_tech_id
                },
                'indirect_procurement': {
                    'name': indirect_procurement_name,
                    'id': indirect_procurement_id
                }
            }
        }
    except Exception as e:
        raise Exception(f"Error extracting general information: {str(e)}")


def extract_products_from_row_18(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Extract products list starting from row 18
    
    Args:
        file_content: Binary content of the Excel file
        filename: Original filename
        
    Returns:
        List of dictionaries containing product information
    """
    try:
        # Read Excel file from bytes
        excel_file = io.BytesIO(file_content)
        
        # Read with header starting from row 17 (0-indexed: 16) to get column names
        # Then data starts from row 18 (0-indexed: 17)
        if filename.endswith('.xlsx'):
            df = pd.read_excel(excel_file, engine='openpyxl', header=16)  # Row 17 is header
        elif filename.endswith('.xls'):
            df = pd.read_excel(excel_file, engine='xlrd', header=16)
        else:
            df = pd.read_excel(excel_file, engine='openpyxl', header=16)
        
        # Normalize column names (strip whitespace)
        df.columns = df.columns.str.strip()
        
        products = []
        
        # Helper function to normalize whitespace in strings
        def normalize_whitespace(text):
            return re.sub(r'\s+', ' ', str(text).strip())
        
        # Helper function to find column name with flexible matching
        def find_column(column_name):
            if column_name in df.columns:
                return column_name
            
            normalized_search = normalize_whitespace(column_name)
            for col in df.columns:
                if normalize_whitespace(col) == normalized_search:
                    return col
            
            normalized_search_lower = normalized_search.lower()
            for col in df.columns:
                if normalize_whitespace(col).lower() == normalized_search_lower:
                    return col
            
            return None
        
        # Helper function to format integer values (remove .0)
        def format_integer_value(val):
            try:
                float_val = float(val)
                if float_val.is_integer():
                    return str(int(float_val))
                return str(float_val)
            except (ValueError, TypeError):
                return str(val)
        
        # Helper function to get value from row with fallback
        def get_value(row, col_name, default="", is_integer=False):
            actual_col_name = find_column(col_name)
            if actual_col_name and actual_col_name in df.columns and pd.notna(row[actual_col_name]):
                val = row[actual_col_name]
                if is_integer:
                    val = format_integer_value(val)
                else:
                    val = str(val).strip()
                return val if val != 'nan' else default
            return default
        
        # Extract products starting from row 18 (now index 0 after header=16)
        for index, row in df.iterrows():
            product = {
                'line': get_value(row, 'Line', is_integer=True),
                'description': get_value(row, 'Description'),
                'manufacturer': get_value(row, 'Manufacturer'),
                'manufacturer_part_number': get_value(row, 'Manufacturer Part # or Gore Part # or MD Drawing #'),
                'qty_on_machine': get_value(row, 'Qty. on Machine', is_integer=True),
                'suggested_supplier': get_value(row, 'Suggested Supplier (when applicable)'),
                'supplier_part_number': get_value(row, 'Supplier Part Number (when applicable)'),
                'gore_stock_number': get_value(row, 'Gore Stock number (ERP#) (when applicable)', is_integer=True),
                'is_part_likely_to_fail': get_value(row, 'Is Part likely to fail during the life of the machine?'),
                'will_failure_stop_machine': get_value(row, 'Will Part Failure stop the machine from supporting production?'),
                'stocking_decision': get_value(row, 'Stocking Decision'),
                'min_qty_to_stock': get_value(row, 'Min Qty to Stock for this Machine', is_integer=True),
                'part_replacement_line_number': get_value(row, 'Part Replacement Line # (Refer to 6.3.4 in MD205158)'),
                'notes': get_value(row, 'Notes (Refer to 6.1.4.4 of MD205158)'),
                'row_index': index + 18  # Actual row number in Excel (1-based)
            }
            
            # Skip completely empty rows (no manufacturer or part number)
            if not product['manufacturer'] and not product['manufacturer_part_number']:
                continue
            
            products.append(product)
        
        return products
        
    except Exception as e:
        raise Exception(f"Error extracting products: {str(e)}")


def parse_excel_file(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Parse Excel file and return product list (legacy function for backward compatibility)
    
    Args:
        file_content: Binary content of the Excel file
        filename: Original filename
        
    Returns:
        List of dictionaries containing product information
    """
    return extract_products_from_row_18(file_content, filename)


def parse_excel_file_complete(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse Excel file and return both general information and products list
    
    Args:
        file_content: Binary content of the Excel file
        filename: Original filename
        
    Returns:
        Dictionary containing 'general_info' and 'products'
    """
    try:
        general_info = extract_general_information(file_content, filename)
        products = extract_products_from_row_18(file_content, filename)
        
        return {
            'general_info': general_info,
            'products': products,
            'total_products': len(products)
        }
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


if __name__ == "__main__":
    # Test the extraction functions
    file = "../3000027009 Bonder, Split Die, V3.18.xlsx"
    with open(file, "rb") as f:
        file_content = f.read()
    
    # Test general information extraction
    general_info = extract_general_information(file_content, file)
    print("General Information:")
    print(general_info)
    
    # Test products extraction
    products = extract_products_from_row_18(file_content, file)
    print(f"\nProducts found: {len(products)}")
    if products:
        print("First product:")
        print(products[0])