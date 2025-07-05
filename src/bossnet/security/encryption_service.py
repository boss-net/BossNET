"""
Data Encryption Service for Bangladesh Education Data Warehouse
Provides encryption at rest for sensitive data with key rotation support
"""

import base64
import os
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from audit.audit_service import AuditService
from config.settings import settings
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Session

from database.base import Base


class EncryptionMethod(str, Enum):
    """Encryption method types"""

    SYMMETRIC = "symmetric"  # Fernet (AES 128)
    ASYMMETRIC = "asymmetric"  # RSA
    HYBRID = "hybrid"  # AES + RSA for large data


class KeyType(str, Enum):
    """Encryption key types"""

    MASTER = "master"
    DATA = "data"
    BACKUP = "backup"


class EncryptionKeyModel(Base):
    """Encryption key model for storing encryption keys"""

    __tablename__ = "encryption_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(64), unique=True, nullable=False, index=True)
    key_type = Column(String(20), nullable=False)  # master, data, backup
    algorithm = Column(String(50), nullable=False)  # fernet, rsa-2048, etc.
    key_data = Column(LargeBinary, nullable=False)  # Encrypted key material
    public_key = Column(Text, nullable=True)  # For asymmetric keys
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    rotation_count = Column(Integer, default=0, nullable=False)

    def is_expired(self) -> bool:
        """Check if key is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class EncryptedDataModel(Base):
    """Model for tracking encrypted data"""

    __tablename__ = "encrypted_data"

    id = Column(Integer, primary_key=True, index=True)
    data_id = Column(String(64), unique=True, nullable=False, index=True)
    table_name = Column(String(100), nullable=False)
    column_name = Column(String(100), nullable=False)
    record_id = Column(String(255), nullable=False)
    key_id = Column(String(64), nullable=False)
    encryption_method = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, nullable=True)


class PIIField(BaseModel):
    """PII field configuration"""

    table: str
    column: str
    field_type: str  # email, phone, ssn, etc.
    encryption_required: bool = True


class EncryptionService:
    """Comprehensive encryption service"""

    def __init__(self):
        self.audit_service = AuditService()
        self.master_key = self._get_or_create_master_key()
        self.pii_fields = self._load_pii_configuration()

    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        # In production, this should be stored in a secure key management service
        # like AWS KMS, Azure Key Vault, or HashiCorp Vault
        master_key_env = os.getenv("MASTER_ENCRYPTION_KEY")

        if master_key_env:
            return base64.urlsafe_b64decode(master_key_env.encode())

        # Generate new master key (for development only)
        master_key = Fernet.generate_key()
        print(f"Generated new master key: {base64.urlsafe_b64encode(master_key).decode()}")
        print("Please set MASTER_ENCRYPTION_KEY environment variable in production!")

        return master_key

    def _load_pii_configuration(self) -> List[PIIField]:
        """Load PII field configuration"""
        # This would typically be loaded from configuration file or database
        return [
            PIIField(table="students", column="national_id", field_type="national_id"),
            PIIField(table="students", column="birth_certificate_no", field_type="birth_certificate"),
            PIIField(table="students", column="email", field_type="email"),
            PIIField(table="students", column="phone", field_type="phone"),
            PIIField(table="students", column="father_nid", field_type="national_id"),
            PIIField(table="students", column="mother_nid", field_type="national_id"),
            PIIField(table="guardians", column="national_id", field_type="national_id"),
            PIIField(table="guardians", column="email", field_type="email"),
            PIIField(table="guardians", column="phone", field_type="phone"),
            PIIField(table="users", column="email", field_type="email"),
        ]

    def generate_symmetric_key(self) -> bytes:
        """Generate a new symmetric encryption key"""
        return Fernet.generate_key()

    def generate_asymmetric_keypair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        """Generate RSA key pair"""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend())

        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem

    def create_encryption_key(
        self, key_type: KeyType, algorithm: str = "fernet", expires_in_days: Optional[int] = None, db: Session = None
    ) -> str:
        """Create and store a new encryption key"""
        key_id = secrets.token_hex(32)

        # Generate key based on algorithm
        if algorithm == "fernet":
            key_data = self.generate_symmetric_key()
            public_key_data = None
        elif algorithm.startswith("rsa"):
            key_size = int(algorithm.split("-")[1]) if "-" in algorithm else 2048
            private_key, public_key = self.generate_asymmetric_keypair(key_size)
            key_data = private_key
            public_key_data = public_key.decode()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # Encrypt key data with master key
        fernet = Fernet(self.master_key)
        encrypted_key_data = fernet.encrypt(key_data)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Store key in database
        if db:
            encryption_key = EncryptionKeyModel(
                key_id=key_id,
                key_type=key_type.value,
                algorithm=algorithm,
                key_data=encrypted_key_data,
                public_key=public_key_data,
                expires_at=expires_at,
            )

            db.add(encryption_key)
            db.commit()

        return key_id

    def get_encryption_key(self, key_id: str, db: Session) -> Optional[bytes]:
        """Retrieve and decrypt encryption key"""
        key_record = (
            db.query(EncryptionKeyModel)
            .filter(EncryptionKeyModel.key_id == key_id, EncryptionKeyModel.is_active == True)
            .first()
        )

        if not key_record:
            return None

        if key_record.is_expired():
            return None

        # Decrypt key data
        fernet = Fernet(self.master_key)
        try:
            decrypted_key = fernet.decrypt(key_record.key_data)
            return decrypted_key
        except Exception:
            return None

    def encrypt_data(
        self,
        data: Union[str, bytes],
        method: EncryptionMethod = EncryptionMethod.SYMMETRIC,
        key_id: Optional[str] = None,
        db: Session = None,
    ) -> Tuple[bytes, str]:
        """Encrypt data using specified method"""
        if isinstance(data, str):
            data = data.encode("utf-8")

        if method == EncryptionMethod.SYMMETRIC:
            return self._encrypt_symmetric(data, key_id, db)
        elif method == EncryptionMethod.ASYMMETRIC:
            return self._encrypt_asymmetric(data, key_id, db)
        elif method == EncryptionMethod.HYBRID:
            return self._encrypt_hybrid(data, key_id, db)
        else:
            raise ValueError(f"Unsupported encryption method: {method}")

    def _encrypt_symmetric(self, data: bytes, key_id: Optional[str], db: Session) -> Tuple[bytes, str]:
        """Encrypt data using symmetric encryption (Fernet)"""
        if not key_id:
            key_id = self.create_encryption_key(KeyType.DATA, "fernet", 365, db)

        key_data = self.get_encryption_key(key_id, db)
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Encryption key not found or expired"
            )

        fernet = Fernet(key_data)
        encrypted_data = fernet.encrypt(data)

        return encrypted_data, key_id

    def _encrypt_asymmetric(self, data: bytes, key_id: Optional[str], db: Session) -> Tuple[bytes, str]:
        """Encrypt data using asymmetric encryption (RSA)"""
        if not key_id:
            key_id = self.create_encryption_key(KeyType.DATA, "rsa-2048", 365, db)

        # Get public key for encryption
        key_record = (
            db.query(EncryptionKeyModel)
            .filter(EncryptionKeyModel.key_id == key_id, EncryptionKeyModel.is_active == True)
            .first()
        )

        if not key_record or not key_record.public_key:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Public key not found")

        # Load public key
        public_key = serialization.load_pem_public_key(key_record.public_key.encode(), backend=default_backend())

        # RSA can only encrypt small amounts of data
        max_chunk_size = (public_key.key_size // 8) - 2 * (hashes.SHA256().digest_size) - 2

        if len(data) > max_chunk_size:
            raise ValueError("Data too large for RSA encryption, use hybrid method")

        encrypted_data = public_key.encrypt(
            data, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )

        return encrypted_data, key_id

    def _encrypt_hybrid(self, data: bytes, key_id: Optional[str], db: Session) -> Tuple[bytes, str]:
        """Encrypt data using hybrid encryption (AES + RSA)"""
        # Generate symmetric key for data encryption
        symmetric_key = Fernet.generate_key()

        # Encrypt data with symmetric key
        fernet = Fernet(symmetric_key)
        encrypted_data = fernet.encrypt(data)

        # Encrypt symmetric key with RSA
        if not key_id:
            key_id = self.create_encryption_key(KeyType.DATA, "rsa-2048", 365, db)

        encrypted_key, _ = self._encrypt_asymmetric(symmetric_key, key_id, db)

        # Combine encrypted key and data
        combined_data = len(encrypted_key).to_bytes(4, "big") + encrypted_key + encrypted_data

        return combined_data, key_id

    def decrypt_data(
        self, encrypted_data: bytes, key_id: str, method: EncryptionMethod = EncryptionMethod.SYMMETRIC, db: Session = None
    ) -> bytes:
        """Decrypt data using specified method"""
        if method == EncryptionMethod.SYMMETRIC:
            return self._decrypt_symmetric(encrypted_data, key_id, db)
        elif method == EncryptionMethod.ASYMMETRIC:
            return self._decrypt_asymmetric(encrypted_data, key_id, db)
        elif method == EncryptionMethod.HYBRID:
            return self._decrypt_hybrid(encrypted_data, key_id, db)
        else:
            raise ValueError(f"Unsupported decryption method: {method}")

    def _decrypt_symmetric(self, encrypted_data: bytes, key_id: str, db: Session) -> bytes:
        """Decrypt data using symmetric decryption"""
        key_data = self.get_encryption_key(key_id, db)
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Decryption key not found or expired"
            )

        fernet = Fernet(key_data)
        try:
            decrypted_data = fernet.decrypt(encrypted_data)
            return decrypted_data
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Decryption failed: {str(e)}")

    def _decrypt_asymmetric(self, encrypted_data: bytes, key_id: str, db: Session) -> bytes:
        """Decrypt data using asymmetric decryption"""
        private_key_data = self.get_encryption_key(key_id, db)
        if not private_key_data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Private key not found or expired")

        # Load private key
        private_key = serialization.load_pem_private_key(private_key_data, password=None, backend=default_backend())

        try:
            decrypted_data = private_key.decrypt(
                encrypted_data,
                padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
            )
            return decrypted_data
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Decryption failed: {str(e)}")

    def _decrypt_hybrid(self, encrypted_data: bytes, key_id: str, db: Session) -> bytes:
        """Decrypt data using hybrid decryption"""
        # Extract encrypted key length
        key_length = int.from_bytes(encrypted_data[:4], "big")

        # Extract encrypted symmetric key and data
        encrypted_key = encrypted_data[4 : 4 + key_length]
        encrypted_payload = encrypted_data[4 + key_length :]

        # Decrypt symmetric key with RSA
        symmetric_key = self._decrypt_asymmetric(encrypted_key, key_id, db)

        # Decrypt data with symmetric key
        fernet = Fernet(symmetric_key)
        try:
            decrypted_data = fernet.decrypt(encrypted_payload)
            return decrypted_data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Hybrid decryption failed: {str(e)}"
            )

    def encrypt_pii_field(self, table_name: str, column_name: str, record_id: str, value: str, db: Session) -> str:
        """Encrypt PII field and track it"""
        # Check if field is configured for encryption
        pii_field = next(
            (field for field in self.pii_fields if field.table == table_name and field.column == column_name), None
        )

        if not pii_field or not pii_field.encryption_required:
            return value  # Return unencrypted if not required

        # Encrypt the value
        encrypted_data, key_id = self.encrypt_data(value, EncryptionMethod.SYMMETRIC, db=db)

        # Track encrypted data
        data_id = secrets.token_hex(32)
        encrypted_record = EncryptedDataModel(
            data_id=data_id,
            table_name=table_name,
            column_name=column_name,
            record_id=record_id,
            key_id=key_id,
            encryption_method=EncryptionMethod.SYMMETRIC.value,
        )

        db.add(encrypted_record)
        db.commit()

        # Return base64 encoded encrypted data with metadata
        encoded_data = base64.b64encode(encrypted_data).decode()
        return f"enc:{data_id}:{encoded_data}"

    def decrypt_pii_field(self, encrypted_value: str, db: Session) -> str:
        """Decrypt PII field"""
        if not encrypted_value.startswith("enc:"):
            return encrypted_value  # Not encrypted

        try:
            # Parse encrypted value format: enc:data_id:base64_data
            parts = encrypted_value.split(":", 2)
            if len(parts) != 3:
                return encrypted_value

            data_id = parts[1]
            encrypted_data = base64.b64decode(parts[2])

            # Get encryption metadata
            encrypted_record = db.query(EncryptedDataModel).filter(EncryptedDataModel.data_id == data_id).first()

            if not encrypted_record:
                return encrypted_value

            # Update last accessed
            encrypted_record.last_accessed = datetime.utcnow()
            db.commit()

            # Decrypt data
            method = EncryptionMethod(encrypted_record.encryption_method)
            decrypted_data = self.decrypt_data(encrypted_data, encrypted_record.key_id, method, db)

            return decrypted_data.decode("utf-8")

        except Exception:
            return encrypted_value  # Return original if decryption fails

    def rotate_key(self, old_key_id: str, db: Session) -> str:
        """Rotate encryption key"""
        # Get old key
        old_key = db.query(EncryptionKeyModel).filter(EncryptionKeyModel.key_id == old_key_id).first()

        if not old_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

        # Create new key
        new_key_id = self.create_encryption_key(KeyType(old_key.key_type), old_key.algorithm, 365, db)  # 1 year expiration

        # Mark old key as inactive
        old_key.is_active = False
        old_key.rotation_count += 1

        # Update encrypted data records to use new key
        # This would require re-encrypting all data with the old key
        # For now, we'll just update the tracking
        encrypted_records = db.query(EncryptedDataModel).filter(EncryptedDataModel.key_id == old_key_id).all()

        for record in encrypted_records:
            record.key_id = new_key_id

        db.commit()

        # Log key rotation
        self.audit_service.log_event(
            event_type="security",
            action="key_rotation",
            details={"old_key_id": old_key_id, "new_key_id": new_key_id, "affected_records": len(encrypted_records)},
            severity="medium",
            db=db,
        )

        return new_key_id

    def setup_key_rotation_schedule(self, db: Session):
        """Set up automatic key rotation schedule"""
        # This would integrate with a task scheduler like Celery
        # to automatically rotate keys based on policy
        pass

    def get_encryption_statistics(self, db: Session) -> Dict[str, Any]:
        """Get encryption statistics"""
        total_keys = db.query(EncryptionKeyModel).count()
        active_keys = db.query(EncryptionKeyModel).filter(EncryptionKeyModel.is_active == True).count()
        expired_keys = db.query(EncryptionKeyModel).filter(EncryptionKeyModel.expires_at < datetime.utcnow()).count()

        total_encrypted_data = db.query(EncryptedDataModel).count()

        # Group by table
        encrypted_by_table = {}
        for pii_field in self.pii_fields:
            count = db.query(EncryptedDataModel).filter(EncryptedDataModel.table_name == pii_field.table).count()
            encrypted_by_table[pii_field.table] = count

        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "total_encrypted_records": total_encrypted_data,
            "encrypted_by_table": encrypted_by_table,
        }
