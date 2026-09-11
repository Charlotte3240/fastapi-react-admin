import { ModalForm, PageContainer, ProFormSelect, ProFormText, ProTable } from '@ant-design/pro-components';
import { Button, Modal, Switch, Tag, Typography, message } from 'antd';
import { useRef } from 'react';

import { api, ServiceAccount } from '@/services/api';

function showApiKey(apiKey: string) {
  Modal.info({
    title: '请立即保存 API Key',
    width: 680,
    content: <><Typography.Paragraph>该密钥只显示这一次，关闭后无法再次查看。</Typography.Paragraph><Typography.Paragraph copyable code>{apiKey}</Typography.Paragraph></>,
  });
}

export default function ServiceAccountsPage() {
  const actionRef = useRef<{ reload: () => void } | undefined>(undefined);
  return (
    <PageContainer>
      <ProTable<ServiceAccount>
        rowKey="id" actionRef={actionRef as never} search={false}
        request={async () => ({ data: await api.serviceAccounts(), success: true })}
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: '编码', dataIndex: 'code', copyable: true },
          { title: '权限数', render: (_, row) => row.permission_codes.length },
          { title: '有效密钥', render: (_, row) => row.active_key_prefixes.map((prefix) => <Tag key={prefix}>{prefix}…</Tag>) },
          { title: '最后调用', dataIndex: 'last_used_at', valueType: 'dateTime' },
          { title: '状态', render: (_, row) => <Switch checked={row.enabled} onChange={async (enabled) => { await api.updateServiceAccount(row.id, { enabled }); actionRef.current?.reload(); }} /> },
          { title: '操作', valueType: 'option', render: (_, row) => [
            <ModalForm key="edit" title="编辑服务账号" trigger={<a>编辑权限</a>} initialValues={{ name: row.name, permission_codes: row.permission_codes }}
              onFinish={async (values) => { await api.updateServiceAccount(row.id, values); message.success('服务账号已更新'); actionRef.current?.reload(); return true; }}>
              <ProFormText name="name" label="名称" rules={[{ required: true }]} />
              <ProFormSelect name="permission_codes" label="API 权限" mode="multiple" request={async () => (await api.permissions()).filter((item) => !item.code.startsWith('system:')).map((item) => ({ label: `${item.module} / ${item.name}`, value: item.code }))} />
            </ModalForm>,
            <a key="rotate" onClick={() => Modal.confirm({ title: '轮换 API Key？', content: '现有密钥将立即失效。', onOk: async () => { const result = await api.rotateServiceAccountKey(row.id, { revoke_existing: true }); showApiKey(result.api_key); actionRef.current?.reload(); } })}>轮换密钥</a>,
          ] },
        ]}
        toolBarRender={() => [
          <ModalForm key="create" title="创建服务账号" trigger={<Button type="primary">创建服务账号</Button>}
            onFinish={async (values) => { const result = await api.createServiceAccount(values); showApiKey(result.api_key); actionRef.current?.reload(); return true; }}>
            <ProFormText name="name" label="名称" rules={[{ required: true }]} />
            <ProFormText name="code" label="编码" rules={[{ required: true, pattern: /^[a-z][a-z0-9_]*$/ }]} />
            <ProFormSelect name="permission_codes" label="API 权限" mode="multiple" rules={[{ required: true }]}
              request={async () => (await api.permissions()).filter((item) => !item.code.startsWith('system:')).map((item) => ({ label: `${item.module} / ${item.name}`, value: item.code }))} />
          </ModalForm>,
        ]}
      />
    </PageContainer>
  );
}
