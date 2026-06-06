"""
API routes for alert management
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db, Alert, AlertEvent, Node

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    """Schema for creating an alert rule"""
    node_id: Optional[str] = Field(None, description="Node ID (null for global alert)")
    name: str = Field(..., description="Alert name")
    metric: str = Field(..., description="Metric path (e.g., cpu.usage_percent)")
    operator: str = Field(..., description="Comparison operator: gt, lt, eq, gte, lte")
    threshold: float = Field(..., description="Threshold value")
    description: Optional[str] = Field(None, description="Alert description")


class AlertSchema(BaseModel):
    """Schema for alert rule"""
    id: int
    node_id: Optional[str]
    name: str
    metric: str
    operator: str
    threshold: float
    active: bool
    description: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AlertEventSchema(BaseModel):
    """Schema for alert event"""
    id: int
    alert_id: int
    node_id: str
    triggered: str
    resolved: Optional[str]
    value: float
    message: Optional[str]
    alert_name: Optional[str]

    class Config:
        from_attributes = True


@router.post("", response_model=AlertSchema)
async def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    """
    Create a new alert rule

    Operators:
    - gt: greater than
    - lt: less than
    - eq: equal to
    - gte: greater than or equal to
    - lte: less than or equal to
    """
    # Validate operator
    valid_operators = ['gt', 'lt', 'eq', 'gte', 'lte']
    if alert.operator not in valid_operators:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid operator. Must be one of: {', '.join(valid_operators)}"
        )

    # If node_id is specified, verify it exists
    if alert.node_id:
        node = db.query(Node).filter(Node.node_id == alert.node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {alert.node_id} not found")

    # Create alert
    db_alert = Alert(
        node_id=alert.node_id,
        name=alert.name,
        metric=alert.metric,
        operator=alert.operator,
        threshold=alert.threshold,
        description=alert.description
    )

    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    return AlertSchema(
        id=db_alert.id,
        node_id=db_alert.node_id,
        name=db_alert.name,
        metric=db_alert.metric,
        operator=db_alert.operator,
        threshold=db_alert.threshold,
        active=db_alert.active,
        description=db_alert.description,
        created_at=db_alert.created_at.isoformat(),
        updated_at=db_alert.updated_at.isoformat()
    )


@router.get("", response_model=List[AlertSchema])
async def list_alerts(
    active_only: bool = True,
    node_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all alert rules

    Args:
        active_only: Only return active alerts (default: True)
        node_id: Filter by node ID
    """
    query = db.query(Alert)

    if active_only:
        query = query.filter(Alert.active == True)

    if node_id:
        query = query.filter(Alert.node_id == node_id)

    alerts = query.all()

    return [
        AlertSchema(
            id=a.id,
            node_id=a.node_id,
            name=a.name,
            metric=a.metric,
            operator=a.operator,
            threshold=a.threshold,
            active=a.active,
            description=a.description,
            created_at=a.created_at.isoformat(),
            updated_at=a.updated_at.isoformat()
        )
        for a in alerts
    ]


@router.get("/{alert_id}", response_model=AlertSchema)
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get a specific alert by ID"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    return AlertSchema(
        id=alert.id,
        node_id=alert.node_id,
        name=alert.name,
        metric=alert.metric,
        operator=alert.operator,
        threshold=alert.threshold,
        active=alert.active,
        description=alert.description,
        created_at=alert.created_at.isoformat(),
        updated_at=alert.updated_at.isoformat()
    )


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert rule"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    db.delete(alert)
    db.commit()

    return {"success": True, "message": f"Alert {alert_id} deleted"}


@router.patch("/{alert_id}/toggle")
async def toggle_alert(alert_id: int, db: Session = Depends(get_db)):
    """Toggle an alert between active and inactive"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert.active = not alert.active
    db.commit()

    return {
        "success": True,
        "alert_id": alert_id,
        "active": alert.active
    }


@router.get("/events/active", response_model=List[AlertEventSchema])
async def get_active_events(db: Session = Depends(get_db)):
    """
    Get all currently active (unresolved) alert events
    """
    events = db.query(AlertEvent).filter(AlertEvent.resolved == None).all()

    result = []
    for event in events:
        result.append(AlertEventSchema(
            id=event.id,
            alert_id=event.alert_id,
            node_id=event.node_id,
            triggered=event.triggered.isoformat(),
            resolved=event.resolved.isoformat() if event.resolved else None,
            value=event.value,
            message=event.message,
            alert_name=event.alert.name if event.alert else None
        ))

    return result


@router.get("/events/history")
async def get_event_history(
    node_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get alert event history

    Args:
        node_id: Filter by node ID
        limit: Maximum number of events to return (default: 100)
    """
    query = db.query(AlertEvent).order_by(AlertEvent.triggered.desc())

    if node_id:
        query = query.filter(AlertEvent.node_id == node_id)

    events = query.limit(limit).all()

    result = []
    for event in events:
        result.append({
            "id": event.id,
            "alert_id": event.alert_id,
            "alert_name": event.alert.name if event.alert else None,
            "node_id": event.node_id,
            "triggered": event.triggered.isoformat(),
            "resolved": event.resolved.isoformat() if event.resolved else None,
            "value": event.value,
            "message": event.message,
            "duration_seconds": (
                (event.resolved - event.triggered).total_seconds()
                if event.resolved else None
            )
        })

    return result
