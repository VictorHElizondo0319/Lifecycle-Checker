"""
Analysis API Routes - Handle product lifecycle analysis
"""
from flask import Blueprint, request, jsonify, Response
import sys
import os
# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from services.ai_service import AIService
from services.excel_service import split_products_into_chunks
import json
import concurrent.futures
from typing import List, Dict, Any

analyze_bp = Blueprint('analyze', __name__)
ai_service = AIService()


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
        print(stream)
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
        
        # Non-streaming: process all products
        # Split into chunks of 30 for parallel processing
        chunks = split_products_into_chunks(products, chunk_size=30)
        
        all_results = []
        conversation_id = None
        
        # Process chunks in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(chunks), 5)) as executor:
            future_to_chunk = {
                executor.submit(ai_service.analyze_product_chunk, chunk, conversation_id): chunk
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
            "total_analyzed": len(all_results)
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
        # Split into chunks
        chunks = split_products_into_chunks(products, chunk_size=30)
        total_chunks = len(chunks)
        
        # Send initial progress
        yield f"data: {json.dumps({'type': 'start', 'total_chunks': total_chunks, 'total_products': len(products)})}\n\n"
        
        all_results = []
        conversation_id = None
        
        # Process chunks sequentially for streaming (can be parallelized with more complex logic)
        for idx, chunk in enumerate(chunks):
            # Send chunk progress
            yield f"data: {json.dumps({'type': 'chunk_start', 'chunk': idx + 1, 'total_chunks': total_chunks, 'products_in_chunk': len(chunk)})}\n\n"
            
            # Analyze chunk
            for stream_data in ai_service.analyze_product_chunk_streaming(chunk, conversation_id):
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

