/**
 * Utility for generating secure unique identifiers.
 */

export const generateSecureId = (prefix: string = ''): string => {
  // 🛡️ Sentinel: Use cryptographically secure ID generation to prevent collisions and predictability
  // Note: crypto.randomUUID() is only available in secure contexts (HTTPS/localhost).
  // We provide a fallback for insecure environments, but log a warning.
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    const uuid = crypto.randomUUID();
    // Return a shorter string (first segment) if prefix is used to match previous Math.random() length somewhat,
    // or just return full UUID. Let's return the full UUID for better uniqueness.
    return prefix ? `${prefix}-${uuid}` : uuid;
  }

  console.warn('crypto.randomUUID() is not available. Falling back to insecure Math.random() ID generation.');
  const insecureRandom = Math.random().toString(36).substring(2, 11);
  return prefix ? `${prefix}-${insecureRandom}` : insecureRandom;
};
