// Format file size
export const formatFileSize = (bytes?: number): string => {
  if (!bytes) return 'Unknown size';
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(2)} MB`;
};

// Format date
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
};

// Get status icon
export const getStatusIcon = (status: string): string => {
  switch (status) {
    case 'completed': return '✅';
    case 'failed': return '❌';
    case 'processing': return '⏳';
    case 'queued': return '⏸️';
    default: return '❓';
  }
};

// Get status color
export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'completed': return '#4caf50';
    case 'failed': return '#f44336';
    case 'processing': return '#ff9800';
    case 'queued': return '#2196f3';
    default: return '#9e9e9e';
  }
};
