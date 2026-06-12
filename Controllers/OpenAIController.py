"""
OpenAI Controller
Handles PDF indexing and retrieval using OpenAI vector stores (RAG approach).
"""

import os
import time
from datetime import datetime
from flask import Blueprint, request, jsonify
from openai import OpenAI

POLL_INTERVAL = 1    # seconds between status checks
POLL_TIMEOUT = 120   # max seconds to wait for vector store indexing

SYSTEM_PROMPT = """You are a road design standards expert.
Use the file_search tool to locate requirements in the indexed PDF documents.

Given a description of one or more horizontal curves, you must:
1. Extract every curve parameter provided (design speed, radius, superelevation, lane width, etc.) and note its unit.
2. Search the knowledge base for the governing threshold or requirement for each parameter. Cite the document name, section, and page number.
3. Compare each provided value against the required threshold and record PASS or FAIL.
4. If non-compliant, give a specific corrective action (e.g., "Increase radius from 200 ft to at least 350 ft").
5. If a required input is absent, state "Not provided" and indicate whether a compliance verdict is still possible.

Respond using this exact format:

## Assessment: [COMPLIANT | NON-COMPLIANT | INSUFFICIENT DATA]

## Parameters Checked
| Parameter | Provided | Required | Result |
|---|---|---|---|
| [name] | [value + unit] | [value + unit] | PASS / FAIL |

## Citations
- [document], Section [X], Page [Y]: "[relevant text]"

## Recommendations
- [Only if non-compliant: specific corrective actions]

Be precise with numbers and units. Do not truncate or summarise the compliance table."""

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise RuntimeError('OPENAI_API_KEY is not set')
        _client = OpenAI(api_key=api_key)
    return _client


# Create Blueprint
openai_bp = Blueprint('openai', __name__, url_prefix='/api/openai')


def _upload_file(file_storage):
    """Upload a PDF to OpenAI and return the file ID."""
    try:
        client = _get_client()
        response = client.files.create(
            file=(file_storage.filename, file_storage.stream, file_storage.content_type),
            purpose='assistants',
        )
        return response.id
    except Exception as e:
        raise Exception(f"Failed to upload to OpenAI: {str(e)}")


def _poll_batch(vector_store_id, batch_id):
    """Wait for a file batch to finish processing. Raises on failure or timeout."""
    client = _get_client()
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        batch = client.vector_stores.file_batches.retrieve(
            vector_store_id=vector_store_id,
            batch_id=batch_id,
        )
        if batch.status == 'completed':
            return batch
        if batch.status in ('failed', 'cancelled'):
            raise Exception(f"Vector store file batch ended with status: {batch.status}")
        time.sleep(POLL_INTERVAL)
    raise Exception(f"Timed out waiting for vector store indexing after {POLL_TIMEOUT}s")


@openai_bp.route('/indexedpdfs', methods=['GET'])
def get_indexed_pdfs():
    """
    GET /api/openai/indexedpdfs
    Returns list of vector stores from OpenAI (one per indexed PDF).
    """
    try:
        client = _get_client()
        vector_stores = client.vector_stores.list()
        pdfs = [
            {'vector_store_id': vs.id, 'filename': vs.name, 'created_at': vs.created_at}
            for vs in vector_stores.data
        ]
        return jsonify(pdfs), 200
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        return jsonify({'error': f'Failed to load indexed PDFs: {str(e)}'}), 500


@openai_bp.route('/indexpdf', methods=['POST'])
def index_pdf():
    """
    POST /api/openai/indexpdf
    Uploads a PDF to OpenAI and creates a vector store for semantic search.
    Polls until indexing is complete before returning (up to 120 s).
    Expects: multipart/form-data with 'file' field (PDF).
    """
    try:
        client = _get_client()
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    try:
        openai_file_id = _upload_file(file)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    try:
        vector_store = client.vector_stores.create(
            name=f"{file.filename} - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        batch = client.vector_stores.file_batches.create(
            vector_store_id=vector_store.id,
            file_ids=[openai_file_id],
        )
        _poll_batch(vector_store.id, batch.id)
    except Exception as e:
        try:
            client.files.delete(openai_file_id)
        except Exception:
            pass
        return jsonify({'error': f'Failed to create vector store: {str(e)}'}), 500

    return jsonify({
        'success': True,
        'message': 'PDF indexed and ready for querying',
        'pdf': {
            'vector_store_id': vector_store.id,
            'openai_file_id': openai_file_id,
            'filename': file.filename,
        },
    }), 200


@openai_bp.route('/query', methods=['POST'])
def query_knowledge_base():
    """
    POST /api/openai/query
    Query indexed PDFs using OpenAI Responses API with the file_search tool.
    Expects JSON: { "question": "...", "vector_store_id": optional_id }
    """
    try:
        client = _get_client()
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503

    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400

        question = data['question']
        vector_store_id = data.get('vector_store_id')

        if vector_store_id:
            try:
                vs = client.vector_stores.retrieve(vector_store_id)
                vector_store_ids = [vs.id]
                context_info = f"Using PDF: {vs.name}"
            except Exception as e:
                return jsonify({'error': f'Vector store not found: {str(e)}'}), 404
        else:
            vector_stores = client.vector_stores.list()
            vector_store_ids = [vs.id for vs in vector_stores.data]
            if not vector_store_ids:
                return jsonify({'error': 'No PDFs indexed yet. Use /api/openai/indexpdf first.'}), 400
            context_info = f"Searching {len(vector_store_ids)} indexed PDF(s)"

        response = client.responses.create(
            model='gpt-4o',
            instructions=SYSTEM_PROMPT,
            input=question,
            tools=[{
                'type': 'file_search',
                'vector_store_ids': vector_store_ids,
            }],
        )

        return jsonify({
            'success': True,
            'question': question,
            'answer': response.output_text,
            'context': context_info,
            'model': 'gpt-4o',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to query knowledge base: {str(e)}'}), 500
