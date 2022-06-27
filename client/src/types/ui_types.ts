export type BootstrapVariant = | 'primary'
  | 'secondary'
  | 'success'
  | 'danger'
  | 'warning'
  | 'info'
  | 'dark'
  | 'light';

export type BootstrapButtonVariant = BootstrapVariant
  | 'link'
  | 'outline-primary'
  | 'outline-secondary'
  | 'outline-success'
  | 'outline-danger'
  | 'outline-warning'
  | 'outline-info'
  | 'outline-light'
  | 'outline-dark';

export type BootstrapModalSize = | 'sm'
  | 'lg'
  | 'xl';

export interface TableColumnInfo {
  name: string,
  ordering: string;
  textAlign?: 'text-left' | 'text-center' | 'text-right';
}
