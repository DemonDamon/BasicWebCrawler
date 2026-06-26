"""wechat_collector.worker 包入口。

    python -m wechat_collector.worker
"""

from wechat_collector.worker.fetch_worker import main

if __name__ == "__main__":
    raise SystemExit(main())
