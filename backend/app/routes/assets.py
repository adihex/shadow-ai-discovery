from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_db
from app.models import Asset

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.get("", response_model=List[Asset])
def get_assets(db: Session = Depends(get_db)):
    """Retrieve all discovered cloud assets."""
    statement = select(Asset)
    results = db.exec(statement).all()
    return results
