from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import anthropic
import base64
 
import json
import os   

@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = datetime.now()

@dataclass
class ResumeVersion:
    content: Dict  # Now stores the structured JSON resume data
    latex_content: Optional[str]  # Stores the LaTeX version
    changes_made: str
    timestamp: datetime = datetime.now()
    feedback: Optional[str] = None
    version_number: int = 0
    pdf_path: Optional[str] = None

class MultiturnResumeAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.conversation_history: List[Message] = []
        self.resume_versions: List[ResumeVersion] = []
        self.job_description: Optional[str] = None
        self.current_focus: Optional[str] = None
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv('ANTHROPIC_KEY_1'))
        
        # Load prompts
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load all prompt templates"""
        prompts = {}
        prompt_files = {
            'resume_parser': 'PROMPTS/ResumeParser.md',
            'resume_creator': 'PROMPTS/ComplexResumeCreator.md'
        }
        
        for key, filepath in prompt_files.items():
            try:
                with open(filepath, 'r') as file:
                    prompts[key] = file.read()
            except FileNotFoundError:
                prompts[key] = ""  # Fallback empty prompt if file not found
        
        return prompts
    
    def call_model(self, 
                  system_prompt: str, 
                  messages: List[Dict], 
                  model_name: str = "claude-3-5-sonnet-20241022") -> str:
        """Make a call to Claude"""
        response = self.client.messages.create(
            model=model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    
    def parse_resume_pdf(self, pdf_base64: str) -> Dict:
        """Parse PDF resume into structured JSON"""
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
        
        messages = [{"role": "user", "content": user_prompt_content}]
        
        try:
            parsed_json = self.call_model(
                system_prompt=self.prompts['resume_parser'],
                messages=messages
            )
            
            # Add the first version to our version control
            resume_data = json.loads(parsed_json)
            self.add_resume_version(
                content=resume_data,
                changes_made="Initial PDF parse",
                latex_content=None
            )
            
            return resume_data
            
        except Exception as e:
            error_msg = f"Error parsing PDF: {str(e)}"
            self._add_system_message(error_msg)
            raise
    
    def generate_tailored_latex(self, target_version: int = -1) -> Dict:
        """Generate LaTeX from the specified resume version, incorporating conversation history"""
        if not self.resume_versions or not self.job_description:
            raise ValueError("Both resume and job description are required")
            
        # Get target resume version
        resume_version = (self.resume_versions[target_version] 
                        if target_version != -1 
                        else self.current_resume)
        
        if not resume_version:
            raise ValueError("Invalid resume version")
        
        try:
            # Analyze conversation history for improvements and suggestions
            conversation_insights = self._analyze_conversation_history()
            
            # Build enhanced prompt incorporating conversation insights
            prompt = f"""Here is a job description:

    {self.job_description}

    Here is the resume data:

    {json.dumps(resume_version.content, indent=2)}

    Based on our conversation, these improvements were suggested:
    {json.dumps(conversation_insights, indent=2)}

    IMPORTANT: Create a professional LaTeX resume that STRICTLY follows these rules:
    1. Use ONLY the information provided in the resume data above and from our conversation ONLY - DO NOT add or fabricate any additional experiences, skills, or qualifications
    2. You may rephrase or reformat existing content, but must maintain complete factual accuracy
    3. Maintain professional formatting and structure

    {self.prompts['resume_creator']}

    Return only the LaTeX code."""

            system_prompt = """You are an expert resume writer with a strict commitment to accuracy. 
    Create a professional LaTeX resume using ONLY the information provided in the resume data. 
    Never add, fabricate, or enhance details beyond what is explicitly stated in the source data. 
    Focus on optimal presentation of existing information only.
    Return only the LaTeX code."""

            messages = [{"role": "user", "content": prompt}]
            
            latex_code = self.call_model(system_prompt, messages)
            
            # Validate LaTeX code
            if not latex_code.startswith('\\documentclass'):
                raise ValueError("Generated LaTeX code appears to be invalid")
            
            # Save to file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tailored_resume_{timestamp}.tex"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(latex_code)
            
            # Update resume version with LaTeX content
            resume_version.latex_content = latex_code
            
            return {
                'status': 'success',
                'message': f'LaTeX file saved as {filename}',
                'latex_code': latex_code,
                'filepath': filename,
                'improvements_applied': conversation_insights
            }
            
        except Exception as e:
            error_msg = f"Error generating LaTeX: {str(e)}"
            self._add_system_message(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }

    def _analyze_conversation_history(self) -> Dict:
        """Extract improvements and suggestions from conversation history"""
        insights = {
            'general_improvements': [],
            'section_specific': {},
            'skills_focus': [],
            'formatting': [],
            'keywords': [],
            'model_suggested_changes': [],  # New field for tracking model suggestions
            'approved_changes': []  # New field for tracking user-approved changes
        }
        
        try:
            analysis_prompt = """Carefully analyze this conversation history about a resume and extract:
    1. General improvements suggested
    2. Section-specific changes
    3. Skills to emphasize
    4. Formatting suggestions
    5. Keywords to include
    6. Model-suggested changes: Extract specific changes that I (the AI assistant) suggested during our conversation
    7. Approved changes: Note which suggestions the user explicitly agreed with or approved

    IMPORTANT:
    - Only include changes that can be made using existing information from the resume
    - For each suggestion or change, indicate whether it was:
        a) Suggested by the user
        b) Suggested by me (the AI assistant)
        c) Explicitly approved by the user
    - Do not include suggestions that would require adding new information not present in the original resume

    Return the analysis as a JSON object with the following structure:
    {
        "general_improvements": ["improvement1", "improvement2"],
        "section_specific": {"section_name": ["change1", "change2"]},
        "skills_focus": ["skill1", "skill2"],
        "formatting": ["format1", "format2"],
        "keywords": ["keyword1", "keyword2"],
        "model_suggested_changes": [
            {"suggestion": "change description", "status": "approved/pending", "source": "assistant"}
        ],
        "approved_changes": ["approved change1", "approved change2"]
    }

    Conversation:
    """
            # Add relevant conversation messages
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in self.conversation_history
                if msg['role'] in ['user', 'assistant']
            ])
            
            # Get analysis from Claude
            messages = [{
                "role": "user", 
                "content": analysis_prompt + conversation_text
            }]
            
            analysis = self.call_model(
                system_prompt="""You are an expert at analyzing resume discussions. 
                Focus on extracting concrete, actionable changes while maintaining strict accuracy. 
                Only include changes that work with existing resume information.
                Return results as properly formatted JSON.""",
                messages=messages
            )
            
            # Parse and structure the insights
            insights = json.loads(analysis)
            
        except Exception as e:
            self._add_system_message(f"Error analyzing conversation: {str(e)}")
            
        return insights
    
    @property
    def current_resume(self) -> Optional[ResumeVersion]:
        """Get the most recent version of the resume"""
        return self.resume_versions[-1] if self.resume_versions else None
    
    def add_resume_version(self, 
                          content: Dict, 
                          changes_made: str, 
                          latex_content: Optional[str] = None,
                          feedback: Optional[str] = None) -> None:
        """Add a new version of the resume"""
        version_number = len(self.resume_versions)
        new_version = ResumeVersion(
            content=content,
            latex_content=latex_content,
            changes_made=changes_made,
            feedback=feedback,
            version_number=version_number
        )
        self.resume_versions.append(new_version)
        self._add_system_message(f"New resume version {version_number} created. Resume Content {content}. Changes: {changes_made}")
    
    def _add_system_message(self, content: str) -> None:
        """Add a system message to the conversation history"""
        self.conversation_history.append(Message(role="system", content=content))
    
    def chat(self, user_message: str) -> str:
        """Handle ongoing conversation about the resume"""
        self.conversation_history.append(Message(role="user", content=user_message))
        
        context = {
            "resume": self.current_resume.content if self.current_resume else None,
            "resume_version": self.current_resume.version_number if self.current_resume else None,
            "job_description": self.job_description,
            "current_focus": self.current_focus,
             "version_info": {
                "current_version": self.current_resume.version_number if self.current_resume else None,
                "total_versions": len(self.resume_versions)
            }
        }
        
        system_prompt = f"""You are an expert resume consultant. 
Current context: {json.dumps(context, indent=2)}

Provide specific, actionable advice for improving the resume based on the conversation history.
If suggesting changes, be specific about what should be modified and why."""

        messages = [{"role": "user", "content": user_message}]
        
        try:
            response = self.call_model(system_prompt, messages)
            self.conversation_history.append(Message(role="assistant", content=response))
            return response
            
        except Exception as e:
            error_msg = f"Error in conversation: {str(e)}"
            self._add_system_message(error_msg)
            return error_msg