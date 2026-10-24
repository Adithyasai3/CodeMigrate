"""Background scan execution: PENDING -> RUNNING -> COMPLETED | FAILED."""

from __future__ import annotations

import json
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from sqlmodel import Session

from codemigrate.api.db import get_engine
from codemigrate.api.models import Scan, ScanStatus
from codemigrate.pipeline import Pipeline, SystemConfig

log = logging.getLogger(__name__)
EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="scan")


def run_scan(scan_id: int) -> None:
    """Execute one scan and persist its outcome (never raises)."""
    with Session(get_engine()) as session:
        scan = session.get(Scan, scan_id)
        if scan is None:
            log.error("scan %s vanished", scan_id)
            return
        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.now(UTC)
        session.add(scan)
        session.commit()
        try:
            sources = [tuple(x) for x in json.loads(scan.sources_json)]
            cfg = SystemConfig(name=f"api-{scan.provider}", retriever=scan.retriever,
                               provider=scan.provider)
            result = Pipeline(cfg).scan_sources(sources, scan.from_version, scan.to_version)
            data = result.model_dump(mode="json")
            for f in data["findings"] + data["rejected"]:
                f.pop("evidence", None)
            scan.result_json = json.dumps(data)
            scan.findings_count = len(result.findings)
            scan.status = ScanStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001 - surfaced to the user as FAILED + logged
            log.exception("scan %s failed", scan_id)
            scan.status = ScanStatus.FAILED
            scan.error = f"{type(exc).__name__}: {exc}"[:1000]
            log.debug(traceback.format_exc())
        scan.finished_at = datetime.now(UTC)
        session.add(scan)
        session.commit()


def submit(scan_id: int) -> None:
    EXECUTOR.submit(run_scan, scan_id)
