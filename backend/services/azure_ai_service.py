from typing import List, Dict, Any, Generator, Optional
import os
import sys
import json
import re
import time

from azure.ai.projects import AIProjectClient
from azure.identity import ClientSecretCredential

# Ensure we can import `config` from backend
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from config import SYSTEM_PROMPT, SYSTEM_PROMPT_FIND_REPLACEMENT
from services.analysis_logger import log_debug, log_info, log_error


class AzureAIService:
    def __init__(self):
        # Debug: Log environment variable status
        log_debug("Checking environment variables...")
        log_debug("AZURE_AI_API_ENDPOINT exists: {}", bool(os.getenv('AZURE_AI_API_ENDPOINT')))
        log_debug("AZURE_AI_AGENT exists: {}", bool(os.getenv('AZURE_AI_AGENT')))
        log_debug("AZURE_TENANT_ID exists: {}", bool(os.getenv('AZURE_TENANT_ID')))
        log_debug("AZURE_CLIENT_ID exists: {}", bool(os.getenv('AZURE_CLIENT_ID')))
        log_debug("AZURE_CLIENT_SECRET exists: {}", bool(os.getenv('AZURE_CLIENT_SECRET')))
        
        endpoint = os.getenv("AZURE_AI_API_ENDPOINT", "")
        agent_name = os.getenv("AZURE_AI_AGENT", "")
        replacement_agent_name = os.getenv("AZURE_AI_REPLACEMENT_AGENT", "")

        if not endpoint:
            raise RuntimeError("AZURE_AI_API_ENDPOINT is not set")
        if not agent_name:
            raise RuntimeError("AZURE_AI_AGENT is not set")

        # Get Service Principal credentials from environment variables
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")

        if not tenant_id:
            raise RuntimeError(
                "AZURE_TENANT_ID is not set. Please configure Azure Service Principal credentials.\n"
                "Required environment variables: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET"
            )
        if not client_id:
            raise RuntimeError(
                "AZURE_CLIENT_ID is not set. Please configure Azure Service Principal credentials.\n"
                "Required environment variables: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET"
            )
        if not client_secret:
            raise RuntimeError(
                "AZURE_CLIENT_SECRET is not set. Please configure Azure Service Principal credentials.\n"
                "Required environment variables: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET"
            )

        # Initialize Azure credentials using Service Principal (no Azure CLI required)
        try:
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
        except Exception as e:
            # If ClientSecretCredential fails, provide a helpful error message
            error_msg = (
                f"Failed to initialize Azure credentials: {str(e)}\n"
                "Please ensure Azure Service Principal credentials are correctly configured.\n"
                "Required environment variables: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET"
            )
            raise RuntimeError(error_msg) from e

        try:
            self.project = AIProjectClient(
                credential=credential,
                endpoint=endpoint,
            )

            # Get OpenAI client from project client
            self.openai_client = self.project.get_openai_client()

            # Agent identifier configured in env
            self.agent = self.project.agents.get(agent_name=agent_name)
            self.agent_name = agent_name
            self.system_prompt = SYSTEM_PROMPT
        except Exception as e:
            # If project/client initialization fails, provide helpful error
            error_msg = (
                f"Failed to initialize Azure AI Project Client: {str(e)}\n"
                "Please check your Azure credentials and configuration."
            )
            raise RuntimeError(error_msg) from e
        
        # Replacement agent (optional, falls back to main agent if not set)
        if replacement_agent_name:
            try:
                self.replacement_agent = self.project.agents.get(agent_name=replacement_agent_name)
                self.replacement_agent_name = replacement_agent_name
            except Exception:
                # Fallback to main agent if replacement agent not found
                self.replacement_agent = self.agent
                self.replacement_agent_name = agent_name
        else:
            self.replacement_agent = self.agent
            self.replacement_agent_name = agent_name
        
        self.system_prompt_find_replacement = SYSTEM_PROMPT_FIND_REPLACEMENT
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def _get_assistant_message_text(self, messages) -> Optional[str]:
        """
        Extract text from assistant messages only.
        Returns the text from the last assistant message, or None if no assistant message exists.
        """
        response_text = None
        
        # Convert messages to list for iteration
        messages_list = list(messages) if messages else []
        
        # Debug: Print message structure to understand what we're working with
        if not messages_list:
            print("DEBUG: No messages found in thread")
            return None
        
        # Try multiple strategies to find assistant messages
        for message in reversed(messages_list):
            try:
                # Strategy 1: Check role attribute (case-insensitive)
                role = getattr(message, 'role', None)
                if role:
                    role_lower = str(role).lower()
                    if role_lower not in ['assistant', 'agent']:
                        continue
                
                # Strategy 2: Check message type or category
                msg_type = getattr(message, 'type', None) or getattr(message, 'message_type', None)
                if msg_type:
                    msg_type_lower = str(msg_type).lower()
                    if msg_type_lower not in ['assistant', 'agent', 'ai']:
                        continue
                
                # Strategy 3: If no role/type filtering, check if it's not user/system
                if not role and not msg_type:
                    # Skip if it's clearly a user message
                    if hasattr(message, 'content') and isinstance(message.content, str):
                        # Heuristic: user messages often start with "Manufacturer:" based on our format
                        if message.content.startswith('Manufacturer:'):
                            continue
                
                # Extract text from message
                # Try multiple ways to get the text content
                text_val = None
                
                # Method 1: text_messages array
                if hasattr(message, 'text_messages') and message.text_messages:
                    try:
                        last_text_msg = message.text_messages[-1]
                        if hasattr(last_text_msg, 'text'):
                            text_obj = last_text_msg.text
                            if hasattr(text_obj, 'value'):
                                text_val = text_obj.value
                            elif isinstance(text_obj, str):
                                text_val = text_obj
                        elif isinstance(last_text_msg, str):
                            text_val = last_text_msg
                    except Exception as e:
                        log_debug("Error extracting from text_messages: {}", str(e))
                
                # Method 2: content attribute directly
                if not text_val and hasattr(message, 'content'):
                    content = message.content
                    if isinstance(content, str):
                        text_val = content
                    elif isinstance(content, dict):
                        text_val = content.get('text') or content.get('value')
                
                # Method 3: text attribute directly
                if not text_val and hasattr(message, 'text'):
                    text_obj = message.text
                    if isinstance(text_obj, str):
                        text_val = text_obj
                    elif hasattr(text_obj, 'value'):
                        text_val = text_obj.value
                
                if text_val:
                    text_val = str(text_val).strip()
                    if text_val:  # Only return non-empty text
                        response_text = text_val
                        log_debug("Found assistant message with {} characters", len(text_val))
                        break
                        
            except Exception as e:
                log_debug("Error processing message: {}", str(e))
                continue
        
        if not response_text:
            log_debug("No assistant message found. Total messages: {}", len(messages_list))
            # Debug: Log first few messages to understand structure
            for i, msg in enumerate(messages_list[-3:]):  # Last 3 messages
                log_debug("Message {}: role={}, type={}, has_text_messages={}", 
                         i, getattr(msg, 'role', 'N/A'), getattr(msg, 'type', 'N/A'), hasattr(msg, 'text_messages'))
        
        return response_text

    def _generate_fallback_json(self, products: List[Dict[str, Any]], is_replacement: bool = False) -> Dict[str, Any]:
        """
        Generate a fallback JSON response when no assistant message is found.
        This ensures we always return a deterministic result.
        """
        if is_replacement:
            from datetime import datetime
            return {
                "checked_date": datetime.now().strftime("%Y-%m-%d"),
                "results": [
                    {
                        "obsolete_part_number": product.get('manufacturer_part_number') or product.get('part_number', ''),
                        "manufacturer": product.get('part_manufacturer') or product.get('manufacturer', ''),
                        "recommended_replacement": None,
                        "replacement_manufacturer": None,
                        "price": None,
                        "currency": None,
                        "source_type": "None",
                        "source_url": "",
                        "notes": "No assistant message received. Analysis incomplete.",
                        "confidence": "Low"
                    }
                    for product in products
                ]
            }
        else:
            return {
                "results": [
                    {
                        "manufacturer": product.get('part_manufacturer') or product.get('manufacturer', ''),
                        "part_number": product.get('manufacturer_part_number') or product.get('part_number', ''),
                        "ai_status": "Review",
                        "notes_by_ai": "No assistant message received. Analysis incomplete.",
                        "ai_confidence": "Low"
                    }
                    for product in products
                ]
            }

    def analyze_product_chunk(self, products: List[Dict[str, Any]], conversation_id: str = None) -> Dict[str, Any]:
        """
        Analyze products using OpenAI client with agent reference.
        Always returns a deterministic result, even if no assistant message is found.
        """
        for attempt in range(self.max_retries):
            try:
                product_list_text = self._format_products_for_analysis(products)

                # Prepare input messages
                input_messages = [
                    {"role": "user", "content": product_list_text}
                ]

                # Prepare extra_body with agent reference
                extra_body = {
                    "agent": {
                        "name": self.agent_name,
                        "type": "agent_reference"
                    }
                }

                # Add previous_response_id for conversation continuity if available
                if conversation_id:
                    extra_body["previous_response_id"] = conversation_id

                # Call OpenAI client with agent reference
                response = self.openai_client.responses.create(
                    input=input_messages,
                    extra_body=extra_body
                )

                # Debug: Log response object details
                log_debug("Response object type: {}", type(response))
                log_debug("Response object attributes: {}", [attr for attr in dir(response) if not attr.startswith('_')])
                
                # Try multiple ways to get response text
                response_text = None
                
                # Method 1: Try output_text attribute
                if hasattr(response, 'output_text'):
                    response_text = getattr(response, 'output_text', None)
                    log_debug("output_text found: {}, length: {}", response_text is not None, len(response_text) if response_text else 0)
                
                # Method 2: Try output attribute
                if not response_text and hasattr(response, 'output'):
                    output = getattr(response, 'output', None)
                    if output:
                        if isinstance(output, str):
                            response_text = output
                        elif hasattr(output, 'text'):
                            response_text = getattr(output, 'text', None)
                        elif isinstance(output, list) and len(output) > 0:
                            # Try to get text from first item
                            first_item = output[0]
                            if hasattr(first_item, 'text'):
                                response_text = getattr(first_item, 'text', None)
                            elif isinstance(first_item, dict) and 'text' in first_item:
                                response_text = first_item.get('text')
                        log_debug("output attribute found: {}", response_text is not None)
                
                # Method 3: Try to get from messages
                if not response_text and hasattr(response, 'messages'):
                    messages = getattr(response, 'messages', None)
                    if messages:
                        response_text = self._get_assistant_message_text(messages)
                        log_debug("messages found, extracted text: {}", response_text is not None)
                
                # Method 4: Try to serialize and look for text
                if not response_text:
                    try:
                        response_dict = response.__dict__ if hasattr(response, '__dict__') else {}
                        # Look for common text fields
                        for key in ['text', 'content', 'message', 'output_text', 'response_text']:
                            if key in response_dict:
                                value = response_dict[key]
                                if isinstance(value, str) and value.strip():
                                    response_text = value
                                    log_debug("Found text in {}", key)
                                    break
                    except Exception as e:
                        log_error("Error inspecting response dict: {}", str(e))
                
                # Clean up response text
                if response_text:
                    response_text = response_text.strip()
                    log_debug("Final response_text length: {}", len(response_text))
                else:
                    log_error("No response text found. Response object: {}", str(response))
                    # Try to log response as string for debugging
                    try:
                        response_str = str(response)[:500]
                        log_debug("Response str representation: {}", response_str)
                    except Exception as e:
                        log_error("Error converting response to string: {}", str(e))

                # Get response ID for conversation continuity
                response_id = getattr(response, 'id', None) or conversation_id

                # If no response text, use fallback
                if not response_text:
                    log_error("No response text found, using fallback")
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    return {
                        'success': True,
                        'conversation_id': response_id,
                        'response_text': json.dumps(fallback_json),
                        'parsed_json': fallback_json,
                        'products_analyzed': len(products)
                    }

                # Parse JSON from response
                parsed_json = self._parse_json_from_response(response_text)

                # If JSON parsing failed, use fallback
                if parsed_json is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    return {
                        'success': True,
                        'conversation_id': response_id,
                        'response_text': response_text or json.dumps(fallback_json),
                        'parsed_json': fallback_json,
                        'products_analyzed': len(products)
                    }

                return {
                    'success': True,
                    'conversation_id': response_id,
                    'response_text': response_text,
                    'parsed_json': parsed_json,
                    'products_analyzed': len(products)
                }

            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                log_error("Error in analyze_product_chunk (attempt {}): {}", attempt + 1, str(e))
                log_error("Full traceback:\n{}", error_trace)
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                # On final attempt failure, return fallback
                fallback_json = self._generate_fallback_json(products, is_replacement=False)
                return {
                    'success': True,
                    'conversation_id': conversation_id,
                    'response_text': json.dumps(fallback_json),
                    'parsed_json': fallback_json,
                    'products_analyzed': len(products),
                    'error': str(e)  # Include error for debugging
                }
        
        # Should never reach here, but just in case
        fallback_json = self._generate_fallback_json(products, is_replacement=False)
        return {
            'success': True,
            'conversation_id': conversation_id,
            'response_text': json.dumps(fallback_json),
            'parsed_json': fallback_json,
            'products_analyzed': len(products)
        }

    def analyze_product_chunk_streaming(self, products: List[Dict[str, Any]], conversation_id: str = None) -> Generator[str, None, None]:
        """
        Stream analysis results using OpenAI client with agent reference.
        Always returns a deterministic result, even if no assistant message is found.
        """
        for attempt in range(self.max_retries):
            try:
                product_list_text = self._format_products_for_analysis(products)

                yield json.dumps({
                    'type': 'progress',
                    'message': f'Analyzing {len(products)} products...'
                })

                # Prepare input messages
                input_messages = [
                    {"role": "user", "content": product_list_text}
                ]

                # Prepare extra_body with agent reference
                extra_body = {
                    "agent": {
                        "name": self.agent_name,
                        "type": "agent_reference"
                    }
                }

                # Add previous_response_id for conversation continuity if available
                if conversation_id:
                    extra_body["previous_response_id"] = conversation_id

                # Call OpenAI client with agent reference
                response = self.openai_client.responses.create(
                    input=input_messages,
                    extra_body=extra_body
                )

                # Try multiple ways to get response text (same as analyze_product_chunk)
                response_text = None
                
                # Method 1: Try output_text attribute
                if hasattr(response, 'output_text'):
                    response_text = getattr(response, 'output_text', None)
                
                # Method 2: Try output attribute
                if not response_text and hasattr(response, 'output'):
                    output = getattr(response, 'output', None)
                    if output:
                        if isinstance(output, str):
                            response_text = output
                        elif hasattr(output, 'text'):
                            response_text = getattr(output, 'text', None)
                        elif isinstance(output, list) and len(output) > 0:
                            first_item = output[0]
                            if hasattr(first_item, 'text'):
                                response_text = getattr(first_item, 'text', None)
                            elif isinstance(first_item, dict) and 'text' in first_item:
                                response_text = first_item.get('text')
                
                # Method 3: Try to get from messages
                if not response_text and hasattr(response, 'messages'):
                    messages = getattr(response, 'messages', None)
                    if messages:
                        response_text = self._get_assistant_message_text(messages)
                
                # Method 4: Try to serialize and look for text
                if not response_text:
                    try:
                        response_dict = response.__dict__ if hasattr(response, '__dict__') else {}
                        for key in ['text', 'content', 'message', 'output_text', 'response_text']:
                            if key in response_dict:
                                value = response_dict[key]
                                if isinstance(value, str) and value.strip():
                                    response_text = value
                                    break
                    except Exception:
                        pass
                
                # Clean up response text
                if response_text:
                    response_text = response_text.strip()

                # Get response ID for conversation continuity
                response_id = getattr(response, 'id', None) or conversation_id

                # If no response text, use fallback
                if not response_text:
                    log_error("No response text in streaming, using fallback")
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': response_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                # Parse JSON from response
                parsed_json = self._parse_json_from_response(response_text)

                # If JSON parsing failed, use fallback
                if parsed_json is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': response_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                # Success - return parsed JSON
                yield json.dumps({
                    'type': 'result',
                    'conversation_id': response_id,
                    'data': parsed_json,
                    'products_analyzed': len(products)
                })
                return

            except Exception as e:
                print(f"DEBUG: Error in analyze_product_chunk_streaming (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                # On final attempt failure, return fallback instead of error
                fallback_json = self._generate_fallback_json(products, is_replacement=False)
                yield json.dumps({
                    'type': 'result',
                    'conversation_id': conversation_id,
                    'data': fallback_json,
                    'products_analyzed': len(products)
                })
                return
        
        # Should never reach here, but just in case
        fallback_json = self._generate_fallback_json(products, is_replacement=False)
        yield json.dumps({
            'type': 'result',
            'conversation_id': conversation_id,
            'data': fallback_json,
            'products_analyzed': len(products)
        })

    def _format_products_for_analysis(self, products: List[Dict[str, Any]]) -> str:
        lines = [""]
        for product in products:
            manufacturer = (
                product.get('part_manufacturer', '') or 
                product.get('manufacture', '') or 
                product.get('manufacturer', '')
            )
            part_number = (
                product.get('manufacturer_part_number', '') or 
                product.get('part_number', '') or
                product.get('part_number_ai_modified', '')
            )
            lines.append(f"{manufacturer}\t{part_number}\n")

        return "\n".join(lines)

    def _parse_json_from_response(self, response_text: str) -> Dict[str, Any]:
        parsed_json = None
        print(response_text)
        # Strategy 1: JSON code block
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1))
                return parsed_json
            except json.JSONDecodeError:
                pass

        # Strategy 2: Find balanced braces
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

        # Strategy 3: Try parsing entire message
        try:
            parsed_json = json.loads(response_text)
            return parsed_json
        except json.JSONDecodeError:
            pass

        return None

    def find_replacement_chunk_streaming(self, products: List[Dict[str, Any]], conversation_id: str = None) -> Generator[str, None, None]:
        """
        Find replacement parts for obsolete products using OpenAI client with agent reference.
        Always returns a deterministic result, even if no assistant message is found.
        
        Args:
            products: List of product dictionaries to find replacements for
            conversation_id: Optional conversation ID for context
            
        Yields:
            JSON strings containing partial or complete replacement finding results
        """
        for attempt in range(self.max_retries):
            try:
                product_list_text = self._format_products_for_analysis(products)

                yield json.dumps({
                    'type': 'progress',
                    'message': f'Finding replacements for {len(products)} products...'
                })

                # Prepare input messages
                input_messages = [
                    {"role": "user", "content": product_list_text}
                ]

                # Prepare extra_body with replacement agent reference
                extra_body = {
                    "agent": {
                        "name": self.replacement_agent_name,
                        "type": "agent_reference"
                    }
                }

                # Add previous_response_id for conversation continuity if available
                if conversation_id:
                    extra_body["previous_response_id"] = conversation_id

                # Call OpenAI client with agent reference
                response = self.openai_client.responses.create(
                    input=input_messages,
                    extra_body=extra_body
                )

                # Try multiple ways to get response text (same as analyze_product_chunk)
                response_text = None
                
                # Method 1: Try output_text attribute
                if hasattr(response, 'output_text'):
                    response_text = getattr(response, 'output_text', None)
                
                # Method 2: Try output attribute
                if not response_text and hasattr(response, 'output'):
                    output = getattr(response, 'output', None)
                    if output:
                        if isinstance(output, str):
                            response_text = output
                        elif hasattr(output, 'text'):
                            response_text = getattr(output, 'text', None)
                        elif isinstance(output, list) and len(output) > 0:
                            first_item = output[0]
                            if hasattr(first_item, 'text'):
                                response_text = getattr(first_item, 'text', None)
                            elif isinstance(first_item, dict) and 'text' in first_item:
                                response_text = first_item.get('text')
                
                # Method 3: Try to get from messages
                if not response_text and hasattr(response, 'messages'):
                    messages = getattr(response, 'messages', None)
                    if messages:
                        response_text = self._get_assistant_message_text(messages)
                
                # Method 4: Try to serialize and look for text
                if not response_text:
                    try:
                        response_dict = response.__dict__ if hasattr(response, '__dict__') else {}
                        for key in ['text', 'content', 'message', 'output_text', 'response_text']:
                            if key in response_dict:
                                value = response_dict[key]
                                if isinstance(value, str) and value.strip():
                                    response_text = value
                                    break
                    except Exception:
                        pass
                
                # Clean up response text
                if response_text:
                    response_text = response_text.strip()

                # Get response ID for conversation continuity
                response_id = getattr(response, 'id', None) or conversation_id

                # If no response text, use fallback
                if not response_text:
                    log_error("No response text in replacement streaming, using fallback")
                    fallback_json = self._generate_fallback_json(products, is_replacement=True)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': response_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                # Parse JSON from response
                parsed_json = self._parse_json_from_response(response_text)

                # If JSON parsing failed, use fallback
                if parsed_json is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=True)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': response_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                # Success - return parsed JSON
                yield json.dumps({
                    'type': 'result',
                    'conversation_id': response_id,
                    'data': parsed_json,
                    'products_analyzed': len(products)
                })
                return

            except Exception as e:
                print(f"DEBUG: Error in find_replacement_chunk_streaming (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                # On final attempt failure, return fallback instead of error
                fallback_json = self._generate_fallback_json(products, is_replacement=True)
                yield json.dumps({
                    'type': 'result',
                    'conversation_id': conversation_id,
                    'data': fallback_json,
                    'products_analyzed': len(products)
                })
                return
        
        # Should never reach here, but just in case
        fallback_json = self._generate_fallback_json(products, is_replacement=True)
        yield json.dumps({
            'type': 'result',
            'conversation_id': conversation_id,
            'data': fallback_json,
            'products_analyzed': len(products)
        })
