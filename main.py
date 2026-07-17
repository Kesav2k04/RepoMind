from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import asyncio

from master import orchestrate_analysis
from schemas import AgentsConfiguration

app = FastAPI(title="RepoMind Orchestrator", description="Multi-Agent Codebase Analyzer")

class AnalyzeRequest(BaseModel):
    repo_url: str

class AnalysisStatus(BaseModel):
    job_id: str
    status: str
    result: AgentsConfiguration | None = None

# In-memory store for demo purposes
jobs = {}

@app.post("/api/analyze", response_model=AnalysisStatus)
async def start_analysis(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    job_id = f"job_{len(jobs) + 1}"
    jobs[job_id] = {"status": "running", "result": None}
    
    # Run the heavy orchestration in the background
    background_tasks.add_task(run_analysis_task, job_id, request.repo_url)
    
    return AnalysisStatus(job_id=job_id, status="running")

async def run_analysis_task(job_id: str, repo_url: str):
    try:
        # Pass control to Terra Master Agent
        final_config = await orchestrate_analysis(repo_url)
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = final_config
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

@app.get("/api/analyze/{job_id}", response_model=AnalysisStatus)
async def get_analysis_status(job_id: str):
    if job_id not in jobs:
        return AnalysisStatus(job_id=job_id, status="not_found")
    return AnalysisStatus(
        job_id=job_id,
        status=jobs[job_id]["status"],
        result=jobs[job_id].get("result")
    )
