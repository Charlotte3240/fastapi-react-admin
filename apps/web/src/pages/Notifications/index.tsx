import {
  ModalForm,
  PageContainer,
  ProFormSelect,
  ProFormText,
  ProFormTextArea,
  ProTable,
} from '@ant-design/pro-components';
import { Button, Switch, Tabs, Tag, message } from 'antd';
import { useRef } from 'react';
import {
  api,
  NotificationChannel,
  NotificationDelivery,
  NotificationTemplate,
} from '@/services/api';

const statusColor: Record<string, string> = {
  pending: 'blue', sending: 'processing', sent: 'green', retry: 'orange', failed: 'red',
};

export default function NotificationsPage() {
  const channelRef = useRef<{ reload: () => void } | undefined>(undefined);
  const templateRef = useRef<{ reload: () => void } | undefined>(undefined);
  const deliveryRef = useRef<{ reload: () => void } | undefined>(undefined);
  return (
    <PageContainer>
      <Tabs items={[
        {
          key: 'channels', label: '通知渠道', children: (
            <ProTable<NotificationChannel> rowKey="id" actionRef={channelRef as never} search={false}
              request={async () => ({ data: await api.notificationChannels(), success: true })}
              columns={[
                { title: '渠道名称', dataIndex: 'name' }, { title: '编码', dataIndex: 'code' },
                { title: '类型', dataIndex: 'channel_type' }, { title: 'Webhook', dataIndex: 'webhook_hint' },
                { title: '签名', render: (_, row) => row.has_signing_secret ? <Tag color="green">已配置</Tag> : <Tag>未配置</Tag> },
                { title: '状态', render: (_, row) => <Switch checked={row.enabled} checkedChildren="启用" unCheckedChildren="停用"
                  onChange={async (enabled) => { await api.updateNotificationChannel(row.id, { enabled }); channelRef.current?.reload(); }} /> },
                { title: '操作', valueType: 'option', render: (_, row) => (
                  <ModalForm title="编辑通知渠道" trigger={<a>编辑</a>} initialValues={{ name: row.name }}
                    onFinish={async (values) => { await api.updateNotificationChannel(row.id, values); message.success('渠道已更新'); channelRef.current?.reload(); return true; }}>
                    <ProFormText name="name" label="渠道名称" rules={[{ required: true }]} />
                    <ProFormText name="webhook_url" label="新 Webhook 地址" tooltip="不填写则保留原地址" rules={[{ type: 'url' }]} />
                    <ProFormText.Password name="signing_secret" label="新签名密钥" tooltip="不填写则保留，输入空字符串可清除" />
                  </ModalForm>
                ) },
              ]}
              toolBarRender={() => [
                <ModalForm key="create" title="添加飞书 Webhook" trigger={<Button type="primary">添加渠道</Button>}
                  onFinish={async (values) => {
                    await api.createNotificationChannel(values); message.success('渠道已创建'); channelRef.current?.reload(); return true;
                  }}>
                  <ProFormText name="name" label="渠道名称" rules={[{ required: true }]} />
                  <ProFormText name="code" label="渠道编码" rules={[{ required: true, pattern: /^[a-z][a-z0-9_]*$/ }]} />
                  <ProFormText name="webhook_url" label="Webhook 地址" rules={[{ required: true, type: 'url' }]} />
                  <ProFormText.Password name="signing_secret" label="签名密钥" />
                </ModalForm>,
              ]} />
          ),
        },
        {
          key: 'templates', label: '通知模板', children: (
            <ProTable<NotificationTemplate> rowKey="id" actionRef={templateRef as never} search={false}
              request={async () => ({ data: await api.notificationTemplates(), success: true })}
              columns={[
                { title: '模板名称', dataIndex: 'name' }, { title: '编码', dataIndex: 'code' },
                { title: '消息类型', dataIndex: 'message_type' }, { title: '内容', dataIndex: 'body_template', ellipsis: true },
                { title: '状态', render: (_, row) => <Switch checked={row.enabled} checkedChildren="启用" unCheckedChildren="停用"
                  onChange={async (enabled) => { await api.updateNotificationTemplate(row.id, { enabled }); templateRef.current?.reload(); }} /> },
                { title: '操作', valueType: 'option', render: (_, row) => (
                  <ModalForm title="编辑通知模板" trigger={<a>编辑</a>} initialValues={row}
                    onFinish={async (values) => { await api.updateNotificationTemplate(row.id, values); message.success('模板已更新'); templateRef.current?.reload(); return true; }}>
                    <ProFormText name="name" label="模板名称" rules={[{ required: true }]} />
                    <ProFormText name="title_template" label="标题模板" />
                    <ProFormTextArea name="body_template" label="内容模板" tooltip="变量使用 $name 格式" rules={[{ required: true }]} />
                  </ModalForm>
                ) },
              ]}
              toolBarRender={() => [
                <ModalForm key="create" title="创建通知模板" trigger={<Button type="primary">创建模板</Button>}
                  initialValues={{ message_type: 'text' }} onFinish={async (values) => {
                    await api.createNotificationTemplate(values); message.success('模板已创建'); templateRef.current?.reload(); return true;
                  }}>
                  <ProFormText name="name" label="模板名称" rules={[{ required: true }]} />
                  <ProFormText name="code" label="模板编码" rules={[{ required: true, pattern: /^[a-z][a-z0-9_]*$/ }]} />
                  <ProFormSelect name="message_type" label="消息类型" options={[{ label: '纯文本', value: 'text' }, { label: '富文本', value: 'post' }]} />
                  <ProFormText name="title_template" label="标题模板" />
                  <ProFormText name="body_template" label="内容模板" tooltip="变量使用 $name 格式" rules={[{ required: true }]} />
                </ModalForm>,
              ]} />
          ),
        },
        {
          key: 'deliveries', label: '发送记录', children: (
            <ProTable<NotificationDelivery> rowKey="id" actionRef={deliveryRef as never} search={false}
              request={async () => ({ data: await api.notificationDeliveries(), success: true })}
              columns={[
                { title: '幂等键', dataIndex: 'idempotency_key', copyable: true },
                { title: '状态', render: (_, row) => <Tag color={statusColor[row.status]}>{row.status}</Tag> },
                { title: '尝试次数', dataIndex: 'attempt_count' },
                { title: '创建时间', dataIndex: 'created_at', valueType: 'dateTime' },
                { title: '错误', dataIndex: 'last_error', ellipsis: true },
                { title: '操作', valueType: 'option', render: (_, row) => ['failed', 'retry'].includes(row.status) ? (
                  <a onClick={async () => { await api.retryNotificationDelivery(row.id); message.success('已加入重试队列'); deliveryRef.current?.reload(); }}>重试</a>
                ) : '-' },
              ]}
              toolBarRender={() => [
                <ModalForm key="test" title="发送测试通知" trigger={<Button type="primary">测试发送</Button>}
                  onFinish={async (values) => {
                    let variables: Record<string, string> = {};
                    try { variables = values.variables_json ? JSON.parse(values.variables_json) : {}; }
                    catch { message.error('变量必须是合法 JSON'); return false; }
                    await api.createNotificationDelivery({
                      channel_code: values.channel_code,
                      template_code: values.template_code,
                      variables,
                      idempotency_key: `manual-${Date.now()}-${crypto.randomUUID()}`,
                    });
                    message.success('已加入发送队列'); deliveryRef.current?.reload(); return true;
                  }}>
                  <ProFormSelect name="channel_code" label="通知渠道" rules={[{ required: true }]}
                    request={async () => (await api.notificationChannels()).filter((item) => item.enabled).map((item) => ({ label: item.name, value: item.code }))} />
                  <ProFormSelect name="template_code" label="通知模板" rules={[{ required: true }]}
                    request={async () => (await api.notificationTemplates()).filter((item) => item.enabled).map((item) => ({ label: item.name, value: item.code }))} />
                  <ProFormTextArea name="variables_json" label="模板变量（JSON）" initialValue={'{\n  "name": "测试用户"\n}'} />
                </ModalForm>,
              ]} />
          ),
        },
      ]} />
    </PageContainer>
  );
}
