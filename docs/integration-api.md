# UniBiz 系统集成 API

## 认证

在“系统管理 → 服务账号”创建账号并授予所需权限。API Key 只显示一次，调用时通过请求头传递：

```http
X-API-Key: ubk_xxxxxxxx_xxxxxxxxxxxxxxxxx
Content-Type: application/json
```

不要把 API Key 放在 URL、前端代码或日志中。生产环境必须使用 HTTPS。

## 按外部标识写入客户

```http
PUT /api/v1/integrations/crm/customers/{source_system}/{external_id}
```

所需权限：`crm:customer:external:upsert`。

同一个 `source_system + external_id` 第一次调用创建客户，之后调用更新同一客户，不会产生重复数据。`owner_id` 必须是启用状态的内部人员账号。

```json
{
  "customer_type": "organization",
  "name": "示例科技有限公司",
  "owner_id": "内部用户 UUID",
  "credit_code": "91310000XXXXXXXXXX",
  "industry": "软件和信息技术服务业",
  "phone": "021-12345678",
  "status": "active",
  "extra_data": {
    "source_status": "normal"
  }
}
```

响应中的 `created` 表示本次是创建还是更新。

## 按外部标识查询客户

```http
GET /api/v1/integrations/crm/customers/{source_system}/{external_id}
```

所需权限：`crm:customer:view`。联系人敏感信息是否脱敏仍由 `crm:contact:sensitive:view` 控制。

## 状态码

- `200`：查询或幂等写入成功
- `401`：API Key 无效、过期或已撤销
- `403`：服务账号缺少权限
- `404`：外部客户不存在
- `422`：参数或内部负责人无效

错误响应会包含稳定的 `code`、可读的 `message`、兼容字段 `detail` 和用于排查日志的 `request_id`。响应头也会返回同一个 `X-Request-ID`，调用方可以主动传入该请求头。
