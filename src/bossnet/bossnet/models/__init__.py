"""
Database models for the Bangladesh Education Data Warehouse.
"""

from ..infrastructure.persistence.sqlalchemy.models.user import UserRoleModel
from .academic import AssessmentModel, AssessmentResultModel, AttendanceModel, EnrollmentModel, GradeModel, SubjectModel
from .base import Base
from .geography import DistrictModel, DivisionModel, UpazilaModel
from .performance import PerformanceMetricModel, SchoolPerformanceModel, StudentPerformanceModel
from .school import ClassroomModel, SchoolModel, TeacherModel
from .student import GuardianModel, StudentModel
from .user import RefreshTokenModel, RoleModel, UserModel

__all__ = [
    # Base
    "Base",
    # User models
    "UserModel",
    "UserRoleModel",
    "RefreshTokenModel",
    "RoleModel",
    # Student models
    "StudentModel",
    "GuardianModel",
    # School models
    "SchoolModel",
    "TeacherModel",
    "ClassroomModel",
    # Academic models
    "EnrollmentModel",
    "AttendanceModel",
    "AssessmentModel",
    "AssessmentResultModel",
    "SubjectModel",
    "GradeModel",
    # Geography models
    "DivisionModel",
    "DistrictModel",
    "UpazilaModel",
    # Performance models
    "StudentPerformanceModel",
    "SchoolPerformanceModel",
    "PerformanceMetricModel",
]
