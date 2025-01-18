from fastapi import FastAPI, HTTPException, Depends, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
from MultiturnResumeAgent import MultiturnResumeAgent
from contextlib import asynccontextmanager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Secret key for JWT - use proper env var in production
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

# Store for active sessions
sessions: Dict[str, MultiturnResumeAgent] = {}

# Pydantic models for request/response
class SessionResponse(BaseModel):
    session_id: str
    token: str

class ChatRequest(BaseModel):
    message: str

class ResumeUploadRequest(BaseModel):
    resume_base64: str

class JobDescriptionRequest(BaseModel):
    job_description: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup: cleanup old sessions
    await cleanup_old_sessions()
    yield
    # Shutdown: cleanup old sessions again
    await cleanup_old_sessions()

# Update FastAPI initialization
app = FastAPI(lifespan=lifespan)

def create_session_token(session_id: str) -> str:
    """Create JWT token for session"""
    expiration = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(
        {"session_id": session_id, "exp": expiration},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

async def get_session_id(authorization: str = Header(...)) -> str:
    """Validate JWT and return session_id"""
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        session_id = payload.get("session_id")
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@app.post("/sessions", response_model=SessionResponse)
async def create_session():
    """Create new resume improvement session"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = MultiturnResumeAgent()
    token = create_session_token(session_id)
    return SessionResponse(session_id=session_id, token=token)

@app.post("/resume")
async def upload_resume(
    request: ResumeUploadRequest,
    session_id: str = Depends(get_session_id)
):
    """Upload and parse resume"""
    agent = sessions[session_id]
    try:
        parsed_resume = agent.parse_resume_pdf(request.resume_base64)
        return {"status": "success", "resume_data": parsed_resume}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/job-description")
async def set_job_description(
    request: JobDescriptionRequest,
    session_id: str = Depends(get_session_id)
):
    """Set job description for session"""
    agent = sessions[session_id]
    agent.job_description = request.job_description
    return {"status": "success"}

@app.post("/chat")
async def chat(
    request: ChatRequest,
    session_id: str = Depends(get_session_id)
):
    """Chat with the resume agent"""
    agent = sessions[session_id]
    try:
        response = agent.chat(request.message)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/generate-latex")
async def generate_latex(
    session_id: str = Depends(get_session_id)
):
    """Generate tailored LaTeX resume"""
    agent = sessions[session_id]
    try:
        result = agent.generate_tailored_latex()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/conversation-history")
async def get_history(
    session_id: str = Depends(get_session_id)
):
    """Get conversation history for session"""
    agent = sessions[session_id]
    return {
        "history": agent.conversation_history,
        "current_version": agent.current_resume.version_number if agent.current_resume else None
    }

# Session cleanup
async def cleanup_old_sessions():
    """Remove expired sessions"""
    now = datetime.utcnow()
    expired = []
    for session_id in sessions:
        try:
            # Check if token is expired
            token = create_session_token(session_id)
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            expired.append(session_id)
    
    for session_id in expired:
        del sessions[session_id]

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "ResumeAgentService:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload during development
    )