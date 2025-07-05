"""
Multi-Factor Authentication (MFA) Service
Supports TOTP, SMS, and Email-based MFA
"""

import base64
import io
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import pyotp
import qrcode
from audit.audit_service import AuditService
from auth.email_service import EmailService
from config.settings import settings
from fastapi import HTTPException, status
from models.user import UserModel
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session, relationship
from twilio.base.exceptions import TwilioException
from twilio.rest import Client as TwilioClient
from utils.security_utils import generate_secure_token

from database.base import Base


class MFAMethod(str):
    """MFA method types"""

    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"


class MFADeviceModel(Base):
    """MFA device model for storing user MFA configurations"""

    __tablename__ = "mfa_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_name = Column(String(100), nullable=False)
    method = Column(String(20), nullable=False)  # totp, sms, email
    secret_key = Column(String(255), nullable=True)  # For TOTP
    phone_number = Column(String(20), nullable=True)  # For SMS
    email_address = Column(String(255), nullable=True)  # For Email MFA
    backup_codes = Column(Text, nullable=True)  # JSON array of backup codes
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="mfa_devices")

    def __repr__(self):
        return f"<MFADevice(user_id={self.user_id}, method={self.method}, name={self.device_name})>"


class MFAChallengeModel(Base):
    """MFA challenge model for temporary verification codes"""

    __tablename__ = "mfa_challenges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenge_id = Column(String(64), unique=True, nullable=False, index=True)
    method = Column(String(20), nullable=False)
    code = Column(String(10), nullable=False)
    phone_number = Column(String(20), nullable=True)
    email_address = Column(String(255), nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("UserModel")

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired() and self.attempts < self.max_attempts


class TOTPSetupResponse(BaseModel):
    """TOTP setup response"""

    secret: str
    qr_code: str  # Base64 encoded QR code image
    backup_codes: List[str]
    manual_entry_key: str


class MFAVerificationRequest(BaseModel):
    """MFA verification request"""

    challenge_id: str
    code: str
    method: str


class MFAService:
    """Multi-Factor Authentication service"""

    def __init__(self):
        self.email_service = EmailService()
        self.audit_service = AuditService()

        # Initialize Twilio client if configured
        self.twilio_client = None
        if hasattr(settings, "TWILIO_ACCOUNT_SID") and settings.TWILIO_ACCOUNT_SID:
            self.twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    def generate_totp_secret(self) -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for MFA"""
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8-character hex code
            codes.append(f"{code[:4]}-{code[4:]}")  # Format: XXXX-XXXX
        return codes

    def create_qr_code(self, secret: str, user_email: str, issuer: str = None) -> str:
        """Create QR code for TOTP setup"""
        if not issuer:
            issuer = settings.PROJECT_NAME

        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=user_email, issuer_name=issuer)

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"

    async def setup_totp(self, user_id: int, device_name: str, db: Session) -> TOTPSetupResponse:
        """Set up TOTP MFA for a user"""
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Generate secret and backup codes
        secret = self.generate_totp_secret()
        backup_codes = self.generate_backup_codes()

        # Create MFA device record
        mfa_device = MFADeviceModel(
            user_id=user_id,
            device_name=device_name,
            method=MFAMethod.TOTP,
            secret_key=secret,
            backup_codes=",".join(backup_codes),
            is_active=True,
            is_verified=False,
        )

        db.add(mfa_device)
        db.commit()
        db.refresh(mfa_device)

        # Generate QR code
        qr_code = self.create_qr_code(secret, user.email)

        # Log MFA setup
        await self.audit_service.log_event(
            event_type="security",
            action="mfa_setup_initiated",
            user_id=user_id,
            details={"method": MFAMethod.TOTP, "device_name": device_name},
        )

        return TOTPSetupResponse(secret=secret, qr_code=qr_code, backup_codes=backup_codes, manual_entry_key=secret)

    async def verify_totp_setup(self, user_id: int, device_name: str, code: str, db: Session) -> bool:
        """Verify TOTP setup with user-provided code"""
        mfa_device = (
            db.query(MFADeviceModel)
            .filter(
                MFADeviceModel.user_id == user_id,
                MFADeviceModel.device_name == device_name,
                MFADeviceModel.method == MFAMethod.TOTP,
                MFADeviceModel.is_active == True,
            )
            .first()
        )

        if not mfa_device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TOTP device not found")

        # Verify TOTP code
        totp = pyotp.TOTP(mfa_device.secret_key)
        if totp.verify(code, valid_window=1):  # Allow 1 window tolerance
            mfa_device.is_verified = True
            mfa_device.last_used = datetime.utcnow()
            mfa_device.use_count += 1
            db.commit()

            # Log successful verification
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_setup_completed",
                user_id=user_id,
                details={"method": MFAMethod.TOTP, "device_name": device_name},
            )

            return True
        else:
            # Log failed verification
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_setup_failed",
                user_id=user_id,
                details={"method": MFAMethod.TOTP, "device_name": device_name, "reason": "invalid_code"},
            )

            return False

    async def setup_sms_mfa(self, user_id: int, phone_number: str, device_name: str, db: Session) -> str:
        """Set up SMS MFA for a user"""
        if not self.twilio_client:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="SMS MFA not configured")

        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Generate verification code
        verification_code = secrets.randbelow(900000) + 100000  # 6-digit code
        challenge_id = generate_secure_token(32)

        # Create MFA challenge
        challenge = MFAChallengeModel(
            user_id=user_id,
            challenge_id=challenge_id,
            method=MFAMethod.SMS,
            code=str(verification_code),
            phone_number=phone_number,
            expires_at=datetime.utcnow() + timedelta(minutes=5),
        )

        db.add(challenge)
        db.commit()

        # Send SMS
        try:
            message = self.twilio_client.messages.create(
                body=f"Your {settings.PROJECT_NAME} verification code is: {verification_code}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number,
            )

            # Log SMS sent
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_sms_sent",
                user_id=user_id,
                details={"phone_number": phone_number[-4:], "message_sid": message.sid},  # Only log last 4 digits
            )

            return challenge_id

        except TwilioException as e:
            # Log SMS failure
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_sms_failed",
                user_id=user_id,
                details={"phone_number": phone_number[-4:], "error": str(e)},
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send SMS verification code"
            )

    async def verify_sms_setup(self, challenge_id: str, code: str, device_name: str, db: Session) -> bool:
        """Verify SMS MFA setup"""
        challenge = (
            db.query(MFAChallengeModel)
            .filter(MFAChallengeModel.challenge_id == challenge_id, MFAChallengeModel.method == MFAMethod.SMS)
            .first()
        )

        if not challenge or not challenge.is_valid():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge")

        challenge.attempts += 1

        if challenge.code == code:
            # Mark challenge as used
            challenge.is_used = True

            # Create MFA device
            backup_codes = self.generate_backup_codes()
            mfa_device = MFADeviceModel(
                user_id=challenge.user_id,
                device_name=device_name,
                method=MFAMethod.SMS,
                phone_number=challenge.phone_number,
                backup_codes=",".join(backup_codes),
                is_active=True,
                is_verified=True,
            )

            db.add(mfa_device)
            db.commit()

            # Log successful setup
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_sms_setup_completed",
                user_id=challenge.user_id,
                details={"device_name": device_name, "phone_number": challenge.phone_number[-4:]},
            )

            return True
        else:
            db.commit()  # Save attempt count

            # Log failed verification
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_sms_verification_failed",
                user_id=challenge.user_id,
                details={"challenge_id": challenge_id, "attempts": challenge.attempts},
            )

            return False

    async def setup_email_mfa(self, user_id: int, email_address: str, device_name: str, db: Session) -> str:
        """Set up Email MFA for a user"""
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Generate verification code
        verification_code = secrets.randbelow(900000) + 100000  # 6-digit code
        challenge_id = generate_secure_token(32)

        # Create MFA challenge
        challenge = MFAChallengeModel(
            user_id=user_id,
            challenge_id=challenge_id,
            method=MFAMethod.EMAIL,
            code=str(verification_code),
            email_address=email_address,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )

        db.add(challenge)
        db.commit()

        # Send email
        try:
            await self.email_service.send_mfa_code_email(email_address, user.first_name or "User", verification_code)

            # Log email sent
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_email_sent",
                user_id=user_id,
                details={"email_address": email_address, "device_name": device_name},
            )

            return challenge_id

        except Exception as e:
            # Log email failure
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_email_failed",
                user_id=user_id,
                details={"email_address": email_address, "error": str(e)},
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send email verification code"
            )

    async def verify_email_setup(self, challenge_id: str, code: str, device_name: str, db: Session) -> bool:
        """Verify Email MFA setup"""
        challenge = (
            db.query(MFAChallengeModel)
            .filter(MFAChallengeModel.challenge_id == challenge_id, MFAChallengeModel.method == MFAMethod.EMAIL)
            .first()
        )

        if not challenge or not challenge.is_valid():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge")

        challenge.attempts += 1

        if challenge.code == code:
            # Mark challenge as used
            challenge.is_used = True

            # Create MFA device
            backup_codes = self.generate_backup_codes()
            mfa_device = MFADeviceModel(
                user_id=challenge.user_id,
                device_name=device_name,
                method=MFAMethod.EMAIL,
                email_address=challenge.email_address,
                backup_codes=",".join(backup_codes),
                is_active=True,
                is_verified=True,
            )

            db.add(mfa_device)
            db.commit()

            # Log successful setup
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_email_setup_completed",
                user_id=challenge.user_id,
                details={"device_name": device_name, "email_address": challenge.email_address},
            )

            return True
        else:
            db.commit()  # Save attempt count

            # Log failed verification
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_email_verification_failed",
                user_id=challenge.user_id,
                details={"challenge_id": challenge_id, "attempts": challenge.attempts},
            )

            return False

    async def initiate_mfa_challenge(self, user_id: int, method: str, db: Session) -> str:
        """Initiate MFA challenge for login"""
        # Find user's MFA device
        mfa_device = (
            db.query(MFADeviceModel)
            .filter(
                MFADeviceModel.user_id == user_id,
                MFADeviceModel.method == method,
                MFADeviceModel.is_active == True,
                MFADeviceModel.is_verified == True,
            )
            .first()
        )

        if not mfa_device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No verified {method} MFA device found")

        challenge_id = generate_secure_token(32)

        if method == MFAMethod.TOTP:
            # TOTP doesn't need a challenge, return challenge ID for verification
            challenge = MFAChallengeModel(
                user_id=user_id,
                challenge_id=challenge_id,
                method=method,
                code="",  # TOTP codes are generated by the user's device
                expires_at=datetime.utcnow() + timedelta(minutes=5),
            )
            db.add(challenge)
            db.commit()

            return challenge_id

        elif method == MFAMethod.SMS:
            if not self.twilio_client:
                raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="SMS MFA not configured")

            # Generate and send SMS code
            verification_code = secrets.randbelow(900000) + 100000
            challenge = MFAChallengeModel(
                user_id=user_id,
                challenge_id=challenge_id,
                method=method,
                code=str(verification_code),
                phone_number=mfa_device.phone_number,
                expires_at=datetime.utcnow() + timedelta(minutes=5),
            )

            db.add(challenge)
            db.commit()

            # Send SMS
            try:
                message = self.twilio_client.messages.create(
                    body=f"Your {settings.PROJECT_NAME} login code is: {verification_code}",
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=mfa_device.phone_number,
                )

                await self.audit_service.log_event(
                    event_type="authentication",
                    action="mfa_challenge_sent",
                    user_id=user_id,
                    details={"method": method, "phone_number": mfa_device.phone_number[-4:], "message_sid": message.sid},
                )

                return challenge_id

            except TwilioException as e:
                await self.audit_service.log_event(
                    event_type="security",
                    action="mfa_challenge_failed",
                    user_id=user_id,
                    details={"method": method, "error": str(e)},
                )

                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send SMS code")

        elif method == MFAMethod.EMAIL:
            # Generate and send email code
            verification_code = secrets.randbelow(900000) + 100000
            challenge = MFAChallengeModel(
                user_id=user_id,
                challenge_id=challenge_id,
                method=method,
                code=str(verification_code),
                email_address=mfa_device.email_address,
                expires_at=datetime.utcnow() + timedelta(minutes=10),
            )

            db.add(challenge)
            db.commit()

            # Send email
            try:
                user = db.query(UserModel).filter(UserModel.id == user_id).first()
                await self.email_service.send_mfa_code_email(
                    mfa_device.email_address, user.first_name or "User", verification_code
                )

                await self.audit_service.log_event(
                    event_type="authentication",
                    action="mfa_challenge_sent",
                    user_id=user_id,
                    details={"method": method, "email_address": mfa_device.email_address},
                )

                return challenge_id

            except Exception as e:
                await self.audit_service.log_event(
                    event_type="security",
                    action="mfa_challenge_failed",
                    user_id=user_id,
                    details={"method": method, "error": str(e)},
                )

                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send email code")

    async def verify_mfa_challenge(self, challenge_id: str, code: str, db: Session) -> bool:
        """Verify MFA challenge code"""
        challenge = db.query(MFAChallengeModel).filter(MFAChallengeModel.challenge_id == challenge_id).first()

        if not challenge or not challenge.is_valid():
            await self.audit_service.log_event(
                event_type="security",
                action="mfa_verification_failed",
                user_id=challenge.user_id if challenge else None,
                details={"challenge_id": challenge_id, "reason": "invalid_or_expired_challenge"},
            )

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired challenge")

        challenge.attempts += 1

        # Verify code based on method
        is_valid = False

        if challenge.method == MFAMethod.TOTP:
            # Get user's TOTP device
            mfa_device = (
                db.query(MFADeviceModel)
                .filter(
                    MFADeviceModel.user_id == challenge.user_id,
                    MFADeviceModel.method == MFAMethod.TOTP,
                    MFADeviceModel.is_active == True,
                    MFADeviceModel.is_verified == True,
                )
                .first()
            )

            if mfa_device:
                totp = pyotp.TOTP(mfa_device.secret_key)
                is_valid = totp.verify(code, valid_window=1)

                if is_valid:
                    mfa_device.last_used = datetime.utcnow()
                    mfa_device.use_count += 1

        elif challenge.method in [MFAMethod.SMS, MFAMethod.EMAIL]:
            is_valid = challenge.code == code

        # Check backup codes if primary method failed
        if not is_valid:
            is_valid = await self._verify_backup_code(challenge.user_id, code, db)

        if is_valid:
            challenge.is_used = True
            db.commit()

            await self.audit_service.log_event(
                event_type="authentication",
                action="mfa_verification_success",
                user_id=challenge.user_id,
                details={"method": challenge.method, "challenge_id": challenge_id},
            )

            return True
        else:
            db.commit()  # Save attempt count

            await self.audit_service.log_event(
                event_type="security",
                action="mfa_verification_failed",
                user_id=challenge.user_id,
                details={"method": challenge.method, "challenge_id": challenge_id, "attempts": challenge.attempts},
            )

            return False

    async def _verify_backup_code(self, user_id: int, code: str, db: Session) -> bool:
        """Verify backup code"""
        mfa_devices = (
            db.query(MFADeviceModel)
            .filter(
                MFADeviceModel.user_id == user_id,
                MFADeviceModel.is_active == True,
                MFADeviceModel.is_verified == True,
                MFADeviceModel.backup_codes.isnot(None),
            )
            .all()
        )

        for device in mfa_devices:
            backup_codes = device.backup_codes.split(",") if device.backup_codes else []

            if code in backup_codes:
                # Remove used backup code
                backup_codes.remove(code)
                device.backup_codes = ",".join(backup_codes)
                db.commit()

                await self.audit_service.log_event(
                    event_type="security",
                    action="backup_code_used",
                    user_id=user_id,
                    details={"device_id": device.id, "remaining_codes": len(backup_codes)},
                )

                return True

        return False

    def get_user_mfa_devices(self, user_id: int, db: Session) -> List[MFADeviceModel]:
        """Get user's MFA devices"""
        return db.query(MFADeviceModel).filter(MFADeviceModel.user_id == user_id, MFADeviceModel.is_active == True).all()

    async def disable_mfa_device(self, user_id: int, device_id: int, db: Session) -> bool:
        """Disable MFA device"""
        mfa_device = db.query(MFADeviceModel).filter(MFADeviceModel.id == device_id, MFADeviceModel.user_id == user_id).first()

        if not mfa_device:
            return False

        mfa_device.is_active = False
        db.commit()

        await self.audit_service.log_event(
            event_type="security",
            action="mfa_device_disabled",
            user_id=user_id,
            details={"device_id": device_id, "method": mfa_device.method, "device_name": mfa_device.device_name},
        )

        return True

    def user_has_mfa(self, user_id: int, db: Session) -> bool:
        """Check if user has any active MFA devices"""
        count = (
            db.query(MFADeviceModel)
            .filter(MFADeviceModel.user_id == user_id, MFADeviceModel.is_active == True, MFADeviceModel.is_verified == True)
            .count()
        )

        return count > 0
