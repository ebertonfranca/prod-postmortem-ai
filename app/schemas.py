from typing import List, Optional, Dict, Any
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
    images: List[str] = Field(default=[], description="Base64 encoded images (e.g. Datadog screenshots)")

class ExecutiveSummary(BaseModel):
    impact: str = Field(..., description="Impact of the incident")
    root_cause: str = Field(..., description="Root cause of the incident")
    resolution: str = Field(..., description="How it was resolved")

class Metrics(BaseModel):
    incident_title: str = Field(..., description="Short title, e.g. Checkout Service Outage")
    impact: str = Field(..., description="Event Impact, e.g. P1 - Crítico, P2 - Alto, or P3 - Médio")
    total_downtime: str = Field(..., description="User friendly string, e.g., 59 minutes")
    downtime_minutes: int = Field(..., description="Total downtime purely in minutes as integer")
    service_status: str = Field(..., description="Current status, e.g. Resolved")
    affected_customers: str = Field(default="N/A", description="Customers affected (or 'Internal')")
    
    affected_users: Optional[str] = Field(None, description="E.g. 4,892 (or null if not found)")
    error_count: Optional[str] = Field(None, description="Amount of errors, e.g. 15,312 (or null)")
    main_service: Optional[str] = Field(None, description="Main service affected e.g. checkout-api (or null)")
    infra_slo: Optional[str] = Field(None, description="Infra SLO e.g. 99.9% (or null)")

class CriticalEvent(BaseModel):
    timestamp: str = Field(..., description="Time of the event, e.g., 09:00:00")
    event: str = Field(..., description="Description of the event")

class IncidentReport(BaseModel):
    executive_summary: ExecutiveSummary
    metrics: Metrics
    timeline: List[CriticalEvent]
    next_steps: List[str] = Field(..., description="Bullet points of suggested next steps")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token usage stats")
