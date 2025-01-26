# Using Python requests:
import requests
import json
import json
import anthropic
import os
from datetime import datetime

import subprocess
import os
from datetime import datetime



def generate_tailored_latex(resume_json, job_description):
    """
    Creates LaTeX code for a professionally formatted resume tailored to the job description.
    
    Args:
        resume_json (dict): Resume data in JSON format
        job_description (str): Target job description
    
    Returns:
        dict: Status and LaTeX code or error message
    """
    
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_KEY_1'))
    
      # Create prompt
    prompt = f"Here is a job description:\n\n{job_description}\n\n"
    prompt += f"And here is the resume data:\n\n{json.dumps(resume_json, indent=2)}\n\n"
    prompt += """Create a complete LaTeX resume that highlights relevant experience for this job. 
    Update the available information to match the job description. Highlight important part of the job description to match the experience I have gained.
    The LaTeX code should:
    1. Use the article document class
    2. Include necessary packages (geometry, hyperref, etc.)
    3. Have professional formatting
    4. Include all relevant sections
    5. Be ready to compile in Overleaf
    
    Return ONLY the complete LaTeX code."""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system="You are an expert resume writer. Create a professional LaTeX resume that highlights relevant experience for the job description. Return only the LaTeX code.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        latex_code = response.content[0].text.strip()
        
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

def test_resume_parser():
    # URL of your Flask application
    url = 'http://127.0.0.1:5000/parse-resume'
    
    # Path to your test resume
    resume_path = './Notebooks/Agents/AzPM.pdf'
    
    # Prepare the file for upload
    files = {
        'resume': ('resume.pdf', open(resume_path, 'rb'), 'application/pdf')
    }
    
    try:
        # Send POST request
        response = requests.post(url, files=files)

        response = response.json()
        
        # Pretty print the JSON response
        print("\nResponse:")
        # print(json.dumps(response.json(), indent=2))

        job_description = """
Meta Product Managers work with cross-functional teams of engineers, designers, data scientists and researchers to build products. We are looking for extremely entrepreneurial Product Managers with Machine Learning expertise who value moving quickly, and can help innovate and coherently drive product initiatives across the company.
Product Manager, Machine Learning Responsibilities
Display strong leadership, organizational and execution skills.
Is the primary driver for identifying significant opportunities, and driving product vision, strategies and roadmaps in the context of broader organizational strategies and goals.
Incorporate data, research and market analysis to inform product strategies and roadmaps.
Leads and motivates a team of engineers and other cross-functional representatives, and maintains team health.
Understand Facebook’s strategic and competitive position and deliver products that are aligned with our mission and recognized best in the industry.
Maximize efficiency in a constantly evolving environment where the process is fluid and creative solutions are the norm.
Minimum Qualifications
8+ years product management or related industry experience with domain specific expertise in Machine Learning
Requires a Bachelor's degree (or foreign degree equivalent) in Computer Science, Engineering, Information Systems, Analytics, Mathematics, Physics, Applied Sciences, or a related field and 2+ years of experience in the following:
Experience working in a technical environment with a broad, cross functional team to drive product vision, define product requirements, coordinate resources from other groups (design, legal, etc.), and guide the team through key milestones
Experience delivering technical presentations
Experience in analyzing complex, large-scale data sets and making decisions based on data
Experience in gathering requirements across diverse areas and users, and converting and developing them into a product solution
Displaying leadership, organizational and execution skills
Proven communication skills
Preferred Qualifications
Experience defining vision and strategy for a product.
Experience going through a full product lifecycle, integrating customer feedback into product requirements, driving prioritization and pre/post-launch execution.
Experience with leveraging ML/AI to build large scale consumer products.
Experience recruiting and leading a cross-functional team of world-class individuals.
Enthusiastic and resilient in a constantly evolving environment where the process is fluid and creative solutions are the norm.
For those who live in or expect to work from California if hired for this position, please click here for additional information.
"""

        personal_info = response
        # print(personal_info)
        res = generate_tailored_latex(personal_info, job_description)
        # res =generate_resume_pdf(personal_info, job_description)
        # res = generate_resume(personal_info, job_description)

        print(res)
        print("DONE")

        # # Save the generated LaTeX code to a file
        # with open('tailored_resume.tex', 'w') as file:
        #     file.write(res['data'])
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print("Raw response:", response.text)
        
if __name__ == "__main__":
    test_resume_parser()