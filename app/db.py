# Copyright (c) 2026 Kuo-Chen Wu (吳國禎). All Rights Reserved.
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DB_PATH = os.environ.get("CV_DB", os.path.join(os.path.dirname(__file__), "..", "data", "cv.db"))
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def _wal(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
