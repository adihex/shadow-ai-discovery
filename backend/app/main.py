from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, get_db
from app.routes import assets, agents, scans
from app.models import Asset
from app.services.scanner import GCPScanner
from app.config import settings
from sqlmodel import Session, select

app = FastAPI(
    title="Shadow AI Discovery Engine API",
    description="Backend API for discovering and cataloging Shadow AI Agents in cloud infrastructure.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for POC simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(assets.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(scans.router, prefix="/api")

@app.on_event("startup")
def on_startup():
    init_db()
    
    # Pre-populate database with an initial scan if empty
    db_gen = get_db()
    db = next(db_gen)
    try:
        statement = select(Asset)
        results = db.exec(statement).first()
        if not results:
            print("Database is empty. Pre-populating with initial mock workloads...")
            scanner = GCPScanner(project_id=settings.GCP_PROJECT_ID, db_session=db)
            scanner.run_scan()
    except Exception as e:
        print(f"Error prepopulating database: {e}")
    finally:
        db.close()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Shadow AI Discovery Engine API",
        "docs": "/docs"
    }
