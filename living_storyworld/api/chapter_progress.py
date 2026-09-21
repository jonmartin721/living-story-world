import asyncio
import time


class ChapterProgress:
    """Keep the latest update so disconnected readers can resume independently."""

    def __init__(self, slug: str, job_id: str):
        self.slug = slug
        self.job_id = job_id
        self.latest: dict = {"stage": "init", "percent": 0, "message": "Starting..."}
        self.version = 1
        self.finished_at: float | None = None
        self.changed = asyncio.Condition()

    async def put(self, update: dict) -> None:
        async with self.changed:
            if self.finished_at is not None:
                return
            self.latest = update
            self.version += 1
            if update["stage"] in {"complete", "error"}:
                self.finished_at = time.monotonic()
            self.changed.notify_all()

    def snapshot(self) -> dict:
        stage = self.latest["stage"]
        return {
            "job_id": self.job_id,
            "status": stage if stage in {"complete", "error"} else "running",
            "progress": self.latest if self.finished_at is None else None,
            "chapter": self.latest.get("chapter"),
            "error": self.latest.get("error"),
        }

    async def updates(self):
        version = 0
        while True:
            async with self.changed:
                try:
                    await asyncio.wait_for(self.changed.wait_for(lambda: version != self.version), 15)
                except asyncio.TimeoutError:
                    update = None
                else:
                    version = self.version
                    update = self.latest
            yield update
            if update is not None and update["stage"] in {"complete", "error"}:
                return
