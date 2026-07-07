import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Dict, Any
from app.database import get_db, engine
from app.models import Scan, utc_now
from app.services.scanner import GCPScanner
from app.config import settings

router = APIRouter(prefix="/scan", tags=["Scans"])

def execute_scan_task(scan_id: str, project_id: str):
    # The request-scoped session is closed by the time the background task
    # runs, so open a fresh session bound to the shared engine.
    with Session(engine) as db:
        scan = db.get(Scan, scan_id)
        if not scan:
            return
        
        try:
            scanner = GCPScanner(project_id=project_id, db_session=db)
            results = scanner.run_scan()
            
            scan.status = "completed"
            scan.assets_found = results.get("assets_found", 0)
            scan.agents_found = results.get("agents_found", 0)
            scan.error_message = None
        except Exception as e:
            scan.status = "failed"
            scan.error_message = str(e)
        finally:
            db.add(scan)
            db.commit()

@router.post("", response_model=Scan)
def trigger_scan(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger a new discovery scan (asynchronous)."""
    scan_id = f"scan-{uuid.uuid4().hex[:8]}"
    scan = Scan(
        id=scan_id,
        timestamp=utc_now(),
        status="running",
        assets_found=0,
        agents_found=0
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    # Run scan asynchronously as a background task
    background_tasks.add_task(execute_scan_task, scan_id, settings.GCP_PROJECT_ID)
    return scan

@router.get("/history", response_model=List[Scan])
def get_scan_history(db: Session = Depends(get_db)):
    """Retrieve history of all scans."""
    statement = select(Scan).order_by(Scan.timestamp.desc())
    results = db.exec(statement).all()
    return results
