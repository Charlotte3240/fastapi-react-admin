export type CurrentUser = {
  id: string;
  displayName: string;
  permissions: string[];
  isSuperuser: boolean;
};

export default function access(initialState?: { currentUser?: CurrentUser }) {
  const user = initialState?.currentUser;
  const has = (code: string) => Boolean(user?.isSuperuser || user?.permissions.includes(code));
  return {
    hasPermission: has,
    canViewCustomers: has('crm:customer:view'),
    canManageSystem: has('system:role:view') || has('system:user:view') || has('audit:log:view') || has('system:service_account:manage') || has('system:outbound_connector:manage'),
    canViewAudit: has('audit:log:view'),
    canManageServiceAccounts: has('system:service_account:manage'),
    canManageOutbound: has('system:outbound_connector:manage'),
  };
}
