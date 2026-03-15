/**
 * Utility function to generate secure unique identifiers.
 * Uses the Web Crypto API `crypto.randomUUID()` when available,
 * with a fallback to `Math.random()` for environments without it (e.g., JSDOM).
 *
 * @param prefix Optional prefix to prepend to the generated ID
 * @returns A unique identifier string
 */
export const generateSecureId = (prefix?: string): string => {
  let uniquePart = '';

  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    uniquePart = crypto.randomUUID();
  } else {
    // Fallback for environments without Web Crypto API
    uniquePart = `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
  }

  return prefix ? `${prefix}-${uniquePart}` : uniquePart;
};
