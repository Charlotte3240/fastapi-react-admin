# UniBiz

UniBiz is a modular ERP/CRM foundation for a single company. The first release
contains authentication, RBAC, organization management, a minimal CRM flow and
reliable notification delivery.

## Applications

- `apps/api`: FastAPI HTTP API and PostgreSQL worker
- `apps/web`: React + Ant Design Pro administration UI
- `deploy`: local Docker Compose and container definitions
- `docs`: architecture and product decisions

## Local development

使用根目录统一脚本（本机 PostgreSQL 连接信息从 `.env` 读取）：

```bash
./start.sh          # 迁移数据库并启动 API、Worker 和 Web
./start.sh status   # 查看状态
./start.sh logs     # 查看日志
./start.sh stop     # 停止服务
./start.sh restart  # 重启服务
```

如果默认端口已被占用，可以临时指定端口：

```bash
API_PORT=18080 WEB_PORT=18081 ./start.sh
```

启动完成后访问 `http://localhost:8001`，API 文档位于
`http://localhost:8000/docs`。运行日志及 PID 保存在被 Git 忽略的 `.run/`。

也可以使用 Docker Compose：

1. Copy `.env.example` to `.env` and replace every development secret.
2. Start PostgreSQL and the applications:

   ```bash
   docker compose -f deploy/compose.yaml up --build
   ```

3. Open `http://localhost:8000/docs` for the API and `http://localhost:8001`
   for the web application.

Database migrations run as a one-shot container before the API and worker start.
For host-based development, run them explicitly from `apps/api`:

```bash
../../.venv/bin/alembic upgrade head
```

The bootstrap endpoint is available only while the database has no users and
requires the `BOOTSTRAP_TOKEN` configured in `.env`.
