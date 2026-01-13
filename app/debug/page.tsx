"use client";

import { useSession } from "@/lib/auth-client";
import { useEffect } from "react";

export default function DebugPage() {
  const { data: session, isPending } = useSession();

  useEffect(() => {
    if (session) {
      console.log("=== FULL SESSION DATA ===");
      console.log(JSON.stringify(session, null, 2));
      console.log("=== USER DATA ===");
      console.log(JSON.stringify(session.user, null, 2));
    }
  }, [session]);

  if (isPending) {
    return <div className="p-8">Loading session...</div>;
  }

  if (!session) {
    return <div className="p-8">No session found. Please log in.</div>;
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Session Debug Page</h1>
      <div className="bg-gray-100 p-4 rounded-lg overflow-auto">
        <h2 className="font-semibold mb-2">Full Session Object:</h2>
        <pre className="text-xs">{JSON.stringify(session, null, 2)}</pre>
      </div>
      <div className="mt-4 bg-blue-100 p-4 rounded-lg">
        <h2 className="font-semibold mb-2">Instructions:</h2>
        <ol className="list-decimal list-inside space-y-1 text-sm">
          <li>Check the browser console (F12) for detailed logs</li>
          <li>Look for the JWT token in the session data above</li>
          <li>The token should be a long string with three parts separated by dots</li>
        </ol>
      </div>
    </div>
  );
}
