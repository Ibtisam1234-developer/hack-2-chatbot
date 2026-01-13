import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { Pool } from "pg";

// Create PostgreSQL connection pool for Neon
const pool = new Pool({
  connectionString: process.env.DATABASE_URL!,
  ssl: {
    rejectUnauthorized: false, // Required for Neon serverless PostgreSQL
  },
});

export const auth = betterAuth({
  secret: process.env.BETTER_AUTH_SECRET!,
  database: pool,
  emailAndPassword: {
    enabled: true,
  },
  plugins: [
    jwt({
      jwt: {
        expiresIn: 60 * 60 * 24 * 7, // 7 days in seconds
        issuer: "todoweb",
        audience: "todoweb-api",
      },
    }),
  ],
});

export type Session = typeof auth.$Infer.Session;
