from flask import Flask, request, jsonify, make_response
import anthropic
import os
from ResumeAgent import ResumeAgent
from flask_cors import CORS
import logging
import subprocess
import tempfile

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
        
        # Generate LaTeX
        latex_result = resumeAgent.generate_tailored_latex(parsed_data, data['job_description'])
        
        if latex_result['status'] != 'success':
            return jsonify({
                'status': 'error',
                'message': latex_result['message']
            }), 500

        # Convert LaTeX to PDF
        try:
            pdf_bytes = latex_to_pdf(latex_result['latex_code'])
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'PDF conversion failed: {str(e)}'
            }), 500
        
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
    app.run(debug=True)