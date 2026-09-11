import {
  ModalForm,
  PageContainer,
  ProColumns,
  ProFormSelect,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import { Button, Switch, Tabs, Tag, message } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { api, Department, Position, Role, SystemUser } from '@/services/api';

export default function OrganizationPage() {
  const userRef = useRef<{ reload: () => void } | undefined>(undefined);
  const departmentRef = useRef<{ reload: () => void } | undefined>(undefined);
  const positionRef = useRef<{ reload: () => void } | undefined>(undefined);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);

  const refreshOptions = async () => {
    const [departmentItems, positionItems, roleItems] = await Promise.all([
      api.departments(), api.positions(), api.roles(),
    ]);
    setDepartments(departmentItems.filter((item) => item.enabled));
    setPositions(positionItems.filter((item) => item.enabled));
    setRoles(roleItems.filter((item) => item.enabled && !item.is_system));
  };
  useEffect(() => { refreshOptions().catch((error) => message.error(error.message)); }, []);

  const userColumns: ProColumns<SystemUser>[] = [
    { title: '姓名', dataIndex: 'display_name' },
    { title: '账号', dataIndex: 'username' },
    { title: '部门', render: (_, row) => departments.find((item) => item.id === row.department_id)?.name ?? '-' },
    { title: '角色', render: (_, row) => row.roles.map((role) => <Tag key={role.id}>{role.name}</Tag>) },
    { title: '岗位', render: (_, row) => row.positions.map((position) => <Tag key={position.id}>{position.name}</Tag>) },
    {
      title: '状态',
      render: (_, row) => row.is_superuser ? <Tag color="gold">超级管理员</Tag> : (
        <Switch checked={row.enabled} onChange={async (enabled) => {
          await api.updateUser(row.id, { enabled });
          userRef.current?.reload();
        }} />
      ),
    },
  ];

  const departmentColumns: ProColumns<Department>[] = [
    { title: '部门名称', dataIndex: 'name' },
    { title: '编码', dataIndex: 'code' },
    { title: '上级部门', render: (_, row) => departments.find((item) => item.id === row.parent_id)?.name ?? '-' },
  ];
  const positionColumns: ProColumns<Position>[] = [
    { title: '岗位名称', dataIndex: 'name' },
    { title: '编码', dataIndex: 'code' },
  ];

  return (
    <PageContainer>
      <Tabs items={[
        {
          key: 'users', label: '用户', children: (
            <ProTable<SystemUser>
              rowKey="id" actionRef={userRef as never} columns={userColumns} search={false}
              request={async () => ({ data: await api.users(), success: true })}
              toolBarRender={() => [
                <ModalForm key="create" title="创建用户" trigger={<Button type="primary">创建用户</Button>}
                  onFinish={async (values) => {
                    await api.createUser(values); message.success('用户已创建'); userRef.current?.reload(); return true;
                  }}>
                  <ProFormText name="display_name" label="姓名" rules={[{ required: true }]} />
                  <ProFormText name="username" label="账号" rules={[{ required: true }]} />
                  <ProFormText.Password name="password" label="初始密码" rules={[{ required: true, min: 12 }]} />
                  <ProFormSelect name="department_id" label="部门" options={departments.map((item) => ({ label: item.name, value: item.id }))} />
                  <ProFormSelect name="position_ids" label="岗位" mode="multiple" options={positions.map((item) => ({ label: item.name, value: item.id }))} />
                  <ProFormSelect name="role_ids" label="角色" mode="multiple" options={roles.map((item) => ({ label: item.name, value: item.id }))} />
                </ModalForm>,
              ]} />
          ),
        },
        {
          key: 'departments', label: '部门', children: (
            <ProTable<Department> rowKey="id" actionRef={departmentRef as never} columns={departmentColumns} search={false}
              request={async () => ({ data: await api.departments(), success: true })}
              toolBarRender={() => [
                <ModalForm key="create" title="创建部门" trigger={<Button type="primary">创建部门</Button>}
                  onFinish={async (values) => {
                    await api.createDepartment(values); message.success('部门已创建'); await refreshOptions(); departmentRef.current?.reload(); return true;
                  }}>
                  <ProFormText name="name" label="部门名称" rules={[{ required: true }]} />
                  <ProFormText name="code" label="部门编码" rules={[{ required: true }]} />
                  <ProFormSelect name="parent_id" label="上级部门" options={departments.map((item) => ({ label: item.name, value: item.id }))} />
                </ModalForm>,
              ]} />
          ),
        },
        {
          key: 'positions', label: '岗位', children: (
            <ProTable<Position> rowKey="id" actionRef={positionRef as never} columns={positionColumns} search={false}
              request={async () => ({ data: await api.positions(), success: true })}
              toolBarRender={() => [
                <ModalForm key="create" title="创建岗位" trigger={<Button type="primary">创建岗位</Button>}
                  onFinish={async (values) => {
                    await api.createPosition(values); message.success('岗位已创建'); await refreshOptions(); positionRef.current?.reload(); return true;
                  }}>
                  <ProFormText name="name" label="岗位名称" rules={[{ required: true }]} />
                  <ProFormText name="code" label="岗位编码" rules={[{ required: true }]} />
                </ModalForm>,
              ]} />
          ),
        },
      ]} />
    </PageContainer>
  );
}

