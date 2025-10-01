# APS Road Design Check

A Python Flask web application using Autodesk Platform Services (APS) for road design checking.

# THIS IS A WORK IN PROGRESS

## Requirements

- Python 3.12
- Virtual environment

## Setup Instructions

### 1. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
- **Autodesk Platform Services**: Get credentials at https://aps.autodesk.com/myapps
  - Set `APS_CLIENT_ID` and `APS_CLIENT_SECRET`
- **OpenAI API**: Get your API key at https://platform.openai.com/api-keys
  - Set `OPENAI_API_KEY`

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e .
```

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:8080`

**Note:** The application will automatically validate that all required environment variables are set. If any are missing, it will exit with a clear error message indicating which variables need to be configured.

## Project Structure

```
aps-road-design-check/
├── app.py              # Main Flask application
├── Controllers/
│   ├── AuthController.py   # Authentication controller
│   ├── HubsController.py   # Hubs & data browsing controller
│   └── OpenAIController.py # PDF indexing for OpenAI
├── uploads/
│   └── temp/           # Temporary PDF uploads (gitignored)
├── templates/
│   └── index.html      # Single page application
├── static/
│   ├── main.css        # Main stylesheet
│   ├── main.js         # Main JavaScript
│   ├── sidebar.js      # Sidebar tree logic
│   └── viewer.js       # APS Viewer logic
├── .env.example        # Environment variables template
├── pyproject.toml      # Project configuration & dependencies
└── README.md           # This file
```

## Architecture

This project uses a simple Flask structure based on the Autodesk Platform Services hub browser pattern:

- **View** (`templates/index.html`): Single page interface with sidebar and viewer
- **Static Assets** (`static/`): CSS and JavaScript modules
- **Routes** (`app.py`): Flask routes - controllers will be added incrementally

## Features

- APS Viewer integration for 3D model viewing
- Tree navigation for browsing hubs, projects, and files
- Authentication with Autodesk accounts
- Responsive design

## Controllers

### AuthController ✅

Handles Autodesk OAuth authentication flow with automatic token refresh:

- `GET /api/auth/login` - Initiates OAuth login
- `GET /api/auth/callback` - OAuth callback handler
  - Exchanges authorization code for tokens
  - Stores access token, refresh token, and expiration time
- `GET /api/auth/logout` - Logout and clear session
- `GET /api/auth/profile` - Get current user profile
- `GET /api/auth/token` - Get access token for Viewer
  - Auto-refreshes token if expired or expiring soon (within 5 minutes)
- `POST /api/auth/refresh` - Manually refresh the access token

### HubsController ✅

Handles APS Data Management API for browsing:

- `GET /api/hubs` - List all accessible hubs
- `GET /api/hubs/{hub_id}/projects` - List projects in a hub
- `GET /api/hubs/{hub_id}/projects/{project_id}/contents` - Get folder/file contents
  - Optional query param: `?folder_id={folder_id}` (returns top-level folders if omitted)
- `GET /api/hubs/{hub_id}/projects/{project_id}/contents/{item_id}/versions` - Get file versions

### OpenAIController ✅

Handles PDF indexing for OpenAI knowledge base using the [OpenAI Python library](https://pypi.org/project/openai/2.0.0/):

- `GET /api/openai/indexedpdfs` - List all indexed PDFs from OpenAI vector stores
- `POST /api/openai/indexpdf` - Upload and index a new PDF
  - Accepts: `multipart/form-data` with `file` field
  - Extracts text from PDF using PyPDF2
  - Uploads file to OpenAI
  - Creates vector store for semantic search
  - No local metadata storage - everything in OpenAI
  - Removes temporary file after upload
- `POST /api/openai/query` - Query the knowledge base using OpenAI Responses API
  - Accepts: JSON with `{ "question": "your question", "pdf_id": optional_id }`
  - Uses file_search tool to search PDFs directly in OpenAI
  - No local downloads - uses files already uploaded to OpenAI
  - Returns AI-generated answer with document citations
- `DELETE /api/openai/pdf/{pdf_id}` - Remove a PDF from index
  - Deletes file from OpenAI

## Development

### Running in Debug Mode

**Option 1: VS Code Debugger (Recommended)**

1. Open the project in VS Code
2. Go to Run and Debug (Ctrl+Shift+D)
3. Select "Python: Flask" from the dropdown
4. Press F5 or click "Start Debugging"
5. Set breakpoints by clicking left of line numbers
6. Application will start at `http://localhost:8080`

**Option 2: Terminal**

```bash
python app.py
```

The application runs with `debug=True` by default. Remember to set `debug=False` in production.

### Debug Configurations

- **Python: Flask** - Debug with auto-reload (reloads on file changes)
- **Python: Flask (No Reload)** - Debug without auto-reload (better for breakpoint debugging)
- **Python: Current File** - Debug the currently open Python file

## License

See LICENSE file for details.