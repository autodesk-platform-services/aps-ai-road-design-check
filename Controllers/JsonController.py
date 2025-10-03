"""
JSON Controller
Handles JSON file upload and returns the JSON object
"""

import os
import json
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

# Create Blueprint
json_bp = Blueprint('json', __name__, url_prefix='/api/json')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'json'}

@json_bp.route('/upload', methods=['POST'])
def upload_json():
    """
    POST /api/json/upload
    Receives a JSON file and returns the parsed JSON object
    """
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    
    try:
        # Read the file content
        file_content = file.read()
        
        # Parse JSON
        json_data = json.loads(file_content.decode('utf-8'))
        
        # Return the JSON object
        return jsonify({
            'success': True,
            'filename': secure_filename(file.filename),
            'data': json_data
        }), 200
        
    except json.JSONDecodeError as e:
        return jsonify({
            'error': 'Invalid JSON format',
            'details': str(e)
        }), 400
    except UnicodeDecodeError as e:
        return jsonify({
            'error': 'Unable to decode file',
            'details': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Failed to process file',
            'details': str(e)
        }), 500