/**
 * Extract a human-readable error message from an Axios error.
 */
export function getErrorMessage(error) {
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg || d.message || JSON.stringify(d)).join('; ');
    }
    return JSON.stringify(detail);
  }
  if (error.message) return error.message;
  return 'An unexpected error occurred.';
}

/**
 * Format a datetime string to a readable format.
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Basic email validation.
 */
export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
