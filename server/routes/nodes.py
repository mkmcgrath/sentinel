"""
API routes for node management
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from db import get_db, Node, Metric

router = APIRouter(prefix="/api/v1/nodes", tags=["nodes"])


class NodeSchema(BaseModel):
    """Schema for node information"""
    node_id: str
    hostname: Optional[str]
    ip_address: Optional[str]
    last_seen: Optional[str]
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class NodeSummary(BaseModel):
    """Summary information for a node"""
    node_id: str
    hostname: Optional[str]
    status: str
    last_seen: Optional[str]
    last_cpu_percent: Optional[float]
    last_memory_percent: Optional[float]
    last_disk_percent: Optional[float]


@router.get("", response_model=List[NodeSummary])
async def list_nodes(
    status: Optional[str] = Query(None, description="Filter by status (online, offline, warning)"),
    db: Session = Depends(get_db)
):
    """
    List all known nodes with summary information

    Optionally filter by status.
    """
    query = db.query(Node)

    if status:
        query = query.filter(Node.status == status)

    nodes = query.all()

    # Update node statuses based on last_seen
    offline_threshold = datetime.now(timezone.utc) - timedelta(seconds=60)

    result = []
    for node in nodes:
        # Check if node is offline
        if node.last_seen and node.last_seen < offline_threshold:
            node.status = "offline"
            db.commit()

        # Get latest metrics for summary
        latest_cpu = db.query(Metric).filter(
            Metric.node_id == node.node_id,
            Metric.metric_type == "cpu"
        ).order_by(Metric.timestamp.desc()).first()

        latest_memory = db.query(Metric).filter(
            Metric.node_id == node.node_id,
            Metric.metric_type == "memory"
        ).order_by(Metric.timestamp.desc()).first()

        latest_disk = db.query(Metric).filter(
            Metric.node_id == node.node_id,
            Metric.metric_type == "disk"
        ).order_by(Metric.timestamp.desc()).first()

        result.append(NodeSummary(
            node_id=node.node_id,
            hostname=node.hostname,
            status=node.status,
            last_seen=node.last_seen.isoformat() if node.last_seen else None,
            last_cpu_percent=latest_cpu.data.get('usage_percent') if latest_cpu else None,
            last_memory_percent=latest_memory.data.get('percent') if latest_memory else None,
            last_disk_percent=max(
                [p.get('percent', 0) for p in latest_disk.data.get('partitions', [])],
                default=None
            ) if latest_disk else None
        ))

    return result


@router.get("/{node_id}", response_model=NodeSchema)
async def get_node(node_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a specific node
    """
    node = db.query(Node).filter(Node.node_id == node_id).first()

    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    return NodeSchema(
        node_id=node.node_id,
        hostname=node.hostname,
        ip_address=node.ip_address,
        last_seen=node.last_seen.isoformat() if node.last_seen else None,
        status=node.status,
        created_at=node.created_at.isoformat(),
        updated_at=node.updated_at.isoformat()
    )


@router.delete("/{node_id}")
async def delete_node(node_id: str, db: Session = Depends(get_db)):
    """
    Delete a node and all its associated metrics

    Use with caution - this will delete all historical data for the node.
    """
    node = db.query(Node).filter(Node.node_id == node_id).first()

    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    db.delete(node)
    db.commit()

    return {
        "success": True,
        "message": f"Node {node_id} and all associated data deleted"
    }


@router.get("/{node_id}/stats")
async def get_node_stats(node_id: str, db: Session = Depends(get_db)):
    """
    Get statistical information about a node's metrics
    """
    node = db.query(Node).filter(Node.node_id == node_id).first()

    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    # Get total metric count
    total_metrics = db.query(func.count(Metric.id)).filter(
        Metric.node_id == node_id
    ).scalar()

    # Get oldest and newest metric timestamps
    oldest = db.query(func.min(Metric.timestamp)).filter(
        Metric.node_id == node_id
    ).scalar()

    newest = db.query(func.max(Metric.timestamp)).filter(
        Metric.node_id == node_id
    ).scalar()

    # Get count per metric type
    metric_counts = {}
    for metric_type in ['cpu', 'memory', 'disk', 'network', 'services', 'containers']:
        count = db.query(func.count(Metric.id)).filter(
            Metric.node_id == node_id,
            Metric.metric_type == metric_type
        ).scalar()
        metric_counts[metric_type] = count

    return {
        "node_id": node_id,
        "total_metrics": total_metrics,
        "oldest_metric": oldest.isoformat() if oldest else None,
        "newest_metric": newest.isoformat() if newest else None,
        "metric_counts": metric_counts
    }
