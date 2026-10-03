const STORAGE_KEY = 'powerpilot-live-token';

/**
 * The launcher opens the UI at `/live?...#token=<secret>`. The secret rides in the URL *fragment* so it
 * is never sent to any server or written to a log. It is moved into sessionStorage (so a reload keeps
 * working) and removed from the address bar. Nothing reads it from a query string.
 */
export function captureToken(): string | null {
  const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''));
  const fromUrl = fragment.get('token');

  if (fromUrl) {
    try {
      sessionStorage.setItem(STORAGE_KEY, fromUrl);
    } catch {
      // Storage blocked: the token still works for this page load.
    }
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    return fromUrl;
  }

  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

/** The model the launcher attached us to, for display only. The backend never trusts these. */
export function launchedModel(): { server: string | null; database: string | null } {
  const params = new URLSearchParams(window.location.search);
  return { server: params.get('server'), database: params.get('db') };
}
