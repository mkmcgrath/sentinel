"""
Database models and connection for Sentinel server
"""
import os
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# Get database URL from environment variable
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://sentinel:changeme@localhost:5432/sentinel'
)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Node(Base):
    """Model for monitored nodes"""
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, unique=True, index=True, nullable=False)
    hostname = Column(String)
    ip_address = Column(String)
    last_seen = Column(DateTime(timezone=True))
    status = Column(String, default="offline")  # online, offline, warning
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    metrics = relationship("Metric", back_populates="node", cascade="all, delete-orphan")
    alert_events = relationship("AlertEvent", back_populates="node", cascade="all, delete-orphan")


class Metric(Base):
    """Model for storing metrics"""
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, ForeignKey("nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_type = Column(String, nullable=False)  # cpu, memory, disk, network, services
    data = Column(JSON, nullable=False)  # Flexible JSON storage for metric data
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    node = relationship("Node", back_populates="metrics")


class Alert(Base):
    """Model for alert rules"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, index=True)  # Can be null for global alerts
    name = Column(String, nullable=False)
    metric = Column(String, nullable=False)  # e.g., "cpu.usage_percent"
    operator = Column(String, nullable=False)  # gt, lt, eq, gte, lte
    threshold = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    events = relationship("AlertEvent", back_populates="alert", cascade="all, delete-orphan")


class AlertEvent(Base):
    """Model for alert events (when alerts are triggered)"""
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String, ForeignKey("nodes.node_id", ondelete="CASCADE"), nullable=False)
    triggered = Column(DateTime(timezone=True), nullable=False)
    resolved = Column(DateTime(timezone=True), nullable=True)
    value = Column(Float, nullable=False)
    message = Column(Text)

    # Relationships
    alert = relationship("Alert", back_populates="events")
    node = relationship("Node", back_populates="alert_events")


def get_db() -> Session:
    """
    Dependency function to get database session
    Use with FastAPI's Depends()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")


def drop_db():
    """Drop all tables - use with caution!"""
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped")


if __name__ == "__main__":
    # If run directly, initialize the database
    print(f"Connecting to database: {DATABASE_URL}")
    init_db()
