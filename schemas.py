from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ArchitectureReport(BaseModel):
    patterns_identified: List[str] = Field(description="List of architectural patterns found (e.g., MVC, Singleton).")
    primary_language: str = Field(description="Primary programming language used.")
    frameworks: List[str] = Field(description="Major frameworks or libraries detected.")
    summary: str = Field(description="Brief summary of the architecture.")

class RiskReport(BaseModel):
    vulnerabilities: List[str] = Field(description="Potential security vulnerabilities.")
    technical_debt: List[str] = Field(description="Areas of significant technical debt.")
    risk_score: int = Field(description="Overall risk score from 1-10.")

class TestingReport(BaseModel):
    coverage_estimate: int = Field(description="Estimated test coverage percentage.")
    test_frameworks: List[str] = Field(description="Testing frameworks identified.")
    missing_tests: List[str] = Field(description="Critical areas missing test coverage.")

class HistoryReport(BaseModel):
    frequent_contributors: List[str] = Field(description="Top contributors to the repository.")
    churn_files: List[str] = Field(description="Files that change most frequently.")
    recent_major_changes: List[str] = Field(description="Recent major architectural or logic changes.")

class WorkerResponse(BaseModel):
    agent_role: str = Field(description="The role of the worker agent (e.g., architecture, risk, testing, history).")
    data: Dict[str, Any] = Field(description="The structured report data.")
    confidence: float = Field(description="Confidence score of the analysis (0.0 to 1.0).")

class AgentsConfiguration(BaseModel):
    repository_name: str
    optimal_model: str = Field(description="The optimal model to use for this codebase.")
    system_prompts: Dict[str, str] = Field(description="Recommended system prompts per agent role.")
    context_rules: List[str] = Field(description="Rules for loading context effectively in this repo.")
