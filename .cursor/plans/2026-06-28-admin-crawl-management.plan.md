# Admin 采集管理页：公众号 CRUD + 环境配置

Planned-with: composer-2.5-fast

## 目标

- FR-1: `/admin/manage` 管理试点公众号（对齐 `pilot_wechat_accounts.csv`）
- FR-2: 公众号增删改查 + 导出 CSV
- FR-3: 可视化编辑 `.env` 配置项（分组展示，Token 脱敏）
- FR-4: 阅读台顶栏入口「采集管理」

## 实现

| 模块 | 路径 |
|------|------|
| 页面 | `wechat_collector/api/static/admin-manage.html` |
| API | `GET/POST/PUT/DELETE /admin/pilot-accounts` |
| 导出 | `GET /admin/pilot-accounts/export.csv` |
| 配置 | `GET/PUT /admin/settings` |
| Service | `org_service.list_pilot_accounts` 等 |
| Service | `settings_service` 读写 `.env` |

## 说明

- 删除为软删除（account/org status=inactive）
- 配置保存写入项目根 `.env`，需重启 Worker/API 进程生效
- API Token 留空或含 `•` 时不覆盖

## Todos

- [x] org_service 试点账号 CRUD
- [x] settings_service + admin API
- [x] admin-manage.html UI
- [x] 单测 test_admin_manage.py
