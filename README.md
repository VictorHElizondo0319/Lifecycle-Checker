# Lifecycle Checker

A full-stack application for checking automation parts lifecycle status using AI.

## Project Structure

```
Lifecycle-Checker/
├── frontend/          # Next.js + TypeScript + Tailwind CSS
├── backend/           # Flask Python backend
│   ├── api/          # API routes
│   ├── services/     # Business logic services
│   └── app.py        # Main Flask application
├── app/               # Electron desktop application
│   ├── main.js       # Electron main process
│   ├── preload.js    # Preload script
│   └── package.json  # Electron configuration
└── README.md
```

## Application Versions

This project provides two ways to run the application:

1. **Web Application** - Run backend and frontend separately (see setup below)
2. **Desktop Application** - Electron app that bundles everything (see `app/` directory)

### Desktop Application (Electron)

For a standalone desktop application, see the `app/` directory:

```bash
cd app
npm install
npm start
```

See `app/README.md` and `app/SETUP.md` for detailed instructions.

### Web Application

For running as separate web services:

## Features

- Upload Excel files (.xlsx, .xls) with product lists
- Automatic parsing of manufacturer and part number columns
- AI-powered lifecycle status analysis using OpenAI
- Real-time streaming analysis results
- Parallel processing for better performance
- Modern, responsive UI built with Next.js and Tailwind CSS

## Setup

### Backend

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
```

4. Run the Flask server:
```bash
python app.py
```

The backend will run on `http://localhost:5000`

### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file (optional, defaults to localhost:5000):
```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

4. Run the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

## Workflow

1. **Upload Excel File**: User uploads an Excel file containing product information
2. **Parse Products**: Backend parses the Excel file and extracts product list
3. **Display Products**: Frontend displays the parsed products in a table
4. **Analyze**: User clicks "Analyze Products" button
5. **Processing**: Backend splits products into chunks (30 per chunk) and processes them in parallel
6. **Streaming Results**: Analysis results are streamed back to the frontend in real-time
7. **Display Results**: Results are displayed in a table with status, notes, and confidence levels

## Technology Stack

### Frontend
- Next.js 14+ (App Router)
- TypeScript
- Tailwind CSS
- React

### Backend
- Flask
- OpenAI API
- Pandas (Excel parsing)
- Python 3.8+

## API Endpoints

- `POST /api/excel/upload` - Upload and parse Excel file
- `POST /api/analyze` - Analyze products lifecycle status (supports streaming)

See `backend/README.md` for detailed API documentation.
