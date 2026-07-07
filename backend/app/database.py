from sqlmodel import create_engine, SQLModel, Session
from app.config import settings

sqlite_url = f"sqlite:///{settings.DATABASE_PATH}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_db():
    with Session(engine) as session:
        yield session
