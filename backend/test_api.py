"""
Simple Test Script for Todo API Endpoints

This script tests the basic functionality of the Todo API without authentication.
For full integration tests with JWT, see tests/ directory.

Usage:
    python test_api.py

Requirements:
    - API server must be running on http://localhost:8000
    - httpx library must be installed
"""

import asyncio
import sys
from datetime import datetime, timedelta
from jose import jwt
import httpx

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_123"
BETTER_AUTH_SECRET = "test-secret-for-development"  # Replace with actual secret


def create_test_token(user_id: str, secret: str) -> str:
    """
    Create a test JWT token for authentication.

    Args:
        user_id: User ID to include in token
        secret: BETTER_AUTH_SECRET for signing

    Returns:
        JWT token string
    """
    payload = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=1),
        "iss": "todoweb",
        "aud": "todoweb-api"
    }
    return jwt.encode(payload, secret, algorithm="HS256")


async def test_health_check():
    """Test the health check endpoint (no auth required)."""
    print("\n[TEST] Health Check")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200, "Health check failed"
        print("✓ Health check passed")


async def test_root_endpoint():
    """Test the root endpoint (no auth required)."""
    print("\n[TEST] Root Endpoint")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200, "Root endpoint failed"
        print("✓ Root endpoint passed")


async def test_create_todo(token: str):
    """Test creating a todo."""
    print("\n[TEST] Create Todo")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/todos",
            json={
                "title": "Test Todo",
                "description": "This is a test todo",
                "is_completed": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 201, "Create todo failed"
        todo = response.json()
        print(f"✓ Todo created with ID: {todo['id']}")
        return todo["id"]


async def test_list_todos(token: str):
    """Test listing todos."""
    print("\n[TEST] List Todos")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/todos",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200, "List todos failed"
        todos = response.json()
        print(f"✓ Retrieved {len(todos)} todos")
        return todos


async def test_get_todo(token: str, todo_id: str):
    """Test getting a specific todo."""
    print(f"\n[TEST] Get Todo {todo_id}")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/todos/{todo_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200, "Get todo failed"
        print("✓ Todo retrieved successfully")


async def test_update_todo(token: str, todo_id: str):
    """Test updating a todo."""
    print(f"\n[TEST] Update Todo {todo_id}")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{API_BASE_URL}/api/todos/{todo_id}",
            json={
                "title": "Updated Test Todo",
                "description": "This todo has been updated"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200, "Update todo failed"
        print("✓ Todo updated successfully")


async def test_toggle_completion(token: str, todo_id: str):
    """Test toggling todo completion."""
    print(f"\n[TEST] Toggle Todo Completion {todo_id}")
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{API_BASE_URL}/api/todos/{todo_id}/complete",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200, "Toggle completion failed"
        todo = response.json()
        print(f"✓ Todo completion toggled to: {todo['is_completed']}")


async def test_delete_todo(token: str, todo_id: str):
    """Test deleting a todo."""
    print(f"\n[TEST] Delete Todo {todo_id}")
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{API_BASE_URL}/api/todos/{todo_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Status: {response.status_code}")
        assert response.status_code == 204, "Delete todo failed"
        print("✓ Todo deleted successfully")


async def test_unauthorized_access():
    """Test that endpoints reject requests without authentication."""
    print("\n[TEST] Unauthorized Access")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/todos")
        print(f"Status: {response.status_code}")
        assert response.status_code == 403, "Should reject unauthorized requests"
        print("✓ Unauthorized access correctly rejected")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Todo API Test Suite")
    print("=" * 60)
    print(f"API URL: {API_BASE_URL}")
    print(f"Test User: {TEST_USER_ID}")
    print("=" * 60)

    try:
        # Test public endpoints
        await test_health_check()
        await test_root_endpoint()

        # Test unauthorized access
        await test_unauthorized_access()

        # Create test token
        print("\n[SETUP] Creating test JWT token...")
        token = create_test_token(TEST_USER_ID, BETTER_AUTH_SECRET)
        print(f"Token created for user: {TEST_USER_ID}")

        # Test authenticated endpoints
        todo_id = await test_create_todo(token)
        await test_list_todos(token)
        await test_get_todo(token, todo_id)
        await test_update_todo(token, todo_id)
        await test_toggle_completion(token, todo_id)
        await test_delete_todo(token, todo_id)

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except httpx.ConnectError:
        print("\n✗ Cannot connect to API server")
        print(f"Make sure the server is running at {API_BASE_URL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
