from flask import Flask, request, jsonify
import anthropic
import base64
import os
from werkzeug.utils import secure_filename
from ResumeAgentsFunctions import ResumeAgentsFunctions

app = Flask(__name__)

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf'}

resumeAgent = ResumeAgentsFunctions()

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_pdf_as_base64(file_path):
    """Convert PDF file to base64 string"""
    with open(file_path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')


@app.route('/parse-resume', methods=['POST'])
def parse_resume():
    """Endpoint to receive and parse resume PDFs"""
    
    # Validate request has file
    if 'resume' not in request.files:
        return jsonify({
            'status': 'error',
            'message': 'No resume file provided'
        }), 400
    
    file = request.files['resume']
    
    # Validate filename
    if file.filename == '':
        return jsonify({
            'status': 'error',
            'message': 'No selected file'
        }), 400
    
    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({
            'status': 'error',
            'message': 'File must be a PDF'
        }), 400

    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Convert PDF to base64
        try:
            pdf_base64 = read_pdf_as_base64(file_path)
            parsed_data = resumeAgent.parse_resume_with_claude(pdf_base64)
            response_data = {
                'status': 'success',
                'data': parsed_data
            }
            status_code = 200
        except anthropic.APIError as ae:
            response_data = {
                'status': 'error',
                'message': f'Claude API error: {str(ae)}'
            }
            status_code = 500

        # Clean up temporary file
        os.remove(file_path)
        
        return jsonify(response_data), status_code

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)