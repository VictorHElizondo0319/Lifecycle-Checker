# Backend - Parts Lifecycle Checker

Flask backend for the Parts Lifecycle Checker application.

## Structure

```
backend/
├── api/
│   ├── excel_routes.py    # Excel upload and parsing endpoints
│   └── analyze_routes.py  # Product analysis endpoints
├── services/
│   ├── excel.service.py   # Excel parsing service
│   └── ai.service.py      # OpenAI AI analysis service
├── app.py                 # Main Flask application
├── config.py             # Configuration (system prompts)
└── requirements.txt      # Python dependencies
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the backend directory:
```
OPENAI_API_KEY=your_openai_api_key_here
```

3. Run the application:
```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

### POST /api/excel/upload
Upload and parse an Excel file.

**Request:**
- Content-Type: multipart/form-data
- Field: `file` (Excel file .xlsx or .xls)

**Response:**
```json
{
  "success": true,
  "products": [
    {
      "manufacturer": "BANNER",
      "part_number": "45136",
      "row_index": 1
    }
  ],
  "total": 10
}
```

### POST /api/analyze
Analyze products lifecycle status.

**Request:**
```json
{
  "products": [
    {
      "manufacturer": "BANNER",
      "part_number": "45136"
    }
  ],
  "stream": false
}
```

**Response (non-streaming):**
```json
{
  "success": true,
  "results": [
    {
      "manufacturer": "BANNER",
      "part_number": "45136",
      "ai_status": "Active",
      "notes_by_ai": "...",
      "ai_confidence": "High"
    }
  ],
  "total_analyzed": 10
}
```

**Response (streaming):**
Server-Sent Events (SSE) stream with JSON objects.

## Features

- Excel file parsing (supports .xlsx and .xls)
- Automatic column detection for manufacturer and part number
- Parallel processing of product chunks (30 products per chunk)
- Streaming analysis results for real-time updates
- OpenAI integration with web search capabilities

