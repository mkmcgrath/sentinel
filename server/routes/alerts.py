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

class AlertSchema(BaseModel):
    """Schema for alert rule"""
    #it needs id node_id name, metric, operator, thrshold, active, descrption, create3d_at, updated_at

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
