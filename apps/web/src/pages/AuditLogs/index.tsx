import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';

import { api, AuditLog } from '@/services/api';

export default function AuditLogsPage() {
  return (
    <PageContainer>
      <ProTable<AuditLog>
        rowKey="id"
        request={async (params) => {
          const query = new URLSearchParams({
            page: String(params.current ?? 1),
            page_size: String(params.pageSize ?? 20),
          });
          if (params.action) query.set('action', String(params.action));
          if (params.resource_type) query.set('resource_type', String(params.resource_type));
          const result = await api.auditLogs(query);
          return { data: result.items, total: result.total, success: true };
        }}
        columns={[
          { title: '时间', dataIndex: 'occurred_at', valueType: 'dateTime', search: false, width: 180 },
          { title: '操作人', dataIndex: 'actor_name', search: false, render: (_, row) => row.actor_name ?? '系统/匿名' },
          { title: '动作', dataIndex: 'action', copyable: true },
          { title: '资源', dataIndex: 'resource_type', render: (_, row) => <Tag>{row.resource_type}</Tag> },
          { title: '资源 ID', dataIndex: 'resource_id', search: false, copyable: true, ellipsis: true },
          { title: 'IP 地址', dataIndex: 'ip_address', search: false },
          { title: '请求', dataIndex: 'changes', search: false, render: (_, row) => row.changes ? `${row.changes.method} ${row.changes.path}` : '-' },
        ]}
      />
    </PageContainer>
  );
}
