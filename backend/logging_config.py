import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(_PROJECT_DIR / ".env")


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def setup_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [stream_handler]

    if _to_bool(os.getenv("LOG_TO_FILE", "true")):
        log_path = os.getenv("LOG_FILE_PATH", "logs/app.log")
        log_path_obj = Path(log_path)
        if not log_path_obj.is_absolute():
            log_path_obj = _PROJECT_DIR / log_path_obj
        log_path_obj.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path_obj, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers)


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
