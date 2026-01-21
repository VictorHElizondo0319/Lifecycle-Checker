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


class AzureAIService:
    def __init__(self):
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
                        print(f"DEBUG: Error extracting from text_messages: {e}")
                
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
                        print(f"DEBUG: Found assistant message with {len(text_val)} characters")
                        break
                        
            except Exception as e:
                print(f"DEBUG: Error processing message: {e}")
                continue
        
        if not response_text:
            print(f"DEBUG: No assistant message found. Total messages: {len(messages_list)}")
            # Debug: Print first few messages to understand structure
            for i, msg in enumerate(messages_list[-3:]):  # Last 3 messages
                print(f"DEBUG: Message {i}: role={getattr(msg, 'role', 'N/A')}, type={getattr(msg, 'type', 'N/A')}, has_text_messages={hasattr(msg, 'text_messages')}")
        
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

                # Get response text directly
                response_text = getattr(response, 'output_text', None)
                if response_text:
                    response_text = response_text.strip()

                # Get response ID for conversation continuity
                response_id = getattr(response, 'id', None) or conversation_id

                # If no response text, use fallback
                if not response_text:
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
                print(f"DEBUG: Error in analyze_product_chunk (attempt {attempt + 1}): {e}")
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
                    'products_analyzed': len(products)
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

                # Get response text directly
                response_text = getattr(response, 'output_text', None)
                if response_text:
                    response_text = response_text.strip()

                # Get response ID for conversation continuity
                response_id = getattr(response, 'id', None) or conversation_id

                # If no response text, use fallback
                if not response_text:
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

                # Get response text directly
                response_text = getattr(response, 'output_text', None)
                if response_text:
                    response_text = response_text.strip()

                # Get response ID for conversation continuity
                response_id = getattr(response, 'id', None) or conversation_id

                # If no response text, use fallback
                if not response_text:
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
