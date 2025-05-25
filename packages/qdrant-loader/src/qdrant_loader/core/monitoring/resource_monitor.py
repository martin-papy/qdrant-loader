import asyncio

import psutil

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


async def monitor_resources(
    cpu_threshold: float = 80.0,
    mem_threshold: float = 80.0,
    interval: float = 5.0,
    stop_event: asyncio.Event | None = None,
):
    """
    Periodically check system CPU and memory usage and log warnings if thresholds are exceeded.
    Args:
        cpu_threshold: CPU usage percent threshold to trigger warning
        mem_threshold: Memory usage percent threshold to trigger warning
        interval: Seconds between checks
        stop_event: Optional asyncio.Event to signal stopping
    """
    logger.info(
        f"Starting resource monitor: CPU>{cpu_threshold}%, MEM>{mem_threshold}%, interval={interval}s"
    )
    while True:
        if stop_event and stop_event.is_set():
            logger.info("Resource monitor stopping (stop_event set)")
            break
        try:
            if psutil:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
            else:
                # Fallback: only show process memory
                import resource

                cpu = 0.0  # Not available
                mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
                logger.info(f"[ResourceMonitor] Process memory usage: {mem:.2f} MB")
            if psutil:
                logger.debug(f"[ResourceMonitor] CPU: {cpu:.1f}%, MEM: {mem:.1f}%")
                if cpu > cpu_threshold:
                    logger.warning(f"[ResourceMonitor] High CPU usage: {cpu:.1f}%")
                if mem > mem_threshold:
                    logger.warning(f"[ResourceMonitor] High memory usage: {mem:.1f}%")
        except Exception as e:
            logger.error(f"[ResourceMonitor] Error checking resources: {e}")
        await asyncio.sleep(interval)
