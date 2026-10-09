export function plainError(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) return fallback;
  let msg = error.message.trim();
  if (msg.startsWith("{")) {
    try {
      const parsed = JSON.parse(msg) as { detail?: unknown };
      if (typeof parsed.detail === "string") msg = parsed.detail;
    } catch {
      return fallback;
    }
  }
  msg = msg.replace(/\s+/g, " ").trim();
  if (!msg || msg.length > 280 || msg.startsWith("<")) return fallback;
  if (/^(failed to fetch|networkerror.*|load failed|network request failed)$/i.test(msg)) return fallback;
  return msg;
}
