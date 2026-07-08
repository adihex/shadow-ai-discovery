from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_db
from app.models import Asset

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("", response_model=List[Asset])
def get_agents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve workloads identified as likely AI agents."""
    statement = select(Asset).where(Asset.is_ai_agent).offset(skip).limit(limit)
    results = db.exec(statement).all()
    return results

@router.get("/{agent_id}", response_model=Asset)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific AI agent workload."""
    agent = db.get(Asset, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent workload not found")
    if not agent.is_ai_agent:
        raise HTTPException(status_code=400, detail="Requested workload is not classified as an AI Agent")
    return agent
