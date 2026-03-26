import asyncio
import logging

from .service import WorkerService


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")


def main() -> None:
    service = WorkerService()
    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        logging.info("Shutting down workers...")


if __name__ == "__main__":
    main()
