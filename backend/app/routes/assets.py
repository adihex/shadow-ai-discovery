from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_db
from app.models import Asset

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.get("", response_model=List[Asset])
def get_assets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve all discovered cloud assets."""
    statement = select(Asset).offset(skip).limit(limit)
    results = db.exec(statement).all()
    return results

@router.get("/{asset_id}", response_model=Asset)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific cloud asset."""
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
