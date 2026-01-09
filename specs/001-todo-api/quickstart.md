# Quickstart Guide: Todo API Development

**Feature**: Todo API with Authentication
**Date**: 2026-01-07
**Audience**: Developers setting up local development environment

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Neon Account**: Free tier at [neon.tech](https://neon.tech)
- **Git**: For version control
- **Code Editor**: VS Code recommended

## Project Structure Overview

```
todoweb/
├── backend/              # FastAPI Python backend
│   ├── src/
│   │   ├── models/      # SQLModel schemas
│   │   ├── api/         # FastAPI routes and middleware
│   │   ├── services/    # Business logic (wraps CLI)
│   │   ├── cli/         # Existing CLI code (preserved)
│   │   └── db/          # Database connection
│   ├── tests/           # Backend tests
│   └── requirements.txt
├── frontend/            # Next.js React frontend
│   ├── src/
│   │   ├── app/         # Next.js App Router
│   │   ├── components/  # React components
│   │   └── lib/         # Auth and API client
│   └── package.json
└── .env                 # Shared environment variables
```

## Step 1: Clone and Setup Repository

```bash
# Clone repository
git clone <repository-url>
cd todoweb

# Checkout feature branch
git checkout 001-todo-api
```

## Step 2: Configure Neon Database

### Create Neon Project

1. Go to [console.neon.tech](https://console.neon.tech)
2. Click "Create Project"
3. Name: "todoweb"
4. Region: Choose closest to you
5. PostgreSQL version: 16 (latest)
6. Click "Create Project"

### Get Connection String

1. In Neon dashboard, click "Connection Details"
2. Copy the connection string (looks like):
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb
   ```
3. Save for next step

## Step 3: Environment Variables

Create `.env` file in project root:

```bash
# Generate secure secret (run this command)
openssl rand -base64 32

# Copy output and paste below
```

```bash
# .env file (DO NOT COMMIT)

# Shared Secret (CRITICAL: Must be identical in both services)
BETTER_AUTH_SECRET=<paste-generated-secret-here>

# Backend (FastAPI)
DATABASE_URL=postgresql+asyncpg://user:password@host.neon.tech/neondb
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://user:password@host.neon.tech/neondb
```

**Important**: Replace `<paste-generated-secret-here>` with the output from `openssl rand -base64 32`

## Step 4: Backend Setup (FastAPI)

### Install Dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Requirements.txt

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlmodel==0.0.14
asyncpg==0.29.0
python-jose[cryptography]==3.3.0
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
```

### Create Database Tables

```bash
# Run database initialization script
python -m src.db.init_db
```

This will create the `todos` table with proper schema and indexes.

### Run Backend Server

```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload --port 8000

# Server will start at http://localhost:8000
# API docs available at http://localhost:8000/docs
```

### Verify Backend

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy"}
```

## Step 5: Frontend Setup (Next.js)

### Install Dependencies

```bash
cd frontend

# Install packages
npm install
```

### Package.json Dependencies

```json
{
  "dependencies": {
    "next": "16.1.1",
    "react": "19.2.3",
    "react-dom": "19.2.3",
    "better-auth": "^1.0.0",
    "@better-auth/react": "^1.0.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "typescript": "^5",
    "tailwindcss": "^4",
    "eslint": "^9",
    "eslint-config-next": "16.1.1"
  }
}
```

### Run Frontend Server

```bash
# Development mode
npm run dev

# Server will start at http://localhost:3000
```

### Verify Frontend

1. Open browser to http://localhost:3000
2. You should see the login page
3. Register a new account
4. After login, you should see the todo dashboard

## Step 6: Verify Integration

### Test Authentication Flow

1. **Register**: Create account at http://localhost:3000/register
2. **Login**: Sign in at http://localhost:3000/login
3. **Dashboard**: Redirected to http://localhost:3000/dashboard

### Test API Endpoints

```bash
# Get JWT token from browser (open DevTools > Application > Cookies)
# Copy the auth token value

# Set token variable
TOKEN="<your-jwt-token>"

# List todos (should return empty array initially)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/todos

# Create todo
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test todo","description":"Testing API"}' \
  http://localhost:8000/api/todos

# List todos again (should show created todo)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/todos
```

## Step 7: Run Tests

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_auth.py
pytest tests/test_user_isolation.py
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

## Development Workflow

### Backend Development

1. **Make changes** to Python files in `backend/src/`
2. **Server auto-reloads** (uvicorn --reload)
3. **Test changes** at http://localhost:8000/docs
4. **Run tests**: `pytest`
5. **Commit changes**: `git commit -m "feat: add feature"`

### Frontend Development

1. **Make changes** to TypeScript/React files in `frontend/src/`
2. **Hot reload** updates browser automatically
3. **Test changes** in browser at http://localhost:3000
4. **Run tests**: `npm test`
5. **Commit changes**: `git commit -m "feat: add component"`

## Common Tasks

### Add New API Endpoint

1. Define route in `backend/src/api/routes/todos.py`
2. Add business logic in `backend/src/services/todo_service.py`
3. Update OpenAPI docs (automatic via FastAPI)
4. Write tests in `backend/tests/`

### Add New Frontend Component

1. Create component in `frontend/src/components/`
2. Import in page: `frontend/src/app/dashboard/page.tsx`
3. Use API client: `import { apiClient } from '@/lib/api-client'`
4. Write tests in `frontend/tests/components/`

### Database Migrations

```bash
cd backend

# Create migration (after changing models)
alembic revision --autogenerate -m "Add new field"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Troubleshooting

### "Invalid authentication token"

**Problem**: JWT token verification fails

**Solutions**:
1. Verify `BETTER_AUTH_SECRET` is identical in both .env files
2. Check token hasn't expired (7-day default)
3. Ensure token format is `Bearer <token>`

### "Connection refused" to database

**Problem**: Cannot connect to Neon database

**Solutions**:
1. Verify `DATABASE_URL` is correct
2. Check Neon project is active (not suspended)
3. Ensure IP is whitelisted in Neon dashboard
4. Test connection: `psql $DATABASE_URL`

### "Module not found" errors

**Problem**: Import errors in Python or TypeScript

**Solutions**:
1. Backend: Activate virtual environment (`source venv/bin/activate`)
2. Backend: Reinstall dependencies (`pip install -r requirements.txt`)
3. Frontend: Reinstall packages (`npm install`)
4. Frontend: Clear cache (`rm -rf .next node_modules && npm install`)

### CORS errors in browser

**Problem**: Browser blocks API requests

**Solutions**:
1. Verify `CORS_ORIGINS` includes `http://localhost:3000`
2. Check FastAPI CORS middleware is configured
3. Ensure frontend uses correct API URL

### Tests failing

**Problem**: pytest or npm test shows failures

**Solutions**:
1. Check environment variables are set
2. Ensure test database is separate from dev database
3. Run tests in isolation: `pytest tests/test_file.py::test_name`
4. Check test fixtures are properly set up

## IDE Setup (VS Code)

### Recommended Extensions

- **Python**: ms-python.python
- **Pylance**: ms-python.vscode-pylance
- **ESLint**: dbaeumer.vscode-eslint
- **Prettier**: esbenp.prettier-vscode
- **Tailwind CSS IntelliSense**: bradlc.vscode-tailwindcss

### Settings (.vscode/settings.json)

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

## Next Steps

1. ✅ Development environment set up
2. ⏭️ Run `/sp.tasks` to generate implementation tasks
3. ⏭️ Implement features using specialized agents:
   - @neon-schema-manager for database setup
   - @fastapi-migration-engineer for backend
   - @nextjs-auth-frontend for frontend
4. ⏭️ Run tests and verify user isolation
5. ⏭️ Deploy to production

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Next.js Docs**: https://nextjs.org/docs
- **Better Auth Docs**: https://better-auth.com
- **SQLModel Docs**: https://sqlmodel.tiangolo.com
- **Neon Docs**: https://neon.tech/docs
- **Feature Spec**: [spec.md](./spec.md)
- **Implementation Plan**: [plan.md](./plan.md)
- **API Contracts**: [contracts/api-endpoints.yaml](./contracts/api-endpoints.yaml)

## Support

For issues or questions:
1. Check this quickstart guide
2. Review [plan.md](./plan.md) for architecture details
3. Check [research.md](./research.md) for technology decisions
4. Open an issue in the repository
