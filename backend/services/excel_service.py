"""
Excel Service - Handles Excel file parsing and product list extraction
"""
import pandas as pd
from typing import List, Dict, Any
import io


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
        
        # Try to identify manufacturer and part number columns
        # Common column names to look for
        manufacturer_cols = ['manufacturer', 'Manufacturer', 'MANUFACTURER', 'mfg', 'Mfg', 'MFG']
        part_number_cols = ['part_number', 'Part Number', 'PART_NUMBER', 'part#', 'Part#', 'PART#', 
                           'part no', 'Part No', 'PART NO', 'pn', 'PN']
        
        manufacturer_col = None
        part_number_col = None
        
        # Find manufacturer column
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if any(mfg_col.lower() in col_lower for mfg_col in manufacturer_cols):
                manufacturer_col = col
                break
        
        # Find part number column
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if any(pn_col.lower() in col_lower for pn_col in part_number_cols):
                part_number_col = col
                break
        
        # If columns not found, try first two columns
        if manufacturer_col is None and len(df.columns) > 0:
            manufacturer_col = df.columns[0]
        if part_number_col is None and len(df.columns) > 1:
            part_number_col = df.columns[1]
        
        # Extract products
        for index, row in df.iterrows():
            manufacturer = str(row[manufacturer_col]).strip() if manufacturer_col else ""
            part_number = str(row[part_number_col]).strip() if part_number_col else ""
            
            # Skip empty rows
            if not manufacturer or not part_number or manufacturer == 'nan' or part_number == 'nan':
                continue
            
            product = {
                'manufacturer': manufacturer,
                'part_number': part_number,
                'row_index': index + 1  # 1-based index
            }
            
            # Include any additional columns as extra data
            for col in df.columns:
                if col not in [manufacturer_col, part_number_col]:
                    product[str(col).lower().replace(' ', '_')] = str(row[col]).strip() if pd.notna(row[col]) else ""
            
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

