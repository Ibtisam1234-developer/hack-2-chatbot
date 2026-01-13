"use client";

import { createAuthClient } from "better-auth/react";

// Better Auth runs on the Next.js server (same domain), not the backend API
export const authClient = createAuthClient({
  // No baseURL needed - defaults to same domain (localhost:3000)
});

export const { useSession, signIn, signUp, signOut } = authClient;
