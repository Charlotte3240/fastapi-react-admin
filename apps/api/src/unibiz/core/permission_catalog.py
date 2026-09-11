from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from unibiz.models.system import Permission


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    name: str
    module: str


PERMISSION_CATALOG = (
    PermissionDefinition("system:user:view", "查看用户", "system"),
    PermissionDefinition("system:user:manage", "管理用户", "system"),
    PermissionDefinition("system:role:view", "查看角色权限", "system"),
    PermissionDefinition("system:role:manage", "管理角色权限", "system"),
    PermissionDefinition("system:dictionary:manage", "管理数据字典", "system"),
    PermissionDefinition("system:service_account:manage", "管理服务账号", "system"),
    PermissionDefinition("system:outbound_connector:manage", "管理出站连接器", "system"),
    PermissionDefinition("system:outbound_call:view", "查看出站调用记录", "system"),
    PermissionDefinition("crm:customer:view", "查看客户", "crm"),
    PermissionDefinition("crm:customer:create", "创建客户", "crm"),
    PermissionDefinition("crm:customer:update", "修改客户", "crm"),
    PermissionDefinition("crm:customer:transfer", "转移客户负责人", "crm"),
    PermissionDefinition("crm:customer:external:upsert", "外部系统写入客户", "crm"),
    PermissionDefinition("crm:contact:sensitive:view", "查看联系人敏感信息", "crm"),
    PermissionDefinition("crm:contact:sensitive:export", "导出联系人敏感信息", "crm"),
    PermissionDefinition("crm:follow_up:create", "创建跟进记录", "crm"),
    PermissionDefinition("crm:follow_up:void", "作废跟进记录", "crm"),
    PermissionDefinition("notify:channel:manage", "管理通知渠道", "notify"),
    PermissionDefinition("notify:delivery:view", "查看通知记录", "notify"),
    PermissionDefinition("audit:log:view", "查看审计日志", "audit"),
)


async def sync_permission_catalog(db: AsyncSession) -> None:
    existing = {
        permission.code: permission for permission in (await db.scalars(select(Permission))).all()
    }
    changed = False
    for definition in PERMISSION_CATALOG:
        permission = existing.get(definition.code)
        if permission:
            if permission.name != definition.name or permission.module != definition.module:
                permission.name = definition.name
                permission.module = definition.module
                changed = True
        else:
            db.add(Permission(code=definition.code, name=definition.name, module=definition.module))
            changed = True
    if changed:
        await db.commit()
