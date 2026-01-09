# Todo API with Authentication

A full-stack todo application with JWT authentication, built with Next.js 16, FastAPI, and Neon PostgreSQL.

## Features

- ✅ **JWT Authentication** - Secure token-based auth with Better Auth
- ✅ **User Isolation** - Each user can only access their own todos
- ✅ **Full CRUD Operations** - Create, read, update, delete todos
- ✅ **Completion Tracking** - Mark todos as complete/incomplete
- ✅ **Responsive UI** - Mobile-first design with Tailwind CSS
- ✅ **Optimistic Updates** - Instant UI feedback
- ✅ **Type Safety** - Full TypeScript coverage
- ✅ **Serverless Database** - Neon PostgreSQL with connection pooling

## Tech Stack

**Frontend:**
- Next.js 16 (App Router)
- React 19
- Better Auth (JWT plugin)
- Tailwind CSS
- TypeScript 5

**Backend:**
- FastAPI (Python)
- SQLModel (async ORM)
- Neon PostgreSQL
- python-jose (JWT verification)
- asyncpg (database driver)

## Quick Start (5 minutes)

### Prerequisites

- Node.js 20+
- Python 3.11+
- PostgreSQL database (Neon recommended)

### 1. Clone and Install

```bash
# Install frontend dependencies
npm install

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..
```

### 2. Configure Environment

```bash
# Generate a secure secret
openssl rand -base64 32

# Copy the output - you'll need it for both .env files
```

**Root `.env` (Frontend):**
```env
BETTER_AUTH_SECRET=<paste-generated-secret-here>
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
```

**Backend `.env`:**
```env
BETTER_AUTH_SECRET=<same-secret-as-above>
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

**CRITICAL:** The `BETTER_AUTH_SECRET` must be identical in both files.

### 3. Start the Backend

```bash
cd backend
python run_dev.py
```

Backend will start at http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 4. Start the Frontend

```bash
# In a new terminal
npm run dev
```

Frontend will start at http://localhost:3000

### 5. Test the Application

1. Open http://localhost:3000
2. Click "create a new account"
3. Sign up with email/password
4. Create your first todo
5. Test toggle completion and delete

## Project Structure

```
todoweb/
├── app/                    # Next.js app directory
│   ├── api/               # API routes (Better Auth)
│   ├── dashboard/         # Protected dashboard page
│   ├── login/            # Login page
│   └── signup/           # Signup page
├── components/            # React components
│   ├── TodoList.tsx      # Todo list display
│   ├── TodoItem.tsx      # Individual todo card
│   └── CreateTodoForm.tsx # Todo creation form
├── lib/                   # Utilities
│   ├── auth.ts           # Better Auth configuration
│   ├── auth-client.ts    # Better Auth React hooks
│   ├── api-client.ts     # API client with JWT
│   └── types.ts          # TypeScript types
├── backend/               # FastAPI backend
│   ├── src/
│   │   ├── api/          # API routes and middleware
│   │   │   ├── middleware/auth.py  # JWT verification
│   │   │   ├── routes/todos.py     # Todo endpoints
│   │   │   └── main.py             # FastAPI app
│   │   └── db/           # Database models and connection
│   │       ├── models.py          # SQLModel schemas
│   │       ├── connection.py      # Database engine
│   │       └── __init__.py        # Database utilities
│   ├── tests/            # Backend tests
│   │   ├── test_auth.py           # JWT validation tests
│   │   ├── test_user_isolation.py # Security tests
│   │   └── test_todos.py          # API endpoint tests
│   └── requirements.txt  # Python dependencies
└── specs/                # Feature specifications
    └── 001-todo-api/
        ├── spec.md       # Feature requirements
        ├── plan.md       # Architecture design
        ├── tasks.md      # Implementation tasks
        ├── data-model.md # Database schema
        └── contracts/    # API contracts
```

## API Endpoints

All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

- `POST /api/todos` - Create a new todo
- `GET /api/todos` - List all todos (user-isolated)
- `GET /api/todos/{id}` - Get a specific todo
- `PUT /api/todos/{id}` - Update a todo
- `DELETE /api/todos/{id}` - Delete a todo
- `PATCH /api/todos/{id}/complete` - Toggle completion status

See `backend/src/api/routes/todos.py` for implementation details.

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

Tests include:
- JWT token validation (valid, expired, invalid signature)
- User isolation (User A cannot access User B's todos)
- All 6 API endpoints with authentication

### Frontend Type Checking

```bash
npm run build
```

## Security Features

- **JWT Authentication** - HS256 algorithm with shared secret
- **User Isolation** - All database queries filter by user_id
- **httpOnly Cookies** - Tokens stored securely (not localStorage)
- **CORS Protection** - Backend only accepts requests from frontend
- **Input Validation** - Pydantic models validate all inputs
- **404 vs 403** - Returns 404 to prevent information leakage

## Troubleshooting

### "Not authenticated" error
- Verify `BETTER_AUTH_SECRET` matches in both `.env` files
- Check `DATABASE_URL` is correct and accessible
- Clear browser cookies and try again

### "Failed to fetch todos" error
- Ensure backend is running at http://localhost:8000
- Verify `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env`
- Check backend CORS allows http://localhost:3000

### Database connection error
- Verify `DATABASE_URL` format is correct
- Ensure database is accessible from your network
- Check firewall/network settings
- Better Auth will auto-create tables on first run

## Documentation

- **QUICKSTART.md** - 5-minute setup guide
- **SETUP.md** - Comprehensive setup and deployment
- **IMPLEMENTATION.md** - Technical implementation details
- **specs/001-todo-api/** - Complete feature specification
  - `spec.md` - User requirements and acceptance criteria
  - `plan.md` - Architecture and technical design
  - `tasks.md` - Implementation task breakdown
  - `data-model.md` - Database schema
  - `contracts/` - API contracts and JWT protocol

## Architecture Highlights

### JWT Authentication Flow

1. User authenticates via Better Auth
2. JWT token generated with user ID in `sub` claim
3. Token stored in httpOnly cookie (prevents XSS)
4. Frontend extracts token from session for API calls
5. Backend verifies token signature and extracts user ID
6. All database queries filtered by user ID

### Multi-Tenant Isolation

- Every database table includes `user_id` column (indexed)
- All queries MUST filter by `user_id`
- Returns 404 (not 403) to prevent information leakage
- UUID primary keys prevent enumeration attacks

### Serverless Optimization

- `pool_pre_ping=True` validates connections before use
- Small connection pool (5) optimized for Neon
- Connection recycling prevents stale connections
- Async/await throughout for performance

## License

MIT

## Contributing

See `specs/001-todo-api/` for feature specifications and implementation guidelines.
