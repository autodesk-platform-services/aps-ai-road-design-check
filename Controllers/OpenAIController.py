"""
OpenAI Controller
Handles PDF indexing and retrieval for OpenAI knowledge base
"""

import os
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI
from PyPDF2 import PdfReader

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Create Blueprint
openai_bp = Blueprint('openai', __name__, url_prefix='/api/openai')


# Ensure temp upload directory exists
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)

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
def get_indexed_pdfs():
    """
    GET /api/openai/indexedpdfs
    Returns list of vector stores from OpenAI (represents indexed PDFs)
    """
    try:
        # Get all vector stores from OpenAI
        vector_stores = client.vector_stores.list()
        
        # Transform to simplified format
        pdfs = []
        for vs in vector_stores.data:
            pdfs.append({
                'id': vs.id,
                'filename': vs.name,
                'created_at': vs.created_at
            })
        
        return jsonify(pdfs), 200
    except Exception as e:
        return jsonify({'error': f'Failed to load indexed PDFs: {str(e)}'}), 500


@openai_bp.route('/indexpdf', methods=['POST'])
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
        
        # Validate it's a valid PDF
        try:
            PdfReader(filepath)
        except Exception as e:
            # Clean up the temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Invalid PDF file: {str(e)}'}), 400
        
        # Upload to OpenAI
        try:
            openai_file_id = upload_to_openai(filepath, filename)
        except Exception as e:
            # Clean up the temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Failed to upload to OpenAI: {str(e)}'}), 500
        
        # Create vector store for this PDF
        try:
            vector_store = client.vector_stores.create(
                name=f"{filename} - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Add file to the vector store
            client.vector_stores.file_batches.create(
                vector_store_id=vector_store.id,
                file_ids=[openai_file_id]
            )
            vector_store_id = vector_store.id
        except Exception as e:
            # Clean up if vector store creation fails
            if os.path.exists(filepath):
                os.remove(filepath)
            try:
                client.files.delete(openai_file_id)
            except:
                pass
            return jsonify({'error': f'Failed to create vector store: {str(e)}'}), 500
        
        # Delete the local file after successful upload to OpenAI
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({
            'success': True,
            'message': 'PDF indexed successfully',
            'pdf': {
                'vector_store_id': vector_store_id,
                'openai_file_id': openai_file_id,
                'filename': filename
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to index PDF: {str(e)}'}), 500


@openai_bp.route('/query', methods=['POST'])
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
        vector_store_id = data.get('vector_store_id')
        openai_file_id = data.get('openai_file_id')
        
        # Get vector store IDs from OpenAI
        if vector_store_id:
            # Use specific vector store
            try:
                vs = client.vector_stores.retrieve(vector_store_id)
                vector_store_ids = [vs.id]
                context_info = f"Using PDF: {vs.name}"
            except Exception as e:
                return jsonify({'error': f'Vector store not found: {str(e)}'}), 404
        else:
            # Use all vector stores
            try:
                vector_stores = client.vector_stores.list()
                vector_store_ids = [vs.id for vs in vector_stores.data]
                if not vector_store_ids:
                    return jsonify({'error': 'No PDFs indexed yet'}), 400
                context_info = f"Using {len(vector_store_ids)} indexed PDF(s)"
            except Exception as e:
                return jsonify({'error': f'Failed to list vector stores: {str(e)}'}), 500
        
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
                "vector_store_ids": vector_store_ids
            }]
        )
        
        return jsonify({
            'success': True,
            'question': question,
            'answer': response.output_text,
            'context': context_info,
            'model': 'gpt-4o'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to query knowledge base: {str(e)}'}), 500


@openai_bp.route('/pdf/<vector_store_id>', methods=['DELETE'])
def delete_pdf(vector_store_id):
    """
    DELETE /api/openai/pdf/{vector_store_id}
    Removes a PDF by deleting its vector store from OpenAI
    """
    try:
        # Delete vector store from OpenAI (this also removes associated files)
        client.vector_stores.delete(vector_store_id)
        
        return jsonify({
            'success': True,
            'message': 'PDF deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete PDF: {str(e)}'}), 500
