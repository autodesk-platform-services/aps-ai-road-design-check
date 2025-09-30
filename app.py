"""
Main Flask Application
"""

import os
from flask import Flask, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Register Controllers
from Controllers.AuthController import auth_bp
from Controllers.HubsController import hubs_bp

app.register_blueprint(auth_bp)
app.register_blueprint(hubs_bp)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)