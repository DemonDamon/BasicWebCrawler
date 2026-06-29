# P1 项目骨架 + DB 迁移

Plan-Id: 2026-06-25-wc-p1-skeleton-db
Planned-with: claude-opus-4.8
父 Plan: 2026-06-25-wechat-org-collector-master
依赖: 无（DAG 根节点）
阶段: 一 | 难度: ⭐

## 目标
搭起 `wechat_collector/` Python 包骨架、配置、数据库连接与迁移基础，让后续模块有统一落点。

## 交付物
- 目录结构：
  ```
  wechat_collector/
    __init__.py
    config.py            # pydantic-settings，读 .env（DB_URL/API_TOKEN 等）
    db/
      __init__.py
      base.py            # SQLAlchemy engine/session
      models.py          # 五张表 ORM（organizations/wechat_accounts/article_candidates/articles/account_health）
    migrations/          # Alembic
    parsers/
      wechat.json        # 解析器选择器配置（P5 填充）
  extension/             # Chrome 插件骨架（P6 填充）
  ```
- `requirements-collector.txt`：fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, pydantic-settings, pytest。
- `.env.example`：`COLLECTOR_DB_URL`, `COLLECTOR_API_TOKEN`, `COLLECTOR_DB_URL` 支持 sqlite 兜底。
- Alembic 初始迁移：建好方案 §5 的五张表 + 索引（org_code unique、url unique、normalized_url、content_hash、account_id 外键索引）。

## 步骤
1. 建包与 `config.py`（环境变量 + sqlite/pg 切换）。
2. 用 SQLAlchemy 定义五张表 ORM（字段对齐方案 5.1–5.5）。
3. `alembic init`，生成首版迁移，本地 sqlite 跑通 `upgrade head`。
4. README 增补「采集系统」一节（安装/迁移/启动）。

## 验收
- [x] `alembic upgrade head` 在 sqlite 成功建表
- [x] `python -c "from wechat_collector.db import models"` 无错
- [x] `pytest tests/test_collector_models.py` 通过
- [ ] PostgreSQL 环境验证（需本地 PG 实例，迁移脚本已兼容）

## 完成提交
`/commit @wechat_collector --spec=.cursor/plans/2026-06-25-wc-p1-skeleton-db.plan.md`
