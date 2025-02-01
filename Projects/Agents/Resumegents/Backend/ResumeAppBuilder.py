from flask import Flask, request, jsonify
import anthropic
import os
from ResumeAgent import ResumeAgent

app = Flask(__name__)

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf'}

resumeAgent = ResumeAgent()

@app.route('/customize-resume', methods=['POST'])
def customize_resume():
    """Endpoint to receive base64 PDF and job description"""
    
    print("Request received as: ", request)
    data = request.get_json()
    print("The data is: ", data)

    if not data or 'resume_base64' not in data or 'job_description' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing resume_base64 or job_description in request body'
        }), 400

    try:
        parsed_data = resumeAgent.parse_resume_with_claude(data['resume_base64'])
        response_data = {
            'status': 'success',
            'data': parsed_data
        }

        latex_code_resume = resumeAgent.generate_tailored_latex(parsed_data, data['current_editted_resume_json'], data['job_description'], data['instructions_or_feedback'])
        return jsonify(latex_code_resume), 200

    except anthropic.APIError as ae:
        return jsonify({
            'status': 'error',
            'message': f'Claude API error: {str(ae)}'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)