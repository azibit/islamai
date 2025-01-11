from flask import Flask, request, jsonify
import anthropic
import base64
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure Anthropic client
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_KEY_1'))

# Configure upload settings
UPLOAD_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = {'pdf'}



def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_pdf_as_base64(file_path):
    """Convert PDF file to base64 string"""
    with open(file_path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')

def parse_resume_with_claude(pdf_base64):
    """Use Claude to extract structured information from resume"""
    
    system_prompt = """You are a resume parser that extracts structured information from resumes. 
    Analyze the provided resume and return a JSON object with EXACTLY the following structure:
    
    {
        "personal_info": {
            "name": "string",
            "email": "string",
            "phone": "string",
            "location": {
                "city": "string",
                "state": "string",
                "country": "string"
            },
            "linkedin": "string (optional)"
        },
        "education": [
            {
                "institution": "string",
                "degree": "string",
                "field_of_study": "string",
                "graduation_date": "string (MM/YYYY)",
                "gpa": "float (optional)",
                "highlights": ["string"]
            }
        ],
        "work_experience": [
            {
                "company": "string",
                "title": "string",
                "location": "string",
                "start_date": "string (MM/YYYY)",
                "end_date": "string (MM/YYYY or 'Present')",
                "responsibilities": ["string"],
                "achievements": ["string"]
            }
        ],
        "skills": {
            "technical": ["string"],
            "soft_skills": ["string"],
            "languages": ["string"],
            "certifications": ["string"]
        }
    }

    Important:
    1. Follow this structure exactly
    2. Do not add any additional fields
    3. Use null for missing optional fields
    4. Return ONLY the JSON object with no additional text
    5. Ensure all dates are in MM/YYYY format
    6. Convert any bullet points into array items
    7. Separate technical and soft skills"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": "Extract the structured information from this resume and return it as JSON following the exact format specified:"
                    }
                ]
            }
        ]
    )

    return response.content[0].text

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
            parsed_data = parse_resume_with_claude(pdf_base64)
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