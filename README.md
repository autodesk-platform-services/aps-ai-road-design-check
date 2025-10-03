# APS Road Design Check

A Python Flask web application using Autodesk Platform Services (APS) for road design checking (Curves specifically).
This sample reads data from Department of Transportation standards and compare against the data from alignments from a Civil 3D design. It works for also for NWCs ;).

There are two ways to perform this comparision:

1. Using the `AlignmentCheckExtensionAI` extension that leverages OpenAI to verify against standards indexed from PDFs
2. Using the `AlignmentCheckExtensionJSON` extension that leverages a method 100% deterministic to verify against standards from a structured json containing the specific rules.

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

MIT