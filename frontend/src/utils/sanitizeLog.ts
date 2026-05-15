/**
 * Sanitizes user-controlled values before logging to prevent log injection.
 * Strips control characters (newlines, carriage returns, tabs) that could
 * be used to forge log entries.
 */
export function sanitizeForLog(value: unknown): string {
  if (value == null) return '';
  const str = String(value);
  return str.replace(/[\r\n\t]/g, ' ');
}
