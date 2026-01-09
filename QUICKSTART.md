# Quick Start Guide

## Prerequisites
- Node.js 20+ installed
- PostgreSQL database (Neon recommended)
- Backend API running at http://localhost:8000

## Setup (5 minutes)

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment
```bash
# Generate a secure secret
openssl rand -base64 32

# Copy the output and add to .env
cp .env.example .env
```

Edit `.env` and set:
```env
BETTER_AUTH_SECRET=<paste-generated-secret-here>
DATABASE_URL=postgresql://user:password@host.neon.tech/db
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
```

**CRITICAL**: Use the same `BETTER_AUTH_SECRET` in backend/.env

### 3. Start Development Server
```bash
npm run dev
```

Open http://localhost:3000

## First Run

1. Click "create a new account"
2. Sign up with email/password
3. You'll be redirected to the dashboard
4. Create your first todo
5. Toggle completion and test delete

## Troubleshooting

### "Not authenticated" error
- Check BETTER_AUTH_SECRET matches backend
- Verify DATABASE_URL is correct
- Clear browser cookies and try again

### "Failed to fetch todos" error
- Ensure backend is running at http://localhost:8000
- Check NEXT_PUBLIC_API_URL in .env
- Verify backend CORS allows http://localhost:3000

### Database connection error
- Verify DATABASE_URL format
- Ensure database is accessible
- Check network/firewall settings

## What's Included

- ✅ Better Auth with JWT (7-day tokens)
- ✅ Email/password authentication
- ✅ Protected dashboard
- ✅ Todo CRUD operations
- ✅ User isolation (can't see other users' todos)
- ✅ Optimistic UI updates
- ✅ Responsive design
- ✅ Loading and error states

## Next Steps

See SETUP.md for detailed documentation and IMPLEMENTATION.md for technical details.
