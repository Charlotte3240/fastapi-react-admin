import { LoginFormPage, ProFormText } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { message } from 'antd';
import { api } from '@/services/api';

export default function BootstrapPage() {
  return (
    <LoginFormPage
      title="初始化 UniBiz"
      subTitle="创建系统的首位超级管理员"
      submitter={{ searchConfig: { submitText: '完成初始化' } }}
      onFinish={async (values) => {
        try {
          await api.bootstrapAdmin(values as Record<string, string>);
          message.success('初始化完成，请登录');
          history.replace('/login');
          return true;
        } catch (error) {
          message.error((error as Error).message);
          return false;
        }
      }}
    >
      <ProFormText.Password name="bootstrap_token" label="初始化密钥" rules={[{ required: true }]} />
      <ProFormText name="username" label="管理员账号" rules={[{ required: true, min: 3 }]} />
      <ProFormText name="display_name" label="显示名称" rules={[{ required: true }]} />
      <ProFormText.Password name="password" label="密码" rules={[{ required: true, min: 12 }]} />
    </LoginFormPage>
  );
}

