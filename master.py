import asyncio
from typing import List, Dict, Any
from worker import run_worker
from schemas import AgentsConfiguration, WorkerResponse

async def reconcile_reports(reports: List[WorkerResponse]) -> AgentsConfiguration:
    """
    Simulates Terra master agent reconciling the parallel worker reports.
    In reality, Terra reads the JSON reports and generates the final configuration using high reasoning.
    """
    print("[Master: Terra] Reconciling worker reports...")
    
    # Simulate high reasoning effort
    await asyncio.sleep(3)
    
    # Compile system prompts based on findings
    prompts = {}
    for report in reports:
        if report.agent_role == "architecture":
            prompts["architecture_guidance"] = f"Maintain {report.data.get('primary_language')} standards. Follow {', '.join(report.data.get('patterns_identified', []))} patterns."
        elif report.agent_role == "risk":
            prompts["risk_guidance"] = f"Avoid touching technical debt areas: {', '.join(report.data.get('technical_debt', []))}"
            
    print("[Master: Terra] Reconciliation complete. Generating AGENTS.md content.")
    
    return AgentsConfiguration(
        repository_name="TargetRepo",
        optimal_model="gpt-5.6-luna", # Recommending Luna for typical tasks on this repo
        system_prompts=prompts,
        context_rules=[
            "Always load api/routes.py first as it is high churn.",
            "Exclude vendor/ and node_modules/ from context."
        ]
    )

async def orchestrate_analysis(repo_path: str) -> AgentsConfiguration:
    """
    Master orchestrator function.
    Fires off Luna workers in parallel, waits for results, and reconciles them using Terra.
    """
    roles = ["architecture", "risk", "testing", "history"]
    
    print("[Master: Terra] Dispatching Luna workers in parallel...")
    # Execute workers concurrently
    tasks = [run_worker(role, repo_path) for role in roles]
    results = await asyncio.gather(*tasks)
    
    # Reconcile outputs
    final_config = await reconcile_reports(results)
    return final_config
