from typing import List, Optional
from pydantic import BaseModel, Field

class AnalyzeRequest(BaseModel):
    logs: str = Field(..., description="System logs during the incident")
    transcription: Optional[str] = Field("", description="Chat/Voice transcription of the team during the incident")
    time_range: Optional[str] = Field(None, description="Optional time window of the incident")
    affected_services: Optional[str] = Field(None, description="Optional blast radius / affected services")
    impact: Optional[str] = Field(None, description="Low, Medium, or High impact classification")
    key_stakeholders: Optional[str] = Field(None, description="Optional key stakeholders involved")
    sla_hours: int = Field(2, description="Selected SLA boundary in hours")
    customers: Optional[str] = Field(None, description="Affected customers to highlight")

class ExecutiveSummary(BaseModel):
    impact: str = Field(..., description="Impact of the incident")
    root_cause: str = Field(..., description="Root cause of the incident")
    resolution: str = Field(..., description="How it was resolved")

class Metrics(BaseModel):
    incident_title: str = Field(..., description="Short title, e.g. Checkout Service Outage")
    total_downtime: str = Field(..., description="User friendly string, e.g., 59 seconds")
    downtime_minutes: int = Field(..., description="Total downtime purely in minutes as integer")
    service_status: str = Field(..., description="Current status, e.g. Resolved")
    affected_requests: int = Field(..., description="Number of affected requests")
    affected_users: int = Field(..., description="Number of affected users")

class CriticalEvent(BaseModel):
    timestamp: str = Field(..., description="Time of the event, e.g., 09:00:00")
    event: str = Field(..., description="Description of the event")

class IncidentReport(BaseModel):
    executive_summary: ExecutiveSummary
    metrics: Metrics
    timeline: List[CriticalEvent]
    next_steps: List[str] = Field(..., description="Bullet points of suggested next steps")
