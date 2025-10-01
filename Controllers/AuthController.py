"""
Authentication Controller
Handles Autodesk OAuth authentication flow
"""

import os
import time
import requests
from flask import Blueprint, redirect, request, session, jsonify
from urllib.parse import urlencode

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# APS OAuth configuration
APS_CLIENT_ID = os.getenv('APS_CLIENT_ID', '')
APS_CLIENT_SECRET = os.getenv('APS_CLIENT_SECRET', '')
APS_CALLBACK_URL = os.getenv('APS_CALLBACK_URL', 'http://localhost:8080/api/auth/callback')
APS_SCOPES = ['data:read','data:write']

AUTODESK_AUTH_URL = 'https://developer.api.autodesk.com/authentication/v2/authorize'
AUTODESK_TOKEN_URL = 'https://developer.api.autodesk.com/authentication/v2/token'
AUTODESK_USERINFO_URL = 'https://api.userprofile.autodesk.com/userinfo'


def refresh_access_token():
    """
    Refresh the access token using the refresh token
    Returns True if successful, False otherwise
    """
    if 'refresh_token' not in session:
        return False
    
    token_data = {
        'grant_type': 'refresh_token',
        'refresh_token': session['refresh_token'],
        'client_id': APS_CLIENT_ID,
        'client_secret': APS_CLIENT_SECRET
    }
    
    try:
        response = requests.post(AUTODESK_TOKEN_URL, data=token_data)
        response.raise_for_status()
        
        token_response = response.json()
        
        # Update tokens in session
        session['access_token'] = token_response.get('access_token')
        session['expires_in'] = token_response.get('expires_in')
        session['token_expires_at'] = time.time() + token_response.get('expires_in', 3600)
        
        # Update refresh token if a new one is provided
        if 'refresh_token' in token_response:
            session['refresh_token'] = token_response.get('refresh_token')
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to refresh token: {str(e)}")
        return False


def is_token_expired():
    """
    Check if the access token is expired or about to expire (within 5 minutes)
    """
    if 'token_expires_at' not in session:
        return True
    
    # Consider token expired if it expires within 5 minutes
    return time.time() >= (session['token_expires_at'] - 300)


@auth_bp.route('/login')
def login():
    """
    Initiates the OAuth login flow
    Redirects user to Autodesk login page
    """
    # Build authorization URL
    params = {
        'response_type': 'code',
        'client_id': APS_CLIENT_ID,
        'redirect_uri': APS_CALLBACK_URL,
        'scope': ' '.join(APS_SCOPES)
    }
    
    auth_url = f"{AUTODESK_AUTH_URL}?{urlencode(params)}"
    return redirect(auth_url)


@auth_bp.route('/callback')
def callback():
    """
    OAuth callback endpoint
    Exchanges authorization code for access token
    """
    # Get authorization code from query params
    code = request.args.get('code')
    
    if not code:
        return jsonify({'error': 'No authorization code received'}), 400
    
    # Exchange code for token
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': APS_CLIENT_ID,
        'client_secret': APS_CLIENT_SECRET,
        'redirect_uri': APS_CALLBACK_URL
    }
    
    try:
        # Request access token
        response = requests.post(AUTODESK_TOKEN_URL, data=token_data)
        response.raise_for_status()
        
        token_response = response.json()
        
        # Store tokens in session
        session['access_token'] = token_response.get('access_token')
        session['refresh_token'] = token_response.get('refresh_token')
        session['expires_in'] = token_response.get('expires_in', 3600)
        session['token_expires_at'] = time.time() + session['expires_in']
        
        # Get user profile
        headers = {'Authorization': f"Bearer {session['access_token']}"}
        user_response = requests.get(AUTODESK_USERINFO_URL, headers=headers)
        user_response.raise_for_status()
        
        user_data = user_response.json()
        session['user'] = {
            'name': user_data.get('name'),
            'email': user_data.get('email'),
            'userId': user_data.get('sub')
        }
        
        # Redirect to home page
        return redirect('/')
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Authentication failed: {str(e)}'}), 500


@auth_bp.route('/logout')
def logout():
    """
    Logs out the user by clearing the session
    """
    session.clear()
    return redirect('/')


@auth_bp.route('/profile')
def profile():
    """
    Returns the current user's profile
    """
    if 'user' in session:
        return jsonify(session['user']), 200
    else:
        return jsonify({'error': 'Not authenticated'}), 401


@auth_bp.route('/token')
def token():
    """
    Returns the access token for the APS Viewer
    Auto-refreshes the token if it's expired or about to expire
    """
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Check if token is expired and refresh if needed
    if is_token_expired():
        if not refresh_access_token():
            # If refresh fails, user needs to login again
            session.clear()
            return jsonify({'error': 'Token expired, please login again'}), 401
    
    return jsonify({
        'access_token': session['access_token'],
        'expires_in': session.get('expires_in', 3600)
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Manually refresh the access token
    """
    if 'refresh_token' not in session:
        return jsonify({'error': 'No refresh token available'}), 401
    
    if refresh_access_token():
        return jsonify({
            'success': True,
            'message': 'Token refreshed successfully',
            'expires_in': session.get('expires_in', 3600)
        }), 200
    else:
        session.clear()
        return jsonify({'error': 'Failed to refresh token, please login again'}), 401
