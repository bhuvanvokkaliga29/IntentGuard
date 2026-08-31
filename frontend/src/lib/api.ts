/**
 * IntentGuard API Client
 * Robust API helper with automatic failover and error containment.
 */

const API_BASE = "http://127.0.0.1:8000";
const BACKUP_BASE = "http://localhost:8000";

export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<any> {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

  // Try direct 127.0.0.1
  try {
    const res = await fetch(`${API_BASE}${cleanEndpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    // Try backup localhost
    try {
      const res = await fetch(`${BACKUP_BASE}${cleanEndpoint}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (backupErr) {
      // Try proxy rewrite
      try {
        const res = await fetch(`/api/proxy${cleanEndpoint}`, {
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
          },
        });
        if (res.ok) {
          return await res.json();
        }
      } catch (proxyErr) {
        console.warn(`[apiFetch] Could not reach API at ${cleanEndpoint}`);
      }
    }
  }
  return null;
}
