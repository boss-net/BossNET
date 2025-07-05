"""Create complete schema for Bangladesh Education Data Warehouse

Revision ID: 20250105_001
Revises:
Create Date: 2025-01-05 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250105_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create all tables for the education data warehouse."""

    # Create divisions table
    op.create_table(
        "divisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_bn", sa.String(length=100), nullable=True),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("area_sq_km", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_divisions_code", "divisions", ["code"])

    # Create districts table
    op.create_table(
        "districts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_bn", sa.String(length=100), nullable=True),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("division_id", sa.Integer(), nullable=False),
        sa.Column("area_sq_km", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["division_id"],
            ["divisions.id"],
        ),
    )
    op.create_index("ix_districts_code", "districts", ["code"])
    op.create_index("ix_districts_division_name", "districts", ["division_id", "name"])

    # Create upazilas table
    op.create_table(
        "upazilas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_bn", sa.String(length=100), nullable=True),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("area_sq_km", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["districts.id"],
        ),
    )
    op.create_index("ix_upazilas_code", "upazilas", ["code"])
    op.create_index("ix_upazilas_district_name", "upazilas", ["district_id", "name"])

    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, default=0),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("profile_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("preferences", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # Create user_roles association table
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assigned_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
        ),
    )

    # Create schools table
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_code", sa.String(length=50), nullable=False),
        sa.Column("eiin", sa.String(length=20), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_bn", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("fax", sa.String(length=20), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.String(length=10), nullable=True),
        sa.Column("division_id", sa.Integer(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("upazila_id", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column("establishment_date", sa.Date(), nullable=True),
        sa.Column("recognition_date", sa.Date(), nullable=True),
        sa.Column("total_classrooms", sa.Integer(), nullable=False, default=0),
        sa.Column("total_labs", sa.Integer(), nullable=False, default=0),
        sa.Column("library_available", sa.Boolean(), nullable=False, default=False),
        sa.Column("computer_lab_available", sa.Boolean(), nullable=False, default=False),
        sa.Column("science_lab_available", sa.Boolean(), nullable=False, default=False),
        sa.Column("playground_available", sa.Boolean(), nullable=False, default=False),
        sa.Column("electricity_available", sa.Boolean(), nullable=False, default=False),
        sa.Column("internet_available", sa.Boolean(), nullable=False, default=False),
        sa.Column("water_supply_available", sa.Boolean(), nullable=False, default=False),
        sa.Column("toilet_facilities", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("shifts", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("medium_of_instruction", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("grades_offered", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("total_capacity", sa.Integer(), nullable=True),
        sa.Column("current_enrollment", sa.Integer(), nullable=False, default=0),
        sa.Column("total_teachers", sa.Integer(), nullable=False, default=0),
        sa.Column("total_staff", sa.Integer(), nullable=False, default=0),
        sa.Column("monthly_fee_range", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("scholarship_available", sa.Boolean(), nullable=False, default=False),
        sa.Column("accreditation_status", sa.String(length=50), nullable=True),
        sa.Column("recognition_authority", sa.String(length=100), nullable=True),
        sa.Column("pass_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("attendance_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_co_educational", sa.Boolean(), nullable=False, default=True),
        sa.Column("facilities", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("achievements", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_code"),
        sa.UniqueConstraint("eiin"),
        sa.ForeignKeyConstraint(
            ["division_id"],
            ["divisions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["districts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["upazila_id"],
            ["upazilas.id"],
        ),
    )
    op.create_index("ix_schools_school_code", "schools", ["school_code"])
    op.create_index("ix_schools_eiin", "schools", ["eiin"])
    op.create_index("ix_schools_location", "schools", ["division_id", "district_id", "upazila_id"])
    op.create_index("ix_schools_type_category", "schools", ["type", "category"])
    op.create_index("ix_schools_name", "schools", ["name"])

    # Create students table
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.String(length=50), nullable=False),
        sa.Column("national_id", sa.String(length=20), nullable=True),
        sa.Column("birth_certificate_no", sa.String(length=30), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("first_name_bn", sa.String(length=100), nullable=True),
        sa.Column("last_name_bn", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("blood_group", sa.String(length=5), nullable=True),
        sa.Column("religion", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("emergency_contact", sa.String(length=20), nullable=True),
        sa.Column("present_address", sa.Text(), nullable=True),
        sa.Column("permanent_address", sa.Text(), nullable=True),
        sa.Column("division_id", sa.Integer(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("upazila_id", sa.Integer(), nullable=True),
        sa.Column("father_name", sa.String(length=200), nullable=True),
        sa.Column("father_name_bn", sa.String(length=200), nullable=True),
        sa.Column("father_occupation", sa.String(length=100), nullable=True),
        sa.Column("father_phone", sa.String(length=20), nullable=True),
        sa.Column("father_nid", sa.String(length=20), nullable=True),
        sa.Column("mother_name", sa.String(length=200), nullable=True),
        sa.Column("mother_name_bn", sa.String(length=200), nullable=True),
        sa.Column("mother_occupation", sa.String(length=100), nullable=True),
        sa.Column("mother_phone", sa.String(length=20), nullable=True),
        sa.Column("mother_nid", sa.String(length=20), nullable=True),
        sa.Column("guardian_name", sa.String(length=200), nullable=True),
        sa.Column("guardian_relation", sa.String(length=50), nullable=True),
        sa.Column("guardian_phone", sa.String(length=20), nullable=True),
        sa.Column("guardian_address", sa.Text(), nullable=True),
        sa.Column("admission_date", sa.Date(), nullable=True),
        sa.Column("current_class", sa.String(length=20), nullable=True),
        sa.Column("current_section", sa.String(length=10), nullable=True),
        sa.Column("roll_number", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, default="active"),
        sa.Column("is_scholarship_recipient", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_special_needs", sa.Boolean(), nullable=False, default=False),
        sa.Column("special_needs_details", sa.Text(), nullable=True),
        sa.Column("monthly_family_income", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("fee_waiver_percentage", sa.Integer(), nullable=False, default=0),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("documents", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("medical_info", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("extra_curricular", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id"),
        sa.UniqueConstraint("national_id"),
        sa.UniqueConstraint("birth_certificate_no"),
        sa.UniqueConstraint("email"),
        sa.ForeignKeyConstraint(
            ["division_id"],
            ["divisions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["district_id"],
            ["districts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["upazila_id"],
            ["upazilas.id"],
        ),
    )
    op.create_index("ix_students_student_id", "students", ["student_id"])
    op.create_index("ix_students_national_id", "students", ["national_id"])
    op.create_index("ix_students_birth_certificate_no", "students", ["birth_certificate_no"])
    op.create_index("ix_students_email", "students", ["email"])
    op.create_index("ix_students_name", "students", ["first_name", "last_name"])
    op.create_index("ix_students_location", "students", ["division_id", "district_id", "upazila_id"])
    op.create_index("ix_students_status_class", "students", ["status", "current_class"])
    op.create_index("ix_students_admission_date", "students", ["admission_date"])

    # Create teachers table
    op.create_table(
        "teachers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.String(length=50), nullable=False),
        sa.Column("national_id", sa.String(length=20), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("first_name_bn", sa.String(length=100), nullable=True),
        sa.Column("last_name_bn", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("religion", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("emergency_contact", sa.String(length=20), nullable=True),
        sa.Column("present_address", sa.Text(), nullable=True),
        sa.Column("permanent_address", sa.Text(), nullable=True),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.String(length=50), nullable=True),
        sa.Column("designation", sa.String(length=100), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.Column("employment_type", sa.String(length=30), nullable=False),
        sa.Column("salary", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("highest_qualification", sa.String(length=100), nullable=True),
        sa.Column("qualifications", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("certifications", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("subjects_taught", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("classes_taught", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("teaching_experience_years", sa.Integer(), nullable=False, default=0),
        sa.Column("performance_rating", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("last_evaluation_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, default="active"),
        sa.Column("is_head_teacher", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_class_teacher", sa.Boolean(), nullable=False, default=False),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("documents", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_id"),
        sa.UniqueConstraint("national_id"),
        sa.UniqueConstraint("email"),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
        ),
    )
    op.create_index("ix_teachers_teacher_id", "teachers", ["teacher_id"])
    op.create_index("ix_teachers_national_id", "teachers", ["national_id"])
    op.create_index("ix_teachers_email", "teachers", ["email"])
    op.create_index("ix_teachers_school_status", "teachers", ["school_id", "status"])
    op.create_index("ix_teachers_name", "teachers", ["first_name", "last_name"])
    op.create_index("ix_teachers_designation", "teachers", ["designation"])

    # Create subjects table
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_bn", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=True),
        sa.Column("credit_hours", sa.Integer(), nullable=False, default=1),
        sa.Column("total_marks", sa.Integer(), nullable=False, default=100),
        sa.Column("pass_marks", sa.Integer(), nullable=False, default=40),
        sa.Column("applicable_grades", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, default=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_subjects_code", "subjects", ["code"])

    # Create grades table
    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("name_bn", sa.String(length=20), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=30), nullable=False),
        sa.Column("subjects", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_grades_level", "grades", ["level"])
    op.create_index("ix_grades_stage", "grades", ["stage"])

    # Create enrollments table
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("section", sa.String(length=10), nullable=True),
        sa.Column("roll_number", sa.String(length=20), nullable=True),
        sa.Column("enrollment_date", sa.Date(), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, default="active"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("fee_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("scholarship_amount", sa.Numeric(precision=10, scale=2), nullable=False, default=0),
        sa.Column("fee_waiver_percentage", sa.Integer(), nullable=False, default=0),
        sa.Column("final_result", sa.String(length=20), nullable=True),
        sa.Column("final_grade", sa.String(length=10), nullable=True),
        sa.Column("final_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "school_id", "academic_year"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
        ),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"],
            ["grades.id"],
        ),
    )
    op.create_index("ix_enrollments_student_year", "enrollments", ["student_id", "academic_year"])
    op.create_index("ix_enrollments_school_year", "enrollments", ["school_id", "academic_year"])
    op.create_index("ix_enrollments_status", "enrollments", ["status"])

    # Create assessments table
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("term", sa.String(length=20), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("total_marks", sa.Integer(), nullable=False),
        sa.Column("pass_marks", sa.Integer(), nullable=False),
        sa.Column("grade_system", sa.String(length=20), nullable=False, default="percentage"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, default=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("syllabus", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["school_id"],
            ["schools.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"],
            ["grades.id"],
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["teachers.id"],
        ),
    )
    op.create_index("ix_assessments_code", "assessments", ["code"])
    op.create_index("ix_assessments_school_year", "assessments", ["school_id", "academic_year"])
    op.create_index("ix_assessments_subject_grade", "assessments", ["subject_id", "grade_id"])
    op.create_index("ix_assessments_date", "assessments", ["scheduled_date"])

    # Create assessment_results table
    op.create_table(
        "assessment_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("marks_obtained", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("total_marks", sa.Integer(), nullable=False),
        sa.Column("percentage", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("letter_grade", sa.String(length=5), nullable=True),
        sa.Column("grade_point", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("is_pass", sa.Boolean(), nullable=False),
        sa.Column("is_absent", sa.Boolean(), nullable=False, default=False),
        sa.Column("rank_in_class", sa.Integer(), nullable=True),
        sa.Column("rank_in_school", sa.Integer(), nullable=True),
        sa.Column("teacher_comments", sa.Text(), nullable=True),
        sa.Column("result_date", sa.Date(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "assessment_id", "subject_id"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["enrollments.id"],
        ),
    )
    op.create_index("ix_assessment_results_student_assessment", "assessment_results", ["student_id", "assessment_id"])
    op.create_index("ix_assessment_results_assessment_marks", "assessment_results", ["assessment_id", "marks_obtained"])
    op.create_index("ix_assessment_results_subject_grade", "assessment_results", ["subject_id", "letter_grade"])

    # Create attendances table
    op.create_table(
        "attendances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("period", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, default="present"),
        sa.Column("arrival_time", sa.Time(), nullable=True),
        sa.Column("departure_time", sa.Time(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "attendance_date", "period", "subject_id"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["enrollments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["teachers.id"],
        ),
    )
    op.create_index("ix_attendances_student_date", "attendances", ["student_id", "attendance_date"])
    op.create_index("ix_attendances_enrollment_date", "attendances", ["enrollment_id", "attendance_date"])
    op.create_index("ix_attendances_date_status", "attendances", ["attendance_date", "status"])

    # Create student_performances table
    op.create_table(
        "student_performances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("term", sa.String(length=20), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("week", sa.Integer(), nullable=True),
        sa.Column("overall_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("overall_grade", sa.String(length=5), nullable=True),
        sa.Column("overall_gpa", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("subject_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("subject_grade", sa.String(length=5), nullable=True),
        sa.Column("subject_gpa", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("attendance_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("total_days", sa.Integer(), nullable=True),
        sa.Column("present_days", sa.Integer(), nullable=True),
        sa.Column("absent_days", sa.Integer(), nullable=True),
        sa.Column("assignments_completed", sa.Integer(), nullable=False, default=0),
        sa.Column("assignments_total", sa.Integer(), nullable=False, default=0),
        sa.Column("assignment_completion_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("discipline_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("participation_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("class_rank", sa.Integer(), nullable=True),
        sa.Column("school_rank", sa.Integer(), nullable=True),
        sa.Column("district_rank", sa.Integer(), nullable=True),
        sa.Column("trend_direction", sa.String(length=20), nullable=True),
        sa.Column("improvement_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("predicted_final_grade", sa.String(length=5), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("extra_curricular_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("leadership_score", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("metrics_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["enrollments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
        ),
    )
    op.create_index("ix_student_performance_student_year", "student_performances", ["student_id", "academic_year"])
    op.create_index("ix_student_performance_enrollment_term", "student_performances", ["enrollment_id", "term"])
    op.create_index("ix_student_performance_subject_year", "student_performances", ["subject_id", "academic_year"])
    op.create_index("ix_student_performance_rankings", "student_performances", ["class_rank", "school_rank"])


def downgrade():
    """Drop all tables."""
    op.drop_table("student_performances")
    op.drop_table("attendances")
    op.drop_table("assessment_results")
    op.drop_table("assessments")
    op.drop_table("enrollments")
    op.drop_table("grades")
    op.drop_table("subjects")
    op.drop_table("teachers")
    op.drop_table("students")
    op.drop_table("schools")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("upazilas")
    op.drop_table("districts")
    op.drop_table("divisions")
