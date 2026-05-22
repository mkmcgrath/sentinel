from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from db import get_db, Node, Metric
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

class MetricPayload(BaseModel):
    node_id: str
    hostname: str
    timestamp: str
    metrics: Dict[str, Any]

@router.post("/metrics")
async def collect_metrics(payload: MetricPayload, db: Session = Depends(get_db)):
    """
    Endpoint for agents to push metrics (Phase 4.1)
    This endpoint updates the node's last_seen status and stores the metric snapshot.
    """
    # 1. Update or create Node record
    node = db.query(Node).filter(Node.node_id == payload.node_id).first()
    if not node:
        node = Node(node_id=payload.node_id, hostname=payload.hostname)
        db.add(node)
    
    node.last_seen = datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00'))
    node.status = "online"

    # 2. Store metrics
    new_metric = Metric(
        node_id=payload.node_id,
        timestamp=node.last_seen,
        data=payload.metrics
    )
    db.add(new_metric)
    
    db.commit()
    return {"status": "success"}
