from datetime import date
from typing import List, Optional

from auth.dependencies import admin_required, get_current_active_user, teacher_or_admin_required
from auth.models import UserInDB, UserRole
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from models.student import PaginatedStudentResponse, StudentCreate, StudentResponse, StudentUpdate
from models.student_model import Gender, StudentDB
from sqlalchemy.orm import Session

from database.base import get_db

router = APIRouter(
    prefix="/api/students",
    tags=["students"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new student record",
    dependencies=[Depends(teacher_or_admin_required)],
)
async def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    """
    Create a new student record with the provided information.
    """
    # Check if student with same ID or email already exists
    db_student = (
        db.query(StudentDB).filter((StudentDB.student_id == student.student_id) | (StudentDB.email == student.email)).first()
    )

    if db_student:
        if db_student.student_id == student.student_id:
            raise HTTPException(status_code=400, detail=f"Student with ID {student.student_id} already exists")
        if db_student.email == student.email:
            raise HTTPException(status_code=400, detail=f"Email {student.email} is already registered")

    # Create new student
    db_student = StudentDB(**student.dict())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    return db_student


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get a student by ID",
    dependencies=[Depends(get_current_active_user)],
)
async def read_student(student_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a student's information by their unique student ID.
    """
    db_student = db.query(StudentDB).filter(StudentDB.student_id == student_id).first()
    if db_student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return db_student


@router.get(
    "/",
    response_model=PaginatedStudentResponse,
    summary="List all students with pagination",
    dependencies=[Depends(get_current_active_user)],
)
async def list_students(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, le=1000, description="Maximum number of records to return"),
    name: Optional[str] = Query(None, description="Filter by student name"),
    division: Optional[str] = Query(None, description="Filter by division"),
    district: Optional[str] = Query(None, description="Filter by district"),
    gender: Optional[Gender] = Query(None, description="Filter by gender"),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of students with optional filtering.
    """
    query = db.query(StudentDB)

    # Apply filters
    if name:
        query = query.filter((StudentDB.first_name.ilike(f"%{name}%")) | (StudentDB.last_name.ilike(f"%{name}%")))
    if division:
        query = query.filter(StudentDB.division.ilike(f"%{division}%"))
    if district:
        query = query.filter(StudentDB.district.ilike(f"%{district}%"))
    if gender:
        query = query.filter(StudentDB.gender == gender)

    # Get total count and paginated results
    total = query.count()
    students = query.offset(skip).limit(limit).all()

    return {"total": total, "skip": skip, "limit": limit, "items": students}


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Update a student's information",
    dependencies=[Depends(teacher_or_admin_required)],
)
async def update_student(student_id: str, student_update: StudentUpdate, db: Session = Depends(get_db)):
    """
    Update a student's information by their ID.
    """
    db_student = db.query(StudentDB).filter(StudentDB.student_id == student_id).first()
    if db_student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    # Update only the provided fields
    update_data = student_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_student, field, value)

    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    return db_student


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a student record",
    dependencies=[Depends(admin_required)],
)
async def delete_student(student_id: str, db: Session = Depends(get_db)):
    """
    Delete a student record by ID.
    """
    db_student = db.query(StudentDB).filter(StudentDB.student_id == student_id).first()
    if db_student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(db_student)
    db.commit()

    return {"ok": True}
