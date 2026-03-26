"""Pydantic schemas for request/response payloads."""

from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


IPAddress = IPv4Address | IPv6Address


class ClientInfo(BaseModel):
    name: Optional[str] = None
    external_code: Optional[str] = None
    contact_email: Optional[str] = None


class HostInfo(BaseModel):
    hostname: Optional[str] = None
    ip_address: Optional[IPAddress] = None
    root_folder: str
    environment: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)


class AutomationInfo(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    owner_team: Optional[str] = None


class AutomationInstanceRequest(BaseModel):
    instance_id: Optional[UUID] = None
    automation: AutomationInfo
    host: HostInfo
    client: Optional[ClientInfo] = None
    deployment_tag: Optional[str] = None
    config_signature: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AckResponse(BaseModel):
    status: str = "accepted"


class RunCreateRequest(BaseModel):
    run_id: UUID
    automation_instance_id: Optional[UUID] = None
    instance: Optional[AutomationInstanceRequest] = None
    started_at: Optional[datetime] = None
    status: Optional[str] = "running"
    pid: Optional[int] = None
    user_name: Optional[str] = None
    server_mode: bool = False
    host_ip: Optional[IPAddress] = None
    root_folder: Optional[str] = None
    config_version: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    status: str = "accepted"
    run_id: UUID


class RunUpdateRequest(BaseModel):
    run_id: UUID
    status: Optional[str] = None
    finished_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class LogEntryPayload(BaseModel):
    sequence: int
    ts: datetime
    level: str
    message: str
    logger_name: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)


class LogBatchRequest(BaseModel):
    run_id: UUID
    entries: List[LogEntryPayload]


class SnapshotRequest(BaseModel):
    snapshot_type: str
    taken_at: Optional[datetime] = None
    payload: Dict[str, Any]


class EmailEventCreateRequest(BaseModel):
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    recipients: List[str] = Field(default_factory=list)
    bcc_recipients: List[str] = Field(default_factory=list)
    source_paths: List[str] = Field(default_factory=list)
    status: str = "enviado"
    error: Optional[str] = None
    sent_at: Optional[datetime] = None
    retention_days: Optional[int] = Field(default=None, ge=1)


class EmailEventCreateResponse(BaseModel):
    status: str = "accepted"
    email_id: UUID


class EmailAttachmentCreateResponse(BaseModel):
    status: str = "accepted"
    attachment_id: UUID
    filename: str
    mime_type: Optional[str] = None
    size_bytes: int
    preview_supported: bool


# ---------------------------------------------------------------------------
# Read-only / insights schemas
# ---------------------------------------------------------------------------


class HostSummary(BaseModel):
    id: UUID
    hostname: Optional[str]
    display_name: Optional[str] = None
    ip_address: Optional[str]
    root_folder: str
    environment: Optional[str]
    tags: Dict[str, Any] = Field(default_factory=dict)
    automation_count: int
    last_seen_at: Optional[datetime]


class HostUpdateRequest(BaseModel):
    display_name: Optional[str] = None


class HostListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[HostSummary]


class HostAutomationSummary(BaseModel):
    instance_id: UUID
    automation_id: UUID
    automation_code: str
    automation_name: str
    client_id: Optional[UUID]
    client_name: Optional[str]
    root_folder: Optional[str]
    deployment_tag: Optional[str]
    config_signature: Optional[str]
    last_seen_at: Optional[datetime]
    runs_count: int
    last_run_started_at: Optional[datetime]


class AutomationSummary(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str]
    owner_team: Optional[str]
    instances_count: int
    hosts_count: int
    clients_count: int
    host_ids: List[UUID] = []
    last_seen_at: Optional[datetime]
    last_run_started_at: Optional[datetime]


class AutomationListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[AutomationSummary]


class AutomationInstanceSummary(BaseModel):
    id: UUID
    automation_id: UUID
    automation_code: str
    automation_name: str
    client_id: Optional[UUID]
    client_name: Optional[str]
    host_id: Optional[UUID]
    host_hostname: Optional[str]
    host_display_name: Optional[str] = None
    host_ip: Optional[str]
    root_folder: Optional[str]
    deployment_tag: Optional[str]
    config_signature: Optional[str]
    last_seen_at: Optional[datetime]
    total_runs: int
    last_run_started_at: Optional[datetime]
    available_args: List[Dict[str, Any]] = []
    default_args: List[str] = []


class RunSummary(BaseModel):
    id: UUID
    automation_instance_id: UUID
    automation_id: Optional[UUID] = None
    automation_code: Optional[str] = None
    automation_name: Optional[str] = None
    client_id: Optional[UUID] = None
    client_name: Optional[str] = None
    host_id: Optional[UUID] = None
    host_hostname: Optional[str] = None
    host_display_name: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    server_mode: bool
    host_ip: Optional[str]
    root_folder: Optional[str]
    config_version: Optional[str]
    log_entries: int
    origin: Optional[str] = None


class RunListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[RunSummary]


class RunOverviewBucket(BaseModel):
    bucket: str
    label: str
    total: int


class RunOverviewResponse(BaseModel):
    total_runs: int
    total_logs: int
    status_counts: Dict[str, int] = Field(default_factory=dict)
    runs_by_day: List[RunOverviewBucket] = Field(default_factory=list)
    runs_by_hour: List[RunOverviewBucket] = Field(default_factory=list)


class RunDetailResponse(RunSummary):
    automation_id: UUID
    automation_code: str
    automation_name: str
    client_id: Optional[UUID]
    client_name: Optional[str]
    host_id: Optional[UUID]
    host_hostname: Optional[str]
    host_display_name: Optional[str] = None


class RunTimelineItem(BaseModel):
    id: UUID
    automation_instance_id: Optional[UUID] = None
    automation_code: Optional[str]
    automation_name: Optional[str]
    client_name: Optional[str]
    host_hostname: Optional[str]
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    last_log_at: Optional[datetime] = None
    has_overlap: bool = False
    has_code_overlap: bool = False


class RunTimelineResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[RunTimelineItem]


class EmailAttachmentSummary(BaseModel):
    id: UUID
    filename: str
    mime_type: Optional[str]
    size_bytes: int
    source_path: Optional[str]
    preview_supported: bool
    created_at: datetime


class EmailEventSummary(BaseModel):
    id: UUID
    run_id: UUID
    subject: Optional[str]
    body_text: Optional[str]
    body_html: Optional[str]
    recipients: List[str] = Field(default_factory=list)
    bcc_recipients: List[str] = Field(default_factory=list)
    source_paths: List[str] = Field(default_factory=list)
    status: str
    error: Optional[str]
    retention_days: int
    sent_at: datetime
    expires_at: datetime
    attachments: List[EmailAttachmentSummary] = Field(default_factory=list)


class EmailEventListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[EmailEventSummary]


class LogEntryResponse(BaseModel):
    sequence: int
    ts: datetime
    level: str
    message: str
    logger_name: Optional[str]
    context: Dict[str, Any]
    extra: Dict[str, Any]


class LogEntriesResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[LogEntryResponse]


class LogMetricsTimelineItem(BaseModel):
    ts: datetime
    level: str


class LogMetricsResponse(BaseModel):
    total: int
    counts: Dict[str, int]
    timeline: List[LogMetricsTimelineItem]


class ClientSummary(BaseModel):
    id: UUID
    name: str
    external_code: Optional[str]
    contact_email: Optional[str]
    automations_count: int
    instances_count: int
    host_ids: List[UUID] = []
    last_seen_at: Optional[datetime]


class ClientAutomationSummary(BaseModel):
    automation_id: UUID
    automation_code: str
    automation_name: str
    host_id: Optional[UUID]
    host_hostname: Optional[str]
    host_display_name: Optional[str] = None
    host_ip: Optional[str]
    deployment_tag: Optional[str]
    last_run_started_at: Optional[datetime]
    total_runs: int


class ClientListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ClientSummary]


# ---------------------------------------------------------------------------
# Remote control schemas (schedules, commands, agent)
# ---------------------------------------------------------------------------


class RecurrenceConfig(BaseModel):
    time: str  # "HH:MM"
    days_of_week: Optional[List[int]] = None  # 0=Mon .. 6=Sun
    day_of_month: Optional[int] = None
    business_day: Optional[bool] = None
    month: Optional[int] = None  # 1-12, for yearly recurrence


class ScheduleCreateRequest(BaseModel):
    automation_instance_id: UUID
    script: str = "main.py"
    args: List[str] = Field(default_factory=list)
    recurrence_type: str  # daily|weekdays|specific_days|monthly|yearly
    recurrence_config: RecurrenceConfig
    execution_mode: str = "parallel"  # parallel|sequential
    timezone: str = "America/Sao_Paulo"
    enabled: bool = True


class ScheduleUpdateRequest(BaseModel):
    script: Optional[str] = None
    args: Optional[List[str]] = None
    recurrence_type: Optional[str] = None
    recurrence_config: Optional[RecurrenceConfig] = None
    execution_mode: Optional[str] = None
    timezone: Optional[str] = None
    enabled: Optional[bool] = None


class ScheduleSummary(BaseModel):
    id: UUID
    automation_instance_id: UUID
    automation_code: Optional[str] = None
    automation_name: Optional[str] = None
    client_name: Optional[str] = None
    host_id: Optional[UUID] = None
    host_hostname: Optional[str] = None
    host_display_name: Optional[str] = None
    script: str
    args: List[str]
    recurrence_type: str
    recurrence_config: Dict[str, Any]
    execution_mode: str
    timezone: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ScheduleListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ScheduleSummary]


class CalendarEvent(BaseModel):
    id: UUID
    automation_instance_id: UUID
    automation_id: Optional[UUID] = None
    automation_code: Optional[str] = None
    automation_name: Optional[str] = None
    client_id: Optional[UUID] = None
    client_name: Optional[str] = None
    host_hostname: Optional[str] = None
    host_display_name: Optional[str] = None
    scheduled_time: datetime
    recurrence_type: str
    execution_mode: str
    enabled: bool


class CalendarResponse(BaseModel):
    items: List[CalendarEvent]


class RunNowRequest(BaseModel):
    automation_instance_id: UUID
    script: str = "main.py"
    args: List[str] = Field(default_factory=list)
    execution_mode: str = "parallel"


class CommandSummary(BaseModel):
    id: UUID
    scheduled_job_id: Optional[UUID] = None
    host_id: UUID
    host_hostname: Optional[str] = None
    automation_instance_id: UUID
    automation_code: Optional[str] = None
    automation_name: Optional[str] = None
    client_name: Optional[str] = None
    script: str
    args: List[str]
    working_dir: str
    execution_mode: str
    status: str
    run_id: Optional[UUID] = None
    created_by: str
    created_at: datetime
    acked_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_message: Optional[str] = None


class CommandListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[CommandSummary]


class InstanceArgsUpdate(BaseModel):
    available_args: List[Dict[str, Any]]
    default_args: Optional[List[str]] = None


class AgentStatusItem(BaseModel):
    host_id: UUID
    hostname: Optional[str] = None
    connected: bool
    last_ping: Optional[datetime] = None
