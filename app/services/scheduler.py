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

    _scheduler.add_job(
        func=_daily_reflection_job,
        trigger="cron",
        hour=23,
        minute=30,
        id="daily_reflection",
        next_run_time=datetime.now() + timedelta(minutes=15),
    )

    _scheduler.add_job(
        func=_weekly_cleanup_job,
        trigger="interval",
        days=7,
        id="weekly_cleanup",
        next_run_time=datetime.now() + timedelta(hours=2),
    )

    _scheduler.start()
    logger.info("Scheduler started (yt=%sh, reflection=23:30, cleanup=7d)", interval)
    import atexit
    atexit.register(shutdown_scheduler)
    return _scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler shut down")


def _check_subs_job():
    from .subscription_service import check_all_subscriptions
    result = check_all_subscriptions()
    logger.info("Scheduler sub check complete: %r", result)


def _daily_reflection_job():
    from .reflection_service import generate_daily_reflection
    logger.info("Running daily reflection job")
    try:
        result = generate_daily_reflection()
        if result:
            logger.info("Daily reflection generated: %s topics", len(result.get("topics", [])))
        else:
            logger.info("No daily reflection generated (no messages today)")
    except Exception as e:
        logger.error("Daily reflection job failed: %s", e)


def _weekly_cleanup_job():
    logger.info("Running weekly cleanup job")
    try:
        _vacuum_db()
        _generate_missed_reflections()
        logger.info("Weekly cleanup complete")
    except Exception as e:
        logger.error("Weekly cleanup job failed: %s", e)


def _vacuum_db():
    from ..models.reflection_db import get_connection
    conn = get_connection()
    conn.execute("PRAGMA optimize")
    conn.execute("VACUUM")
    conn.close()
    logger.info("Database vacuumed")


def _generate_missed_reflections():
    from .reflection_service import generate_missed_reflections
    generated = generate_missed_reflections()
    if generated:
        logger.info("Generated %d missed reflections", len(generated))
