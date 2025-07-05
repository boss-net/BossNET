#!/usr/bin/env python3
"""
Seed data script for Bangladesh Education Data Warehouse.
Populates the database with initial data including divisions, districts, subjects, etc.
"""
import asyncio
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config.settings import settings
from models.academic import AssessmentModel, AssessmentResultModel, EnrollmentModel, GradeModel, SubjectModel

# Import models
from models.base import Base
from models.geography import DistrictModel, DivisionModel, UpazilaModel
from models.school import SchoolModel, TeacherModel
from models.student import StudentModel
from models.user import RoleModel, UserModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

# Database setup
engine = create_engine(settings.SYNC_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_divisions(session):
    """Seed Bangladesh divisions."""
    divisions_data = [
        {
            "name": "Dhaka",
            "name_bn": "ঢাকা",
            "code": "DHA",
            "area_sq_km": Decimal("20593.74"),
            "population": 36054418,
            "latitude": Decimal("23.8103"),
            "longitude": Decimal("90.4125"),
        },
        {
            "name": "Chittagong",
            "name_bn": "চট্টগ্রাম",
            "code": "CTG",
            "area_sq_km": Decimal("33771.18"),
            "population": 28423019,
            "latitude": Decimal("22.3569"),
            "longitude": Decimal("91.7832"),
        },
        {
            "name": "Rajshahi",
            "name_bn": "রাজশাহী",
            "code": "RAJ",
            "area_sq_km": Decimal("18153.08"),
            "population": 18484858,
            "latitude": Decimal("24.3636"),
            "longitude": Decimal("88.6241"),
        },
        {
            "name": "Khulna",
            "name_bn": "খুলনা",
            "code": "KHU",
            "area_sq_km": Decimal("22285.00"),
            "population": 15563000,
            "latitude": Decimal("22.8456"),
            "longitude": Decimal("89.5403"),
        },
        {
            "name": "Barisal",
            "name_bn": "বরিশাল",
            "code": "BAR",
            "area_sq_km": Decimal("13644.85"),
            "population": 8325666,
            "latitude": Decimal("22.7010"),
            "longitude": Decimal("90.3535"),
        },
        {
            "name": "Sylhet",
            "name_bn": "সিলেট",
            "code": "SYL",
            "area_sq_km": Decimal("12635.22"),
            "population": 9910219,
            "latitude": Decimal("24.8949"),
            "longitude": Decimal("91.8687"),
        },
        {
            "name": "Rangpur",
            "name_bn": "রংপুর",
            "code": "RAN",
            "area_sq_km": Decimal("16317.45"),
            "population": 15665000,
            "latitude": Decimal("25.7439"),
            "longitude": Decimal("89.2752"),
        },
        {
            "name": "Mymensingh",
            "name_bn": "ময়মনসিংহ",
            "code": "MYM",
            "area_sq_km": Decimal("10584.06"),
            "population": 11370000,
            "latitude": Decimal("24.7471"),
            "longitude": Decimal("90.4203"),
        },
    ]

    for div_data in divisions_data:
        division = DivisionModel(**div_data)
        session.add(division)

    session.commit()
    print("✅ Seeded 8 divisions")


def seed_districts(session):
    """Seed major districts for each division."""
    # Get divisions
    divisions = {div.code: div for div in session.query(DivisionModel).all()}

    districts_data = [
        # Dhaka Division
        {
            "name": "Dhaka",
            "name_bn": "ঢাকা",
            "code": "DHA-01",
            "division_code": "DHA",
            "latitude": Decimal("23.8103"),
            "longitude": Decimal("90.4125"),
        },
        {
            "name": "Gazipur",
            "name_bn": "গাজীপুর",
            "code": "DHA-02",
            "division_code": "DHA",
            "latitude": Decimal("24.0022"),
            "longitude": Decimal("90.4264"),
        },
        {
            "name": "Narayanganj",
            "name_bn": "নারায়ণগঞ্জ",
            "code": "DHA-03",
            "division_code": "DHA",
            "latitude": Decimal("23.6238"),
            "longitude": Decimal("90.4990"),
        },
        {
            "name": "Tangail",
            "name_bn": "টাঙ্গাইল",
            "code": "DHA-04",
            "division_code": "DHA",
            "latitude": Decimal("24.2513"),
            "longitude": Decimal("89.9167"),
        },
        # Chittagong Division
        {
            "name": "Chittagong",
            "name_bn": "চট্টগ্রাম",
            "code": "CTG-01",
            "division_code": "CTG",
            "latitude": Decimal("22.3569"),
            "longitude": Decimal("91.7832"),
        },
        {
            "name": "Coxs Bazar",
            "name_bn": "কক্সবাজার",
            "code": "CTG-02",
            "division_code": "CTG",
            "latitude": Decimal("21.4272"),
            "longitude": Decimal("92.0058"),
        },
        {
            "name": "Comilla",
            "name_bn": "কুমিল্লা",
            "code": "CTG-03",
            "division_code": "CTG",
            "latitude": Decimal("23.4607"),
            "longitude": Decimal("91.1809"),
        },
        # Rajshahi Division
        {
            "name": "Rajshahi",
            "name_bn": "রাজশাহী",
            "code": "RAJ-01",
            "division_code": "RAJ",
            "latitude": Decimal("24.3636"),
            "longitude": Decimal("88.6241"),
        },
        {
            "name": "Bogra",
            "name_bn": "বগুড়া",
            "code": "RAJ-02",
            "division_code": "RAJ",
            "latitude": Decimal("24.8465"),
            "longitude": Decimal("89.3772"),
        },
        {
            "name": "Pabna",
            "name_bn": "পাবনা",
            "code": "RAJ-03",
            "division_code": "RAJ",
            "latitude": Decimal("24.0064"),
            "longitude": Decimal("89.2372"),
        },
        # Khulna Division
        {
            "name": "Khulna",
            "name_bn": "খুলনা",
            "code": "KHU-01",
            "division_code": "KHU",
            "latitude": Decimal("22.8456"),
            "longitude": Decimal("89.5403"),
        },
        {
            "name": "Jessore",
            "name_bn": "যশোর",
            "code": "KHU-02",
            "division_code": "KHU",
            "latitude": Decimal("23.1634"),
            "longitude": Decimal("89.2182"),
        },
        {
            "name": "Satkhira",
            "name_bn": "সাতক্ষীরা",
            "code": "KHU-03",
            "division_code": "KHU",
            "latitude": Decimal("22.7185"),
            "longitude": Decimal("89.0705"),
        },
        # Barisal Division
        {
            "name": "Barisal",
            "name_bn": "বরিশাল",
            "code": "BAR-01",
            "division_code": "BAR",
            "latitude": Decimal("22.7010"),
            "longitude": Decimal("90.3535"),
        },
        {
            "name": "Patuakhali",
            "name_bn": "পটুয়াখালী",
            "code": "BAR-02",
            "division_code": "BAR",
            "latitude": Decimal("22.3596"),
            "longitude": Decimal("90.3298"),
        },
        # Sylhet Division
        {
            "name": "Sylhet",
            "name_bn": "সিলেট",
            "code": "SYL-01",
            "division_code": "SYL",
            "latitude": Decimal("24.8949"),
            "longitude": Decimal("91.8687"),
        },
        {
            "name": "Moulvibazar",
            "name_bn": "মৌলভীবাজার",
            "code": "SYL-02",
            "division_code": "SYL",
            "latitude": Decimal("24.4829"),
            "longitude": Decimal("91.7774"),
        },
        # Rangpur Division
        {
            "name": "Rangpur",
            "name_bn": "রংপুর",
            "code": "RAN-01",
            "division_code": "RAN",
            "latitude": Decimal("25.7439"),
            "longitude": Decimal("89.2752"),
        },
        {
            "name": "Dinajpur",
            "name_bn": "দিনাজপুর",
            "code": "RAN-02",
            "division_code": "RAN",
            "latitude": Decimal("25.6217"),
            "longitude": Decimal("88.6354"),
        },
        # Mymensingh Division
        {
            "name": "Mymensingh",
            "name_bn": "ময়মনসিংহ",
            "code": "MYM-01",
            "division_code": "MYM",
            "latitude": Decimal("24.7471"),
            "longitude": Decimal("90.4203"),
        },
        {
            "name": "Netrokona",
            "name_bn": "নেত্রকোণা",
            "code": "MYM-02",
            "division_code": "MYM",
            "latitude": Decimal("24.8103"),
            "longitude": Decimal("90.7298"),
        },
    ]

    for dist_data in districts_data:
        division_code = dist_data.pop("division_code")
        district = DistrictModel(division_id=divisions[division_code].id, **dist_data)
        session.add(district)

    session.commit()
    print("✅ Seeded 20 districts")


def seed_upazilas(session):
    """Seed sample upazilas."""
    # Get districts
    districts = {dist.code: dist for dist in session.query(DistrictModel).all()}

    upazilas_data = [
        # Dhaka District
        {"name": "Dhanmondi", "name_bn": "ধানমন্ডি", "code": "DHA-01-01", "district_code": "DHA-01"},
        {"name": "Gulshan", "name_bn": "গুলশান", "code": "DHA-01-02", "district_code": "DHA-01"},
        {"name": "Ramna", "name_bn": "রমনা", "code": "DHA-01-03", "district_code": "DHA-01"},
        {"name": "Tejgaon", "name_bn": "তেজগাঁও", "code": "DHA-01-04", "district_code": "DHA-01"},
        # Gazipur District
        {"name": "Gazipur Sadar", "name_bn": "গাজীপুর সদর", "code": "DHA-02-01", "district_code": "DHA-02"},
        {"name": "Kaliakair", "name_bn": "কালিয়াকৈর", "code": "DHA-02-02", "district_code": "DHA-02"},
        # Chittagong District
        {"name": "Chittagong Sadar", "name_bn": "চট্টগ্রাম সদর", "code": "CTG-01-01", "district_code": "CTG-01"},
        {"name": "Hathazari", "name_bn": "হাটহাজারী", "code": "CTG-01-02", "district_code": "CTG-01"},
        {"name": "Raozan", "name_bn": "রাউজান", "code": "CTG-01-03", "district_code": "CTG-01"},
        # Rajshahi District
        {"name": "Rajshahi Sadar", "name_bn": "রাজশাহী সদর", "code": "RAJ-01-01", "district_code": "RAJ-01"},
        {"name": "Paba", "name_bn": "পবা", "code": "RAJ-01-02", "district_code": "RAJ-01"},
        # Khulna District
        {"name": "Khulna Sadar", "name_bn": "খুলনা সদর", "code": "KHU-01-01", "district_code": "KHU-01"},
        {"name": "Dumuria", "name_bn": "ডুমুরিয়া", "code": "KHU-01-02", "district_code": "KHU-01"},
    ]

    for upazila_data in upazilas_data:
        district_code = upazila_data.pop("district_code")
        upazila = UpazilaModel(district_id=districts[district_code].id, **upazila_data)
        session.add(upazila)

    session.commit()
    print("✅ Seeded 12 upazilas")


def seed_roles(session):
    """Seed system roles."""
    roles_data = [
        {
            "name": "super_admin",
            "description": "Super Administrator with full system access",
            "permissions": {
                "users": ["create", "read", "update", "delete"],
                "schools": ["create", "read", "update", "delete"],
                "students": ["create", "read", "update", "delete"],
                "teachers": ["create", "read", "update", "delete"],
                "assessments": ["create", "read", "update", "delete"],
                "reports": ["create", "read", "update", "delete"],
                "system": ["configure", "backup", "restore"],
            },
        },
        {
            "name": "admin",
            "description": "Administrator with limited system access",
            "permissions": {
                "schools": ["create", "read", "update"],
                "students": ["create", "read", "update"],
                "teachers": ["create", "read", "update"],
                "assessments": ["create", "read", "update"],
                "reports": ["read", "create"],
            },
        },
        {
            "name": "head_teacher",
            "description": "Head Teacher with school management access",
            "permissions": {
                "students": ["create", "read", "update"],
                "teachers": ["read", "update"],
                "assessments": ["create", "read", "update"],
                "reports": ["read", "create"],
                "school_data": ["read", "update"],
            },
        },
        {
            "name": "teacher",
            "description": "Teacher with classroom management access",
            "permissions": {
                "students": ["read", "update"],
                "assessments": ["create", "read", "update"],
                "attendance": ["create", "read", "update"],
                "grades": ["create", "read", "update"],
            },
        },
        {
            "name": "student",
            "description": "Student with limited read access",
            "permissions": {
                "profile": ["read", "update"],
                "grades": ["read"],
                "attendance": ["read"],
                "assessments": ["read"],
            },
        },
        {
            "name": "parent",
            "description": "Parent/Guardian with child data access",
            "permissions": {
                "child_data": ["read"],
                "grades": ["read"],
                "attendance": ["read"],
                "assessments": ["read"],
                "communication": ["read", "create"],
            },
        },
    ]

    for role_data in roles_data:
        role = RoleModel(**role_data)
        session.add(role)

    session.commit()
    print("✅ Seeded 6 system roles")


def seed_subjects(session):
    """Seed academic subjects."""
    subjects_data = [
        # Core Subjects
        {"code": "BAN", "name": "Bengali", "name_bn": "বাংলা", "category": "core", "type": "theory", "is_mandatory": True},
        {"code": "ENG", "name": "English", "name_bn": "ইংরেজি", "category": "core", "type": "theory", "is_mandatory": True},
        {"code": "MAT", "name": "Mathematics", "name_bn": "গণিত", "category": "core", "type": "theory", "is_mandatory": True},
        {"code": "SCI", "name": "Science", "name_bn": "বিজ্ঞান", "category": "core", "type": "both", "is_mandatory": True},
        {
            "code": "SST",
            "name": "Social Studies",
            "name_bn": "সামাজিক বিজ্ঞান",
            "category": "core",
            "type": "theory",
            "is_mandatory": True,
        },
        {"code": "REL", "name": "Religion", "name_bn": "ধর্ম", "category": "core", "type": "theory", "is_mandatory": True},
        # Secondary Subjects
        {
            "code": "PHY",
            "name": "Physics",
            "name_bn": "পদার্থবিজ্ঞান",
            "category": "science",
            "type": "both",
            "is_mandatory": False,
        },
        {
            "code": "CHE",
            "name": "Chemistry",
            "name_bn": "রসায়ন",
            "category": "science",
            "type": "both",
            "is_mandatory": False,
        },
        {
            "code": "BIO",
            "name": "Biology",
            "name_bn": "জীববিজ্ঞান",
            "category": "science",
            "type": "both",
            "is_mandatory": False,
        },
        {
            "code": "GEO",
            "name": "Geography",
            "name_bn": "ভূগোল",
            "category": "humanities",
            "type": "theory",
            "is_mandatory": False,
        },
        {
            "code": "HIS",
            "name": "History",
            "name_bn": "ইতিহাস",
            "category": "humanities",
            "type": "theory",
            "is_mandatory": False,
        },
        {
            "code": "ECO",
            "name": "Economics",
            "name_bn": "অর্থনীতি",
            "category": "commerce",
            "type": "theory",
            "is_mandatory": False,
        },
        {
            "code": "ACC",
            "name": "Accounting",
            "name_bn": "হিসাববিজ্ঞান",
            "category": "commerce",
            "type": "theory",
            "is_mandatory": False,
        },
        # Skill Subjects
        {
            "code": "ICT",
            "name": "ICT",
            "name_bn": "তথ্য ও যোগাযোগ প্রযুক্তি",
            "category": "skill",
            "type": "practical",
            "is_mandatory": False,
        },
        {
            "code": "ART",
            "name": "Arts & Crafts",
            "name_bn": "চারু ও কারুকলা",
            "category": "creative",
            "type": "practical",
            "is_mandatory": False,
        },
        {
            "code": "PE",
            "name": "Physical Education",
            "name_bn": "শারীরিক শিক্ষা",
            "category": "physical",
            "type": "practical",
            "is_mandatory": False,
        },
    ]

    for subject_data in subjects_data:
        subject = SubjectModel(**subject_data)
        session.add(subject)

    session.commit()
    print("✅ Seeded 16 subjects")


def seed_grades(session):
    """Seed grade levels."""
    grades_data = [
        # Primary Level
        {"name": "Class 1", "name_bn": "প্রথম শ্রেণি", "level": 1, "stage": "primary"},
        {"name": "Class 2", "name_bn": "দ্বিতীয় শ্রেণি", "level": 2, "stage": "primary"},
        {"name": "Class 3", "name_bn": "তৃতীয় শ্রেণি", "level": 3, "stage": "primary"},
        {"name": "Class 4", "name_bn": "চতুর্থ শ্রেণি", "level": 4, "stage": "primary"},
        {"name": "Class 5", "name_bn": "পঞ্চম শ্রেণি", "level": 5, "stage": "primary"},
        # Secondary Level
        {"name": "Class 6", "name_bn": "ষষ্ঠ শ্রেণি", "level": 6, "stage": "secondary"},
        {"name": "Class 7", "name_bn": "সপ্তম শ্রেণি", "level": 7, "stage": "secondary"},
        {"name": "Class 8", "name_bn": "অষ্টম শ্রেণি", "level": 8, "stage": "secondary"},
        {"name": "Class 9", "name_bn": "নবম শ্রেণি", "level": 9, "stage": "secondary"},
        {"name": "Class 10", "name_bn": "দশম শ্রেণি", "level": 10, "stage": "secondary"},
        # Higher Secondary Level
        {"name": "Class 11", "name_bn": "একাদশ শ্রেণি", "level": 11, "stage": "higher_secondary"},
        {"name": "Class 12", "name_bn": "দ্বাদশ শ্রেণি", "level": 12, "stage": "higher_secondary"},
    ]

    for grade_data in grades_data:
        grade = GradeModel(**grade_data)
        session.add(grade)

    session.commit()
    print("✅ Seeded 12 grade levels")


def seed_admin_user(session):
    """Seed default admin user."""
    # Get super_admin role
    super_admin_role = session.query(RoleModel).filter_by(name="super_admin").first()

    admin_user = UserModel(
        username="admin",
        email=settings.FIRST_SUPERUSER_EMAIL,
        password_hash=generate_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
        first_name="System",
        last_name="Administrator",
        is_active=True,
        is_verified=True,
        is_superuser=True,
        profile_data={"department": "IT", "position": "System Administrator", "phone": "+8801700000000"},
    )

    session.add(admin_user)
    session.commit()

    # Assign super_admin role
    if super_admin_role:
        admin_user.roles.append(super_admin_role)
        session.commit()

    print("✅ Seeded admin user")


def seed_sample_schools(session):
    """Seed sample schools."""
    # Get geographic data
    dhaka_division = session.query(DivisionModel).filter_by(code="DHA").first()
    dhaka_district = session.query(DistrictModel).filter_by(code="DHA-01").first()

    schools_data = [
        {
            "school_code": "DHA-GOV-001",
            "eiin": "108001",
            "name": "Dhaka Government High School",
            "name_bn": "ঢাকা সরকারি উচ্চ বিদ্যালয়",
            "type": "secondary",
            "category": "government",
            "level": "Secondary",
            "email": "info@dhakagovhigh.edu.bd",
            "phone": "+8802-9558877",
            "address": "Dhanmondi, Dhaka-1205",
            "division_id": dhaka_division.id if dhaka_division else None,
            "district_id": dhaka_district.id if dhaka_district else None,
            "establishment_date": date(1950, 1, 1),
            "total_classrooms": 25,
            "total_labs": 3,
            "library_available": True,
            "computer_lab_available": True,
            "science_lab_available": True,
            "playground_available": True,
            "electricity_available": True,
            "internet_available": True,
            "water_supply_available": True,
            "total_capacity": 1200,
            "current_enrollment": 980,
            "total_teachers": 45,
            "total_staff": 15,
            "is_co_educational": True,
            "grades_offered": ["6", "7", "8", "9", "10"],
            "medium_of_instruction": ["Bengali", "English"],
        },
        {
            "school_code": "DHA-PRI-001",
            "eiin": "108002",
            "name": "Gulshan Model Primary School",
            "name_bn": "গুলশান মডেল প্রাথমিক বিদ্যালয়",
            "type": "primary",
            "category": "government",
            "level": "Primary",
            "email": "info@gulshanprimary.edu.bd",
            "phone": "+8802-9887766",
            "address": "Gulshan-2, Dhaka-1212",
            "division_id": dhaka_division.id if dhaka_division else None,
            "district_id": dhaka_district.id if dhaka_district else None,
            "establishment_date": date(1975, 6, 15),
            "total_classrooms": 15,
            "total_labs": 1,
            "library_available": True,
            "computer_lab_available": True,
            "playground_available": True,
            "electricity_available": True,
            "internet_available": True,
            "water_supply_available": True,
            "total_capacity": 600,
            "current_enrollment": 520,
            "total_teachers": 20,
            "total_staff": 8,
            "is_co_educational": True,
            "grades_offered": ["1", "2", "3", "4", "5"],
            "medium_of_instruction": ["Bengali"],
        },
    ]

    for school_data in schools_data:
        school = SchoolModel(**school_data)
        session.add(school)

    session.commit()
    print("✅ Seeded 2 sample schools")


def main():
    """Main seeding function."""
    print("🌱 Starting database seeding...")

    session = SessionLocal()

    try:
        # Seed in order of dependencies
        seed_divisions(session)
        seed_districts(session)
        seed_upazilas(session)
        seed_roles(session)
        seed_subjects(session)
        seed_grades(session)
        seed_admin_user(session)
        seed_sample_schools(session)

        print("\n🎉 Database seeding completed successfully!")
        print(f"📧 Admin login: {settings.FIRST_SUPERUSER_EMAIL}")
        print(f"🔑 Admin password: {settings.FIRST_SUPERUSER_PASSWORD}")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
