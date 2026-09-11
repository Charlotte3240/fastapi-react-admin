export type BootstrapStatus = { initialized: boolean };
export type CurrentUser = {
  id: string;
  display_name: string;
  permissions: string[];
  is_superuser: boolean;
};
export type Permission = { id: string; code: string; name: string; module: string };
export type Role = {
  id: string;
  name: string;
  code: string;
  is_system: boolean;
  enabled: boolean;
  view_scope: string;
  edit_scope: string;
  permissions: Permission[];
};
export type Customer = {
  id: string;
  customer_type: string;
  name: string;
  phone?: string;
  email?: string;
  industry?: string;
  status?: string;
};
export type Department = { id: string; name: string; code: string; parent_id?: string; enabled: boolean };
export type Position = { id: string; name: string; code: string; enabled: boolean };
export type SystemUser = {
  id: string;
  username: string;
  display_name: string;
  department_id?: string;
  enabled: boolean;
  is_superuser: boolean;
  roles: Array<{ id: string; name: string; code: string }>;
  positions: Array<{ id: string; name: string; code: string }>;
};
export type Contact = {
  id: string;
  name: string;
  title?: string;
  phone?: string;
  email?: string;
  is_primary: boolean;
};
export type FollowUp = {
  id: string;
  contact_id?: string;
  method: string;
  content: string;
  result?: string;
  followed_at: string;
  next_follow_up_at?: string;
  voided_at?: string;
  void_reason?: string;
};
export type NotificationChannel = {
  id: string; code: string; name: string; channel_type: string; enabled: boolean;
  webhook_hint: string; has_signing_secret: boolean;
};
export type NotificationTemplate = {
  id: string; code: string; name: string; message_type: string;
  title_template?: string; body_template: string; enabled: boolean;
};
export type NotificationDelivery = {
  id: string; idempotency_key: string; status: string; attempt_count: number;
  next_attempt_at: string; last_error?: string; sent_at?: string; created_at: string;
};
export type AuditLog = {
  id: string; actor_id?: string; actor_name?: string; action: string; resource_type: string;
  resource_id?: string; changes?: Record<string, unknown>; occurred_at: string; ip_address?: string;
};
export type ServiceAccount = {
  id: string; code: string; name: string; enabled: boolean; permission_codes: string[];
  expires_at?: string; last_used_at?: string; active_key_prefixes: string[];
};
export type ServiceAccountCreated = ServiceAccount & { api_key: string };
export type OutboundConnector = {
  id: string; code: string; name: string; base_url: string; allowed_host: string;
  auth_type: string; has_credential: boolean; health_path: string;
  timeout_seconds: number; enabled: boolean;
};
export type OutboundCallLog = {
  id: string; connector_id: string; operation: string; method: string; url_path: string;
  status: string; http_status?: number; duration_ms?: number; error?: string;
  response_excerpt?: string; completed_at?: string; created_at: string;
};
export type OutboundTask = {
  id: string; connector_id: string; operation: string; method: string; url_path: string;
  idempotency_key: string; status: string; attempt_count: number; max_attempts: number;
  next_attempt_at: string; last_error?: string; last_http_status?: number;
  completed_at?: string; created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = sessionStorage.getItem('access_token');
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) throw new Error((await response.json()).detail ?? '请求失败');
  return response.json() as Promise<T>;
}

export const api = {
  bootstrapStatus: () => request<BootstrapStatus>('/system/bootstrap/status'),
  bootstrapAdmin: (body: Record<string, string>) =>
    request<{ id: string }>('/system/bootstrap/admin', { method: 'POST', body: JSON.stringify(body) }),
  login: (body: { username: string; password: string }) =>
    request<{ access_token: string }>('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => request<CurrentUser>('/auth/me'),
  permissions: () => request<Permission[]>('/system/permissions'),
  roles: () => request<Role[]>('/system/roles'),
  createRole: (body: Record<string, unknown>) =>
    request<Role>('/system/roles', { method: 'POST', body: JSON.stringify(body) }),
  updateRole: (id: string, body: Record<string, unknown>) =>
    request<Role>(`/system/roles/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  customers: (params: URLSearchParams) =>
    request<{ items: Customer[]; total: number }>(`/crm/customers?${params}`),
  createCustomer: (body: Record<string, unknown>) =>
    request<Customer>('/crm/customers', { method: 'POST', body: JSON.stringify(body) }),
  customer: (id: string) => request<Customer>(`/crm/customers/${id}`),
  departments: () => request<Department[]>('/system/departments'),
  createDepartment: (body: Record<string, unknown>) =>
    request<Department>('/system/departments', { method: 'POST', body: JSON.stringify(body) }),
  positions: () => request<Position[]>('/system/positions'),
  createPosition: (body: Record<string, unknown>) =>
    request<Position>('/system/positions', { method: 'POST', body: JSON.stringify(body) }),
  users: () => request<SystemUser[]>('/system/users'),
  createUser: (body: Record<string, unknown>) =>
    request<SystemUser>('/system/users', { method: 'POST', body: JSON.stringify(body) }),
  updateUser: (id: string, body: Record<string, unknown>) =>
    request<SystemUser>(`/system/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  contacts: (customerId: string) => request<Contact[]>(`/crm/customers/${customerId}/contacts`),
  createContact: (customerId: string, body: Record<string, unknown>) =>
    request<Contact>(`/crm/customers/${customerId}/contacts`, { method: 'POST', body: JSON.stringify(body) }),
  followUps: (customerId: string) => request<FollowUp[]>(`/crm/customers/${customerId}/follow-ups`),
  createFollowUp: (customerId: string, body: Record<string, unknown>) =>
    request<FollowUp>(`/crm/customers/${customerId}/follow-ups`, { method: 'POST', body: JSON.stringify(body) }),
  notificationChannels: () => request<NotificationChannel[]>('/system/notifications/channels'),
  createNotificationChannel: (body: Record<string, unknown>) =>
    request<NotificationChannel>('/system/notifications/channels', { method: 'POST', body: JSON.stringify(body) }),
  updateNotificationChannel: (id: string, body: Record<string, unknown>) =>
    request<NotificationChannel>(`/system/notifications/channels/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  notificationTemplates: () => request<NotificationTemplate[]>('/system/notifications/templates'),
  createNotificationTemplate: (body: Record<string, unknown>) =>
    request<NotificationTemplate>('/system/notifications/templates', { method: 'POST', body: JSON.stringify(body) }),
  updateNotificationTemplate: (id: string, body: Record<string, unknown>) =>
    request<NotificationTemplate>(`/system/notifications/templates/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  createNotificationDelivery: (body: Record<string, unknown>) =>
    request<NotificationDelivery>('/system/notifications/deliveries', { method: 'POST', body: JSON.stringify(body) }),
  notificationDeliveries: () => request<NotificationDelivery[]>('/system/notifications/deliveries'),
  retryNotificationDelivery: (id: string) =>
    request<NotificationDelivery>(`/system/notifications/deliveries/${id}/retry`, { method: 'POST' }),
  auditLogs: (params: URLSearchParams) =>
    request<{ items: AuditLog[]; total: number }>(`/system/audit-logs?${params}`),
  serviceAccounts: () => request<ServiceAccount[]>('/system/service-accounts'),
  createServiceAccount: (body: Record<string, unknown>) =>
    request<ServiceAccountCreated>('/system/service-accounts', { method: 'POST', body: JSON.stringify(body) }),
  updateServiceAccount: (id: string, body: Record<string, unknown>) =>
    request<ServiceAccount>(`/system/service-accounts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  rotateServiceAccountKey: (id: string, body: Record<string, unknown>) =>
    request<{ api_key: string; key_prefix: string }>(`/system/service-accounts/${id}/rotate-key`, { method: 'POST', body: JSON.stringify(body) }),
  outboundConnectors: () => request<OutboundConnector[]>('/system/outbound/connectors'),
  createOutboundConnector: (body: Record<string, unknown>) =>
    request<OutboundConnector>('/system/outbound/connectors', { method: 'POST', body: JSON.stringify(body) }),
  updateOutboundConnector: (id: string, body: Record<string, unknown>) =>
    request<OutboundConnector>(`/system/outbound/connectors/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  testOutboundConnector: (id: string) =>
    request<OutboundCallLog>(`/system/outbound/connectors/${id}/test`, { method: 'POST' }),
  outboundCallLogs: () => request<OutboundCallLog[]>('/system/outbound/calls'),
  outboundTasks: () => request<OutboundTask[]>('/system/outbound/tasks'),
  retryOutboundTask: (id: string) =>
    request<OutboundTask>(`/system/outbound/tasks/${id}/retry`, { method: 'POST' }),
};
