from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from markdown_webscraper import ScraperConfig, WebsiteScraper

from .config import MCPServerConfig

FETCHING_STATUS = "fetching website and converting to markdown in progress!"
COMPLETED_STATUS = "fetch completed and markdown saved!"
TIMED_OUT_STATUS = "fetching timed out!"
FAILED_STATUS = "failed to fetch!"


def make_response(*, status: str, operation: str) -> dict[str, str]:
    return {"status": status, "operation": operation}


@dataclass
class JobRecord:
    operation: str
    status: str
    error: str | None = None


@dataclass
class JobRequest:
    mode: str
    url: str
    dir_path: str
    record: JobRecord
    notify: Callable[[dict[str, str]], Awaitable[None]]


@dataclass
class SessionState:
    queue: asyncio.Queue[JobRequest]
    worker_task: asyncio.Task[None] | None
    worker_executor: ThreadPoolExecutor
    jobs_by_mode_url_dir: dict[tuple[str, str, str], JobRecord]
    latest_by_url_dir: dict[tuple[str, str], JobRecord]


class ScrapeJobService:
    def __init__(self, config: MCPServerConfig) -> None:
        self._config = config
        self._sessions: dict[str, SessionState] = {}

    def start_job(
        self,
        *,
        session_id: str,
        mode: str,
        operation: str,
        url: str,
        dir_path: str,
        notify: Callable[[dict[str, str]], Awaitable[None]],
    ) -> dict[str, str]:
        state = self._get_or_create_session_state(session_id)
        normalized_dir = str(Path(dir_path))
        key = (mode, url, normalized_dir)

        record = JobRecord(operation=operation, status="fetching")
        state.jobs_by_mode_url_dir[key] = record
        state.latest_by_url_dir[(url, normalized_dir)] = record
        state.queue.put_nowait(
            JobRequest(
                mode=mode,
                url=url,
                dir_path=dir_path,
                record=record,
                notify=notify,
            )
        )
        return make_response(status=FETCHING_STATUS, operation=record.operation)

    def get_latest_status(self, *, session_id: str, url: str, dir_path: str) -> dict[str, str]:
        state = self._get_or_create_session_state(session_id)
        record = state.latest_by_url_dir.get((url, str(Path(dir_path))))
        if record is None:
            return make_response(status=FAILED_STATUS, operation="unknown")
        return self._status_response(record.status, record.operation)

    def _status_response(self, status: str, operation: str) -> dict[str, str]:
        if status == "completed":
            return make_response(status=COMPLETED_STATUS, operation=operation)
        if status == "timed_out":
            return make_response(status=TIMED_OUT_STATUS, operation=operation)
        if status == "fetching":
            return make_response(status=FETCHING_STATUS, operation=operation)
        return make_response(status=FAILED_STATUS, operation=operation)

    def _get_or_create_session_state(self, session_id: str) -> SessionState:
        state = self._sessions.get(session_id)
        if state is not None:
            return state

        queue: asyncio.Queue[JobRequest] = asyncio.Queue()
        safe_prefix = "".join(char if char.isalnum() else "_" for char in session_id)[:24]
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"scrape_{safe_prefix}")
        state = SessionState(
            queue=queue,
            worker_task=None,
            worker_executor=executor,
            jobs_by_mode_url_dir={},
            latest_by_url_dir={},
        )
        self._sessions[session_id] = state
        state.worker_task = asyncio.create_task(self._session_worker(session_id))
        return state

    async def aclose(self) -> None:
        worker_tasks: list[asyncio.Task[None]] = []
        for state in self._sessions.values():
            if state.worker_task is not None:
                state.worker_task.cancel()
                worker_tasks.append(state.worker_task)
            state.worker_executor.shutdown(wait=False, cancel_futures=True)
        if worker_tasks:
            await asyncio.gather(*worker_tasks, return_exceptions=True)
        self._sessions.clear()

    async def _session_worker(self, session_id: str) -> None:
        state = self._sessions[session_id]
        while True:
            job = await state.queue.get()
            try:
                await self._run_job(state=state, job=job)
            finally:
                state.queue.task_done()

    async def _run_job(self, *, state: SessionState, job: JobRequest) -> None:
        record = state.jobs_by_mode_url_dir[(job.mode, job.url, str(Path(job.dir_path)))]
        timeout = self._config.total_timeout if self._config.total_timeout > 0 else None
        try:
            loop = asyncio.get_running_loop()
            await asyncio.wait_for(
                loop.run_in_executor(
                    state.worker_executor,
                    self._run_scraper_sync,
                    job.mode,
                    job.url,
                    job.dir_path,
                ),
                timeout=timeout,
            )
        except TimeoutError:
            record.status = "timed_out"
            await job.notify(make_response(status=TIMED_OUT_STATUS, operation=record.operation))
            return
        except Exception as exc:  # noqa: BLE001
            record.status = "failed"
            record.error = str(exc)
            await job.notify(make_response(status=FAILED_STATUS, operation=record.operation))
            return

        record.status = "completed"
        await job.notify(make_response(status=COMPLETED_STATUS, operation=record.operation))

    def _run_scraper_sync(self, mode: str, url: str, dir_path: str) -> None:
        output_dir = Path(dir_path)
        scraper_cfg = ScraperConfig(
            raw_html_dir=output_dir / "raw_html",
            markdown_dir=output_dir / "markdown",
            wildcard_websites=[url] if mode == "wildcard" else [],
            individual_websites=[url] if mode == "single" else [],
            remove_header_footer=self._config.remove_header_footer,
            markdown_convert=self._config.markdown_convert,
            time_delay=self._config.time_delay,
            total_timeout=0,
        )
        WebsiteScraper(scraper_cfg).run()
