from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import json
import re
from dotenv import load_dotenv
from config import SYSTEM_PROMPT
# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# System prompt for parts lifecycle checking

# Store conversation IDs by session (Responses API can keep server-side state)
session_conversations = {}

@app.route("/")
def index():
    # optional template
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json or {}
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id", "default")

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Pull existing conversation for this session (if any)
        conversation_id = session_conversations.get(session_id)

        # Use Responses API with web search tool enabled (no external scraping libs)
        resp = client.responses.create(
            model="gpt-4.1",                 # or "gpt-4.1-mini"
            instructions=SYSTEM_PROMPT,      # system prompt goes here
            input=user_message,              # user content goes here
            tools=[{"type": "web_search"}],  # built-in web search tool
            conversation=conversation_id,    # thread continuity (optional)
            max_output_tokens=2500,
            temperature=0.2,
        )

        # Save/refresh conversation id so subsequent turns keep context
        if getattr(resp, "conversation_id", None):
            session_conversations[session_id] = resp.conversation_id

        # Get the full text response
        assistant_message = resp.output_text.strip()
        original_message = assistant_message
        
        # Try to extract JSON from the response
        parsed_json = None
        
        # Strategy 1: Look for JSON in markdown code blocks first
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', assistant_message, re.DOTALL)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1))
                assistant_message = json_match.group(1)  # Use extracted JSON
            except json.JSONDecodeError:
                pass
        
        # Strategy 2: Try to find and parse JSON object directly (handle nested braces)
        if not parsed_json:
            # Find the first { and try to match braces
            start_idx = assistant_message.find('{')
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(assistant_message)):
                    if assistant_message[i] == '{':
                        brace_count += 1
                    elif assistant_message[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                if end_idx > start_idx:
                    json_str = assistant_message[start_idx:end_idx]
                    try:
                        parsed_json = json.loads(json_str)
                        assistant_message = json_str
                    except json.JSONDecodeError:
                        pass
        
        # Strategy 3: Try parsing the entire message
        if not parsed_json:
            try:
                parsed_json = json.loads(assistant_message)
            except json.JSONDecodeError:
                pass
        
        # If we successfully parsed JSON, validate and return
        if parsed_json and isinstance(parsed_json, dict) and "results" in parsed_json:
            # Validate that results is an array and each item has required fields
            results = parsed_json.get("results", [])
            if isinstance(results, list) and len(results) > 0:
                # Check if first result has the required fields
                first_result = results[0] if results else {}
                required_fields = ["manufacturer", "part_number", "ai_status", "notes_by_ai", "ai_confidence"]
                if all(field in first_result for field in required_fields):
                    return jsonify({
                        "response": assistant_message,  # Keep extracted JSON string
                        "json_data": parsed_json,       # Parsed JSON for frontend
                        "session_id": session_id,
                        "format": "json"
                    })
        
        # Fallback: return as plain text
        print(f"JSON parsing failed. Response preview: {original_message[:200]}...")
        return jsonify({
            "response": original_message,
            "session_id": session_id,
            "format": "text"
        })

    except Exception as e:
        # Helpful error surface
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/clear", methods=["POST"])
def clear_history():
    try:
        data = request.json or {}
        session_id = data.get("session_id", "default")
        if session_id in session_conversations:
            del session_conversations[session_id]
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
