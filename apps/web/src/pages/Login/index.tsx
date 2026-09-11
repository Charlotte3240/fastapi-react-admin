import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormText } from '@ant-design/pro-components';
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
    <LoginForm
      title="UniBiz"
      subTitle="企业业务管理平台"
      // LoginForm 的容器默认是 flex 纵向布局且不带垂直居中，需显式居中，
      // 否则表单会贴在页面顶部（水平居中由 .ant-pro-form-login-main 的 margin:0 auto 保证）。
      containerStyle={{ justifyContent: 'center' }}
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
    </LoginForm>
  );
}
