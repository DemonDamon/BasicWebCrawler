from fastapi import FastAPI

from wechat_collector.api.routers import admin, articles, candidates, coverage, discovery, health, monitoring, tasks

app = FastAPI(
    title="WeChat Org Collector API",
    description="微信公众号 3000+ 组织定向采集服务",
    version="0.1.0",
)

app.include_router(articles.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(coverage.router, prefix="/api")
app.include_router(discovery.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(admin.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
