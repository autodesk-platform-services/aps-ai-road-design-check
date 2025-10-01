"""
Hubs Controller
Handles APS Data Management API for browsing hubs, projects, and files
"""

import os
import requests
from flask import Blueprint, session, jsonify, request
from functools import wraps

# Create Blueprint
hubs_bp = Blueprint('hubs', __name__, url_prefix='/api/hubs')

# APS API endpoints
APS_BASE_URL = 'https://developer.api.autodesk.com'
ACC_ISSUES_BASE = 'https://developer.api.autodesk.com/construction/issues/v1'


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_headers():
    """Get authorization headers for APS API calls"""
    return {
        'Authorization': f"Bearer {session['access_token']}",
        'Content-Type': 'application/json'
    }


@hubs_bp.route('')
@require_auth
def get_hubs():
    """
    GET /api/hubs
    Returns list of hubs accessible by the user
    """
    try:
        url = f"{APS_BASE_URL}/project/v1/hubs"
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        
        data = response.json()
        
        # Transform to simplified format
        hubs = []
        for item in data.get('data', []):
            hubs.append({
                'id': item['id'],
                'name': item['attributes']['name']
            })
        
        return jsonify(hubs), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch hubs: {str(e)}'}), 500


@hubs_bp.route('/<hub_id>/projects')
@require_auth
def get_projects(hub_id):
    """
    GET /api/hubs/{hub_id}/projects
    Returns list of projects in a hub
    """
    try:
        url = f"{APS_BASE_URL}/project/v1/hubs/{hub_id}/projects"
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        
        data = response.json()
        
        # Transform to simplified format
        projects = []
        for item in data.get('data', []):
            projects.append({
                'id': item['id'],
                'name': item['attributes']['name']
            })
        
        return jsonify(projects), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch projects: {str(e)}'}), 500


@hubs_bp.route('/<hub_id>/projects/<project_id>/contents')
@require_auth
def get_contents(hub_id, project_id):
    """
    GET /api/hubs/{hub_id}/projects/{project_id}/contents?folder_id={folder_id}
    Returns contents of a folder (or top-level folders if no folder_id)
    """
    folder_id = request.args.get('folder_id')
    
    try:
        if folder_id:
            # Get folder contents
            url = f"{APS_BASE_URL}/data/v1/projects/{project_id}/folders/{folder_id}/contents"
        else:
            # Get top-level folders
            url = f"{APS_BASE_URL}/project/v1/hubs/{hub_id}/projects/{project_id}/topFolders"
        
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        
        data = response.json()
        
        # Transform to simplified format
        contents = []
        for item in data.get('data', []):
            item_type = item['type']
            
            if item_type == 'folders':
                contents.append({
                    'id': item['id'],
                    'name': item['attributes']['name'],
                    'folder': True
                })
            elif item_type == 'items':
                contents.append({
                    'id': item['id'],
                    'name': item['attributes']['displayName'],
                    'folder': False
                })
        
        return jsonify(contents), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch contents: {str(e)}'}), 500


@hubs_bp.route('/<hub_id>/projects/<project_id>/contents/<item_id>/versions')
@require_auth
def get_versions(hub_id, project_id, item_id):
    """
    GET /api/hubs/{hub_id}/projects/{project_id}/contents/{item_id}/versions
    Returns versions of an item
    """
    try:
        url = f"{APS_BASE_URL}/data/v1/projects/{project_id}/items/{item_id}/versions"
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        
        data = response.json()
        
        # Transform to simplified format
        versions = []
        for item in data.get('data', []):
            version_number = item['attributes'].get('versionNumber', 1)
            create_time = item['attributes'].get('createTime', '')
            
            versions.append({
                'id': item['id'],
                'name': f"v{version_number} ({create_time[:10] if create_time else 'Unknown'})"
            })
        
        return jsonify(versions), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch versions: {str(e)}'}), 500


@hubs_bp.route('/projects/<project_id>/issues', methods=['POST'])
@require_auth
def create_issue(project_id):
    """
    Creates an ACC issue in the specified project.
    """
    payload = request.get_json() or {}

    # Minimal validation
    title = payload.get('title')
    issue_type_id = payload.get('issue_subtype_id')
    if not title or not issue_type_id:
        return jsonify({'error': 'title and issue_subtype_id are required'}), 400

    try:
        # Prefer project-based endpoint
        url = f"{ACC_ISSUES_BASE}/projects/{project_id}/issues"
        body = {
            'title': title,
            'description': payload.get('description'),
            'issueSubtypeId': issue_type_id,
            'status': payload.get('status')
        }

        # Remove None values to satisfy API schema
        body = {k: v for k, v in body.items() if v is not None}

        response = requests.post(url, headers=get_headers(), json=body)
        response.raise_for_status()

        return jsonify(response.json()), 201

    except requests.exceptions.HTTPError as http_err:
        # Fallback to container-based creation if server indicates project path not allowed
        if payload.get('container_id'):
            try:
                container_url = f"{ACC_ISSUES_BASE}/containers/{payload['container_id']}/issues"
                response = requests.post(container_url, headers=get_headers(), json=body)
                response.raise_for_status()
                return jsonify(response.json()), 201
            except requests.exceptions.RequestException as e:
                return jsonify({'error': f'Failed to create issue via container: {str(e)}'}), 500
        return jsonify({'error': f'Failed to create issue: {str(http_err)}', 'details': response.text if 'response' in locals() else ''}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to create issue: {str(e)}'}), 500

