# APS Road Design Check

A Python Flask web application using Autodesk Platform Services (APS) for road design checking.

## Requirements

- Python 3.12
- Virtual environment

## Setup Instructions

### 1. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Autodesk Platform Services credentials:
- Get credentials at: https://aps.autodesk.com/myapps
- Set `APS_CLIENT_ID` and `APS_CLIENT_SECRET`

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

## Project Structure

```
aps-road-design-check/
├── app.py              # Main Flask application
├── Controllers/
│   ├── AuthController.py   # Authentication controller
│   └── HubsController.py   # Hubs & data browsing controller
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

Handles Autodesk OAuth authentication flow:

- `GET /api/auth/login` - Initiates OAuth login
- `GET /api/auth/callback` - OAuth callback handler
- `GET /api/auth/logout` - Logout and clear session
- `GET /api/auth/profile` - Get current user profile
- `GET /api/auth/token` - Get access token for Viewer

### HubsController ✅

Handles APS Data Management API for browsing:

- `GET /api/hubs` - List all accessible hubs
- `GET /api/hubs/{hub_id}/projects` - List projects in a hub
- `GET /api/hubs/{hub_id}/projects/{project_id}/contents` - Get folder/file contents
  - Optional query param: `?folder_id={folder_id}` (returns top-level folders if omitted)
- `GET /api/hubs/{hub_id}/projects/{project_id}/contents/{item_id}/versions` - Get file versions

## Development

The application runs with `debug=True` by default. Remember to set `debug=False` in production.

## License

See LICENSE file for details.