# 生产环境安全配置

生产环境设置 `APP_ENV=production` 后，应用会拒绝占位密钥、非 HTTPS CORS 来源和通配 Host 白名单。

上线前至少配置：

```dotenv
APP_ENV=production
APP_SECRET_KEY=<独立随机密钥，至少 32 字符>
BOOTSTRAP_TOKEN=<独立的一次性随机令牌>
WEBHOOK_ENCRYPTION_KEY=<Fernet 密钥>
CORS_ORIGINS=https://erp.example.com
TRUSTED_HOSTS=erp.example.com
LOGIN_MAX_FAILURES=5
LOGIN_LOCK_MINUTES=15
MAX_REQUEST_BODY_BYTES=2097152
```

- 同一账号连续登录失败 5 次后默认锁定 15 分钟，错误信息不区分账号不存在、密码错误或账号锁定。
- API 响应默认禁止缓存，并设置 MIME 嗅探、嵌入页面、权限策略和 CSP 等安全响应头。
- HSTS 仅在生产模式返回。启用前应确认域名及其子域名长期只通过 HTTPS 提供服务。
- `TRUSTED_HOSTS` 必须填写实际域名，不能使用 `*`。
- Nginx/API 仅应通过阿里云 SLB 或受控反向代理公开，RDS 不允许公网访问。
- 反向代理需要覆盖客户端传入的转发头。只有明确受信任的代理地址才能被应用服务器配置为 forwarded-allow-ips。
