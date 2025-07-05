"""
Security API endpoints for OAuth2, MFA, Audit, and Vulnerability Management
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from audit.audit_service import AuditSearchRequest, AuditService, AuditStatistics
from auth.dependencies import admin_required, get_current_active_user
from auth.mfa_service import MFAService, MFAVerificationRequest, TOTPSetupResponse
from auth.models import UserInDB
from auth.oauth2_service import OAuth2Service, OAuthUserInfo
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.base import get_db
from security.encryption_service import EncryptionService
from security.vulnerability_scanner import ScanResult, ScanType, VulnerabilityDetail, VulnerabilityScanner

router = APIRouter(
    prefix="/security",
    tags=["security"],
    responses={404: {"description": "Not found"}},
)

# Initialize services
oauth2_service = OAuth2Service()
mfa_service = MFAService()
audit_service = AuditService()
encryption_service = EncryptionService()
vulnerability_scanner = VulnerabilityScanner()


# OAuth2 Endpoints
class OAuthAuthorizationRequest(BaseModel):
    provider: str = Field(..., description="OAuth provider name (google, microsoft)")
    redirect_uri: str = Field(..., description="Redirect URI after authorization")


class OAuthAuthorizationResponse(BaseModel):
    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user_info: Dict[str, Any]


@router.get("/oauth/providers", summary="Get supported OAuth providers")
async def get_oauth_providers():
    """Get list of supported OAuth providers"""
    return {"providers": oauth2_service.get_supported_providers()}


@router.post("/oauth/authorize", response_model=OAuthAuthorizationResponse, summary="Get OAuth authorization URL")
async def get_oauth_authorization_url(request: OAuthAuthorizationRequest, db: Session = Depends(get_db)):
    """Get OAuth authorization URL for specified provider"""
    try:
        auth_url, state = oauth2_service.get_authorization_url(request.provider, request.redirect_uri)

        return OAuthAuthorizationResponse(authorization_url=auth_url, state=state)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/oauth/callback", response_model=OAuthTokenResponse, summary="Handle OAuth callback")
async def handle_oauth_callback(callback_request: OAuthCallbackRequest, request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback and authenticate user"""
    try:
        # Exchange code for token
        token_response = await oauth2_service.exchange_code_for_token(callback_request.code, callback_request.state)

        # Get user info from provider
        access_token = token_response.get("access_token")
        provider_name = "google"  # This should be extracted from state

        oauth_user = await oauth2_service.get_user_info(access_token, provider_name)

        # Authenticate or create user
        user, is_new_user = await oauth2_service.authenticate_user(oauth_user, db)

        # Generate JWT token for our application
        from auth.service import AuthService

        auth_service = AuthService()
        jwt_token = auth_service.create_access_token(data={"sub": str(user.id)})

        return OAuthTokenResponse(
            access_token=jwt_token,
            token_type="bearer",
            expires_in=3600,
            user_info={
                "id": user.id,
                "email": user.email,
                "name": f"{user.first_name} {user.last_name}",
                "is_new_user": is_new_user,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# MFA Endpoints
class MFASetupRequest(BaseModel):
    method: str = Field(..., description="MFA method: totp, sms, email")
    device_name: str = Field(..., description="Device name for identification")
    phone_number: Optional[str] = Field(None, description="Phone number for SMS MFA")
    email_address: Optional[str] = Field(None, description="Email address for Email MFA")


class MFAVerificationResponse(BaseModel):
    success: bool
    message: str


@router.post("/mfa/setup/totp", response_model=TOTPSetupResponse, summary="Set up TOTP MFA")
async def setup_totp_mfa(
    setup_request: MFASetupRequest, current_user: UserInDB = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Set up TOTP (Time-based One-Time Password) MFA"""
    return await mfa_service.setup_totp(current_user.id, setup_request.device_name, db)


@router.post("/mfa/setup/sms", summary="Set up SMS MFA")
async def setup_sms_mfa(
    setup_request: MFASetupRequest, current_user: UserInDB = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Set up SMS-based MFA"""
    if not setup_request.phone_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is required for SMS MFA")

    challenge_id = await mfa_service.setup_sms_mfa(current_user.id, setup_request.phone_number, setup_request.device_name, db)

    return {"challenge_id": challenge_id, "message": "SMS verification code sent"}


@router.post("/mfa/setup/email", summary="Set up Email MFA")
async def setup_email_mfa(
    setup_request: MFASetupRequest, current_user: UserInDB = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Set up Email-based MFA"""
    email_address = setup_request.email_address or current_user.email

    challenge_id = await mfa_service.setup_email_mfa(current_user.id, email_address, setup_request.device_name, db)

    return {"challenge_id": challenge_id, "message": "Email verification code sent"}


@router.post("/mfa/verify", response_model=MFAVerificationResponse, summary="Verify MFA setup or challenge")
async def verify_mfa(
    verification_request: MFAVerificationRequest,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Verify MFA code for setup or authentication"""
    try:
        if verification_request.method == "totp":
            success = await mfa_service.verify_totp_setup(
                current_user.id, "default", verification_request.code, db  # device name would be stored in challenge
            )
        else:
            success = await mfa_service.verify_mfa_challenge(verification_request.challenge_id, verification_request.code, db)

        return MFAVerificationResponse(
            success=success, message="MFA verification successful" if success else "Invalid verification code"
        )

    except Exception as e:
        return MFAVerificationResponse(success=False, message=str(e))


@router.get("/mfa/devices", summary="Get user's MFA devices")
async def get_mfa_devices(current_user: UserInDB = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get user's configured MFA devices"""
    devices = mfa_service.get_user_mfa_devices(current_user.id, db)

    return {
        "devices": [
            {
                "id": device.id,
                "name": device.device_name,
                "method": device.method,
                "is_verified": device.is_verified,
                "created_at": device.created_at,
                "last_used": device.last_used,
            }
            for device in devices
        ]
    }


@router.delete("/mfa/devices/{device_id}", summary="Disable MFA device")
async def disable_mfa_device(
    device_id: int, current_user: UserInDB = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Disable an MFA device"""
    success = await mfa_service.disable_mfa_device(current_user.id, device_id, db)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MFA device not found")

    return {"message": "MFA device disabled successfully"}


# Audit Endpoints
@router.post("/audit/search", summary="Search audit events")
async def search_audit_events(
    search_request: AuditSearchRequest, current_user: UserInDB = Depends(admin_required), db: Session = Depends(get_db)
):
    """Search audit events with filters (Admin only)"""
    events = audit_service.search_events(search_request, db)

    return {
        "events": [
            {
                "id": event.id,
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "action": event.action,
                "severity": event.severity,
                "user_id": event.user_id,
                "ip_address": event.ip_address,
                "timestamp": event.timestamp,
                "success": event.success,
                "details": event.details,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
            }
            for event in events
        ],
        "total": len(events),
    }


@router.get("/audit/statistics", response_model=AuditStatistics, summary="Get audit statistics")
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    current_user: UserInDB = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Get audit statistics (Admin only)"""
    return audit_service.get_audit_statistics(start_date, end_date, db)


@router.get("/audit/suspicious", summary="Detect suspicious activity")
async def detect_suspicious_activity(current_user: UserInDB = Depends(admin_required), db: Session = Depends(get_db)):
    """Detect suspicious activity patterns (Admin only)"""
    suspicious_activities = await audit_service.detect_suspicious_activity(db)
    return {"suspicious_activities": suspicious_activities}


# Encryption Endpoints
@router.get("/encryption/statistics", summary="Get encryption statistics")
async def get_encryption_statistics(current_user: UserInDB = Depends(admin_required), db: Session = Depends(get_db)):
    """Get encryption statistics (Admin only)"""
    return encryption_service.get_encryption_statistics(db)


@router.post("/encryption/rotate-key/{key_id}", summary="Rotate encryption key")
async def rotate_encryption_key(key_id: str, current_user: UserInDB = Depends(admin_required), db: Session = Depends(get_db)):
    """Rotate an encryption key (Admin only)"""
    try:
        new_key_id = encryption_service.rotate_key(key_id, db)
        return {"message": "Key rotated successfully", "old_key_id": key_id, "new_key_id": new_key_id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Vulnerability Scanner Endpoints
class VulnerabilityScanRequest(BaseModel):
    scan_type: str = Field(..., description="Scan type: dependency, code, container, web")
    target: str = Field(..., description="Scan target (file, directory, URL, etc.)")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Scan options")


@router.post("/vulnerabilities/scan", summary="Start vulnerability scan")
async def start_vulnerability_scan(
    scan_request: VulnerabilityScanRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInDB = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Start a vulnerability scan (Admin only)"""
    try:
        scan_type = ScanType(scan_request.scan_type)
        scan_id = await vulnerability_scanner.start_scan(scan_type, scan_request.target, db, scan_request.options)

        return {"scan_id": scan_id, "message": "Vulnerability scan started", "status": "running"}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid scan type: {scan_request.scan_type}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/vulnerabilities/scan/{scan_id}", response_model=ScanResult, summary="Get scan results")
async def get_scan_results(scan_id: str, current_user: UserInDB = Depends(admin_required), db: Session = Depends(get_db)):
    """Get vulnerability scan results (Admin only)"""
    results = vulnerability_scanner.get_scan_results(scan_id, db)

    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    return results


@router.get(
    "/vulnerabilities/scan/{scan_id}/details", response_model=List[VulnerabilityDetail], summary="Get vulnerability details"
)
async def get_vulnerability_details(
    scan_id: str, current_user: UserInDB = Depends(admin_required), db: Session = Depends(get_db)
):
    """Get detailed vulnerabilities for a scan (Admin only)"""
    return vulnerability_scanner.get_vulnerabilities(scan_id, db)


@router.get("/vulnerabilities/history", summary="Get scan history")
async def get_scan_history(
    limit: int = Query(50, le=100, description="Maximum number of scans to return"),
    current_user: UserInDB = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Get vulnerability scan history (Admin only)"""
    return {"scans": vulnerability_scanner.get_scan_history(limit, db)}


@router.get("/vulnerabilities/statistics", summary="Get vulnerability statistics")
async def get_vulnerability_statistics(current_user: UserInDB = Depends(admin_required), db: Session = Depends(get_db)):
    """Get vulnerability statistics (Admin only)"""
    return vulnerability_scanner.get_vulnerability_statistics(db)


# Security Dashboard Endpoint
@router.get("/dashboard", summary="Get security dashboard data")
async def get_security_dashboard(current_user: UserInDB = Depends(admin_required), db: Session = Depends(get_db)):
    """Get comprehensive security dashboard data (Admin only)"""
    # Get data from all security services
    audit_stats = audit_service.get_audit_statistics(db=db)
    encryption_stats = encryption_service.get_encryption_statistics(db)
    vulnerability_stats = vulnerability_scanner.get_vulnerability_statistics(db)
    suspicious_activities = await audit_service.detect_suspicious_activity(db)

    # Check if user has MFA enabled
    user_has_mfa = mfa_service.user_has_mfa(current_user.id, db)

    return {
        "audit": {
            "total_events": audit_stats.total_events,
            "failed_events": audit_stats.failed_events,
            "unique_users": audit_stats.unique_users,
            "events_by_severity": audit_stats.events_by_severity,
        },
        "encryption": {
            "total_keys": encryption_stats["total_keys"],
            "active_keys": encryption_stats["active_keys"],
            "expired_keys": encryption_stats["expired_keys"],
            "encrypted_records": encryption_stats["total_encrypted_records"],
        },
        "vulnerabilities": {
            "total_scans": vulnerability_stats["total_scans"],
            "open_vulnerabilities": vulnerability_stats["open_vulnerabilities"],
            "vulnerabilities_by_severity": vulnerability_stats["vulnerabilities_by_severity"],
            "recent_scans": vulnerability_stats["recent_scans"],
        },
        "security_status": {
            "mfa_enabled": user_has_mfa,
            "suspicious_activities": len(suspicious_activities),
            "last_scan": None,  # Would get from vulnerability_stats
        },
        "alerts": suspicious_activities,
    }
