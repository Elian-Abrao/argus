"""Safe demo entry point for the logger package."""

from __future__ import annotations

from logger import start_logger


def main() -> None:
    logger = start_logger(
        name="logger_demo",
        capture_prints=False,
        capture_emails=False,
    )

    logger.info("Starting logger demo")
    for index in logger.progress(range(3), desc="Processing"):  # type: ignore[attr-defined]
        logger.info("Completed step %s", index + 1)
    logger.info("Logger demo finished")


if __name__ == "__main__":
    main()
