from weasyprint import HTML, CSS
import anthropic, base64, os, json
from datetime import datetime
import logging

class ResumeAgent:
    def __init__(self):
        # Configure Anthropic client
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_KEY_1'))
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
    
    def call_model(self, system_prompt, messages, model_name = "claude-3-5-sonnet-20241022"):
        response = self.client.messages.create(
            model=model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text

    def parse_resume_with_claude(self, pdf_base64):
        """Use Claude to extract structured information from resume"""
        try:
            with open('PROMPTS/ResumeParser.md', 'r') as file:
                system_prompt = file.read()

            user_prompt_content = [
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
                    "text": "Extract the structured information from this resume and return it as a valid JSON object only."
                }
            ]

            user_prompt_content = [
                {
                    "role": "user",
                    "content": user_prompt_content
                }
            ]
            
            response = self.call_model(system_prompt, user_prompt_content)
            self.logger.debug(f"Raw response from Claude: {response}")

            def transform_response(data):
                """Transform Claude's response format to our expected format"""
                transformed = {
                    "name": data["personal_info"]["name"],
                    "email": data["personal_info"]["email"],
                    "phone": data["personal_info"]["phone"],
                    "location": f"{data['personal_info']['location']['city']}, {data['personal_info']['location']['state']}, {data['personal_info']['location']['country']}",
                    "experience": [],
                    "education": [],
                    "skills": {
                        "technical": data["skills"]["technical"],
                        "soft_skills": data["skills"]["soft_skills"]
                    }
                }

                # Transform work experience
                for job in data["work_experience"]:
                    transformed["experience"].append({
                        "title": job["title"],
                        "company": job["company"],
                        "start_date": job["start_date"],
                        "end_date": job["end_date"],
                        "achievements": job.get("achievements", []) + job.get("responsibilities", [])
                    })

                # Transform education
                for edu in data["education"]:
                    transformed["education"].append({
                        "degree": f"{edu['degree']} in {edu['field_of_study']}",
                        "school": edu["institution"],
                        "graduation_date": edu["graduation_date"],
                        "gpa": str(edu.get("gpa", "")),
                        "thesis": next((h for h in edu.get("highlights", []) if "thesis" in h.lower()), "")
                    })

                return transformed

            try:
                # First, parse the raw JSON
                parsed_data = json.loads(response)
                
                # Then transform it to our expected format
                transformed_data = transform_response(parsed_data)
                
                self.logger.debug(f"Transformed data: {json.dumps(transformed_data, indent=2)}")
                return transformed_data
                
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parsing error: {str(e)}")
                self.logger.error(f"Response that failed to parse: {response}")
                raise ValueError(f"Invalid JSON from Claude: {str(e)}")
            except KeyError as e:
                self.logger.error(f"Missing required field: {str(e)}")
                raise ValueError(f"Missing required field in response: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error processing response: {str(e)}")
                raise ValueError(f"Failed to process resume data: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error in parse_resume_with_claude: {str(e)}")
            raise
    
    def generate_tailored_resume(self, resume_data, job_description):
        """
        Creates a professionally formatted PDF resume tailored to the job description.
        """
        try:
            # First, let Claude tailor the content to the job description
            system_prompt = """You are an expert resume writer. Analyze the job description and resume data, then return 
            a JSON object containing the tailored resume sections. Focus on relevant experience and skills that match the job requirements.
            Keep the same structure but prioritize and emphasize relevant experiences."""
            
            prompt = f"""Job Description:
            {job_description}

            Resume Data:
            {json.dumps(resume_data, indent=2)}

            Return a JSON object with the tailored resume content, maintaining the same structure but emphasizing relevant experiences."""

            tailored_content = self.call_model(
                system_prompt,
                [{"role": "user", "content": prompt}]
            )
            
            # Parse the tailored content
            tailored_data = json.loads(tailored_content)

            # Generate HTML with the tailored content
            html_content = self._generate_resume_html(tailored_data)
            
            # Convert to PDF
            html = HTML(string=html_content)
            css = CSS(string=self._get_resume_css())
            pdf_bytes = html.write_pdf(stylesheets=[css])
            
            return pdf_bytes

        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")
            raise

    def _generate_resume_html(self, resume_data):
        """Generate the HTML structure for the resume"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{resume_data.get('name', 'Resume')}</title>
        </head>
        <body>
            <div class="header">
                <h1>{resume_data.get('name', '')}</h1>
                <div class="contact-info">
                    <span>{resume_data.get('email', '')}</span>
                    <span>{resume_data.get('phone', '')}</span>
                    <span>{resume_data.get('location', '')}</span>
                </div>
            </div>

            <div class="section">
                <h2>Experience</h2>
                {self._generate_experience_html(resume_data.get('experience', []))}
            </div>

            <div class="section">
                <h2>Technical Skills</h2>
                {self._generate_skills_html(resume_data.get('skills', {}))}
            </div>

            <div class="section">
                <h2>Education</h2>
                {self._generate_education_html(resume_data.get('education', []))}
            </div>
        </body>
        </html>
        """

    def _generate_experience_html(self, experience):
        html = ""
        for job in experience:
            html += f"""
                <div class="experience-item">
                    <div class="job-header">
                        <span class="job-title">{job.get('title', '')}</span>
                        <span class="job-date">{job.get('start_date', '')} - {job.get('end_date', 'Present')}</span>
                    </div>
                    <div class="company">{job.get('company', '')}</div>
                    <ul>
                        {''.join(f'<li>{item}</li>' for item in job.get('achievements', []))}
                    </ul>
                </div>
            """
        return html

    def _generate_education_html(self, education):
        html = ""
        for edu in education:
            html += f"""
                <div class="education-item">
                    <div class="edu-header">
                        <span class="degree">{edu.get('degree', '')}</span>
                        <span class="date">{edu.get('graduation_date', '')}</span>
                    </div>
                    <div class="school">{edu.get('school', '')}</div>
                    {f'<div class="gpa">GPA: {edu.get("gpa", "")}</div>' if edu.get('gpa') else ''}
                    {f'<div class="thesis">Thesis: {edu.get("thesis", "")}</div>' if edu.get('thesis') else ''}
                </div>
            """
        return html

    def _generate_skills_html(self, skills):
        if isinstance(skills, dict):
            return ''.join(
                f'<div class="skill-category"><strong>{category}:</strong> {", ".join(items)}</div>'
                for category, items in skills.items()
            )
        elif isinstance(skills, list):
            return f'<div class="skills">{", ".join(skills)}</div>'
        return f'<div class="skills">{str(skills)}</div>'

    def _get_resume_css(self):
        """Get the CSS styling for the resume"""
        return """
            @page {
                size: letter;
                margin: 0.75in;
            }
            body {
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 8.5in;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                margin-bottom: 1.5em;
            }
            h1 {
                font-size: 24pt;
                margin: 0 0 0.5em 0;
                color: #2c3e50;
            }
            h2 {
                font-size: 14pt;
                color: #2c3e50;
                border-bottom: 1px solid #2c3e50;
                margin: 1.5em 0 1em 0;
            }
            .contact-info {
                font-size: 11pt;
            }
            .contact-info span {
                margin: 0 1em;
            }
            .section {
                margin-bottom: 1.5em;
            }
            .experience-item, .education-item {
                margin-bottom: 1em;
            }
            .job-header, .edu-header {
                display: flex;
                justify-content: space-between;
                font-weight: bold;
            }
            .company, .school {
                font-style: italic;
            }
            ul {
                margin: 0.5em 0;
                padding-left: 1.5em;
            }
            li {
                margin-bottom: 0.25em;
            }
            .skill-category {
                margin: 0.5em 0;
            }
        """
    
    def generate_tailored_latex(self, resume_json, job_description):
        """
        Creates LaTeX code for a professionally formatted resume tailored to the job description.
        
        Args:
            resume_json (dict): Resume data in JSON format
            job_description (str): Target job description
        
        Returns:
            dict: Status and LaTeX code or error message
        """
            
        # Create prompt
        prompt = f"Here is a job description:\n\n{job_description}\n\n"
        prompt += f"And here is the resume data:\n\n{json.dumps(resume_json, indent=2)}\n\n"

        # Load the Prompt to use from the appropriate file
        with open('PROMPTS/ComplexResumeCreator.md', 'r') as file:
            complex_resumer_creator = file.read()
        
        prompt += complex_resumer_creator

        try:
            system_prompt = "You are an expert resume writer. Create a professional LaTeX resume that highlights relevant experience for the job description. Return only the LaTeX code."
            messages = [{"role": "user", "content": prompt}]

            response = self.call_model(system_prompt, messages)

            latex_code = response.strip()
            
            # Basic validation
            if not latex_code.startswith('\\documentclass'):
                return {
                    'status': 'error',
                    'message': 'Generated LaTeX code appears to be invalid'
                }
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tailored_resume_{timestamp}.tex"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(latex_code)
            
            return {
                'status': 'success',
                'message': f'LaTeX file saved as {filename}',
                'latex_code': latex_code,
                'filepath': filename
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error generating LaTeX: {str(e)}'
            }