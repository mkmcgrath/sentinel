import os
from sqlalchemy import create_all
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
from datetime import datetime

# Database Configuration (Phase 4.2)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sentinel:changeme@db:5432/sentinel")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Node(Base):
    """Represents a monitored machine in the network"""
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, unique=True, index=True)
    hostname = Column(String)
    last_seen = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="online")
    
    metrics = relationship("Metric", back_populates="node")

class Metric(Base):
    """Stores a single snapshot of metrics from a node"""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, ForeignKey("nodes.node_id"))
    timestamp = Column(DateTime, index=True)
    data = Column(JSON) # Store flexible metric payload

    node = relationship("Node", back_populates="metrics")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
