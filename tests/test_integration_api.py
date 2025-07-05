"""
Integration Tests for API Endpoints
==================================
Test complete API workflows and database interactions
"""

import asyncio
import json
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.sqlalchemy.database import get_async_session
from src.infrastructure.persistence.sqlalchemy.models.student import Enrollment, School, Student
from src.infrastructure.persistence.sqlalchemy.models.user import User
from src.main import app


@pytest.mark.asyncio
class TestAuthenticationFlow:
    """Test complete authentication workflows"""

    async def test_user_registration_and_login_flow(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test complete user registration and login flow"""

        # Step 1: Register a new user
        registration_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
            "is_active": True,
        }

        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        assert response.status_code == 201

        user_data = response.json()
        assert user_data["email"] == registration_data["email"]
        assert user_data["full_name"] == registration_data["full_name"]
        assert "id" in user_data
        user_id = user_data["id"]

        # Verify user exists in database
        result = await db_session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.email == registration_data["email"]

        # Step 2: Login with the new user
        login_data = {"username": registration_data["email"], "password": registration_data["password"]}

        response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200

        token_data = response.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"

        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]

        # Step 3: Access protected endpoint with token
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await async_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200

        current_user = response.json()
        assert current_user["email"] == registration_data["email"]
        assert current_user["id"] == user_id

        # Step 4: Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 200

        new_token_data = response.json()
        assert "access_token" in new_token_data
        assert new_token_data["access_token"] != access_token  # Should be different

        # Step 5: Use new token
        new_headers = {"Authorization": f"Bearer {new_token_data['access_token']}"}
        response = await async_client.get("/api/v1/users/me", headers=new_headers)
        assert response.status_code == 200

        # Cleanup
        await db_session.execute(delete(User).where(User.id == user_id))
        await db_session.commit()

    async def test_invalid_login_attempts(self, async_client: AsyncClient):
        """Test handling of invalid login attempts"""

        # Test with non-existent user
        login_data = {"username": "nonexistent@example.com", "password": "password123"}

        response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401

        # Test with invalid password
        # First create a user
        registration_data = {"email": "test2@example.com", "password": "CorrectPassword123!", "full_name": "Test User 2"}

        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        assert response.status_code == 201
        user_id = response.json()["id"]

        # Try login with wrong password
        login_data = {"username": "test2@example.com", "password": "WrongPassword123!"}

        response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401

        # Cleanup
        async with get_async_session() as session:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()

    async def test_token_expiration_handling(self, async_client: AsyncClient):
        """Test handling of expired tokens"""

        # Create user and login
        registration_data = {"email": "test3@example.com", "password": "Password123!", "full_name": "Test User 3"}

        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        user_id = response.json()["id"]

        login_data = {"username": registration_data["email"], "password": registration_data["password"]}

        response = await async_client.post("/api/v1/auth/login", data=login_data)
        token_data = response.json()

        # Mock an expired token (this would require modifying JWT settings for testing)
        # For now, test with invalid token format
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        response = await async_client.get("/api/v1/users/me", headers=invalid_headers)
        assert response.status_code == 401

        # Cleanup
        async with get_async_session() as session:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


@pytest.mark.asyncio
class TestUserManagement:
    """Test user management endpoints"""

    async def test_user_profile_operations(self, async_client: AsyncClient, authenticated_user):
        """Test user profile CRUD operations"""
        user_id, headers = authenticated_user

        # Get current profile
        response = await async_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        profile = response.json()

        # Update profile
        update_data = {"full_name": "Updated Name", "phone_number": "+8801712345678"}

        response = await async_client.put(f"/api/v1/users/{user_id}", json=update_data, headers=headers)
        assert response.status_code == 200

        updated_profile = response.json()
        assert updated_profile["full_name"] == update_data["full_name"]
        assert updated_profile["phone_number"] == update_data["phone_number"]

        # Verify changes in database
        async with get_async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            db_user = result.scalar_one()
            assert db_user.full_name == update_data["full_name"]
            assert db_user.phone_number == update_data["phone_number"]

    async def test_user_list_and_search(self, async_client: AsyncClient, authenticated_user):
        """Test user listing and search functionality"""
        user_id, headers = authenticated_user

        # Create additional test users
        test_users = []
        for i in range(3):
            user_data = {"email": f"testuser{i}@example.com", "password": "Password123!", "full_name": f"Test User {i}"}
            response = await async_client.post("/api/v1/auth/register", json=user_data)
            test_users.append(response.json()["id"])

        try:
            # Test user listing
            response = await async_client.get("/api/v1/users/", headers=headers)
            assert response.status_code == 200

            users_data = response.json()
            assert len(users_data) >= 4  # Original user + 3 test users

            # Test pagination
            response = await async_client.get("/api/v1/users/?skip=0&limit=2", headers=headers)
            assert response.status_code == 200

            paginated_data = response.json()
            assert len(paginated_data) == 2

            # Test search by name
            response = await async_client.get("/api/v1/users/?search=Test User 1", headers=headers)
            assert response.status_code == 200

            search_results = response.json()
            assert len(search_results) == 1
            assert "Test User 1" in search_results[0]["full_name"]

        finally:
            # Cleanup test users
            async with get_async_session() as session:
                for test_user_id in test_users:
                    await session.execute(delete(User).where(User.id == test_user_id))
                await session.commit()


@pytest.mark.asyncio
class TestStudentDataManagement:
    """Test student data management endpoints"""

    async def test_student_crud_operations(self, async_client: AsyncClient, authenticated_user):
        """Test complete CRUD operations for students"""
        user_id, headers = authenticated_user

        # Create a school first (required for student)
        school_data = {
            "school_id": "TEST_SCHOOL_001",
            "school_name": "Test High School",
            "school_type": "Government",
            "education_level": "Secondary",
            "division": "Dhaka",
            "district": "Dhaka",
            "upazila": "Dhanmondi",
        }

        response = await async_client.post("/api/v1/schools/", json=school_data, headers=headers)
        assert response.status_code == 201
        school_id = response.json()["id"]

        try:
            # Create student
            student_data = {
                "student_id": "TEST_STU_001",
                "full_name": "Ahmed Rahman",
                "gender": "Male",
                "date_of_birth": "2010-01-15",
                "division": "Dhaka",
                "district": "Dhaka",
                "upazila": "Dhanmondi",
                "phone_number": "+8801712345678",
                "email": "ahmed@example.com",
            }

            response = await async_client.post("/api/v1/students/", json=student_data, headers=headers)
            assert response.status_code == 201

            created_student = response.json()
            assert created_student["student_id"] == student_data["student_id"]
            assert created_student["full_name"] == student_data["full_name"]
            student_db_id = created_student["id"]

            # Read student
            response = await async_client.get(f"/api/v1/students/{student_db_id}", headers=headers)
            assert response.status_code == 200

            retrieved_student = response.json()
            assert retrieved_student["student_id"] == student_data["student_id"]

            # Update student
            update_data = {"full_name": "Ahmed Rahman Updated", "phone_number": "+8801987654321"}

            response = await async_client.put(f"/api/v1/students/{student_db_id}", json=update_data, headers=headers)
            assert response.status_code == 200

            updated_student = response.json()
            assert updated_student["full_name"] == update_data["full_name"]
            assert updated_student["phone_number"] == update_data["phone_number"]

            # List students
            response = await async_client.get("/api/v1/students/", headers=headers)
            assert response.status_code == 200

            students_list = response.json()
            assert len(students_list) >= 1
            assert any(s["id"] == student_db_id for s in students_list)

            # Delete student
            response = await async_client.delete(f"/api/v1/students/{student_db_id}", headers=headers)
            assert response.status_code == 204

            # Verify deletion
            response = await async_client.get(f"/api/v1/students/{student_db_id}", headers=headers)
            assert response.status_code == 404

        finally:
            # Cleanup school
            await async_client.delete(f"/api/v1/schools/{school_id}", headers=headers)

    async def test_student_enrollment_workflow(self, async_client: AsyncClient, authenticated_user):
        """Test student enrollment workflow"""
        user_id, headers = authenticated_user

        # Create school
        school_data = {
            "school_id": "TEST_SCHOOL_002",
            "school_name": "Test Primary School",
            "school_type": "Government",
            "education_level": "Primary",
            "division": "Chittagong",
            "district": "Chittagong",
            "upazila": "Kotwali",
        }

        response = await async_client.post("/api/v1/schools/", json=school_data, headers=headers)
        school_id = response.json()["id"]

        # Create student
        student_data = {
            "student_id": "TEST_STU_002",
            "full_name": "Fatima Khan",
            "gender": "Female",
            "date_of_birth": "2011-03-20",
            "division": "Chittagong",
            "district": "Chittagong",
            "upazila": "Kotwali",
        }

        response = await async_client.post("/api/v1/students/", json=student_data, headers=headers)
        student_id = response.json()["id"]

        try:
            # Create enrollment
            enrollment_data = {
                "student_id": student_id,
                "school_id": school_id,
                "academic_year": "2024",
                "grade_level": "5",
                "enrollment_date": "2024-01-15",
                "enrollment_status": "Active",
            }

            response = await async_client.post("/api/v1/enrollments/", json=enrollment_data, headers=headers)
            assert response.status_code == 201

            enrollment = response.json()
            assert enrollment["student_id"] == student_id
            assert enrollment["school_id"] == school_id
            enrollment_id = enrollment["id"]

            # Get student with enrollment details
            response = await async_client.get(f"/api/v1/students/{student_id}/enrollments", headers=headers)
            assert response.status_code == 200

            enrollments = response.json()
            assert len(enrollments) == 1
            assert enrollments[0]["id"] == enrollment_id

            # Update enrollment status
            update_data = {"enrollment_status": "Graduated"}
            response = await async_client.put(f"/api/v1/enrollments/{enrollment_id}", json=update_data, headers=headers)
            assert response.status_code == 200

            updated_enrollment = response.json()
            assert updated_enrollment["enrollment_status"] == "Graduated"

        finally:
            # Cleanup
            await async_client.delete(f"/api/v1/students/{student_id}", headers=headers)
            await async_client.delete(f"/api/v1/schools/{school_id}", headers=headers)


@pytest.mark.asyncio
class TestDataProcessingIntegration:
    """Test integration with data processing pipeline"""

    async def test_bulk_data_import(self, async_client: AsyncClient, authenticated_user):
        """Test bulk data import through API"""
        user_id, headers = authenticated_user

        # Prepare bulk student data
        bulk_data = [
            {
                "student_id": f"BULK_STU_{i:03d}",
                "full_name": f"Student {i}",
                "gender": "Male" if i % 2 == 0 else "Female",
                "date_of_birth": f"201{i % 10}-01-15",
                "division": "Dhaka",
                "district": "Dhaka",
            }
            for i in range(1, 11)  # 10 students
        ]

        # Test bulk import
        response = await async_client.post("/api/v1/students/bulk", json={"students": bulk_data}, headers=headers)
        assert response.status_code == 201

        import_result = response.json()
        assert import_result["total_processed"] == 10
        assert import_result["successful"] == 10
        assert import_result["failed"] == 0

        # Verify students were created
        response = await async_client.get("/api/v1/students/?limit=20", headers=headers)
        students = response.json()

        bulk_students = [s for s in students if s["student_id"].startswith("BULK_STU_")]
        assert len(bulk_students) == 10

        # Cleanup
        for student in bulk_students:
            await async_client.delete(f"/api/v1/students/{student['id']}", headers=headers)

    async def test_data_validation_errors(self, async_client: AsyncClient, authenticated_user):
        """Test handling of data validation errors"""
        user_id, headers = authenticated_user

        # Test with invalid student data
        invalid_data = {
            "student_id": "",  # Empty ID
            "full_name": "",  # Empty name
            "gender": "Invalid",  # Invalid gender
            "date_of_birth": "invalid-date",  # Invalid date
            "division": "InvalidDivision",  # Invalid division
        }

        response = await async_client.post("/api/v1/students/", json=invalid_data, headers=headers)
        assert response.status_code == 422  # Validation error

        error_detail = response.json()
        assert "detail" in error_detail

        # Test bulk import with mixed valid/invalid data
        mixed_data = [
            {
                "student_id": "VALID_STU_001",
                "full_name": "Valid Student",
                "gender": "Male",
                "date_of_birth": "2010-01-15",
                "division": "Dhaka",
                "district": "Dhaka",
            },
            {
                "student_id": "",  # Invalid
                "full_name": "Invalid Student",
                "gender": "InvalidGender",
                "date_of_birth": "2010-01-15",
                "division": "Dhaka",
                "district": "Dhaka",
            },
        ]

        response = await async_client.post("/api/v1/students/bulk", json={"students": mixed_data}, headers=headers)
        assert response.status_code == 207  # Multi-status

        result = response.json()
        assert result["total_processed"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

        # Cleanup valid student
        response = await async_client.get("/api/v1/students/?search=VALID_STU_001", headers=headers)
        if response.status_code == 200 and response.json():
            student_id = response.json()[0]["id"]
            await async_client.delete(f"/api/v1/students/{student_id}", headers=headers)


@pytest.mark.asyncio
class TestPerformanceAndScaling:
    """Test API performance and scaling scenarios"""

    async def test_concurrent_requests(self, async_client: AsyncClient, authenticated_user):
        """Test handling of concurrent requests"""
        user_id, headers = authenticated_user

        # Create multiple concurrent requests
        async def create_student(index):
            student_data = {
                "student_id": f"CONCURRENT_STU_{index:03d}",
                "full_name": f"Concurrent Student {index}",
                "gender": "Male",
                "date_of_birth": "2010-01-15",
                "division": "Dhaka",
                "district": "Dhaka",
            }
            return await async_client.post("/api/v1/students/", json=student_data, headers=headers)

        # Execute 10 concurrent requests
        tasks = [create_student(i) for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results
        successful_responses = [r for r in responses if not isinstance(r, Exception) and r.status_code == 201]
        assert len(successful_responses) == 10

        # Cleanup
        for response in successful_responses:
            student_id = response.json()["id"]
            await async_client.delete(f"/api/v1/students/{student_id}", headers=headers)

    async def test_large_dataset_pagination(self, async_client: AsyncClient, authenticated_user):
        """Test pagination with large datasets"""
        user_id, headers = authenticated_user

        # Create a larger dataset
        students_to_create = 50
        created_students = []

        for i in range(students_to_create):
            student_data = {
                "student_id": f"PAGINATE_STU_{i:03d}",
                "full_name": f"Pagination Student {i}",
                "gender": "Male" if i % 2 == 0 else "Female",
                "date_of_birth": "2010-01-15",
                "division": "Dhaka",
                "district": "Dhaka",
            }

            response = await async_client.post("/api/v1/students/", json=student_data, headers=headers)
            if response.status_code == 201:
                created_students.append(response.json()["id"])

        try:
            # Test pagination
            page_size = 10
            all_students = []
            skip = 0

            while True:
                response = await async_client.get(
                    f"/api/v1/students/?skip={skip}&limit={page_size}&search=PAGINATE_STU_", headers=headers
                )
                assert response.status_code == 200

                page_students = response.json()
                if not page_students:
                    break

                all_students.extend(page_students)
                skip += page_size

                # Prevent infinite loop
                if skip > students_to_create * 2:
                    break

            # Verify we got all students
            paginated_students = [s for s in all_students if s["student_id"].startswith("PAGINATE_STU_")]
            assert len(paginated_students) == len(created_students)

        finally:
            # Cleanup
            for student_id in created_students:
                await async_client.delete(f"/api/v1/students/{student_id}", headers=headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
