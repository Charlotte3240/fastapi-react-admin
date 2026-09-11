import {
  ModalForm,
  PageContainer,
  ProDescriptions,
  ProFormDateTimePicker,
  ProFormSelect,
  ProFormSwitch,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import { useParams } from '@umijs/max';
import { Button, Tabs, Tag, message } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { api, Contact, Customer, FollowUp } from '@/services/api';

export default function CustomerDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const contactRef = useRef<{ reload: () => void } | undefined>(undefined);
  const followRef = useRef<{ reload: () => void } | undefined>(undefined);
  const [customer, setCustomer] = useState<Customer>();
  const [contacts, setContacts] = useState<Contact[]>([]);
  useEffect(() => {
    api.customer(id).then(setCustomer).catch((error) => message.error(error.message));
    api.contacts(id).then(setContacts).catch(() => undefined);
  }, [id]);

  return (
    <PageContainer title={customer?.name ?? '客户详情'}>
      <ProDescriptions dataSource={customer} columns={[
        { title: '客户类型', dataIndex: 'customer_type', valueEnum: { organization: '企业', individual: '个人' } },
        { title: '行业', dataIndex: 'industry' },
        { title: '手机号', dataIndex: 'phone' },
        { title: '邮箱', dataIndex: 'email' },
        { title: '状态', dataIndex: 'status' },
      ]} />
      <Tabs items={[
        {
          key: 'contacts', label: '联系人', children: (
            <ProTable<Contact> rowKey="id" actionRef={contactRef as never} search={false}
              request={async () => { const data = await api.contacts(id); setContacts(data); return { data, success: true }; }}
              columns={[
                { title: '姓名', dataIndex: 'name' }, { title: '职位', dataIndex: 'title' },
                { title: '手机号', dataIndex: 'phone' }, { title: '邮箱', dataIndex: 'email' },
                { title: '主联系人', render: (_, row) => row.is_primary ? <Tag color="blue">是</Tag> : '-' },
              ]}
              toolBarRender={() => [
                <ModalForm key="create" title="添加联系人" trigger={<Button type="primary">添加联系人</Button>}
                  onFinish={async (values) => {
                    await api.createContact(id, values); message.success('联系人已添加'); contactRef.current?.reload(); return true;
                  }}>
                  <ProFormText name="name" label="姓名" rules={[{ required: true }]} />
                  <ProFormText name="title" label="职位" /><ProFormText name="phone" label="手机号" />
                  <ProFormText name="email" label="邮箱" /><ProFormSwitch name="is_primary" label="设为主联系人" />
                </ModalForm>,
              ]} />
          ),
        },
        {
          key: 'follow-ups', label: '跟进记录', children: (
            <ProTable<FollowUp> rowKey="id" actionRef={followRef as never} search={false}
              request={async () => ({ data: await api.followUps(id), success: true })}
              columns={[
                { title: '方式', dataIndex: 'method' }, { title: '内容', dataIndex: 'content' },
                { title: '结果', dataIndex: 'result' }, { title: '跟进时间', dataIndex: 'followed_at', valueType: 'dateTime' },
                { title: '状态', render: (_, row) => row.voided_at ? <Tag color="red">已作废</Tag> : <Tag color="green">有效</Tag> },
              ]}
              toolBarRender={() => [
                <ModalForm key="create" title="添加跟进记录" trigger={<Button type="primary">添加跟进</Button>}
                  onFinish={async (values) => {
                    const followedAt = values.followed_at as { toISOString?: () => string } | undefined;
                    await api.createFollowUp(id, { ...values, followed_at: followedAt?.toISOString?.() ?? values.followed_at });
                    message.success('跟进记录已添加'); followRef.current?.reload(); return true;
                  }}>
                  <ProFormSelect name="contact_id" label="联系人" options={contacts.map((item) => ({ label: item.name, value: item.id }))} />
                  <ProFormSelect name="method" label="跟进方式" options={['phone', 'wechat', 'email', 'meeting', 'visit', 'other'].map((value) => ({ label: value, value }))} rules={[{ required: true }]} />
                  <ProFormText name="content" label="跟进内容" rules={[{ required: true }]} />
                  <ProFormText name="result" label="跟进结果" />
                  <ProFormDateTimePicker name="followed_at" label="跟进时间" rules={[{ required: true }]} />
                </ModalForm>,
              ]} />
          ),
        },
      ]} />
    </PageContainer>
  );
}

