import anthropic, base64, os, json
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
        return self.call_model(system_prompt, user_prompt_content)
    
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