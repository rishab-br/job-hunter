from pydantic import BaseModel
from typing import Optional


class NewSessionRequest(BaseModel):
    user_id: Optional[str] = None       # From GitHub OAuth (looks up username automatically)
    github_username: str = ""            # Fallback when OAuth not configured
    target_role: str
    target_market: str = "India"
    target_niche: str = ""


class RunGithubRequest(BaseModel):
    thread_id: Optional[str] = None
    user_id: Optional[str] = None       # When provided, token is looked up from Supabase
    github_username: str = ""            # Fallback
    target_role: str = ""
    target_market: str = "India"
    target_niche: str = ""


class RunModuleRequest(BaseModel):
    thread_id: str
    user_id: Optional[str] = None


class RunDiscoveryRequest(BaseModel):
    thread_id: str
    user_id: Optional[str] = None
    target_role: Optional[str] = None
    target_market: Optional[str] = None
    target_niche: Optional[str] = None


class RunPrepRequest(BaseModel):
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    github_username: str = ""
    target_role: str = ""
    target_market: str = "India"
    target_niche: str = ""
    company: str
    role: str
    jd_text: str
    company_url: str = ""
    job_id: Optional[str] = None


class InjectOfferRequest(BaseModel):
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    github_username: str = ""
    target_role: str = ""
    target_market: str = "India"
    target_niche: str = ""
    company: str
    job_title: str
    offer_letter_text: str
    deadline_date: Optional[str] = None


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool


class SaveFileRequest(BaseModel):
    path: str
    content: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # queued | running | done | failed
    thread_id: str
    error: Optional[str] = None
