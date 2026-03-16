#!/usr/bin/env python3
"""
Development Server Startup Script for Todo API

This script starts the FastAPI development server with hot-reload enabled.

Usage:
    python run_dev.py

Configuration:
    - Reads from backend/.env file
    - Default port: 8000
    - Default host: 0.0.0.0 (accessible from network)

Requirements:
    - BETTER_AUTH_SECRET must be set in .env
    - DATABASE_URL must be set in .env
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify required environment variables
required_vars = ["BETTER_AUTH_SECRET", "DATABASE_URL"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print("ERROR: Missing required environment variables:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\nPlease configure these variables in backend/.env")
    sys.exit(1)

# Get configuration from environment
API_HOST = os.getenv("API_HOST", "0.0.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

print("=" * 60)
print("Starting Todo API Development Server")
print("=" * 60)
print(f"Host: {API_HOST}")
print(f"Log Level: {LOG_LEVEL}")
print(f"Reload: Enabled (development mode)")
print("=" * 60)
print(f"\nAPI Documentation: http://localhost:8000/docs")
print(f"Health Check: http://localhost:8000/health")
print("\nPress CTRL+C to stop the server")
print("=" * 60)

# Start uvicorn server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=API_HOST,
        reload=True,
        log_level=LOG_LEVEL,
        access_log=True
    )
