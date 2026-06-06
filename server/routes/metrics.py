"""
API routes for receiving and retrieving metrics
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db import get_db, Node, Metric

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


class MetricPayload(BaseModel):
    """Schema for incoming metric data from agents"""
    node_id: str
    hostname: str
    timestamp: str
    metrics: Dict[str, Any]


class MetricResponse(BaseModel):
    """Response schema for metric submission"""
    success: bool
    message: str
    node_id: str


@router.post("", response_model=MetricResponse)
async def receive_metrics(payload: MetricPayload, db: Session = Depends(get_db)):
    """
    Receive metrics from an agent node

    This is the main endpoint that agents POST to with their collected metrics.
    """
    try:
        # Parse timestamp
        timestamp = datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00'))

        # Get or create node
        node = db.query(Node).filter(Node.node_id == payload.node_id).first()

        if not node:
            # Create new node
            node = Node(
                node_id=payload.node_id,
                hostname=payload.hostname,
                last_seen=timestamp,
                status="online"
            )
            db.add(node)
        else:
            # Update existing node
            node.hostname = payload.hostname
            node.last_seen = timestamp
            node.status = "online"

        # Store each metric type separately
        for metric_type, metric_data in payload.metrics.items():
            metric = Metric(
                node_id=payload.node_id,
                timestamp=timestamp,
                metric_type=metric_type,
                data=metric_data
            )
            db.add(metric)

        db.commit()

        return MetricResponse(
            success=True,
            message="Metrics received successfully",
            node_id=payload.node_id
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing metrics: {str(e)}")


@router.get("/history/{node_id}")
async def get_metric_history(
    node_id: str,
    metric_type: str = Query(..., description="Type of metric (cpu, memory, disk, network, services)"),
    hours: int = Query(1, description="Number of hours of history to retrieve", ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Get historical metrics for a specific node

    Args:
        node_id: The node identifier
        metric_type: Type of metric to retrieve
        hours: Number of hours of history (default 1, max 168/1 week)
    """
    # Verify node exists
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    # Calculate time range
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    # Query metrics
    metrics = db.query(Metric).filter(
        Metric.node_id == node_id,
        Metric.metric_type == metric_type,
        Metric.timestamp >= start_time,
        Metric.timestamp <= end_time
    ).order_by(Metric.timestamp.asc()).all()

    return {
        "node_id": node_id,
        "metric_type": metric_type,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "count": len(metrics),
        "data": [
            {
                "timestamp": m.timestamp.isoformat(),
                "data": m.data
            }
            for m in metrics
        ]
    }


@router.get("/latest/{node_id}")
async def get_latest_metrics(node_id: str, db: Session = Depends(get_db)):
    """
    Get the most recent metrics for a node
    """
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    # Get latest metric of each type
    latest_metrics = {}

    for metric_type in ['cpu', 'memory', 'disk', 'network', 'services']:
        metric = db.query(Metric).filter(
            Metric.node_id == node_id,
            Metric.metric_type == metric_type
        ).order_by(desc(Metric.timestamp)).first()

        if metric:
            latest_metrics[metric_type] = {
                "timestamp": metric.timestamp.isoformat(),
                "data": metric.data
            }

    return {
        "node_id": node_id,
        "hostname": node.hostname,
        "last_seen": node.last_seen.isoformat() if node.last_seen else None,
        "status": node.status,
        "metrics": latest_metrics
    }
