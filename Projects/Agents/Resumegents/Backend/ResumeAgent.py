import logging
import anthropic, base64, os, json, time
from datetime import datetime

class ResumeAgent:
    def __init__(self):
        # Configure Anthropic client
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_KEY_1'))
    
    def call_model(self, system_prompt, messages, model_name = "claude-3-5-sonnet-20241022"):
        response = self.client.messages.create(
            model=model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    
    def call_model_with_retry(self, system_prompt, messages, max_retries = 3):
        """Call the model with retry logic and better error handling"""
        attempts = 0
        while attempts < max_retries:
            try:
                response = self.call_model(system_prompt, messages)
                if response and response.strip():
                    return response.strip()
                raise Exception("Empty response received from the model")
            except Exception as e:
                attempts += 1
                if attempts == max_retries:
                    raise Exception(f"Failed to generate response after {max_retries} attempts")
                print(f"Error: {str(e)}. Retrying...")
                time.sleep(1 * attempts) # Exponential backoff
        raise Exception("Failed to generate response after multiple attempts")
    
    def validate_resume(self, resume_json):
        """Validate the resume data"""
        required_fields = ['name', 'email', 'phone', 'education', 'experience', 'skills']
        for field in required_fields:
            if field not in resume_json:
                raise ValueError(f"Field {field} is required")

    def parse_resume_with_claude(self, pdf_base64):
        """Use Claude to extract structured information from resume"""
        
        # Load the Prompt to use from the appropriate file
        with open('PROMPTS/ResumeParser.md', 'r') as file:
            system_prompt = file.read()

        # Prepare the user prompt content
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
                "text": "Extract the structured information from this resume and return it as JSON following the exact format specified:"
            }
        ]

        user_prompt_content = [
            {
                "role": "user",
                "content": user_prompt_content
            }
        ]
        
        # Call the model
        try:
            return self.call_model_with_retry(system_prompt, user_prompt_content)
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error parsing resume: {str(e)}'
            }
        
    def _get_system_prompt(self):
        return {
            'role': 'system',
            'content': """You are an expert resume writer with deep experience in LaTeX formatting. You ensure that every latex-code you deliver is ready to be used to make a resume.
            """
    #             - ALWAYS REMEMBER, For every resume you return, YOU MUST:
    # - Always ensure it fills a page unless the user requests for specific information
    # - Ensure the resume is well-formatted, focusing specifically on the Experience sections
    # - Always use the extra requests the user provides 
        }
    
    def _build_prompt(self, original_resume_json, current_editted_resume_json, job_description, instructions_or_feedback):
        """Create a structured prompt with proper error handling and consistent formatting"""
        
        sections = [
            ("Job Description", job_description),
            ("Original Resume", json.dumps(original_resume_json, indent=2))
        ]

        # Add the current editted resume if it exists
        if current_editted_resume_json:
            sections.append(("Current Editted Resume", json.dumps(current_editted_resume_json, indent=2)))

        # Add the instructions or feedback if it exists
        if instructions_or_feedback:
            sections.append(("Instructions or Feedback", instructions_or_feedback))

        # Create the prompt
        prompt = "\n\n".join(
            f"=== {title} ===\n\n{content}\n\n"
            for title, content in sections
        )

        return prompt
    
    def _load_prompt_template(self, template_path='PROMPTS/ComplexResumeCreator.md'):
        """
        Safely loads the prompt template with fallback options
        """
        try:
            with open(template_path, 'r') as file:
                return file.read().strip()
        except FileNotFoundError:
            logging.error(f"Prompt template not found at {template_path}")
            return None
        except Exception as e:
            logging.error(f"Error reading prompt template: {str(e)}")
            return None
    
    def save_resume(self, latex_code, is_backup = False):
        """Save the resume with proper error handling and backup functionality"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tailored_resume_{timestamp}.tex" if not is_backup else f"backup_resume_{timestamp}.tex"

        try:
            # Create a 'resumes' directory if it doesn't exist
            os.makedirs('resumes', exist_ok=True)
            filepath = os.path.join('resumes', filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(latex_code)
            return {
                'status': 'success',
                'message': f'LaTeX file saved as {filename}',
                'filepath': filename,
                'latex_code': latex_code
            }
        except Exception as e:
            if not is_backup:
                backup_filepath = os.path.join('resumes', f"backup_resume_{timestamp}.tex")
                backup_resume = self.save_resume(latex_code, True)
                raise Exception(f"Error saving LaTeX file: {str(e)}. Backup resume saved as {backup_filepath}")
            raise Exception(f"Error saving LaTeX file: {str(e)}")
    
    def generate_tailored_latex(self, original_resume_json, current_editted_resume_json, job_description, instructions_or_feedback):
        """
        Creates LaTeX code for a professionally formatted resume tailored to the job description.
        
        Args:
            original_resume_json (dict): Original resume data in JSON format
            current_editted_resume_json (dict): Current editted resume data in JSON format
            job_description (str): Target job description
            instructions_or_feedback (str): Instructions or feedback to the agent about the resume
        
        Returns:
            dict: Status and LaTeX code or error message
        """
        try:
            self.validate_resume(original_resume_json)
        except ValueError as e:
            return {
                'status': 'error',
                'message': f'Invalid resume data: {str(e)}'
            }

        # Create prompt
        prompt = self._build_prompt(original_resume_json, current_editted_resume_json, job_description, instructions_or_feedback)
        
        complex_resumer_creator = self._load_prompt_template()
        complex_resumer_creator += prompt
        try:
            system_prompt = self._get_system_prompt()['content']
            messages = [{"role": "user", "content": complex_resumer_creator}]

            try:
                response = self.call_model_with_retry(system_prompt, messages)
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Error generating LaTeX: {str(e)}'
                }

            latex_code = response[response.find('\\documentclass'):]
            latex_code = latex_code.strip()
            
            # Basic validation
            if not latex_code.startswith('\\documentclass'):
                return {
                    'status': 'error',
                    'latex_code': latex_code,
                    'message': 'Generated LaTeX code appears to be invalid'
                }
            
            # Save to file
            saved_result = self.save_resume(latex_code)
            
            return saved_result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error generating LaTeX: {str(e)}'
            }