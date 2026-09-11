import {
  ModalForm,
  PageContainer,
  ProColumns,
  ProFormSelect,
  ProFormSwitch,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import { Button, Tag, message } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { api, Permission, Role } from '@/services/api';

const scopeOptions = [
  { label: '仅本人', value: 'self' },
  { label: '本部门', value: 'department' },
  { label: '全部', value: 'all' },
];

export default function RolesPage() {
  const actionRef = useRef<{ reload: () => void } | undefined>(undefined);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  useEffect(() => {
    api.permissions().then(setPermissions).catch((error) => message.error(error.message));
  }, []);
  const permissionOptions = permissions.map((item) => ({
    label: `${item.name}（${item.code}）`,
    value: item.code,
  }));

  const columns: ProColumns<Role>[] = [
    { title: '角色名称', dataIndex: 'name' },
    { title: '角色编码', dataIndex: 'code', copyable: true },
    {
      title: '状态',
      dataIndex: 'enabled',
      render: (_, row) => <Tag color={row.enabled ? 'green' : 'default'}>{row.enabled ? '启用' : '停用'}</Tag>,
    },
    { title: '查看范围', dataIndex: 'view_scope', valueEnum: { self: '仅本人', department: '本部门', all: '全部' } },
    { title: '修改范围', dataIndex: 'edit_scope', valueEnum: { self: '仅本人', department: '本部门', all: '全部' } },
    {
      title: '操作',
      valueType: 'option',
      render: (_, row) => row.is_system ? <Tag>系统内置</Tag> : (
        <ModalForm
          title={`修改角色：${row.name}`}
          trigger={<Button type="link">修改</Button>}
          initialValues={{
            name: row.name,
            enabled: row.enabled,
            view_scope: row.view_scope,
            edit_scope: row.edit_scope,
            permission_codes: row.permissions.map((item) => item.code),
          }}
          onFinish={async (values) => {
            await api.updateRole(row.id, values);
            message.success('角色已更新');
            actionRef.current?.reload();
            return true;
          }}
        >
          <ProFormText name="name" label="角色名称" rules={[{ required: true }]} />
          <ProFormSwitch name="enabled" label="启用" />
          <ProFormSelect name="view_scope" label="查看范围" options={scopeOptions} rules={[{ required: true }]} />
          <ProFormSelect name="edit_scope" label="修改范围" options={scopeOptions} rules={[{ required: true }]} />
          <ProFormSelect name="permission_codes" label="功能权限" mode="multiple" options={permissionOptions} />
        </ModalForm>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Role>
        rowKey="id"
        actionRef={actionRef as never}
        columns={columns}
        search={false}
        request={async () => ({ data: await api.roles(), success: true })}
        toolBarRender={() => [
          <ModalForm
            key="create"
            title="创建角色"
            trigger={<Button type="primary">创建角色</Button>}
            initialValues={{ view_scope: 'self', edit_scope: 'self', enabled: true }}
            onFinish={async (values) => {
              await api.createRole(values);
              message.success('角色已创建');
              actionRef.current?.reload();
              return true;
            }}
          >
            <ProFormText name="name" label="角色名称" rules={[{ required: true }]} />
            <ProFormText name="code" label="角色编码" rules={[{ required: true, pattern: /^[a-z][a-z0-9_]*$/ }]} />
            <ProFormSelect name="view_scope" label="查看范围" options={scopeOptions} />
            <ProFormSelect name="edit_scope" label="修改范围" options={scopeOptions} />
            <ProFormSelect name="permission_codes" label="功能权限" mode="multiple" options={permissionOptions} />
          </ModalForm>,
        ]}
      />
    </PageContainer>
  );
}
