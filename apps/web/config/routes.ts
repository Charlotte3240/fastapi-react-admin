export default [
  { path: '/login', layout: false, component: '@/pages/Login' },
  { path: '/bootstrap', layout: false, component: '@/pages/Bootstrap' },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: '工作台', icon: 'DashboardOutlined', component: '@/pages/Dashboard' },
  {
    path: '/crm',
    name: '客户管理',
    icon: 'TeamOutlined',
    access: 'canViewCustomers',
    routes: [
      { path: '/crm/customers', name: '客户', component: '@/pages/Customers' },
      { path: '/crm/customers/:id', name: '客户详情', component: '@/pages/CustomerDetail', hideInMenu: true },
    ],
  },
  {
    path: '/system',
    name: '系统管理',
    icon: 'SettingOutlined',
    access: 'canManageSystem',
    routes: [
      { path: '/system/organization', name: '组织用户', component: '@/pages/Organization' },
      { path: '/system/roles', name: '角色权限', component: '@/pages/Roles' },
      { path: '/system/notifications', name: '通知中心', component: '@/pages/Notifications' },
      { path: '/system/audit-logs', name: '审计日志', access: 'canViewAudit', component: '@/pages/AuditLogs' },
      { path: '/system/service-accounts', name: '服务账号', access: 'canManageServiceAccounts', component: '@/pages/ServiceAccounts' },
      { path: '/system/outbound', name: '出站连接器', access: 'canManageOutbound', component: '@/pages/Outbound' },
    ],
  },
  { path: '*', component: '@/pages/404' },
];
