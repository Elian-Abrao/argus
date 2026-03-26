"""SQLAlchemy models aligned with db/schema.sql."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Text,
    UniqueConstraint,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import declarative_base, relationship




Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    external_code = Column(String, unique=True)
    contact_email = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    instances = relationship("AutomationInstance", back_populates="client")


class Host(Base):
    __tablename__ = "hosts"
    __table_args__ = (
        UniqueConstraint("ip_address", "root_folder", name="hosts_ip_root_uc"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String)
    display_name = Column(String)
    ip_address = Column(INET)
    root_folder = Column(String, nullable=False)
    environment = Column(String)
    tags = Column(JSONB, default=dict, nullable=False)
    last_agent_ping = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    instances = relationship("AutomationInstance", back_populates="host")


class Automation(Base):
    __tablename__ = "automations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    owner_team = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    instances = relationship("AutomationInstance", back_populates="automation")


class AutomationInstance(Base):
    __tablename__ = "automation_instances"
    __table_args__ = (
        UniqueConstraint(
            "automation_id",
            "client_id",
            "host_id",
            "deployment_tag",
            name="automation_instances_unique_idx",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    automation_id = Column(UUID(as_uuid=True), ForeignKey("automations.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"))
    deployment_tag = Column(String)
    config_signature = Column(String)
    script = Column(String, default="main.py", nullable=False)
    default_args = Column(JSONB, default=list, nullable=False)
    available_args = Column(JSONB, default=list, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime(timezone=True))
    attributes = Column(JSONB, default=dict, nullable=False)

    automation = relationship("Automation", back_populates="instances")
    client = relationship("Client", back_populates="instances")
    host = relationship("Host", back_populates="instances")
    runs = relationship("Run", back_populates="automation_instance")


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    automation_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("automation_instances.id"), nullable=False
    )
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime(timezone=True))
    status = Column(String, default="running", nullable=False)
    pid = Column(Integer)
    user_name = Column(String)
    server_mode = Column(Boolean, default=False, nullable=False)
    host_ip = Column(INET)
    root_folder = Column(String)
    config_version = Column(String)
    attributes = Column(JSONB, default=dict, nullable=False)

    automation_instance = relationship("AutomationInstance", back_populates="runs")
    log_entries = relationship("LogEntry", back_populates="run", cascade="all,delete")
    snapshots = relationship("RunSnapshot", back_populates="run", cascade="all,delete")
    email_events = relationship("EmailEvent", back_populates="run", cascade="all,delete")


class LogEntry(Base):
    __tablename__ = "log_entries"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="log_entries_run_seq_uc"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(BigInteger, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    level = Column(String, nullable=False)
    logger_name = Column(String)
    message = Column(Text, nullable=False)
    context = Column(JSONB, default=dict, nullable=False)
    extra = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="log_entries")


class RunSnapshot(Base):
    __tablename__ = "run_snapshots"
    __table_args__ = (
        UniqueConstraint("run_id", "snapshot_type", "taken_at", name="run_snapshots_unique"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    snapshot_type = Column(String, nullable=False)
    taken_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    payload = Column(JSONB, nullable=False)

    run = relationship("Run", back_populates="snapshots")


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    subject = Column(Text)
    body_text = Column(Text)
    body_html = Column(Text)
    recipients = Column(JSONB, default=list, nullable=False)
    bcc_recipients = Column(JSONB, default=list, nullable=False)
    source_paths = Column(JSONB, default=list, nullable=False)
    status = Column(String, default="enviado", nullable=False)
    error = Column(Text)
    retention_days = Column(Integer, default=7, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    run = relationship("Run", back_populates="email_events")
    attachments = relationship("EmailAttachment", back_populates="email_event", cascade="all,delete")


class EmailAttachment(Base):
    __tablename__ = "email_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("email_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = Column(Text, nullable=False)
    mime_type = Column(String)
    size_bytes = Column(BigInteger, nullable=False)
    storage_key = Column(Text, nullable=False)
    source_path = Column(Text)
    preview_supported = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    email_event = relationship("EmailEvent", back_populates="attachments")


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    automation_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("automation_instances.id"), nullable=False
    )
    script = Column(String, default="main.py", nullable=False)
    args = Column(JSONB, default=list, nullable=False)
    recurrence_type = Column(String, nullable=False)
    recurrence_config = Column(JSONB, default=dict, nullable=False)
    execution_mode = Column(String, default="parallel", nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    timezone = Column(String, default="America/Sao_Paulo", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    automation_instance = relationship("AutomationInstance")


class Command(Base):
    __tablename__ = "commands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)
    automation_instance_id = Column(
        UUID(as_uuid=True), ForeignKey("automation_instances.id"), nullable=False
    )
    scheduled_job_id = Column(UUID(as_uuid=True), ForeignKey("scheduled_jobs.id", ondelete="SET NULL"))
    script = Column(String, default="main.py", nullable=False)
    args = Column(JSONB, default=list, nullable=False)
    working_dir = Column(String, nullable=False)
    execution_mode = Column(String, default="parallel", nullable=False)
    status = Column(String, default="pending", nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"))
    created_by = Column(String, default="user", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    acked_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    result_message = Column(Text)

    host = relationship("Host")
    automation_instance = relationship("AutomationInstance")
    scheduled_job = relationship("ScheduledJob")
    run = relationship("Run")


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    # role: "admin" | "user"
    role = Column(String, nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    permissions = relationship("UserPermission", back_populates="user", cascade="all,delete")
    host_access = relationship("UserHostAccess", back_populates="user", cascade="all,delete")
    automation_access = relationship("UserAutomationAccess", back_populates="user", cascade="all,delete")
    client_access = relationship("UserClientAccess", back_populates="user", cascade="all,delete")
    sessions = relationship("UserSession", back_populates="user", cascade="all,delete")


class UserPermission(Base):
    """Global permissions granted to a user.

    Possible values for ``permission``:
    - ``view_all``         — can see all hosts/automations/runs
    - ``run_automations``  — can start/stop automations and manage schedules
    - ``configure_args``   — can configure execution arguments on instances
    """
    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "permission", name="user_permissions_unique"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission = Column(String, nullable=False)

    user = relationship("User", back_populates="permissions")


class UserHostAccess(Base):
    """Grants a user visibility over a specific host (used when user lacks view_all)."""
    __tablename__ = "user_host_access"
    __table_args__ = (
        UniqueConstraint("user_id", "host_id", name="user_host_access_unique"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="host_access")
    host = relationship("Host")


class UserAutomationAccess(Base):
    """Grants a user visibility over a specific automation (used when user lacks view_all)."""
    __tablename__ = "user_automation_access"
    __table_args__ = (
        UniqueConstraint("user_id", "automation_id", name="user_automation_access_unique"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    automation_id = Column(UUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="automation_access")
    automation = relationship("Automation")


class UserClientAccess(Base):
    """Grants a user visibility over all automations of a specific client."""
    __tablename__ = "user_client_access"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="user_client_access_unique"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="client_access")
    client = relationship("Client")


class UserSession(Base):
    """Stores refresh tokens (hashed) to allow revocation."""
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="sessions")
