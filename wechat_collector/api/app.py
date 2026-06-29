from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wechat_collector.api.routers import accounts, admin, articles, candidates, coverage, discovery, health, monitoring, tasks

app = FastAPI(
    title="WeChat Org Collector API",
    description="微信公众号 3000+ 组织定向采集服务",
    version="0.1.0",
)

# 本地开发：允许 admin 页面与插件调试时的跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(coverage.router, prefix="/api")
app.include_router(discovery.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(admin.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
