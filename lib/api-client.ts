"use client";

import { authClient } from "./auth-client";

export interface ApiError {
  detail: string;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  // Get current session
  const session = await authClient.getSession();

  if (!session?.data?.session) {
    throw new Error("Not authenticated");
  }

  // Better Auth JWT plugin: Get the JWT token using the getToken method
  let token: string | null = null;

  try {
    // Try to get token from authClient's getToken method
    const tokenResponse = await fetch("/api/auth/get-token", {
      credentials: "include",
    });

    if (tokenResponse.ok) {
      const data = await tokenResponse.json();
      token = data.token;
    }
  } catch (error) {
    console.error("Failed to get JWT token:", error);
  }

  if (!token) {
    console.error("Session data structure:", session.data);
    throw new Error("No JWT token found in session");
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const url = `${apiUrl}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired or invalid - redirect to login
      window.location.href = "/login";
      throw new Error("Authentication required");
    }

    // Try to parse error response
    try {
      const errorData: ApiError = await response.json();
      throw new Error(errorData.detail || `API error: ${response.status}`);
    } catch {
      throw new Error(`API error: ${response.status}`);
    }
  }

  // Handle 204 No Content responses
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
