import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginFormPage, ProFormText } from '@ant-design/pro-components';
import { history } from '@umijs/max';
import { message } from 'antd';
import { useEffect } from 'react';
import { api } from '@/services/api';

export default function LoginPage() {
  useEffect(() => {
    api.bootstrapStatus().then(({ initialized }) => {
      if (!initialized) history.replace('/bootstrap');
    });
  }, []);

  return (
    <LoginFormPage
      title="UniBiz"
      subTitle="企业业务管理平台"
      onFinish={async (values) => {
        try {
          const result = await api.login(values as { username: string; password: string });
          sessionStorage.setItem('access_token', result.access_token);
          window.location.assign('/dashboard');
          return true;
        } catch (error) {
          message.error((error as Error).message);
          return false;
        }
      }}
    >
      <ProFormText name="username" placeholder="账号" fieldProps={{ prefix: <UserOutlined /> }} rules={[{ required: true }]} />
      <ProFormText.Password name="password" placeholder="密码" fieldProps={{ prefix: <LockOutlined /> }} rules={[{ required: true }]} />
    </LoginFormPage>
  );
}
