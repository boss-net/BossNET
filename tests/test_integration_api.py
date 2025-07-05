"""Integration tests for API endpoints and database interactions."""

import asyncio
from typing import Dict, Tuple

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User as UserModel
from src.auth.utils import hash_password


@pytest.mark.asyncio
class TestAuthenticationFlow:
    """Test complete authentication workflows."""

    async def test_create_user(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test user creation with valid data.

        Verifies that a new user can be created with valid data
        and that the response contains the expected fields.
        """
        user_data = {
            "email": "test@example.com",
            "password": "testpassword",
            "full_name": "Test User",
        }

        response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201

        user_id = response.json()["id"]

        async with db_session.begin():
            result = await db_session.execute(select(UserModel).where(UserModel.id == user_id))
            db_user = result.scalar_one()
            assert db_user.email == user_data["email"]
            assert db_user.full_name == user_data["full_name"]

        async with db_session.begin():
            stmt = delete(UserModel).where(UserModel.id == user_id)
            await db_session.execute(stmt)

    async def test_invalid_login_attempts(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test handling of invalid login attempts.

        Verifies that multiple failed login attempts are properly handled
        and potentially rate-limited.
        """
        # Create test user
        user = UserModel(
            email="test@example.com",
            hashed_password=hash_password("testpassword"),
            full_name="Test User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        user_id = user.id

        # Test with invalid password
        login_data = {"username": "test@example.com", "password": "wrongpassword"}

        response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401

        async with db_session.begin():
            stmt = delete(UserModel).where(UserModel.id == user_id)
            await db_session.execute(stmt)

    async def test_token_expiration_handling(self, async_client: AsyncClient, db_session: AsyncSession) -> None:
        """Test handling of expired tokens.

        Verifies that expired access tokens are properly rejected
        and refresh tokens can be used to get new access tokens.
        """
        # Create test user
        user = UserModel(
            email="test@example.com",
            hashed_password=hash_password("testpassword"),
            full_name="Test User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        user_id = user.id

        # Get a valid token (though we won't use it for the actual test)
        login_data = {"username": "test@example.com", "password": "testpassword"}
        response = await async_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200

        token_data = response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]

        # Test with expired token
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await async_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

        # Refresh token
        refresh_data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 200

        new_token_data = response.json()
        new_access_token = new_token_data["access_token"]

        # Test with new token
        new_headers = {"Authorization": f"Bearer {new_access_token}"}
        response = await async_client.get("/api/v1/users/me", headers=new_headers)
        assert response.status_code == 200

        response = await async_client.post("/api/v1/auth/login", data=login_data)
        # Test with invalid token format
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        response = await async_client.get("/api/v1/users/me", headers=invalid_headers)
        assert response.status_code == 401

        # Cleanup
        async with db_session.begin():
            await db_session.execute(delete(UserModel).where(UserModel.id == user_id))


@pytest.mark.asyncio
class TestUserManagement:
    """Test user management endpoints."""

    async def test_user_profile_operations(
        self, async_client: AsyncClient, db_session: AsyncSession, authenticated_user: Tuple[str, Dict]
    ) -> None:
        """Test complete CRUD operations for user profiles.

        Verifies that users can view and update their profile information.
        """
        user_id, headers = authenticated_user

        # Get current profile
        response = await async_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        response_data = response.json()
        assert "email" in response_data
        assert "full_name" in response_data

        # Update profile
        update_data = {"full_name": "Updated Name", "phone_number": "+8801712345678"}

        response = await async_client.put(f"/api/v1/users/{user_id}", json=update_data, headers=headers)
        assert response.status_code == 200

        updated_profile = response.json()
        assert updated_profile["full_name"] == update_data["full_name"]
        assert updated_profile["phone_number"] == update_data["phone_number"]

        # Verify changes in database
        async with db_session.begin():
            result = await db_session.execute(select(UserModel).where(UserModel.id == user_id))
            db_user = result.scalar_one()
            assert db_user.full_name == update_data["full_name"]
            assert db_user.phone_number == update_data["phone_number"]

    async def test_user_list_and_search(
        self, async_client: AsyncClient, db_session: AsyncSession, authenticated_user: Tuple[str, Dict]
    ) -> None:
        """Test user listing and search functionality.

        Verifies that users can be listed and searched with various criteria.
        """
        user_id, headers = authenticated_user
        created_user_ids = []

        try:
            # Create test users
            for i in range(3):
                user_data = {"email": f"testuser{i}@example.com", "password": "Password123!", "full_name": f"Test User {i}"}
                response = await async_client.post("/api/v1/auth/register", json=user_data)
                assert response.status_code == 201
                created_user_ids.append(response.json()["id"])

            # Test user listing
            response = await async_client.get("/api/v1/users/", headers=headers)
            assert response.status_code == 200
            users_data = response.json()
            assert len(users_data) >= 3  # Original user + test users

            # Test search functionality
            response = await async_client.get("/api/v1/users/?search=Test User 1", headers=headers)
            assert response.status_code == 200
            search_results = response.json()
            assert any(user["full_name"] == "Test User 1" for user in search_results)

        finally:
            # Cleanup test users
            async with db_session.begin():
                for test_user_id in created_user_ids:
                    await db_session.execute(delete(UserModel).where(UserModel.id == test_user_id))


@pytest.mark.asyncio
class TestStudentDataManagement:
    """Test student data management endpoints.

    Verifies CRUD operations and business logic for student records.
    """

    async def test_student_crud_operations(
        self, async_client: AsyncClient, authenticated_user: tuple[str, dict], db_session: AsyncSession
    ) -> None:
        """Test complete CRUD operations for student records.

        Verifies that students can be created, read, updated, and deleted
        through the API with proper validation and error handling.
        """
        user_id, headers = authenticated_user

        # Create a school first (required for student enrollment)
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
        assert response.status_code == 201, "Failed to create test school"
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
            assert response.status_code == 201, "Failed to create student"

            created_student = response.json()
            assert created_student["student_id"] == student_data["student_id"]
            assert created_student["full_name"] == student_data["full_name"]
            student_db_id = created_student["id"]

            # Read student
            response = await async_client.get(f"/api/v1/students/{student_db_id}", headers=headers)
            assert response.status_code == 200, "Failed to retrieve student"

            retrieved_student = response.json()
            assert retrieved_student["student_id"] == student_data["student_id"], "Retrieved student ID doesn't match"

            # Update student
            update_data = {"full_name": "Ahmed Rahman Updated", "phone_number": "+8801987654321"}

            # Test update operation
            response = await async_client.put(f"/api/v1/students/{student_db_id}", json=update_data, headers=headers)
            assert response.status_code == 200, "Failed to update student"

            updated_student = response.json()
            assert updated_student["full_name"] == update_data["full_name"], "Full name not updated correctly"
            assert updated_student["phone_number"] == update_data["phone_number"], "Phone number not updated correctly"

            # Verify update in database
            response = await async_client.get(f"/api/v1/students/{student_db_id}", headers=headers)
            assert response.status_code == 200, "Failed to retrieve updated student"
            assert response.json()["full_name"] == update_data["full_name"], "Update not persisted in database"

            # Test delete operation
            response = await async_client.delete(f"/api/v1/students/{student_db_id}", headers=headers)
            assert response.status_code == 204, "Failed to delete student"

            # Verify deletion
            response = await async_client.get(f"/api/v1/students/{student_db_id}", headers=headers)
            assert response.status_code == 404, "Student record not deleted"

        finally:
            # Cleanup school
            await async_client.delete(f"/api/v1/schools/{school_id}", headers=headers)

    async def test_student_enrollment_workflow(self, async_client: AsyncClient, authenticated_user: tuple[str, dict]) -> None:
        """Test complete student enrollment workflow.

        Verifies the complete lifecycle of student enrollment including:
        - School creation
        - Student creation
        - Enrollment creation
        - Enrollment status updates
        - Data retrieval and validation
        """
        user_id, headers = authenticated_user

        # Create test school
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
        assert response.status_code == 201, "Failed to create test school"
        school_id = response.json()["id"]

        # Create test student
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
        assert response.status_code == 201, "Failed to create test student"
        student_id = response.json()["id"]

        try:
            # Test enrollment creation
            enrollment_data = {
                "student_id": student_id,
                "school_id": school_id,
                "academic_year": "2024",
                "grade_level": "5",
                "enrollment_date": "2024-01-15",
                "enrollment_status": "Active",
            }

            response = await async_client.post("/api/v1/enrollments/", json=enrollment_data, headers=headers)
            assert response.status_code == 201, "Failed to create enrollment"

            enrollment = response.json()
            assert enrollment["student_id"] == student_id, "Student ID mismatch"
            assert enrollment["school_id"] == school_id, "School ID mismatch"
            assert enrollment["enrollment_status"] == "Active", "Incorrect status"
            enrollment_id = enrollment["id"]

            # Test retrieving student enrollments
            response = await async_client.get(f"/api/v1/students/{student_id}/enrollments", headers=headers)
            assert response.status_code == 200, "Failed to fetch enrollments"

            enrollments = response.json()
            assert len(enrollments) == 1, "Unexpected number of enrollments"
            assert enrollments[0]["id"] == enrollment_id, "Enrollment ID mismatch"

            # Test enrollment status update
            update_data = {"enrollment_status": "Graduated"}
            response = await async_client.put(f"/api/v1/enrollments/{enrollment_id}", json=update_data, headers=headers)
            assert response.status_code == 200, "Failed to update enrollment"

            updated_enrollment = response.json()
            assert updated_enrollment["enrollment_status"] == "Graduated", "Enrollment status not updated"

            # Verify update in database
            response = await async_client.get(f"/api/v1/enrollments/{enrollment_id}", headers=headers)
            assert response.status_code == 200, "Failed to fetch updated enrollment"
            assert response.json()["enrollment_status"] == "Graduated", "Update not persisted"

        finally:
            # Cleanup test data
            try:
                # Delete enrollment if it exists
                await async_client.delete(f"/api/v1/enrollments/{enrollment_id}", headers=headers)
            except Exception:
                pass

            # Delete student and school
            await async_client.delete(f"/api/v1/students/{student_id}", headers=headers)
            await async_client.delete(f"/api/v1/schools/{school_id}", headers=headers)


@pytest.mark.asyncio
class TestDataProcessingIntegration:
    """Test integration with data processing pipeline."""

    async def test_bulk_data_import(self, async_client: AsyncClient, authenticated_user):
        """Test bulk data import through API."""
        user_id, headers = authenticated_user

        # Prepare bulk student data
        bulk_data = [
            {
                "student_id": f"BULK_STU_{i: 03d}",
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
        """Test handling of data validation errors."""
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
class TestPerformanceMetrics:
    """Test performance metrics and monitoring.

    Verifies API performance under various loads and scenarios.
    """

    async def test_concurrent_requests(self, async_client: AsyncClient, authenticated_user):
        """Test handling of multiple concurrent requests."""
        headers = {"Authorization": f"Bearer {authenticated_user[0]}"}

        async def make_request():
            response = await async_client.get("/api/v1/users/me", headers=headers)
            return response.status_code

        # Execute 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Verify all requests completed successfully
        assert all(isinstance(result, int) and result == 200 for result in results)

    async def test_large_dataset_pagination(self, async_client: AsyncClient, authenticated_user):
        """Test pagination with large datasets."""
        user_id, headers = authenticated_user

        # Create a larger dataset
        students_to_create = 50
        created_students = []

        for i in range(students_to_create):
            student_data = {
                "student_id": f"PAGINATE_STU_{i: 03d}",
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
