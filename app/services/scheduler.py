from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
_scheduler = None


def init_scheduler(app):
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    interval = app.config.get("YT_CHECK_INTERVAL_HOURS", 6)
    _scheduler.add_job(
        func=_check_subs_job,
        trigger="interval",
        hours=interval,
        id="yt_sub_check",
        next_run_time=datetime.now() + timedelta(hours=1),
    )
    _scheduler.start()
    logger.info("YouTube subscription scheduler started (interval=%sh)", interval)
    import atexit
    atexit.register(shutdown_scheduler)
    return _scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("YouTube subscription scheduler shut down")


def _check_subs_job():
    from .subscription_service import check_all_subscriptions
    result = check_all_subscriptions()
    logger.info("Scheduler check complete: %r", result)
