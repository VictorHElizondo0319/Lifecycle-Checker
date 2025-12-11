from typing import List, Dict, Any, Generator
import os
import sys
import json
import re

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

# Ensure we can import `config` from backend
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
from config import SYSTEM_PROMPT


class AzureAIService:
    def __init__(self):
        endpoint = os.getenv("AZURE_AI_API_ENDPOINT", "")
        agent_name = os.getenv("AZURE_AI_AGENT", "")

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

    def analyze_product_chunk(self, products: List[Dict[str, Any]], conversation_id: str = None) -> Dict[str, Any]:
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

            if getattr(run, "status", None) == "failed":
                return {
                    'success': False,
                    'error': getattr(run, 'last_error', 'Run failed'),
                    'products_analyzed': len(products)
                }

            # Retrieve messages and find the assistant output
            messages = self.project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

            # Walk messages in reverse to find the last assistant text
            response_text = None
            for message in reversed(list(messages)):
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

            if response_text is None:
                # Fall back to concatenating any textual parts
                full_texts = []
                for message in messages:
                    if getattr(message, 'text_messages', None):
                        for tm in message.text_messages:
                            v = getattr(getattr(tm, 'text', None), 'value', None)
                            if v:
                                full_texts.append(v)
                response_text = "\n\n".join(full_texts).strip()

            parsed_json = self._parse_json_from_response(response_text or "")

            return {
                'success': True,
                'conversation_id': thread_id,
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

            # Start the run
            run = self.project.agents.runs.create_and_process(
                thread_id=thread_id,
                agent_id=self.agent.id,
            )

            yield json.dumps({
                'type': 'progress',
                'message': f'Analyzing {len(products)} products...'
            })

            if getattr(run, "status", None) == "failed":
                yield json.dumps({
                    'type': 'error',
                    'message': getattr(run, 'last_error', 'Run failed'),
                    'products_analyzed': len(products)
                })
                return

            messages = self.project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

            response_text = None
            for message in reversed(list(messages)):
                if getattr(message, 'text_messages', None):
                    try:
                        last_text_msg = message.text_messages[-1]
                        text_val = getattr(getattr(last_text_msg, 'text', None), 'value', None)
                        if text_val:
                            response_text = text_val.strip()
                            break
                    except Exception:
                        continue

            parsed_json = self._parse_json_from_response(response_text or "")

            if parsed_json:
                yield json.dumps({
                    'type': 'result',
                    'conversation_id': thread_id,
                    'data': parsed_json,
                    'products_analyzed': len(products)
                })
            else:
                yield json.dumps({
                    'type': 'error',
                    'message': 'Failed to parse JSON from response',
                    'raw_response': (response_text or '')[:500]
                })

        except Exception as e:
            yield json.dumps({
                'type': 'error',
                'message': str(e),
                'products_analyzed': len(products)
            })

    def _format_products_for_analysis(self, products: List[Dict[str, Any]]) -> str:
        lines = ["Part Manufacturer\tManufacturer Part #\n"]
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
