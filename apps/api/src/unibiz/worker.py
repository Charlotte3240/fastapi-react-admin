import asyncio
import logging

from unibiz.core.database import session_factory
from unibiz.services.notifications import process_one_delivery
from unibiz.services.outbound import process_one_outbound_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unibiz.worker")


async def run() -> None:
    logger.info("UniBiz worker started")
    while True:
        async with session_factory() as db:
            notification_processed = await process_one_delivery(db)
        async with session_factory() as db:
            outbound_processed = await process_one_outbound_task(db)
        processed = notification_processed or outbound_processed
        if not processed:
            await asyncio.sleep(2)  # noqa: ASYNC110 - intentional database polling worker


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
