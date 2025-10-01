"""
OpenAI Controller
Handles PDF indexing and retrieval for OpenAI knowledge base
"""

import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from functools import wraps
from werkzeug.utils import secure_filename
from openai import OpenAI
from PyPDF2 import PdfReader

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Create Blueprint
openai_bp = Blueprint('openai', __name__, url_prefix='/api/openai')

# Configuration
TEMP_UPLOAD_FOLDER = 'uploads/temp'
INDEXED_PDFS_FILE = 'uploads/indexed_pdfs.json'
ALLOWED_EXTENSIONS = {'pdf'}

# Ensure temp upload directory exists
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_indexed_pdfs():
    """Load the list of indexed PDFs from JSON file"""
    if os.path.exists(INDEXED_PDFS_FILE):
        with open(INDEXED_PDFS_FILE, 'r') as f:
            return json.load(f)
    return []


def save_indexed_pdfs(pdfs):
    """Save the list of indexed PDFs to JSON file"""
    os.makedirs(os.path.dirname(INDEXED_PDFS_FILE), exist_ok=True)
    with open(INDEXED_PDFS_FILE, 'w') as f:
        json.dump(pdfs, f, indent=2)


def extract_text_from_pdf(filepath):
    """Extract text content from PDF file"""
    try:
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def upload_to_openai(filepath, filename):
    """Upload PDF file to OpenAI for assistant use"""
    try:
        with open(filepath, 'rb') as file:
            response = client.files.create(
                file=file,
                purpose='assistants'
            )
        return response.id
    except Exception as e:
        raise Exception(f"Failed to upload to OpenAI: {str(e)}")


@openai_bp.route('/indexedpdfs', methods=['GET'])
@require_auth
def get_indexed_pdfs():
    """
    GET /api/openai/indexedpdfs
    Returns list of indexed PDFs available as knowledge base
    """
    try:
        pdfs = load_indexed_pdfs()
        return jsonify(pdfs), 200
    except Exception as e:
        return jsonify({'error': f'Failed to load indexed PDFs: {str(e)}'}), 500


@openai_bp.route('/indexpdf', methods=['POST'])
@require_auth
def index_pdf():
    """
    POST /api/openai/indexpdf
    Indexes a new PDF file for use as OpenAI knowledge base
    Expects: multipart/form-data with 'file' field
    """
    try:
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        # Check if file was actually selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Secure the filename and save to temp location
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(TEMP_UPLOAD_FOLDER, temp_filename)
        
        file.save(filepath)
        
        # Extract text from PDF and get metadata
        try:
            pdf_text = extract_text_from_pdf(filepath)
            page_count = len(PdfReader(filepath).pages)
        except Exception as e:
            # Clean up the temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Failed to process PDF: {str(e)}'}), 400
        
        # Upload to OpenAI
        try:
            openai_file_id = upload_to_openai(filepath, filename)
        except Exception as e:
            # Clean up the temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Failed to upload to OpenAI: {str(e)}'}), 500
        
        # Delete the local file after successful upload to OpenAI
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Load existing indexed PDFs
        pdfs = load_indexed_pdfs()
        
        # Create new PDF entry with OpenAI metadata (no local filepath)
        pdf_id = len(pdfs) + 1
        new_pdf = {
            'id': pdf_id,
            'filename': filename,
            'openai_file_id': openai_file_id,
            'page_count': page_count,
            'text_length': len(pdf_text),
            'indexed_at': datetime.now().isoformat(),
            'indexed_by': session['user'].get('name', 'Unknown')
        }
        
        # Add to list and save
        pdfs.append(new_pdf)
        save_indexed_pdfs(pdfs)
        
        return jsonify({
            'success': True,
            'message': 'PDF indexed successfully',
            'pdf': {
                'id': new_pdf['id'],
                'filename': new_pdf['filename']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to index PDF: {str(e)}'}), 500


@openai_bp.route('/query', methods=['POST'])
@require_auth
def query_knowledge_base():
    """
    POST /api/openai/query
    Query the indexed PDFs using OpenAI Responses API with file_search tool
    Expects JSON: { "question": "your question", "pdf_id": optional_pdf_id }
    Uses PDFs already uploaded to OpenAI - no local downloads
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400
        
        question = data['question']
        pdf_id = data.get('pdf_id')  # Optional: specific PDF to query
        
        # Load indexed PDFs
        pdfs = load_indexed_pdfs()
        
        if not pdfs:
            return jsonify({'error': 'No PDFs indexed yet'}), 400
        
        # Get file IDs to use (PDFs already in OpenAI - no download needed)
        if pdf_id:
            # Use specific PDF
            selected_pdf = next((pdf for pdf in pdfs if pdf['id'] == int(pdf_id)), None)
            if not selected_pdf:
                return jsonify({'error': 'PDF not found'}), 404
            file_ids = [selected_pdf['openai_file_id']]
            context_info = f"Using PDF: {selected_pdf['filename']}"
        else:
            # Use all indexed PDFs
            file_ids = [pdf['openai_file_id'] for pdf in pdfs if 'openai_file_id' in pdf]
            context_info = f"Using {len(file_ids)} indexed PDF(s)"
        
        # Create a vector store with the files
        vector_store = client.vector_stores.create(
            name=f"Query-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        # Add files to the vector store
        client.vector_stores.file_batches.create(
            vector_store_id=vector_store.id,
            file_ids=file_ids
        )
        
        # Use Responses API with file_search tool
        response = client.responses.create(
            model="gpt-4o",
            instructions="""You are a helpful assistant specialized in road design standards and regulations.
            Use the file_search tool to find relevant information in the uploaded PDF documents.
            When answering questions:
            1. Always cite the specific document and section
            2. Provide clear, accurate answers based on the documents
            3. If the answer is not in the documents, clearly state that
            4. Quote relevant passages when helpful""",
            input=question,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store.id]
            }]
        )
        
        # Clean up vector store
        try:
            client.beta.vector_stores.delete(vector_store.id)
        except Exception as cleanup_error:
            print(f"Cleanup warning: {cleanup_error}")
        
        return jsonify({
            'success': True,
            'question': question,
            'answer': response.output_text,
            'context': context_info,
            'model': 'gpt-4o'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to query knowledge base: {str(e)}'}), 500


@openai_bp.route('/pdf/<int:pdf_id>', methods=['DELETE'])
@require_auth
def delete_pdf(pdf_id):
    """
    DELETE /api/openai/pdf/{pdf_id}
    Removes a PDF from the indexed list
    """
    try:
        pdfs = load_indexed_pdfs()
        
        # Find the PDF
        pdf_to_delete = None
        for pdf in pdfs:
            if pdf['id'] == pdf_id:
                pdf_to_delete = pdf
                break
        
        if not pdf_to_delete:
            return jsonify({'error': 'PDF not found'}), 404
        
        # Delete from OpenAI
        if 'openai_file_id' in pdf_to_delete:
            try:
                client.files.delete(pdf_to_delete['openai_file_id'])
            except Exception as e:
                return jsonify({'error': f'Failed to delete file from OpenAI: {str(e)}'}), 500
        
        # Remove from metadata list
        pdfs = [pdf for pdf in pdfs if pdf['id'] != pdf_id]
        save_indexed_pdfs(pdfs)
        
        return jsonify({
            'success': True,
            'message': 'PDF deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete PDF: {str(e)}'}), 500
