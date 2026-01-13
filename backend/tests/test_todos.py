"""
Todo API Endpoint Tests

Purpose: Validate all 6 Todo API endpoints with authentication
Tests: Create, List, Get, Update, Delete, Toggle Completion

Constitutional Requirements:
- REQUIRED: All endpoints must enforce JWT authentication
- REQUIRED: All endpoints must enforce user isolation
- REQUIRED: Proper HTTP status codes (201, 200, 204, 404, 422)
- REQUIRED: Input validation using Pydantic models
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from jose import jwt
import os
from uuid import uuid4

# Test secret
TEST_SECRET = os.getenv("BETTER_AUTH_SECRET", "test-secret-for-testing-only")

# Base URL for API
BASE_URL = "http://localhost:8000"


def create_test_token(user_id: str) -> str:
    """Create a test JWT token for a specific user"""
    payload = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=1),
        "iss": "todoweb",
        "aud": "todoweb-api"
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


class TestHealthEndpoint:
    """Test health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test that health endpoint returns 200"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestCreateTodoEndpoint:
    """Test POST /api/todos endpoint"""

    @pytest.mark.asyncio
    async def test_create_todo_success(self):
        """Test creating a todo with valid data"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            response = await client.post(
                "/api/todos",
                json={
                    "title": "Buy groceries",
                    "description": "Milk, eggs, bread"
                },
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "Buy groceries"
            assert data["description"] == "Milk, eggs, bread"
            assert data["is_completed"] is False
            assert "id" in data
            assert "created_at" in data
            assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_todo_without_description(self):
        """Test creating a todo without description (optional field)"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            response = await client.post(
                "/api/todos",
                json={"title": "Simple task"},
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "Simple task"
            assert data["description"] is None or data["description"] == ""

    @pytest.mark.asyncio
    async def test_create_todo_empty_title(self):
        """Test that empty title returns 422 validation error"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            response = await client.post(
                "/api/todos",
                json={"title": "", "description": "Test"},
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_todo_missing_title(self):
        """Test that missing title returns 422 validation error"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            response = await client.post(
                "/api/todos",
                json={"description": "Test"},
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_todo_title_too_long(self):
        """Test that title exceeding max length returns 422"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            long_title = "x" * 201  # Exceeds 200 character limit
            response = await client.post(
                "/api/todos",
                json={"title": long_title, "description": "Test"},
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_todo_without_auth(self):
        """Test that creating todo without auth returns 401"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.post(
                "/api/todos",
                json={"title": "Test", "description": "Test"}
            )

            assert response.status_code == 401


class TestListTodosEndpoint:
    """Test GET /api/todos endpoint"""

    @pytest.mark.asyncio
    async def test_list_todos_empty(self):
        """Test listing todos when user has none"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token(f"user_{uuid4()}")
            response = await client.get(
                "/api/todos",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0

    @pytest.mark.asyncio
    async def test_list_todos_with_items(self):
        """Test listing todos when user has multiple todos"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user_id = f"user_{uuid4()}"
            token = create_test_token(user_id)

            # Create 3 todos
            for i in range(3):
                await client.post(
                    "/api/todos",
                    json={"title": f"Task {i}", "description": f"Description {i}"},
                    headers={"Authorization": f"Bearer {token}"}
                )

            # List todos
            response = await client.get(
                "/api/todos",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3

    @pytest.mark.asyncio
    async def test_list_todos_without_auth(self):
        """Test that listing todos without auth returns 401"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/api/todos")
            assert response.status_code == 401


class TestGetTodoEndpoint:
    """Test GET /api/todos/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_todo_success(self):
        """Test getting a specific todo by ID"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")

            # Create a todo
            create_response = await client.post(
                "/api/todos",
                json={"title": "Test todo", "description": "Test description"},
                headers={"Authorization": f"Bearer {token}"}
            )
            todo_id = create_response.json()["id"]

            # Get the todo
            response = await client.get(
                f"/api/todos/{todo_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == todo_id
            assert data["title"] == "Test todo"
            assert data["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_get_todo_not_found(self):
        """Test getting a non-existent todo returns 404"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            fake_id = str(uuid4())

            response = await client.get(
                f"/api/todos/{fake_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_todo_invalid_uuid(self):
        """Test getting a todo with invalid UUID format"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")

            response = await client.get(
                "/api/todos/not-a-valid-uuid",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_todo_without_auth(self):
        """Test that getting todo without auth returns 401"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get(f"/api/todos/{uuid4()}")
            assert response.status_code == 401


class TestUpdateTodoEndpoint:
    """Test PUT /api/todos/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_update_todo_success(self):
        """Test updating a todo with valid data"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")

            # Create a todo
            create_response = await client.post(
                "/api/todos",
                json={"title": "Original title", "description": "Original description"},
                headers={"Authorization": f"Bearer {token}"}
            )
            todo_id = create_response.json()["id"]

            # Update the todo
            response = await client.put(
                f"/api/todos/{todo_id}",
                json={"title": "Updated title", "description": "Updated description"},
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Updated title"
            assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_todo_partial(self):
        """Test partial update (only title or description)"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")

            # Create a todo
            create_response = await client.post(
                "/api/todos",
                json={"title": "Original", "description": "Original"},
                headers={"Authorization": f"Bearer {token}"}
            )
            todo_id = create_response.json()["id"]

            # Update only title
            response = await client.put(
                f"/api/todos/{todo_id}",
                json={"title": "New title"},
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "New title"

    @pytest.mark.asyncio
    async def test_update_todo_not_found(self):
        """Test updating non-existent todo returns 404"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            fake_id = str(uuid4())

            response = await client.put(
                f"/api/todos/{fake_id}",
                json={"title": "Updated", "description": "Updated"},
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_todo_without_auth(self):
        """Test that updating todo without auth returns 401"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.put(
                f"/api/todos/{uuid4()}",
                json={"title": "Updated"}
            )
            assert response.status_code == 401


class TestDeleteTodoEndpoint:
    """Test DELETE /api/todos/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_delete_todo_success(self):
        """Test deleting a todo"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")

            # Create a todo
            create_response = await client.post(
                "/api/todos",
                json={"title": "To be deleted", "description": "Delete me"},
                headers={"Authorization": f"Bearer {token}"}
            )
            todo_id = create_response.json()["id"]

            # Delete the todo
            response = await client.delete(
                f"/api/todos/{todo_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 204

            # Verify todo is deleted
            get_response = await client.get(
                f"/api/todos/{todo_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_todo_not_found(self):
        """Test deleting non-existent todo returns 404"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            fake_id = str(uuid4())

            response = await client.delete(
                f"/api/todos/{fake_id}",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_todo_without_auth(self):
        """Test that deleting todo without auth returns 401"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.delete(f"/api/todos/{uuid4()}")
            assert response.status_code == 401


class TestToggleCompletionEndpoint:
    """Test PATCH /api/todos/{id}/complete endpoint"""

    @pytest.mark.asyncio
    async def test_toggle_completion_to_complete(self):
        """Test marking a todo as complete"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")

            # Create a todo (default is incomplete)
            create_response = await client.post(
                "/api/todos",
                json={"title": "Task to complete", "description": "Mark as done"},
                headers={"Authorization": f"Bearer {token}"}
            )
            todo_id = create_response.json()["id"]
            assert create_response.json()["is_completed"] is False

            # Toggle to complete
            response = await client.patch(
                f"/api/todos/{todo_id}/complete",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_completed"] is True

    @pytest.mark.asyncio
    async def test_toggle_completion_to_incomplete(self):
        """Test marking a completed todo as incomplete"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")

            # Create and complete a todo
            create_response = await client.post(
                "/api/todos",
                json={"title": "Completed task", "description": "Already done"},
                headers={"Authorization": f"Bearer {token}"}
            )
            todo_id = create_response.json()["id"]

            # Toggle to complete
            await client.patch(
                f"/api/todos/{todo_id}/complete",
                headers={"Authorization": f"Bearer {token}"}
            )

            # Toggle back to incomplete
            response = await client.patch(
                f"/api/todos/{todo_id}/complete",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_completed"] is False

    @pytest.mark.asyncio
    async def test_toggle_completion_not_found(self):
        """Test toggling completion of non-existent todo returns 404"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            fake_id = str(uuid4())

            response = await client.patch(
                f"/api/todos/{fake_id}/complete",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_toggle_completion_without_auth(self):
        """Test that toggling completion without auth returns 401"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.patch(f"/api/todos/{uuid4()}/complete")
            assert response.status_code == 401


class TestInputValidation:
    """Test input validation across endpoints"""

    @pytest.mark.asyncio
    async def test_create_todo_with_extra_fields(self):
        """Test that extra fields are ignored"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")
            response = await client.post(
                "/api/todos",
                json={
                    "title": "Valid todo",
                    "description": "Valid description",
                    "extra_field": "Should be ignored",
                    "another_field": 123
                },
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 201
            data = response.json()
            assert "extra_field" not in data
            assert "another_field" not in data

    @pytest.mark.asyncio
    async def test_update_todo_with_invalid_data_type(self):
        """Test that invalid data types return 422"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            token = create_test_token("user_123")

            # Create a todo
            create_response = await client.post(
                "/api/todos",
                json={"title": "Test", "description": "Test"},
                headers={"Authorization": f"Bearer {token}"}
            )
            todo_id = create_response.json()["id"]

            # Try to update with invalid data type
            response = await client.put(
                f"/api/todos/{todo_id}",
                json={"title": 123},  # Should be string
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
