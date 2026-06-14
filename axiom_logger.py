import os
import logging
import asyncio
from datetime import datetime, timezone
import axiom_py

logger = logging.getLogger(__name__)

AXIOM_TOKEN = os.getenv("AXIOM_TOKEN")
AXIOM_DATASET = os.getenv("AXIOM_DATASET")

_client = None

if AXIOM_TOKEN and AXIOM_DATASET:
    try:
        _client = axiom_py.Client(token=AXIOM_TOKEN)
        logger.info(
            "Axiom logger client connected successfully. Dataset: %s", AXIOM_DATASET
        )
    except Exception as e:
        logger.warning(
            "Failed to initialize Axiom client: %s. Telemetry is DISABLED.", e
        )
else:
    logger.warning(
        "AXIOM_TOKEN or AXIOM_DATASET missing in env. Telemetry is DISABLED."
    )


async def _send_event(event_type: str, data: dict) -> None:
    if not _client:
        return
    try:
        payload = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        # Axiom-py client ingestion is synchronous, so run it in a thread pool to avoid blocking the event loop
        await asyncio.to_thread(
            _client.ingest_events, dataset=AXIOM_DATASET, events=[payload]
        )
    except Exception as e:
        logger.error("Error sending metric to Axiom: %s", e)


def log_axiom_event(event_type: str, data: dict) -> None:
    """
    Non-blocking background helper to log telemetry data to Axiom.
    """
    if not _client:
        return
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(_send_event(event_type, data))
    except RuntimeError:
        # Fallback if no event loop is running (e.g. during script startup or test setup)
        try:
            payload = {
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **data,
            }
            _client.ingest_events(dataset=AXIOM_DATASET, events=[payload])
        except Exception as e:
            logger.error("Error sending synchronous metric to Axiom: %s", e)
