"""
AI Service - Handles OpenAI API calls for product lifecycle analysis
"""
from openai import OpenAI
import os
from typing import List, Dict, Any, Generator
import json
import re
import sys
import os
# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from config import SYSTEM_PROMPT


class AIService:
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = SYSTEM_PROMPT
    
    def analyze_product_chunk(self, products: List[Dict[str, Any]], conversation_id: str = None) -> Dict[str, Any]:
        """
        Analyze a chunk of products using OpenAI
        
        Args:
            products: List of product dictionaries to analyze
            conversation_id: Optional conversation ID for context
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Format products for analysis
            product_list_text = self._format_products_for_analysis(products)
            
            # Use Responses API with web search tool enabled
            resp = self.client.responses.create(
                model="gpt-4.1",  # or "gpt-4.1-mini"
                instructions=self.system_prompt,
                input=product_list_text,
                tools=[{"type": "web_search"}],
                conversation=conversation_id,
                max_output_tokens=2500,
                temperature=0.2,
            )
            
            # Extract conversation ID if available
            new_conversation_id = getattr(resp, "conversation_id", None)
            
            # Get the response text
            response_text = resp.output_text.strip()
            
            # Parse JSON from response
            parsed_json = self._parse_json_from_response(response_text)
            
            return {
                'success': True,
                'conversation_id': new_conversation_id or conversation_id,
                'response_text': response_text,
                'parsed_json': parsed_json,
                'products_analyzed': len(products)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'products_analyzed': len(products)
            }
    
    def analyze_product_chunk_streaming(self, products: List[Dict[str, Any]], conversation_id: str = None) -> Generator[str, None, None]:
        """
        Analyze a chunk of products using OpenAI with streaming response
        
        Args:
            products: List of product dictionaries to analyze
            conversation_id: Optional conversation ID for context
            
        Yields:
            JSON strings containing partial or complete analysis results
        """
        try:
            # Format products for analysis
            product_list_text = self._format_products_for_analysis(products)
            
            # Use Chat API for streaming (if Responses API doesn't support streaming)
            # For now, we'll use the Responses API and yield the complete result
            # In a real implementation, you might want to use chat completions with streaming
            
            resp = self.client.responses.create(
                model="gpt-4.1",
                instructions=self.system_prompt,
                input=product_list_text,
                tools=[{"type": "web_search"}],
                conversation=conversation_id,
                max_output_tokens=2500,
                temperature=0.2,
            )
            
            new_conversation_id = getattr(resp, "conversation_id", None)
            response_text = resp.output_text.strip()
            
            # Parse JSON from response
            parsed_json = self._parse_json_from_response(response_text)
            
            # Yield progress updates
            yield json.dumps({
                'type': 'progress',
                'message': f'Analyzing {len(products)} products...'
            })
            
            # Yield the complete result
            if parsed_json:
                yield json.dumps({
                    'type': 'result',
                    'conversation_id': new_conversation_id or conversation_id,
                    'data': parsed_json,
                    'products_analyzed': len(products)
                })
            else:
                yield json.dumps({
                    'type': 'error',
                    'message': 'Failed to parse JSON from response',
                    'raw_response': response_text[:500]  # First 500 chars
                })
                
        except Exception as e:
            yield json.dumps({
                'type': 'error',
                'message': str(e),
                'products_analyzed': len(products)
            })
    
    def _format_products_for_analysis(self, products: List[Dict[str, Any]]) -> str:
        """
        Format products list as text for AI analysis
        
        Args:
            products: List of product dictionaries
            
        Returns:
            Formatted text string
        """
        lines = ["Part Manufacturer\tManufacturer Part #"]
        for product in products:
            manufacturer = product.get('manufacturer', '')
            part_number = product.get('part_number', '')
            lines.append(f"{manufacturer}\t{part_number}")
        
        return "\n".join(lines)
    
    def _parse_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from AI response text
        
        Args:
            response_text: Raw response text from AI
            
        Returns:
            Parsed JSON dictionary or None if parsing fails
        """
        parsed_json = None
        
        # Strategy 1: Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1))
                return parsed_json
            except json.JSONDecodeError:
                pass
        
        # Strategy 2: Try to find and parse JSON object directly (handle nested braces)
        start_idx = response_text.find('{')
        if start_idx != -1:
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(response_text)):
                if response_text[i] == '{':
                    brace_count += 1
                elif response_text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                try:
                    parsed_json = json.loads(json_str)
                    return parsed_json
                except json.JSONDecodeError:
                    pass
        
        # Strategy 3: Try parsing the entire message
        try:
            parsed_json = json.loads(response_text)
            return parsed_json
        except json.JSONDecodeError:
            pass
        
        return None

