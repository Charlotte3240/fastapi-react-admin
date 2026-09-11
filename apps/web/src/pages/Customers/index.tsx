import {
  ModalForm,
  PageContainer,
  ProColumns,
  ProFormSelect,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import { Button, message } from 'antd';
import { history } from '@umijs/max';
import { useRef } from 'react';
import { api, Customer } from '@/services/api';

export default function Customers() {
  const actionRef = useRef<{ reload: () => void } | undefined>(undefined);
  const columns: ProColumns<Customer>[] = [
    { title: '客户名称', dataIndex: 'name' },
    { title: '类型', dataIndex: 'customer_type', valueEnum: { organization: '企业', individual: '个人' } },
    { title: '行业', dataIndex: 'industry' },
    { title: '手机号', dataIndex: 'phone', search: false },
    { title: '邮箱', dataIndex: 'email', search: false },
    { title: '状态', dataIndex: 'status' },
    { title: '操作', valueType: 'option', render: (_, row) => <a onClick={() => history.push(`/crm/customers/${row.id}`)}>查看详情</a> },
  ];
  return (
    <PageContainer>
      <ProTable<Customer>
        rowKey="id"
        actionRef={actionRef as never}
        columns={columns}
        request={async (params) => {
          const query = new URLSearchParams({
            page: String(params.current ?? 1),
            page_size: String(params.pageSize ?? 20),
          });
          if (params.name) query.set('keyword', String(params.name));
          const result = await api.customers(query);
          return { data: result.items, total: result.total, success: true };
        }}
        toolBarRender={() => [
          <ModalForm
            key="create"
            title="创建客户"
            trigger={<Button type="primary">创建客户</Button>}
            initialValues={{ customer_type: 'organization' }}
            onFinish={async (values) => {
              await api.createCustomer(values);
              message.success('客户已创建');
              actionRef.current?.reload();
              return true;
            }}
          >
            <ProFormSelect name="customer_type" label="客户类型" options={[{ label: '企业', value: 'organization' }, { label: '个人', value: 'individual' }]} rules={[{ required: true }]} />
            <ProFormText name="name" label="客户名称" rules={[{ required: true }]} />
            <ProFormText name="industry" label="行业" />
            <ProFormText name="phone" label="手机号" />
            <ProFormText name="email" label="邮箱" />
            <ProFormText name="status" label="状态" />
          </ModalForm>,
        ]}
      />
    </PageContainer>
  );
}
