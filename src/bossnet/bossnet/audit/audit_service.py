"""
Comprehensive Audit Logging Service
Tracks all security-relevant events and user actions
"""

import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from config.settings import settings
from fastapi import Request
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, and_, desc, or_
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Session

from database.base import Base, get_db


class AuditEventType(str, Enum):
    """Audit event types"""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM = "system"
    SECURITY = "security"
    ADMIN = "admin"
    ERROR = "error"


class AuditSeverity(str, Enum):
    """Audit event severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEventModel(Base):
    """Audit event model for storing audit logs"""

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False, index=True)

    # Event classification
    event_type = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), default=AuditSeverity.LOW.value, nullable=False)

    # User and session context
    user_id = Column(Integer, nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)

    # Request context
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    endpoint = Column(String(255), nullable=True)
    http_method = Column(String(10), nullable=True)

    # Event details
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    details = Column(JSONB, nullable=True)  # Structured event details

    # Outcome
    success = Column(Boolean, nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    correlation_id = Column(String(255), nullable=True, index=True)  # For tracing related events

    # Data integrity
    checksum = Column(String(64), nullable=True)  # SHA-256 hash for integrity

    # Indexes for performance
    __table_args__ = (
        Index("ix_audit_events_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_events_type_action", "event_type", "action"),
        Index("ix_audit_events_severity_timestamp", "severity", "timestamp"),
        Index("ix_audit_events_resource", "resource_type", "resource_id"),
        Index("ix_audit_events_ip_timestamp", "ip_address", "timestamp"),
    )

    def calculate_checksum(self) -> str:
        """Calculate checksum for data integrity"""
        data = f"{self.event_id}{self.event_type}{self.action}{self.user_id}{self.timestamp}{self.details}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify event integrity"""
        if not self.checksum:
            return False
        return self.checksum == self.calculate_checksum()


class AuditSearchRequest(BaseModel):
    """Audit search request parameters"""

    event_type: Optional[str] = None
    action: Optional[str] = None
    user_id: Optional[int] = None
    severity: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ip_address: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    success: Optional[bool] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditStatistics(BaseModel):
    """Audit statistics response"""

    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    failed_events: int
    unique_users: int
    unique_ips: int
    date_range: Dict[str, datetime]


class AuditService:
    """Comprehensive audit logging service"""

    def __init__(self):
        self.sensitive_fields = {
            "password",
            "token",
            "secret",
            "key",
            "credential",
            "ssn",
            "social_security",
            "credit_card",
            "card_number",
            "pin",
            "otp",
            "verification_code",
        }

    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize sensitive data before logging"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                    # Hash sensitive data instead of storing plaintext
                    if isinstance(value, str) and value:
                        sanitized[key] = f"sha256:{hashlib.sha256(value.encode()).hexdigest()[:16]}..."
                    else:
                        sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            # Check if string contains sensitive patterns
            data_lower = data.lower()
            if any(sensitive in data_lower for sensitive in self.sensitive_fields):
                return "[REDACTED]"

        return data

    def _extract_request_context(self, request: Optional[Request] = None) -> Dict[str, Any]:
        """Extract context information from request"""
        context = {}

        if request:
            context.update(
                {
                    "ip_address": self._get_client_ip(request),
                    "user_agent": request.headers.get("user-agent"),
                    "endpoint": str(request.url.path),
                    "http_method": request.method,
                    "request_id": request.headers.get("x-request-id") or str(uuid4()),
                }
            )

        return context

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers (load balancer, proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    async def log_event(
        self,
        event_type: str,
        action: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: Optional[bool] = None,
        error_message: Optional[str] = None,
        severity: str = AuditSeverity.LOW.value,
        correlation_id: Optional[str] = None,
        request: Optional[Request] = None,
        db: Optional[Session] = None,
    ) -> AuditEventModel:
        """Log an audit event"""

        # Get database session
        if not db:
            db = next(get_db())

        # Extract request context
        request_context = self._extract_request_context(request)

        # Sanitize details
        sanitized_details = self._sanitize_data(details) if details else None

        # Create audit event
        audit_event = AuditEventModel(
            event_type=event_type,
            action=action,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=sanitized_details,
            success=success,
            error_message=error_message,
            correlation_id=correlation_id,
            **request_context,
        )

        # Calculate checksum for integrity
        audit_event.checksum = audit_event.calculate_checksum()

        # Save to database
        try:
            db.add(audit_event)
            db.commit()
            db.refresh(audit_event)

            # Log critical events to external systems if configured
            if severity == AuditSeverity.CRITICAL.value:
                await self._send_critical_alert(audit_event)

            return audit_event

        except Exception as e:
            db.rollback()
            # Log to application logs as fallback
            print(f"Failed to save audit event: {e}")
            raise

    async def _send_critical_alert(self, event: AuditEventModel):
        """Send alert for critical security events"""
        # Implementation would send to SIEM, Slack, email, etc.
        # This is a placeholder for external alerting
        pass

    async def log_authentication_event(
        self,
        action: str,
        user_id: Optional[int] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        db: Optional[Session] = None,
    ):
        """Log authentication-related events"""
        severity = AuditSeverity.MEDIUM.value if not success else AuditSeverity.LOW.value

        await self.log_event(
            event_type=AuditEventType.AUTHENTICATION.value,
            action=action,
            user_id=user_id,
            success=success,
            details=details,
            severity=severity,
            request=request,
            db=db,
        )

    async def log_authorization_event(
        self,
        action: str,
        user_id: int,
        resource_type: str,
        resource_id: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        db: Optional[Session] = None,
    ):
        """Log authorization-related events"""
        severity = AuditSeverity.HIGH.value if not success else AuditSeverity.LOW.value

        await self.log_event(
            event_type=AuditEventType.AUTHORIZATION.value,
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            details=details,
            severity=severity,
            request=request,
            db=db,
        )

    async def log_data_access(
        self,
        action: str,
        user_id: int,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        db: Optional[Session] = None,
    ):
        """Log data access events"""
        await self.log_event(
            event_type=AuditEventType.DATA_ACCESS.value,
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=True,
            details=details,
            severity=AuditSeverity.LOW.value,
            request=request,
            db=db,
        )

    async def log_data_modification(
        self,
        action: str,
        user_id: int,
        resource_type: str,
        resource_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        success: bool = True,
        request: Optional[Request] = None,
        db: Optional[Session] = None,
    ):
        """Log data modification events"""
        details = {}
        if old_values:
            details["old_values"] = old_values
        if new_values:
            details["new_values"] = new_values

        await self.log_event(
            event_type=AuditEventType.DATA_MODIFICATION.value,
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            details=details,
            severity=AuditSeverity.MEDIUM.value,
            request=request,
            db=db,
        )

    async def log_security_event(
        self,
        action: str,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = AuditSeverity.HIGH.value,
        success: Optional[bool] = None,
        request: Optional[Request] = None,
        db: Optional[Session] = None,
    ):
        """Log security-related events"""
        await self.log_event(
            event_type=AuditEventType.SECURITY.value,
            action=action,
            user_id=user_id,
            success=success,
            details=details,
            severity=severity,
            request=request,
            db=db,
        )

    async def log_admin_event(
        self,
        action: str,
        user_id: int,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        request: Optional[Request] = None,
        db: Optional[Session] = None,
    ):
        """Log administrative events"""
        await self.log_event(
            event_type=AuditEventType.ADMIN.value,
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            details=details,
            severity=AuditSeverity.MEDIUM.value,
            request=request,
            db=db,
        )

    def search_events(self, search_params: AuditSearchRequest, db: Session) -> List[AuditEventModel]:
        """Search audit events with filters"""
        query = db.query(AuditEventModel)

        # Apply filters
        if search_params.event_type:
            query = query.filter(AuditEventModel.event_type == search_params.event_type)

        if search_params.action:
            query = query.filter(AuditEventModel.action == search_params.action)

        if search_params.user_id:
            query = query.filter(AuditEventModel.user_id == search_params.user_id)

        if search_params.severity:
            query = query.filter(AuditEventModel.severity == search_params.severity)

        if search_params.start_date:
            query = query.filter(AuditEventModel.timestamp >= search_params.start_date)

        if search_params.end_date:
            query = query.filter(AuditEventModel.timestamp <= search_params.end_date)

        if search_params.ip_address:
            query = query.filter(AuditEventModel.ip_address == search_params.ip_address)

        if search_params.resource_type:
            query = query.filter(AuditEventModel.resource_type == search_params.resource_type)

        if search_params.resource_id:
            query = query.filter(AuditEventModel.resource_id == search_params.resource_id)

        if search_params.success is not None:
            query = query.filter(AuditEventModel.success == search_params.success)

        # Order by timestamp descending (newest first)
        query = query.order_by(desc(AuditEventModel.timestamp))

        # Apply pagination
        query = query.offset(search_params.offset).limit(search_params.limit)

        return query.all()

    def get_audit_statistics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, db: Session = None
    ) -> AuditStatistics:
        """Get audit statistics for dashboard"""
        if not db:
            db = next(get_db())

        query = db.query(AuditEventModel)

        # Apply date filters
        if start_date:
            query = query.filter(AuditEventModel.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditEventModel.timestamp <= end_date)

        # Get total events
        total_events = query.count()

        # Events by type
        events_by_type = {}
        for event_type in AuditEventType:
            count = query.filter(AuditEventModel.event_type == event_type.value).count()
            events_by_type[event_type.value] = count

        # Events by severity
        events_by_severity = {}
        for severity in AuditSeverity:
            count = query.filter(AuditEventModel.severity == severity.value).count()
            events_by_severity[severity.value] = count

        # Failed events
        failed_events = query.filter(AuditEventModel.success == False).count()

        # Unique users and IPs
        unique_users = db.query(AuditEventModel.user_id).filter(AuditEventModel.user_id.isnot(None)).distinct().count()

        unique_ips = db.query(AuditEventModel.ip_address).filter(AuditEventModel.ip_address.isnot(None)).distinct().count()

        # Date range
        date_range = {}
        if total_events > 0:
            earliest = query.order_by(AuditEventModel.timestamp.asc()).first()
            latest = query.order_by(AuditEventModel.timestamp.desc()).first()
            date_range = {"earliest": earliest.timestamp, "latest": latest.timestamp}

        return AuditStatistics(
            total_events=total_events,
            events_by_type=events_by_type,
            events_by_severity=events_by_severity,
            failed_events=failed_events,
            unique_users=unique_users,
            unique_ips=unique_ips,
            date_range=date_range,
        )

    async def cleanup_old_events(self, retention_days: int = 365, db: Session = None):
        """Clean up old audit events based on retention policy"""
        if not db:
            db = next(get_db())

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Delete old events
        deleted_count = db.query(AuditEventModel).filter(AuditEventModel.timestamp < cutoff_date).delete()

        db.commit()

        # Log cleanup event
        await self.log_event(
            event_type=AuditEventType.SYSTEM.value,
            action="audit_cleanup",
            details={
                "retention_days": retention_days,
                "deleted_events": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
            },
            severity=AuditSeverity.LOW.value,
            db=db,
        )

        return deleted_count

    def verify_event_integrity(self, event_id: int, db: Session) -> bool:
        """Verify the integrity of an audit event"""
        event = db.query(AuditEventModel).filter(AuditEventModel.id == event_id).first()

        if not event:
            return False

        return event.verify_integrity()

    async def detect_suspicious_activity(self, db: Session) -> List[Dict[str, Any]]:
        """Detect suspicious activity patterns"""
        suspicious_activities = []

        # Multiple failed login attempts from same IP
        failed_logins = (
            db.query(AuditEventModel)
            .filter(
                and_(
                    AuditEventModel.event_type == AuditEventType.AUTHENTICATION.value,
                    AuditEventModel.action == "login_failed",
                    AuditEventModel.timestamp >= datetime.utcnow() - timedelta(hours=1),
                    AuditEventModel.success == False,
                )
            )
            .all()
        )

        # Group by IP address
        ip_failures = {}
        for event in failed_logins:
            ip = event.ip_address
            if ip:
                ip_failures[ip] = ip_failures.get(ip, 0) + 1

        # Flag IPs with more than 5 failed attempts
        for ip, count in ip_failures.items():
            if count >= 5:
                suspicious_activities.append(
                    {"type": "multiple_failed_logins", "ip_address": ip, "count": count, "severity": "high"}
                )

        # Unusual access patterns (access from new locations)
        # This would require more sophisticated geolocation analysis

        # Multiple MFA failures
        mfa_failures = (
            db.query(AuditEventModel)
            .filter(
                and_(
                    AuditEventModel.event_type == AuditEventType.SECURITY.value,
                    AuditEventModel.action.like("%mfa%failed%"),
                    AuditEventModel.timestamp >= datetime.utcnow() - timedelta(hours=1),
                )
            )
            .count()
        )

        if mfa_failures >= 10:
            suspicious_activities.append({"type": "multiple_mfa_failures", "count": mfa_failures, "severity": "high"})

        return suspicious_activities
