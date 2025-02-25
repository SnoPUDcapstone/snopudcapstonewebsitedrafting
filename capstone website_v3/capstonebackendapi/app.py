"""
This script runs the application using a development server.
It contains the definition of routes and views for the application.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import pandas as pd
import os

app = Flask(__name__)
CORS(app)  # Enable CORS to allow frontend access
wsgi_app = app.wsgi_app  # Make WSGI available

# API route to serve CSV data
@app.route('/data', methods=['GET'])
def get_data():
    """Reads CSV and returns data as JSON."""
    try:
        df = pd.read_csv("C:/Users/dbish/OneDrive/Desktop/capstone/capstone modeling/datadayhighsolar1252025.csv")  # Replace with your actual CSV file
        data = df.to_dict(orient="records")  # Convert DataFrame to list of dictionaries
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Default route
@app.route('/')
def hello():
    """Renders a sample page."""
    return "API is running! Access data at /data"

if __name__ == '__main__':
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(host=HOST, port=PORT, debug=False)
