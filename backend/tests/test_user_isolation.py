"""
User Isolation Security Tests

Purpose: Validate multi-tenant isolation and prevent unauthorized access
Tests: User A cannot access User B's todos

Constitutional Requirements:
- REQUIRED: All queries MUST filter by user_id
- REQUIRED: Return 404 (not 403) to prevent information leakage
- REQUIRED: Never expose existence of other users' todos
- REQUIRED: Enforce isolation at database query level
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from jose import jwt
import os

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


class TestUserIsolation:
    """Test that users can only access their own todos"""

    @pytest.mark.asyncio
    async def test_user_cannot_list_other_user_todos(self):
        """Test that User A cannot see User B's todos in list endpoint"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # User A creates a todo
            user_a_token = create_test_token("user_a")
            response_a = await client.post(
                "/api/todos",
                json={"title": "User A's private todo", "description": "Secret"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_a.status_code == 201

            # User B lists todos - should NOT see User A's todo
            user_b_token = create_test_token("user_b")
            response_b = await client.get(
                "/api/todos",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )
            assert response_b.status_code == 200

            todos = response_b.json()
            # User B should see empty list (no todos)
            assert len(todos) == 0

    @pytest.mark.asyncio
    async def test_user_cannot_get_other_user_todo_by_id(self):
        """Test that User A cannot access User B's todo by ID"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # User A creates a todo
            user_a_token = create_test_token("user_a")
            response_a = await client.post(
                "/api/todos",
                json={"title": "User A's todo", "description": "Private"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_a.status_code == 201
            todo_id = response_a.json()["id"]

            # User B tries to access User A's todo by ID
            user_b_token = create_test_token("user_b")
            response_b = await client.get(
                f"/api/todos/{todo_id}",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )

            # Should return 404 (not 403) to prevent information leakage
            assert response_b.status_code == 404
            assert "not found" in response_b.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_user_todo(self):
        """Test that User A cannot update User B's todo"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # User A creates a todo
            user_a_token = create_test_token("user_a")
            response_a = await client.post(
                "/api/todos",
                json={"title": "Original title", "description": "Original"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_a.status_code == 201
            todo_id = response_a.json()["id"]

            # User B tries to update User A's todo
            user_b_token = create_test_token("user_b")
            response_b = await client.put(
                f"/api/todos/{todo_id}",
                json={"title": "Hacked title", "description": "Hacked"},
                headers={"Authorization": f"Bearer {user_b_token}"}
            )

            # Should return 404 (not 403)
            assert response_b.status_code == 404

            # Verify User A's todo is unchanged
            response_verify = await client.get(
                f"/api/todos/{todo_id}",
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_verify.status_code == 200
            assert response_verify.json()["title"] == "Original title"

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_user_todo(self):
        """Test that User A cannot delete User B's todo"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # User A creates a todo
            user_a_token = create_test_token("user_a")
            response_a = await client.post(
                "/api/todos",
                json={"title": "Important todo", "description": "Do not delete"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_a.status_code == 201
            todo_id = response_a.json()["id"]

            # User B tries to delete User A's todo
            user_b_token = create_test_token("user_b")
            response_b = await client.delete(
                f"/api/todos/{todo_id}",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )

            # Should return 404 (not 403)
            assert response_b.status_code == 404

            # Verify User A's todo still exists
            response_verify = await client.get(
                f"/api/todos/{todo_id}",
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_verify.status_code == 200
            assert response_verify.json()["title"] == "Important todo"

    @pytest.mark.asyncio
    async def test_user_cannot_toggle_other_user_todo_completion(self):
        """Test that User A cannot toggle User B's todo completion status"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # User A creates a todo
            user_a_token = create_test_token("user_a")
            response_a = await client.post(
                "/api/todos",
                json={"title": "User A's task", "description": "Incomplete"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_a.status_code == 201
            todo_id = response_a.json()["id"]
            assert response_a.json()["is_completed"] is False

            # User B tries to toggle User A's todo
            user_b_token = create_test_token("user_b")
            response_b = await client.patch(
                f"/api/todos/{todo_id}/complete",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )

            # Should return 404 (not 403)
            assert response_b.status_code == 404

            # Verify User A's todo is still incomplete
            response_verify = await client.get(
                f"/api/todos/{todo_id}",
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_verify.status_code == 200
            assert response_verify.json()["is_completed"] is False

    @pytest.mark.asyncio
    async def test_multiple_users_can_have_same_todo_titles(self):
        """Test that multiple users can create todos with the same title"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # User A creates a todo
            user_a_token = create_test_token("user_a")
            response_a = await client.post(
                "/api/todos",
                json={"title": "Buy groceries", "description": "User A's list"},
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_a.status_code == 201
            todo_a_id = response_a.json()["id"]

            # User B creates a todo with the same title
            user_b_token = create_test_token("user_b")
            response_b = await client.post(
                "/api/todos",
                json={"title": "Buy groceries", "description": "User B's list"},
                headers={"Authorization": f"Bearer {user_b_token}"}
            )
            assert response_b.status_code == 201
            todo_b_id = response_b.json()["id"]

            # Verify they have different IDs
            assert todo_a_id != todo_b_id

            # User A should only see their todo
            response_a_list = await client.get(
                "/api/todos",
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_a_list.status_code == 200
            todos_a = response_a_list.json()
            assert len(todos_a) == 1
            assert todos_a[0]["description"] == "User A's list"

            # User B should only see their todo
            response_b_list = await client.get(
                "/api/todos",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )
            assert response_b_list.status_code == 200
            todos_b = response_b_list.json()
            assert len(todos_b) == 1
            assert todos_b[0]["description"] == "User B's list"

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_todos_count(self):
        """Test that todo counts are isolated per user"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # User A creates 3 todos
            user_a_token = create_test_token("user_a")
            for i in range(3):
                response = await client.post(
                    "/api/todos",
                    json={"title": f"User A todo {i}", "description": f"Task {i}"},
                    headers={"Authorization": f"Bearer {user_a_token}"}
                )
                assert response.status_code == 201

            # User B creates 5 todos
            user_b_token = create_test_token("user_b")
            for i in range(5):
                response = await client.post(
                    "/api/todos",
                    json={"title": f"User B todo {i}", "description": f"Task {i}"},
                    headers={"Authorization": f"Bearer {user_b_token}"}
                )
                assert response.status_code == 201

            # User A should see exactly 3 todos
            response_a = await client.get(
                "/api/todos",
                headers={"Authorization": f"Bearer {user_a_token}"}
            )
            assert response_a.status_code == 200
            assert len(response_a.json()) == 3

            # User B should see exactly 5 todos
            response_b = await client.get(
                "/api/todos",
                headers={"Authorization": f"Bearer {user_b_token}"}
            )
            assert response_b.status_code == 200
            assert len(response_b.json()) == 5


class TestAuthenticationRequired:
    """Test that all endpoints require authentication"""

    @pytest.mark.asyncio
    async def test_list_todos_requires_auth(self):
        """Test that listing todos requires authentication"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.get("/api/todos")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_todo_requires_auth(self):
        """Test that creating todos requires authentication"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.post(
                "/api/todos",
                json={"title": "Test", "description": "Test"}
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_todo_requires_auth(self):
        """Test that getting a todo requires authentication"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Use a random UUID
            response = await client.get("/api/todos/123e4567-e89b-12d3-a456-426614174000")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_todo_requires_auth(self):
        """Test that updating todos requires authentication"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.put(
                "/api/todos/123e4567-e89b-12d3-a456-426614174000",
                json={"title": "Updated", "description": "Updated"}
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_todo_requires_auth(self):
        """Test that deleting todos requires authentication"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.delete("/api/todos/123e4567-e89b-12d3-a456-426614174000")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_toggle_completion_requires_auth(self):
        """Test that toggling completion requires authentication"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.patch("/api/todos/123e4567-e89b-12d3-a456-426614174000/complete")
            assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
