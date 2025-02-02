from flask import Flask, request, jsonify, send_file
import anthropic
import os
from ResumeAgent import ResumeAgent
from flask_cors import CORS
import logging
import subprocess
import tempfile
from io import BytesIO

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

resumeAgent = ResumeAgent()

def latex_to_pdf(latex_code):
    """Convert LaTeX code to PDF using pdflatex"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temporary tex file
        tex_path = os.path.join(tmpdir, 'resume.tex')
        with open(tex_path, 'w') as f:
            f.write(latex_code)
        
        # Run pdflatex twice to resolve references
        for _ in range(2):
            process = subprocess.Popen(
                ['pdflatex', '-interaction=nonstopmode', tex_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=tmpdir
            )
            process.communicate()
        
        # Read the generated PDF
        pdf_path = os.path.join(tmpdir, 'resume.pdf')
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                return f.read()
        else:
            raise Exception("PDF generation failed")

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
        latex_result = resumeAgent.generate_tailored_latex(
            parsed_data, 
            data.get('current_editted_resume_json', {}),
            data['job_description'],
            data.get('instructions_or_feedback', '')
        )
        
        return jsonify({
            'status': 'success',
            'data': parsed_data,
            'latex_code': latex_result.get('latex_code', latex_result)  # Handle both string and object responses
        }), 200

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
    
@app.route('/get-pdf', methods=['POST'])
def get_pdf():
    """Endpoint to convert LaTeX code to PDF"""
    data = request.get_json()
    
    # Validate input
    if not data or 'latex_code' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing latex_code in request body'
        }), 400
        
    try:
        # Convert LaTeX to PDF using the provided function
        pdf_bytes = latex_to_pdf(data['latex_code'])
        
        # Convert bytes to BytesIO object for send_file
        pdf_blob = BytesIO(pdf_bytes)
        pdf_blob.seek(0)
        
        # Return the PDF file
        return send_file(
            pdf_blob,
            mimetype='application/pdf',
            as_attachment=False,
            download_name='resume.pdf'
        )
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'PDF generation error: {str(e)}'
        }), 500
    
if __name__ == '__main__':
    app.run(debug=True)