"""
Analysis Logger - Log analysis results to .txt files
Works in both development and when packaged as .exe
"""
import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any


def get_log_directory() -> str:
    """
    Get the directory where log files should be saved.
    Works for both development and .exe environments.
    
    Returns:
        Path to the log directory
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        # Use the directory where the exe is located
        base_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        # Use the backend directory
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_dir = backend_dir
    
    # Create logs subdirectory
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    return log_dir


def format_analysis_result(result: Dict[str, Any], is_replacement: bool = False) -> str:
    """
    Format a single analysis result for text output.
    
    Args:
        result: Analysis result dictionary
        is_replacement: Whether this is a replacement finding result
        
    Returns:
        Formatted string representation
    """
    lines = []
    lines.append("=" * 80)
    
    if is_replacement:
        # Replacement finding format
        obsolete_part = result.get('obsolete_part_number', 'N/A')
        manufacturer = result.get('manufacturer', 'N/A')
        lines.append(f"Obsolete Part Number: {obsolete_part}")
        lines.append(f"Manufacturer: {manufacturer}")
        
        # Replacement information
        replacement = result.get('recommended_replacement', '')
        replacement_manufacturer = result.get('replacement_manufacturer', '')
        if replacement:
            lines.append(f"\nRecommended Replacement: {replacement}")
        if replacement_manufacturer:
            lines.append(f"Replacement Manufacturer: {replacement_manufacturer}")
        
        # Price information
        price = result.get('price')
        if price is not None:
            currency = result.get('currency', 'USD')
            lines.append(f"Price: {price} {currency}")
        
        # Source information
        source_type = result.get('source_type', '')
        source_url = result.get('source_url', '')
        if source_type:
            lines.append(f"Source Type: {source_type}")
        if source_url:
            lines.append(f"Source URL: {source_url}")
        
        # Confidence
        confidence = result.get('confidence', 'N/A')
        if confidence:
            lines.append(f"Confidence: {confidence}")
        
        # Notes
        notes = result.get('notes', '')
        if notes:
            lines.append(f"\nNotes:")
            # Wrap long notes
            words = notes.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > 78:
                    if current_line:
                        lines.append(f"  {current_line}")
                    current_line = word
                else:
                    current_line = f"{current_line} {word}" if current_line else word
            if current_line:
                lines.append(f"  {current_line}")
    else:
        # Standard analysis format
        manufacturer = result.get('manufacturer', 'N/A')
        part_number = result.get('part_number', 'N/A')
        lines.append(f"Manufacturer: {manufacturer}")
        lines.append(f"Part Number: {part_number}")
        
        # AI Status
        ai_status = result.get('ai_status', 'N/A')
        lines.append(f"Status: {ai_status}")
        
        # AI Confidence
        ai_confidence = result.get('ai_confidence', 'N/A')
        if ai_confidence:
            lines.append(f"Confidence: {ai_confidence}")
        
        # Notes
        notes = result.get('notes_by_ai', '')
        if notes:
            lines.append(f"\nNotes:")
            # Wrap long notes
            words = notes.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > 78:
                    if current_line:
                        lines.append(f"  {current_line}")
                    current_line = word
                else:
                    current_line = f"{current_line} {word}" if current_line else word
            if current_line:
                lines.append(f"  {current_line}")
    
    lines.append("")
    return "\n".join(lines)


def log_analysis_results(
    results: List[Dict[str, Any]],
    analysis_type: str = "analysis",
    total_analyzed: int = 0,
    total_skipped: int = 0
) -> str:
    """
    Log analysis results to a .txt file.
    
    Args:
        results: List of analysis result dictionaries
        analysis_type: Type of analysis ("analysis" or "replacements")
        total_analyzed: Total number of products analyzed
        total_skipped: Total number of products skipped
        
    Returns:
        Path to the created log file
    """
    try:
        log_dir = get_log_directory()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{analysis_type}_{timestamp}.txt"
        log_path = os.path.join(log_dir, filename)
        
        # Write log file
        with open(log_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write(f"Analysis Results Log\n")
            f.write(f"Analysis Type: {analysis_type.capitalize()}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Products Analyzed: {total_analyzed}\n")
            f.write(f"Total Products Skipped: {total_skipped}\n")
            f.write(f"Total Results: {len(results)}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            
            # Results
            f.write("DETAILED RESULTS\n")
            f.write("-" * 80 + "\n\n")
            
            for idx, result in enumerate(results, 1):
                f.write(f"Result #{idx}\n")
                is_replacement = analysis_type == "replacements"
                f.write(format_analysis_result(result, is_replacement=is_replacement))
                f.write("\n")
            
            # Footer
            f.write("=" * 80 + "\n")
            f.write(f"End of Analysis Log\n")
            f.write(f"Log file: {log_path}\n")
            f.write("=" * 80 + "\n")
        
        return log_path
        
    except Exception as e:
        # Log error but don't crash the application
        print(f"Error writing analysis log: {e}")
        import traceback
        traceback.print_exc()
        return ""


def log_chunk_result(
    chunk_index: int,
    chunk_result: Dict[str, Any],
    chunk_products: List[Dict[str, Any]],
    analysis_type: str = "analysis",
    log_file_path: str = None
) -> str:
    """
    Log a single chunk result to a log file (append mode).
    Logs both success and error cases.
    
    Args:
        chunk_index: Index of the chunk (1-based)
        chunk_result: Result dictionary from chunk processing
        chunk_products: Original products in this chunk
        analysis_type: Type of analysis ("analysis" or "replacements")
        log_file_path: Path to existing log file (if None, creates new one)
        
    Returns:
        Path to the log file
    """
    try:
        if log_file_path is None:
            log_dir = get_log_directory()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{analysis_type}_{timestamp}.txt"
            log_file_path = os.path.join(log_dir, filename)
            
            # Create new file with header
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"Analysis Results Log - Chunk-by-Chunk\n")
                f.write(f"Analysis Type: {analysis_type.capitalize()}\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
        
        # Append chunk result
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"CHUNK #{chunk_index} - Processed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'=' * 80}\n\n")
            
            # Log chunk info
            f.write(f"Products in chunk: {len(chunk_products)}\n")
            f.write(f"Success: {chunk_result.get('success', False)}\n")
            
            # Log error if present
            if not chunk_result.get('success', False):
                error_msg = chunk_result.get('error', 'Unknown error')
                f.write(f"ERROR: {error_msg}\n\n")
                
                # Log the products that failed
                f.write("Products that failed:\n")
                for idx, product in enumerate(chunk_products, 1):
                    manufacturer = product.get('part_manufacturer') or product.get('manufacturer', 'N/A')
                    part_number = product.get('manufacturer_part_number') or product.get('part_number', 'N/A')
                    f.write(f"  {idx}. {manufacturer} - {part_number}\n")
            
            # Log results if successful
            if chunk_result.get('success', False) and chunk_result.get('parsed_json'):
                parsed_json = chunk_result.get('parsed_json', {})
                results = parsed_json.get('results', [])
                
                f.write(f"\nResults: {len(results)} items\n")
                f.write("-" * 80 + "\n\n")
                
                for idx, result in enumerate(results, 1):
                    f.write(f"Result #{idx} in Chunk #{chunk_index}\n")
                    is_replacement = analysis_type == "replacements"
                    f.write(format_analysis_result(result, is_replacement=is_replacement))
                    f.write("\n")
            
            f.write(f"\n{'=' * 80}\n")
        
        return log_file_path
        
    except Exception as e:
        print(f"Error logging chunk result: {e}")
        import traceback
        traceback.print_exc()
        return log_file_path or ""


def log_analysis_results_json(
    results: List[Dict[str, Any]],
    analysis_type: str = "analysis",
    total_analyzed: int = 0,
    total_skipped: int = 0
) -> str:
    """
    Log analysis results to a JSON file (for programmatic access).
    
    Args:
        results: List of analysis result dictionaries
        analysis_type: Type of analysis ("analysis" or "replacements")
        total_analyzed: Total number of products analyzed
        total_skipped: Total number of products skipped
        
    Returns:
        Path to the created log file
    """
    try:
        log_dir = get_log_directory()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{analysis_type}_{timestamp}.json"
        log_path = os.path.join(log_dir, filename)
        
        # Create log data structure
        log_data = {
            "metadata": {
                "analysis_type": analysis_type,
                "generated": datetime.now().isoformat(),
                "total_analyzed": total_analyzed,
                "total_skipped": total_skipped,
                "total_results": len(results)
            },
            "results": results
        }
        
        # Write JSON file
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        return log_path
        
    except Exception as e:
        # Log error but don't crash the application
        print(f"Error writing analysis JSON log: {e}")
        import traceback
        traceback.print_exc()
        return ""
