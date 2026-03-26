"""
Demo main: Logging-only application (external noise controlled via logging config)

Usage: .venv/bin/python sandbox/scripts/demo/main.py
"""

import logging
import requests

from pkg_infra.session import get_session
from pkg_infra.logger import list_loggers


def main():
    # -----------------------------
    # Session logger (your system)
    # -----------------------------
    session = get_session(
        workspace="./",
        include_location=True,
        config_path="sandbox/scripts/demo/config.yaml")
    
    logger = session.session_logger

    print(f"Default logger: {logger.name}")

    print(f"Loggers: {list_loggers()}")


    if logger is None:
        raise RuntimeError("Session logger is not initialized.")

    logger.info("Demo started: clean logging-only setup")

    # -----------------------------
    # 1. Application logs
    # -----------------------------
    logger.debug("Debug message (may be hidden depending on config)")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # -----------------------------
    # 2. HTTP request (urllib3 underneath)
    # -----------------------------
    logger.info("Making HTTP request via requests (urllib3 underneath)")

    try:
        response = requests.get(
            "https://httpbin.org/get",
            timeout=5
        )
        logger.info(f"HTTP status: {response.status_code}")

    except Exception as e:
        logger.error(f"HTTP request failed: {e}")

    # -----------------------------
    # 3. Multiple requests to test pooling
    # -----------------------------
    logger.info("Running multiple HTTP requests to test connection reuse")

    for i in range(5):
        try:
            r = requests.get("https://httpbin.org/uuid", timeout=5)
            logger.info(f"Request {i + 1} OK: {r.status_code}")

        except Exception as e:
            logger.error(f"Request {i + 1} failed: {e}")

    # -----------------------------
    # 4. End of demo
    # -----------------------------
    logger.info("Demo finished successfully")


if __name__ == "__main__":
    main()