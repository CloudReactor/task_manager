export const getSeverityBadgeClass = (severity: string): string => {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'badge badge-danger';
    case 'error':
      return 'badge badge-danger';
    case 'warning':
      return 'badge badge-warning';
    case 'info':
      return 'badge badge-info';
    case 'debug':
      return 'badge badge-secondary';
    case 'trace':
      return 'badge badge-light';
    default:
      return 'badge badge-secondary';
  }
};
