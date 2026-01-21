"""
Analysis API Routes - Handle product lifecycle analysis
"""
from flask import Blueprint, request, jsonify, Response
import sys
import os
# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from services.azure_ai_service import AzureAIService
from services.excel_service import split_products_into_chunks
import json
import concurrent.futures
from typing import List, Dict, Any

analyze_bp = Blueprint('analyze', __name__)
azure_ai_service = None  # Lazy initialization to avoid startup crashes

CHUNK_SIZE = 10

def _should_analyze_product(product: Dict[str, Any]) -> bool:
    """
    Check if a product should be analyzed by AI.
    Products with missing or "no" stocking_decision should not be analyzed.
    """
    stocking_decision = product.get('stocking_decision', '').strip().lower() if product.get('stocking_decision') else ''
    # Skip analysis if stocking_decision is missing, empty, or "no"
    return stocking_decision and stocking_decision != 'no'


def _create_skipped_result(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a result entry for products that were skipped from AI analysis.
    These products will have no AI status, notes, or confidence.
    """
    manufacturer = product.get('part_manufacturer') or product.get('manufacturer', '')
    part_number = product.get('manufacturer_part_number') or product.get('part_number', '')
    
    return {
        "manufacturer": manufacturer,
        "part_number": part_number,
        "ai_status": None,  # Explicitly set to None (not analyzed)
        "notes_by_ai": None,
        "ai_confidence": None
    }


def get_azure_ai_service():
    """
    Get or create AzureAIService instance with lazy initialization.
    This prevents Azure credentials from being initialized at import time.
    """
    global azure_ai_service
    if azure_ai_service is None:
        try:
            azure_ai_service = AzureAIService()
        except Exception as e:
            # If Azure credentials are not available, return None
            # The calling code should handle this gracefully
            print(f"Warning: Could not initialize AzureAIService: {e}")
            print("Azure AI features will be unavailable until Azure Service Principal credentials are configured.")
            return None
    return azure_ai_service
@analyze_bp.route('/analyze', methods=['POST'])
def analyze_products():
    """
    Analyze products lifecycle status
    POST /api/analyze
    
    Request:
        {
            "products": [
                {
                    "manufacturer": "BANNER",
                    "part_number": "45136"
                },
                ...
            ],
            "stream": false  // optional, default false
        }
        
    Response (non-streaming):
        {
            "success": true,
            "results": [
                {
                    "manufacturer": "BANNER",
                    "part_number": "45136",
                    "ai_status": "Active",
                    "notes_by_ai": "...",
                    "ai_confidence": "High"
                },
                ...
            ],
            "total_analyzed": 10
        }
        
    Response (streaming):
        Server-Sent Events (SSE) stream with JSON objects
    """
    try:
        data = request.json or {}
        products = data.get('products', [])
        stream = data.get('stream', False)
        
        if not products:
            return jsonify({"error": "No products provided"}), 400
        
        if not isinstance(products, list):
            return jsonify({"error": "Products must be a list"}), 400
        
        # If streaming requested, use streaming endpoint
        if stream:
            return Response(
                _stream_analysis(products),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )
        
        # Separate products into those that need AI analysis and those that don't
        products_to_analyze = [p for p in products if _should_analyze_product(p)]
        products_to_skip = [p for p in products if not _should_analyze_product(p)]
        
        # Create results for skipped products (no AI analysis)
        skipped_results = [_create_skipped_result(p) for p in products_to_skip]
        all_results = skipped_results.copy()
        
        # If there are products to analyze, process them
        if products_to_analyze:
            # Get Azure AI service
            analyze_service = get_azure_ai_service()
            if analyze_service is None:
                return jsonify({
                    "success": False,
                    "error": "Azure AI service is not available. Please ensure Azure Service Principal credentials are configured (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)."
                }), 503
            
            # Split into chunks for parallel processing
            chunks = split_products_into_chunks(products_to_analyze, chunk_size=CHUNK_SIZE)
            conversation_id = None
            
            # Process chunks in parallel using ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(chunks), 5)) as executor:
                future_to_chunk = {
                    executor.submit(analyze_service.analyze_product_chunk, chunk, conversation_id): chunk
                    for chunk in chunks
                }
                
                for future in concurrent.futures.as_completed(future_to_chunk):
                    result = future.result()
                    if result['success'] and result.get('parsed_json'):
                        parsed_json = result['parsed_json']
                        if isinstance(parsed_json, dict) and 'results' in parsed_json:
                            all_results.extend(parsed_json['results'])
                        # Update conversation_id for next chunk (if available)
                        if result.get('conversation_id'):
                            conversation_id = result['conversation_id']
        
        return jsonify({
            "success": True,
            "results": all_results,
            "total_analyzed": len(products_to_analyze),
            "total_skipped": len(products_to_skip)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _stream_analysis(products: List[Dict[str, Any]]):
    """
    Stream analysis results using Server-Sent Events
    
    Args:
        products: List of products to analyze
        
    Yields:
        SSE-formatted strings
    """
    try:
        # Separate products into those that need AI analysis and those that don't
        products_to_analyze = [p for p in products if _should_analyze_product(p)]
        products_to_skip = [p for p in products if not _should_analyze_product(p)]
        
        # Create results for skipped products (no AI analysis)
        skipped_results = [_create_skipped_result(p) for p in products_to_skip]
        
        all_results = skipped_results.copy()
        total_products = len(products)
        total_to_analyze = len(products_to_analyze)
        total_skipped = len(products_to_skip)
        
        # If no products need analysis, return early
        if total_to_analyze == 0:
            yield f"data: {json.dumps({'type': 'start', 'total_chunks': 0, 'total_products': total_products, 'total_skipped': total_skipped})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'results': all_results, 'total_analyzed': total_to_analyze, 'total_skipped': total_skipped})}\n\n"
            return
        
        # Split products that need analysis into chunks
        chunks = split_products_into_chunks(products_to_analyze, chunk_size=CHUNK_SIZE)
        total_chunks = len(chunks)
        
        # Send initial progress
        yield f"data: {json.dumps({'type': 'start', 'total_chunks': total_chunks, 'total_products': total_products, 'total_to_analyze': total_to_analyze, 'total_skipped': total_skipped})}\n\n"
        
        conversation_id = None

        # Get Azure AI service lazily (only when needed)
        analyze_service = get_azure_ai_service()
        if analyze_service is None:
            error_msg = "Azure AI service is not available. Please ensure Azure Service Principal credentials are configured (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)."
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            return

        # Process chunks sequentially for streaming (can be parallelized with more complex logic)
        for idx, chunk in enumerate(chunks):
            # Send chunk progress
            yield f"data: {json.dumps({'type': 'chunk_start', 'chunk': idx + 1, 'total_chunks': total_chunks, 'products_in_chunk': len(chunk)})}\n\n"
            
            # Analyze chunk
            for stream_data in analyze_service.analyze_product_chunk_streaming(chunk, conversation_id):
                yield f"data: {stream_data}\n\n"
                
                # Parse the stream data to extract results
                try:
                    stream_obj = json.loads(stream_data)
                    if stream_obj.get('type') == 'result' and stream_obj.get('data'):
                        chunk_results = stream_obj['data'].get('results', [])
                        all_results.extend(chunk_results)
                        if stream_obj.get('conversation_id'):
                            conversation_id = stream_obj['conversation_id']
                except:
                    pass
            
            # Send chunk complete
            yield f"data: {json.dumps({'type': 'chunk_complete', 'chunk': idx + 1, 'total_chunks': total_chunks})}\n\n"
        
        # Send final results
        yield f"data: {json.dumps({'type': 'complete', 'results': all_results, 'total_analyzed': total_to_analyze, 'total_skipped': total_skipped})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

@analyze_bp.route('/find_replacements', methods=['POST'])
def find_replacements():
    """
    Find replacement parts for obsolete products using Azure AI
    POST /api/find_replacements
    
    Request:
        {
            "products": [
                {
                    "manufacturer": "BANNER",
                    "part_number": "45136"
                },
                ...
            ]
        }
        
    Response:
        Server-Sent Events (SSE) stream with JSON objects
    """
    try:
        data = request.json or {}
        products = data.get('products', [])
        
        if not products:
            return jsonify({"error": "No products provided"}), 400
        
        if not isinstance(products, list):
            return jsonify({"error": "Products must be a list"}), 400
        
        # Return streaming response
        return Response(
            _stream_find_replacements(products),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _stream_find_replacements(products: List[Dict[str, Any]]):
    """
    Stream replacement finding results using Server-Sent Events
    
    Args:
        products: List of products to find replacements for
    Yields:
        SSE-formatted strings
    """
    try:
        # Split into chunks
        chunks = split_products_into_chunks(products, chunk_size=CHUNK_SIZE)
        total_chunks = len(chunks)
        
        # Send initial progress
        yield f"data: {json.dumps({'type': 'start', 'total_chunks': total_chunks, 'total_products': len(products)})}\n\n"
        
        all_results = []
        conversation_id = None
        
        # Get Azure AI service lazily (only when needed)
        replacement_service = get_azure_ai_service()
        if replacement_service is None:
            error_msg = "Azure AI service is not available. Please ensure Azure Service Principal credentials are configured (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)."
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            return
        
        # Process chunks sequentially for streaming
        for idx, chunk in enumerate(chunks):
            # Send chunk progress
            yield f"data: {json.dumps({'type': 'chunk_start', 'chunk': idx + 1, 'total_chunks': total_chunks, 'products_in_chunk': len(chunk)})}\n\n"
            
            # Find replacements for chunk using Azure AI
            for stream_data in replacement_service.find_replacement_chunk_streaming(chunk, conversation_id):
                yield f"data: {stream_data}\n\n"
                
                # Parse the stream data to extract results
                try:
                    stream_obj = json.loads(stream_data)
                    if stream_obj.get('type') == 'result' and stream_obj.get('data'):
                        chunk_results = stream_obj['data'].get('results', [])
                        all_results.extend(chunk_results)
                        if stream_obj.get('conversation_id'):
                            conversation_id = stream_obj['conversation_id']
                except:
                    pass
            
            # Send chunk complete
            yield f"data: {json.dumps({'type': 'chunk_complete', 'chunk': idx + 1, 'total_chunks': total_chunks})}\n\n"
        
        # Send final results
        yield f"data: {json.dumps({'type': 'complete', 'results': all_results, 'total_analyzed': len(all_results)})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"