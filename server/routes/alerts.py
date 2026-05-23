"""
API routes for alert managment
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

class AlertCreate(BaseModel):
    """ Schema for creating an alert rule"""
    node_id: Optional[str] = Field(None, description="Node ID (null for global alert)")
    name: str = Field(..., description="Alert name")
    metric: str = Field(..., description="Metric path (e.g., cpu.usage_percent)")
    operator: str = Field(..., description="Comparison operator: gt, lt, eq, gte, lte")
    threshold: float = Field(..., description="Threshold value")
    description: Optional[str] = Field(None, description="Alert description")
