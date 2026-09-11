import { ModalForm, PageContainer, ProFormDigit, ProFormSelect, ProFormText, ProTable } from '@ant-design/pro-components';
import { Button, Switch, Tabs, Tag, message } from 'antd';
import { useRef } from 'react';

import { api, OutboundCallLog, OutboundConnector, OutboundTask } from '@/services/api';

export default function OutboundPage() {
  const connectorRef = useRef<{ reload: () => void } | undefined>(undefined);
  const logRef = useRef<{ reload: () => void } | undefined>(undefined);
  const taskRef = useRef<{ reload: () => void } | undefined>(undefined);
  return (
    <PageContainer>
      <Tabs items={[
        { key: 'connectors', label: '连接器', children: (
          <ProTable<OutboundConnector> rowKey="id" actionRef={connectorRef as never} search={false}
            request={async () => ({ data: await api.outboundConnectors(), success: true })}
            columns={[
              { title: '名称', dataIndex: 'name' }, { title: '编码', dataIndex: 'code' },
              { title: '目标域名', dataIndex: 'allowed_host' }, { title: '认证', dataIndex: 'auth_type' },
              { title: '超时', render: (_, row) => `${row.timeout_seconds}s` },
              { title: '状态', render: (_, row) => <Switch checked={row.enabled} onChange={async (enabled) => { await api.updateOutboundConnector(row.id, { enabled }); connectorRef.current?.reload(); }} /> },
              { title: '操作', valueType: 'option', render: (_, row) => <a onClick={async () => { const result = await api.testOutboundConnector(row.id); result.status === 'success' ? message.success(`连接成功（${result.http_status}，${result.duration_ms}ms）`) : message.error(result.error ?? '连接失败'); logRef.current?.reload(); }}>测试连接</a> },
            ]}
            toolBarRender={() => [
              <ModalForm key="create" title="创建出站连接器" trigger={<Button type="primary">创建连接器</Button>}
                initialValues={{ auth_type: 'none', health_path: '/', timeout_seconds: 10 }}
                onFinish={async (values) => { await api.createOutboundConnector(values); message.success('连接器已创建'); connectorRef.current?.reload(); return true; }}>
                <ProFormText name="name" label="名称" rules={[{ required: true }]} />
                <ProFormText name="code" label="编码" rules={[{ required: true, pattern: /^[a-z][a-z0-9_]*$/ }]} />
                <ProFormText name="base_url" label="Base URL" tooltip="仅允许公网 HTTPS 443 地址" rules={[{ required: true, type: 'url' }]} />
                <ProFormSelect name="auth_type" label="认证方式" options={[{ label: '无认证', value: 'none' }, { label: 'Bearer Token', value: 'bearer' }, { label: 'API Key 请求头', value: 'api_key_header' }]} />
                <ProFormText.Password name="credential" label="Token / API Key" />
                <ProFormText name="api_key_header" label="API Key 请求头" initialValue="X-API-Key" />
                <ProFormText name="health_path" label="健康检查路径" rules={[{ required: true, pattern: /^\// }]} />
                <ProFormDigit name="timeout_seconds" label="超时秒数" min={1} max={30} />
              </ModalForm>,
            ]} />
        ) },
        { key: 'tasks', label: '出站任务', children: (
          <ProTable<OutboundTask> rowKey="id" actionRef={taskRef as never} search={false}
            request={async () => ({ data: await api.outboundTasks(), success: true })}
            columns={[
              { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime' },
              { title: '业务操作', dataIndex: 'operation' }, { title: '方法', dataIndex: 'method' },
              { title: '路径', dataIndex: 'url_path', ellipsis: true },
              { title: '幂等键', dataIndex: 'idempotency_key', copyable: true, ellipsis: true },
              { title: '状态', render: (_, row) => <Tag color={row.status === 'succeeded' ? 'green' : row.status === 'failed' ? 'red' : 'orange'}>{row.status}</Tag> },
              { title: '尝试', render: (_, row) => `${row.attempt_count}/${row.max_attempts}` },
              { title: 'HTTP', dataIndex: 'last_http_status' },
              { title: '错误', dataIndex: 'last_error', ellipsis: true },
              { title: '操作', valueType: 'option', render: (_, row) => ['failed', 'retry'].includes(row.status) ? <a onClick={async () => { await api.retryOutboundTask(row.id); message.success('已加入重试队列'); taskRef.current?.reload(); }}>重试</a> : '-' },
            ]} />
        ) },
        { key: 'logs', label: '调用记录', children: (
          <ProTable<OutboundCallLog> rowKey="id" actionRef={logRef as never} search={false}
            request={async () => ({ data: await api.outboundCallLogs(), success: true })}
            columns={[
              { title: '时间', dataIndex: 'created_at', valueType: 'dateTime' },
              { title: '操作', dataIndex: 'operation' }, { title: '方法', dataIndex: 'method' },
              { title: '路径', dataIndex: 'url_path' },
              { title: '状态', render: (_, row) => <Tag color={row.status === 'success' ? 'green' : 'red'}>{row.status}</Tag> },
              { title: 'HTTP', dataIndex: 'http_status' }, { title: '耗时(ms)', dataIndex: 'duration_ms' },
              { title: '错误', dataIndex: 'error', ellipsis: true },
            ]} />
        ) },
      ]} />
    </PageContainer>
  );
}
