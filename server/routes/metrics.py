"""
API routes for receiving and retrieving metrics
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from db import get_db, Node, Metric, Alert, AlertEvent

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])
logger = logging.getLogger(__name__)

WEBHOOK_URL = os.environ.get("WEBHOOK_URL")


def _get_metric_value(metrics: dict, metric_path: str) -> Optional[float]:
    """
    extract a numeric value from the metrics dict using a dot-separated path.
    e.g., "cpu.usage_percent" -> metrics['cpu']['usage_percent']
    For list values (e.g., disk is a list of mounts), returns the max across all items.
    """
    parts = metric_path.split(".")
    current = metrics

    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list):
            # extract the field from each list item, return the max
            values = [
                item[part]
                for item in current
                if isinstance(item, dict)
                and part in item
                and isinstance(item[part], (int, float))
            ]
            return float(max(values)) if values else None
        else:
            return None

    if isinstance(current, (int, float)):
        return float(current)
    return None


def _evaluate_condition(value: float, operator: str, threshold: float) -> bool:
    ops = {
        "gt": lambda v, t: v > t,
        "lt": lambda v, t: v < t,
        "eq": lambda v, t: v == t,
        "gte": lambda v, t: v >= t,
        "lte": lambda v, t: v <= t,
    }
    fn = ops.get(operator)
    return fn(value, threshold) if fn else False


def _send_webhook_notification(alert: Alert, node_id: str, value: float, timestamp: datetime):
    """
    Notify the configured webhook URL that an alert has fired.
    Best-effort: failures are logged, never raised, so they can't break metric ingestion.
    """
    if not WEBHOOK_URL:
        return

    payload = {
        "alert_name": alert.name,
        "node_id": node_id,
        "metric": alert.metric,
        "value": value,
        "threshold": alert.threshold,
        "operator": alert.operator,
        "timestamp": timestamp.isoformat(),
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req, timeout=5):
            pass
    except (URLError, HTTPError) as e:
        logger.warning(f"Failed to deliver webhook notification: {e}")


def _evaluate_alerts(db: Session, node_id: str, metrics: dict, timestamp: datetime):
    """
    Check all active alert rules against incoming metrics.
    - Creates an AlertEvent when a threshold is first breached.
    - Resolves the open AlertEvent when the condition clears.
    - Sets node status to 'warning' if any open events remain after evaluation.
    """
    alerts = (
        db.query(Alert)
        .filter(
            Alert.active == True, or_(Alert.node_id == node_id, Alert.node_id == None)
        )
        .all()
    )

    for alert in alerts:
        value = _get_metric_value(metrics, alert.metric)
        if value is None:
            continue

        breached = _evaluate_condition(value, alert.operator, alert.threshold)

        open_event = (
            db.query(AlertEvent)
            .filter(
                AlertEvent.alert_id == alert.id,
                AlertEvent.node_id == node_id,
                AlertEvent.resolved == None,
            )
            .first()
        )

        if breached and not open_event:
            db.add(
                AlertEvent(
                    alert_id=alert.id,
                    node_id=node_id,
                    triggered=timestamp,
                    value=value,
                    message=f"{alert.metric} = {value} (rule: {alert.operator} {alert.threshold})",
                )
            )
            _send_webhook_notification(alert, node_id, value, timestamp)
        elif not breached and open_event:
            open_event.resolved = timestamp

    # Update node status based on whether any open events remain after this pass.
    # Flush first: the session has autoflush disabled, and without this the
    # count below can miss AlertEvents added/resolved earlier in this same call.
    db.flush()
    has_open_events = (
        db.query(AlertEvent)
        .filter(AlertEvent.node_id == node_id, AlertEvent.resolved == None)
        .count()
        > 0
    )

    node = db.query(Node).filter(Node.node_id == node_id).first()
    if node and node.status != "offline":
        node.status = "warning" if has_open_events else "online"


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
        timestamp = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00"))

        # Get or create node
        node = db.query(Node).filter(Node.node_id == payload.node_id).first()

        if not node:
            # Create new node
            node = Node(
                node_id=payload.node_id,
                hostname=payload.hostname,
                last_seen=timestamp,
                status="online",
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
                data=metric_data,
            )
            db.add(metric)

        # Evaluate alert rules against the incoming metrics
        _evaluate_alerts(db, payload.node_id, payload.metrics, timestamp)

        db.commit()

        return MetricResponse(
            success=True,
            message="Metrics received successfully",
            node_id=payload.node_id,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error processing metrics: {str(e)}"
        )


@router.get("/history/{node_id}")
async def get_metric_history(
    node_id: str,
    metric_type: str = Query(
        ..., description="Type of metric (cpu, memory, disk, network, services)"
    ),
    hours: int = Query(
        1, description="Number of hours of history to retrieve", ge=1, le=168
    ),
    db: Session = Depends(get_db),
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
    metrics = (
        db.query(Metric)
        .filter(
            Metric.node_id == node_id,
            Metric.metric_type == metric_type,
            Metric.timestamp >= start_time,
            Metric.timestamp <= end_time,
        )
        .order_by(Metric.timestamp.asc())
        .all()
    )

    return {
        "node_id": node_id,
        "metric_type": metric_type,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "count": len(metrics),
        "data": [
            {"timestamp": m.timestamp.isoformat(), "data": m.data} for m in metrics
        ],
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

    for metric_type in ["cpu", "memory", "disk", "network", "services", "containers"]:
        metric = (
            db.query(Metric)
            .filter(Metric.node_id == node_id, Metric.metric_type == metric_type)
            .order_by(desc(Metric.timestamp))
            .first()
        )

        if metric:
            latest_metrics[metric_type] = {
                "timestamp": metric.timestamp.isoformat(),
                "data": metric.data,
            }

    return {
        "node_id": node_id,
        "hostname": node.hostname,
        "last_seen": node.last_seen.isoformat() if node.last_seen else None,
        "status": node.status,
        "metrics": latest_metrics,
    }
