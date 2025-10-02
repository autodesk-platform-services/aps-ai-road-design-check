"""
OpenAI Controller
Handles PDF indexing and retrieval for OpenAI knowledge base
"""

import os
from datetime import datetime
from flask import Blueprint, request, jsonify
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Create Blueprint
openai_bp = Blueprint('openai', __name__, url_prefix='/api/openai')


def upload_to_openai(file_storage):
    """Upload PDF file to OpenAI for assistant use"""
    try:
        # OpenAI expects a tuple of (filename, file_object, content_type)
        response = client.files.create(
            file=(file_storage.filename, file_storage.stream, file_storage.content_type),
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
                'vector_store_id': vs.id,
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
        
        # Upload to OpenAI
        try:
            openai_file_id = upload_to_openai(file)
        except Exception as e:
            return jsonify({'error': f'Failed to upload to OpenAI: {str(e)}'}), 500
        
        # Create vector store for this PDF
        try:
            vector_store = client.vector_stores.create(
                name=f"{file.filename} - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Add file to the vector store
            client.vector_stores.file_batches.create(
                vector_store_id=vector_store.id,
                file_ids=[openai_file_id]
            )
            vector_store_id = vector_store.id
        except Exception as e:
            # Clean up if vector store creation fails
            try:
                client.files.delete(openai_file_id)
            except:
                pass
            return jsonify({'error': f'Failed to create vector store: {str(e)}'}), 500

        return jsonify({
            'success': True,
            'message': 'PDF indexed successfully',
            'pdf': {
                'vector_store_id': vector_store_id,
                'openai_file_id': openai_file_id,
                'filename': file.filename
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
            Use the file_search tool to find requirements in the uploaded PDF documents.
            Task: evaluate the road curve(s) described in the user's question for compliance.
            1) Extract all available curve parameters from the question (e.g., design speed, horizontal radius, superelevation rate).
            2) Search the knowledge base for the governing requirements/limits that apply to those parameters (cite document and section).
            3) Determine compliance. If any non-compliance is found, report each issue with:
               - Parameter and provided value
               - Required value or range and the threshold
               - Brief rationale (why it fails)
               - A concrete recommendation to comply (e.g., new radius/length or speed)
            4) If compliant, state that explicitly and still provide the key citations that justify it.
            5) If crucial inputs are missing or ambiguous, ask for them explicitly before concluding.
            Format:
            - Assessment
            - Violations (if any)
            - Citations
            - Recommendations
            KEEP THE ANSWER BELOW 1000 CHARACTERS
            """,
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
