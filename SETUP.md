# TodoWeb Frontend Setup Guide

## Overview

This is a Next.js 16 frontend application with Better Auth JWT authentication and a Todo dashboard. It connects to a FastAPI backend for todo management with secure user isolation.

## Prerequisites

- Node.js 20+ and npm
- PostgreSQL database (Neon recommended)
- Backend API running at http://localhost:8000
- Shared `BETTER_AUTH_SECRET` between frontend and backend

## Installation

### 1. Install Dependencies

```bash
npm install
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Generate a secure secret (must match backend)
BETTER_AUTH_SECRET=your-secret-key-here-min-32-chars

# Database for Better Auth user storage
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Frontend URL
NEXTAUTH_URL=http://localhost:3000
```

**CRITICAL**: The `BETTER_AUTH_SECRET` must be identical in both frontend and backend `.env` files.

### 3. Generate Secure Secret

```bash
# Generate a secure 32-character secret
openssl rand -base64 32
```

Copy this value to both frontend and backend `.env` files.

## Running the Application

### Development Mode

```bash
npm run dev
```

The application will be available at http://localhost:3000

### Production Build

```bash
npm run build
npm start
```

## Application Structure

```
E:\todoweb\
├── app/
│   ├── api/auth/[...all]/route.ts  # Better Auth API handler
│   ├── login/page.tsx              # Login page
│   ├── signup/page.tsx             # Signup page
│   ├── dashboard/page.tsx          # Protected dashboard
│   ├── layout.tsx                  # Root layout
│   └── page.tsx                    # Root page (redirects)
├── components/
│   ├── TodoItem.tsx                # Individual todo card
│   ├── CreateTodoForm.tsx          # Todo creation form
│   └── TodoList.tsx                # Todo list display
├── lib/
│   ├── auth.ts                     # Better Auth server config
│   ├── auth-client.ts              # Better Auth client
│   ├── api-client.ts               # API client with JWT
│   └── types.ts                    # TypeScript types
└── .env                            # Environment variables
```

## Features

### Authentication
- Email/password signup and login
- JWT token-based authentication (7-day expiry)
- Automatic token attachment to API requests
- Protected routes with redirect to login
- Session persistence across page refreshes

### Todo Management
- Create new todos with title and description
- View all todos (user-isolated)
- Toggle todo completion status (optimistic updates)
- Delete todos
- Separate active and completed todo sections

### UI/UX
- Responsive design (mobile-first)
- Loading states for all async operations
- Error handling with user-friendly messages
- Optimistic UI updates for better perceived performance
- Clean, modern interface with Tailwind CSS

## API Integration

All API requests use the `apiClient` utility which:
1. Automatically fetches JWT token from Better Auth session
2. Attaches token to `Authorization: Bearer` header
3. Handles 401 errors by redirecting to login
4. Provides type-safe request/response interfaces

### Example Usage

```typescript
import { apiClient } from "@/lib/api-client";
import { Todo } from "@/lib/types";

// Fetch todos
const todos = await apiClient<Todo[]>("/api/todos");

// Create todo
const newTodo = await apiClient<Todo>("/api/todos", {
  method: "POST",
  body: JSON.stringify({ title: "Buy groceries" }),
});

// Toggle completion
const updated = await apiClient<Todo>(`/api/todos/${id}/complete`, {
  method: "PATCH",
});

// Delete todo
await apiClient(`/api/todos/${id}`, {
  method: "DELETE",
});
```

## Security

### JWT Token Flow
1. User signs up/logs in via Better Auth
2. Better Auth generates JWT with user ID in `sub` claim
3. Token stored in httpOnly cookie (secure by default)
4. Frontend extracts token from session for API calls
5. Backend verifies token signature and extracts user ID
6. All database queries filtered by user ID

### Security Features
- httpOnly cookies prevent XSS token theft
- JWT signature prevents token tampering
- 7-day token expiration limits exposure
- User isolation at database level
- CORS protection (backend configured)
- No tokens in localStorage or console

## Troubleshooting

### "Not authenticated" Error
- Check that `BETTER_AUTH_SECRET` matches in frontend and backend
- Verify database connection in `.env`
- Clear browser cookies and try logging in again

### "Failed to fetch todos" Error
- Ensure backend API is running at http://localhost:8000
- Check `NEXT_PUBLIC_API_URL` in `.env`
- Verify JWT token is being sent (check Network tab)

### TypeScript Errors
- Run `npm install` to ensure all dependencies are installed
- Check that `@/*` path alias is configured in `tsconfig.json`
- Restart TypeScript server in your editor

### Database Connection Issues
- Verify `DATABASE_URL` is correct in `.env`
- Ensure database is accessible from your network
- Check that Better Auth tables are created (auto-created on first run)

## Development Workflow

### Adding New Features
1. Define TypeScript types in `lib/types.ts`
2. Create API client functions using `apiClient`
3. Build components in `components/`
4. Add pages in `app/`
5. Update this documentation

### Testing Authentication
1. Sign up with a new email/password
2. Verify redirect to dashboard
3. Check that todos are user-isolated
4. Log out and verify redirect to login
5. Log in again and verify session persistence

## Production Deployment

### Environment Variables
Set these in your hosting platform (Vercel, Netlify, etc.):
- `BETTER_AUTH_SECRET` (same as backend)
- `DATABASE_URL` (PostgreSQL connection string)
- `NEXT_PUBLIC_API_URL` (production backend URL)
- `NEXTAUTH_URL` (production frontend URL)

### Build Configuration
```bash
npm run build
```

### Deployment Checklist
- [ ] All environment variables configured
- [ ] `BETTER_AUTH_SECRET` matches backend
- [ ] Database accessible from production
- [ ] Backend API URL is HTTPS
- [ ] CORS configured on backend for production domain
- [ ] Test signup, login, and todo operations

## API Endpoints

### Authentication (Better Auth)
- `POST /api/auth/sign-up/email` - Create account
- `POST /api/auth/sign-in/email` - Login
- `POST /api/auth/sign-out` - Logout
- `GET /api/auth/session` - Get current session

### Todos (Backend API)
- `GET /api/todos` - List user's todos
- `POST /api/todos` - Create todo
- `GET /api/todos/{id}` - Get specific todo
- `PUT /api/todos/{id}` - Update todo
- `PATCH /api/todos/{id}/complete` - Toggle completion
- `DELETE /api/todos/{id}` - Delete todo

All todo endpoints require JWT authentication.

## Support

For issues or questions:
1. Check this documentation
2. Review the JWT protocol: `specs/001-todo-api/contracts/jwt-protocol.md`
3. Review API endpoints: `specs/001-todo-api/contracts/api-endpoints.yaml`
4. Check backend logs for authentication errors

## License

MIT
