"""Background loop: writes up finished meetings and delivers webhooks. Run as its own container
(`python -m notetaker.worker`); several can run side by side safely."""
from __future__ import annotations

import logging
import time

from notetaker import outbox, service, states
from notetaker.config import settings
from notetaker.db import init_db, session_scope

log = logging.getLogger("notetaker.worker")


def tick() -> None:
    with session_scope() as db:
        service.reconcile(db)
    with session_scope() as db:
        for m in service.due_for_finalising(db):
            m.attempts += 1
            db.flush()
            try:
                with db.begin_nested():
                    service.finalise(db, m)
            except Exception:
                log.exception("Writing up meeting %s failed (attempt %s)", m.id, m.attempts)
                if m.attempts >= 5:
                    service.set_status(db, m, states.FAILED, "The call was recorded but the notes couldn't be written.")
    with session_scope() as db:
        outbox.deliver_due(db)
        from notetaker.models import ServiceState
        hb = db.get(ServiceState, "worker_heartbeat") or ServiceState(key="worker_heartbeat")
        from notetaker.models import now as _now
        hb.value = _now().isoformat()
        db.merge(hb)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    init_db()
    log.info("Worker started")
    while True:
        try:
            tick()
        except Exception:
            log.exception("Worker tick failed")
        time.sleep(settings.worker_interval_seconds)


if __name__ == "__main__":
    main()
