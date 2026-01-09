import { auth } from "@/lib/auth";
import { NextRequest, NextResponse } from "next/server";
import jwt from "jsonwebtoken";

export async function GET(request: NextRequest) {
  try {
    // Get the session from Better Auth
    const session = await auth.api.getSession({
      headers: request.headers,
    });

    if (!session) {
      return NextResponse.json(
        { error: "Not authenticated" },
        { status: 401 }
      );
    }

    // Generate JWT token manually using the same configuration as Better Auth
    const secret = process.env.BETTER_AUTH_SECRET!;

    // Create JWT payload with user information
    const payload = {
      sub: session.user.id, // subject (user ID) - required by backend
      email: session.user.email,
      sessionId: session.session.id,
      iss: "todoweb", // issuer (must match backend verification)
      aud: "todoweb-api", // audience (must match backend verification)
      iat: Math.floor(Date.now() / 1000), // issued at
      exp: Math.floor(Date.now() / 1000) + (60 * 60 * 24 * 7), // expires in 7 days
    };

    // Sign the JWT token
    const token = jwt.sign(payload, secret, {
      algorithm: "HS256",
    });

    return NextResponse.json({ token });
  } catch (error) {
    console.error("Error generating JWT token:", error);
    return NextResponse.json(
      { error: "Failed to generate JWT token" },
      { status: 500 }
    );
  }
}
