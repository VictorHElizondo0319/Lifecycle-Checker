from typing import List, Dict, Any, Generator, Optional
import os
import sys
import json
import re
import time

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

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

        self.project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=endpoint,
        )

        # Agent identifier configured in env
        self.agent = self.project.agents.get_agent(agent_name)
        self.system_prompt = SYSTEM_PROMPT
        
        # Replacement agent (optional, falls back to main agent if not set)
        if replacement_agent_name:
            try:
                self.replacement_agent = self.project.agents.get_agent(replacement_agent_name)
            except Exception:
                # Fallback to main agent if replacement agent not found
                self.replacement_agent = self.agent
        else:
            self.replacement_agent = self.agent
        
        self.system_prompt_find_replacement = SYSTEM_PROMPT_FIND_REPLACEMENT
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def _get_assistant_message_text(self, messages) -> Optional[str]:
        """
        Extract text from assistant messages only.
        Returns the text from the last assistant message, or None if no assistant message exists.
        """
        response_text = None
        for message in reversed(list(messages)):
            # Filter by role == "assistant"
            role = getattr(message, 'role', None)
            if role != 'assistant':
                continue
            
            # Some messages may not contain text_messages
            if getattr(message, 'text_messages', None):
                try:
                    # Use last text_message chunk if available
                    last_text_msg = message.text_messages[-1]
                    # The SDK stores the text value under `.text.value`
                    text_val = getattr(getattr(last_text_msg, 'text', None), 'value', None)
                    if text_val:
                        response_text = text_val.strip()
                        break
                except Exception:
                    continue
        
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
        Analyze products with retry logic and guaranteed response.
        Always returns a deterministic result, even if no assistant message is found.
        """
        for attempt in range(self.max_retries):
            try:
                product_list_text = self._format_products_for_analysis(products)

                # Create or reuse a thread for the conversation
                if conversation_id:
                    thread_id = conversation_id
                else:
                    thread = self.project.agents.threads.create()
                    thread_id = thread.id

                # Post system prompt (only when starting a new thread)
                if not conversation_id:
                    try:
                        self.project.agents.messages.create(
                            thread_id=thread_id,
                            role="system",
                            content=self.system_prompt,
                        )
                    except Exception:
                        # Non-fatal: some agents may already have system behavior configured server-side
                        pass

                # Post user message with product list
                self.project.agents.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=product_list_text,
                )

                # Create and process a run synchronously
                run = self.project.agents.runs.create_and_process(
                    thread_id=thread_id,
                    agent_id=self.agent.id,
                )

                # Check run status - don't treat silent completion as error
                run_status = getattr(run, "status", None)
                if run_status == "failed":
                    # Only fail on explicit failure, not on completion without message
                    error_msg = getattr(run, 'last_error', 'Run failed')
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return {
                        'success': False,
                        'error': error_msg,
                        'products_analyzed': len(products)
                    }

                # Retrieve messages and find the assistant output
                messages = self.project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

                # Filter messages by role == "assistant"
                response_text = self._get_assistant_message_text(messages)

                # If no assistant message exists, inject fallback JSON
                if response_text is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    return {
                        'success': True,
                        'conversation_id': thread_id,
                        'response_text': json.dumps(fallback_json),
                        'parsed_json': fallback_json,
                        'products_analyzed': len(products)
                    }

                parsed_json = self._parse_json_from_response(response_text)

                # If JSON parsing failed, use fallback
                if parsed_json is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    return {
                        'success': True,
                        'conversation_id': thread_id,
                        'response_text': response_text or json.dumps(fallback_json),
                        'parsed_json': fallback_json,
                        'products_analyzed': len(products)
                    }

                return {
                    'success': True,
                    'conversation_id': thread_id,
                    'response_text': response_text,
                    'parsed_json': parsed_json,
                    'products_analyzed': len(products)
                }

            except Exception as e:
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
        Stream analysis results with retry logic and guaranteed response.
        Always returns a deterministic result, even if no assistant message is found.
        """
        for attempt in range(self.max_retries):
            try:
                product_list_text = self._format_products_for_analysis(products)

                # Create or reuse thread
                if conversation_id:
                    thread_id = conversation_id
                else:
                    thread = self.project.agents.threads.create()
                    thread_id = thread.id

                # Post system prompt for new threads
                if not conversation_id:
                    try:
                        self.project.agents.messages.create(
                            thread_id=thread_id,
                            role="system",
                            content=self.system_prompt,
                        )
                    except Exception:
                        pass

                # Post user message
                self.project.agents.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=product_list_text,
                )

                yield json.dumps({
                    'type': 'progress',
                    'message': f'Analyzing {len(products)} products...'
                })

                # Start the run
                run = self.project.agents.runs.create_and_process(
                    thread_id=thread_id,
                    agent_id=self.agent.id,
                )

                # Check run status - don't treat silent completion as error
                run_status = getattr(run, "status", None)
                if run_status == "failed":
                    error_msg = getattr(run, 'last_error', 'Run failed')
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    # On final failure, return fallback instead of error
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': thread_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                messages = self.project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

                # Filter messages by role == "assistant"
                response_text = self._get_assistant_message_text(messages)

                # If no assistant message exists, inject fallback JSON
                if response_text is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': thread_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                parsed_json = self._parse_json_from_response(response_text)

                # If JSON parsing failed, use fallback
                if parsed_json is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=False)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': thread_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                # Success - return parsed JSON
                yield json.dumps({
                    'type': 'result',
                    'conversation_id': thread_id,
                    'data': parsed_json,
                    'products_analyzed': len(products)
                })
                return

            except Exception as e:
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
            lines.append(f"Manufacturer: {manufacturer}\tManufacturer Part #: {part_number}\n")

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
        Find replacement parts for obsolete products using Azure AI with streaming response.
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

                # Create or reuse thread
                if conversation_id:
                    thread_id = conversation_id
                else:
                    thread = self.project.agents.threads.create()
                    thread_id = thread.id

                # Post system prompt for new threads (using replacement-specific prompt)
                if not conversation_id:
                    try:
                        self.project.agents.messages.create(
                            thread_id=thread_id,
                            role="system",
                            content=self.system_prompt_find_replacement,
                        )
                    except Exception:
                        pass

                # Post user message
                self.project.agents.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=product_list_text,
                )

                yield json.dumps({
                    'type': 'progress',
                    'message': f'Finding replacements for {len(products)} products...'
                })

                # Start the run using replacement agent
                run = self.project.agents.runs.create_and_process(
                    thread_id=thread_id,
                    agent_id=self.replacement_agent.id,
                )

                # Check run status - don't treat silent completion as error
                run_status = getattr(run, "status", None)
                if run_status == "failed":
                    error_msg = getattr(run, 'last_error', 'Run failed')
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    # On final failure, return fallback instead of error
                    fallback_json = self._generate_fallback_json(products, is_replacement=True)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': thread_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                messages = self.project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

                # Filter messages by role == "assistant"
                response_text = self._get_assistant_message_text(messages)

                # If no assistant message exists, inject fallback JSON
                if response_text is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=True)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': thread_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                parsed_json = self._parse_json_from_response(response_text)

                # If JSON parsing failed, use fallback
                if parsed_json is None:
                    fallback_json = self._generate_fallback_json(products, is_replacement=True)
                    yield json.dumps({
                        'type': 'result',
                        'conversation_id': thread_id,
                        'data': fallback_json,
                        'products_analyzed': len(products)
                    })
                    return

                # Success - return parsed JSON
                yield json.dumps({
                    'type': 'result',
                    'conversation_id': thread_id,
                    'data': parsed_json,
                    'products_analyzed': len(products)
                })
                return

            except Exception as e:
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
