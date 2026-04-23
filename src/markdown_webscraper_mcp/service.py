from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from markdown_webscraper import ScraperConfig, WebsiteScraper

from .config import MCPServerConfig

FETCHING_RESPONSE = {"status": "fetching website and converting to markdown in progress!"}
COMPLETED_RESPONSE = {"status": "fetch completed and markdown saved!"}
TIMED_OUT_RESPONSE = {"status": "fetching timed out!"}
FAILED_RESPONSE = {"status": "failed to fetch!"}


@dataclass
class JobRecord:
    task: asyncio.Task[None]
    status: str
    error: str | None = None


class ScrapeJobService:
    def __init__(self, config: MCPServerConfig) -> None:
        self._config = config
        self._jobs_by_mode_url_dir: dict[tuple[str, str, str], JobRecord] = {}
        self._latest_by_url_dir: dict[tuple[str, str], JobRecord] = {}

    def start_job(self, *, mode: str, url: str, dir_path: str) -> dict[str, str]:
        key = (mode, url, str(Path(dir_path)))
        task = asyncio.create_task(self._run_job(mode=mode, url=url, dir_path=dir_path))
        record = JobRecord(task=task, status="fetching")
        self._jobs_by_mode_url_dir[key] = record
        self._latest_by_url_dir[(url, str(Path(dir_path)))] = record

        def _capture_completion(done: asyncio.Task[None], job: JobRecord = record) -> None:
            if done.cancelled():
                job.status = "failed"
                job.error = "task cancelled"
                return
            exc = done.exception()
            if exc is not None:
                job.status = "failed"
                job.error = str(exc)

        task.add_done_callback(_capture_completion)
        return FETCHING_RESPONSE

    def get_latest_status(self, *, url: str, dir_path: str) -> dict[str, str]:
        record = self._latest_by_url_dir.get((url, str(Path(dir_path))))
        if record is None:
            return FAILED_RESPONSE
        return self._status_response(record.status)

    def _status_response(self, status: str) -> dict[str, str]:
        if status == "completed":
            return COMPLETED_RESPONSE
        if status == "timed_out":
            return TIMED_OUT_RESPONSE
        if status == "fetching":
            return FETCHING_RESPONSE
        return FAILED_RESPONSE

    async def _run_job(self, *, mode: str, url: str, dir_path: str) -> None:
        record = self._jobs_by_mode_url_dir[(mode, url, str(Path(dir_path)))]
        timeout = self._config.total_timeout if self._config.total_timeout > 0 else None
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._run_scraper_sync, mode=mode, url=url, dir_path=dir_path),
                timeout=timeout,
            )
        except TimeoutError:
            record.status = "timed_out"
            return
        except Exception as exc:  # noqa: BLE001
            record.status = "failed"
            record.error = str(exc)
            return

        record.status = "completed"

    def _run_scraper_sync(self, *, mode: str, url: str, dir_path: str) -> None:
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
