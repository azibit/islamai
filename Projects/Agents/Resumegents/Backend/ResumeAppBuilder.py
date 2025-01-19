from flask import Flask, request, jsonify, make_response
import anthropic
import os
from ResumeAgent import ResumeAgent
from flask_cors import CORS
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

resumeAgent = ResumeAgent()

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf'}

resumeAgent = ResumeAgent()

@app.route('/customize-resume', methods=['POST', 'OPTIONS'])
def customize_resume():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'success'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response
    
    try:
        data = request.get_json()
        
        if not data or 'resume_base64' not in data or 'job_description' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing resume_base64 or job_description in request body'
            }), 400

        # Parse resume with Claude
        parsed_data = resumeAgent.parse_resume_with_claude(data['resume_base64'])
        
        # Generate PDF
        pdf_bytes = resumeAgent.generate_tailored_resume(parsed_data, data['job_description'])
        
        # Create response with PDF
        response = make_response(pdf_bytes)
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment; filename=tailored_resume.pdf')
        response.headers.set('Access-Control-Allow-Origin', '*')
        
        return response

    except Exception as e:
        app.logger.error(f"Error generating resume: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Server error: {str(e)}'
        }), 500
    
if __name__ == '__main__':
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)