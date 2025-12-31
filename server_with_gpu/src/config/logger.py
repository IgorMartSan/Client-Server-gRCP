import os
import logging
import queue
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener

LOG_QUEUE_SIZE = 10_000


class ErrorModeFilter(logging.Filter):
    """
    Filtro que controla como mensagens de erro são exibidas.

    Modes:
        - "full"     → mostra stacktrace completo
        - "lastline" → mostra apenas a última linha útil do erro
    """
    def __init__(self, mode: str):
        self.mode = mode.lower()

    def filter(self, record: logging.LogRecord) -> bool:
        if self.mode == "lastline" and record.levelno >= logging.ERROR:
            msg = record.getMessage()
            if "\n" in msg:
                record.msg = msg.strip().splitlines()[-1]
                record.args = ()
        return True


def setup_logger(
    container_name: str,
    log_dir: str = "/system_log",
    show_log: bool = True,
    error_mode: str = "lastline",
) -> None:
    """
    Configure a high-performance, non-blocking logger with optional stacktrace filtering.

    Args:
        container_name (str): Name of the container or service (log file name).
        log_dir (str): Directory where log files will be written.
        show_log (bool): Whether to print logs to stdout.
        error_mode (str): How error messages should be displayed:
            - "full"     → keep full stacktrace
            - "lastline" → keep only the last useful line of the error (default).

    This logger uses a bounded queue to avoid blocking critical threads.
    """

    os.makedirs(log_dir, exist_ok=True)
    path_log = os.path.join(log_dir, f"{container_name}.log")

    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()
    root.setLevel(logging.INFO)

    root.addFilter(ErrorModeFilter(error_mode))

    log_queue = queue.Queue(maxsize=LOG_QUEUE_SIZE)
    root.addHandler(QueueHandler(log_queue))

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(process)d:%(threadName)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s"
    )

    handlers = []

    file_handler = RotatingFileHandler(path_log, maxBytes=10 * 1024 * 1024, backupCount=1)
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)

    if show_log:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    QueueListener(log_queue, *handlers, respect_handler_level=True).start()

    logging.info(
        "Logger initialized | name=%s | queue=%s | error_mode=%s",
        container_name, LOG_QUEUE_SIZE, error_mode,
    )
