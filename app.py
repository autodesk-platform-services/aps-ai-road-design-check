"""
Main Flask Application
"""

import os
import sys
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

# Validate required environment variables
REQUIRED_ENV_VARS = ['APS_CLIENT_ID', 'APS_CLIENT_SECRET', 'APS_CALLBACK_URL', 'OPENAI_API_KEY']
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]

if missing_vars:
    error_msg = f"ERROR: Missing required environment variables: {', '.join(missing_vars)}\n"
    error_msg += "Please create a .env file with the following variables:\n"
    for var in REQUIRED_ENV_VARS:
        error_msg += f"  - {var}\n"
    error_msg += "\nSee .env.example for reference."
    print(error_msg, file=sys.stderr)
    sys.exit(1)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

from Controllers.AuthController import auth_bp
from Controllers.HubsController import hubs_bp
from Controllers.OpenAIController import openai_bp
from Controllers.JsonController import json_bp

app.register_blueprint(auth_bp)
app.register_blueprint(hubs_bp)
app.register_blueprint(openai_bp)
app.register_blueprint(json_bp)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)