import atexit
import logging
import logging.config
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, Optional


_log_queue: Queue = Queue(maxsize=-1)
_queue_listener: Optional[QueueListener] = None
_logging_started: bool = False


def start_logging(config: dict[str, Any]) -> None:
    global _queue_listener, _log_queue, _logging_started
    if _logging_started:
        return
        
    logging.config.dictConfig(config)
    
    # Base setup: Get all handlers from the dictConfig instantiation
    root_logger = logging.getLogger()
    all_handlers = list(root_logger.handlers)

    # We use a QueueHandler to make logging non-blocking for the main app
    _queue_handler = QueueHandler(_log_queue)
    
    # Replace handlers in root and defined loggers with the QueueHandler
    root_logger.handlers = [_queue_handler]
    for logger_name in config.get("loggers", {}):
        if logger_name:
            l = logging.getLogger(logger_name)
            for h in list(l.handlers):
                if h not in all_handlers:
                    all_handlers.append(h)
            l.handlers = [_queue_handler]

    if all_handlers:
        _queue_listener = QueueListener(_log_queue, *all_handlers, respect_handler_level=True)
        _queue_listener.start()
    
    _logging_started = True
    logging.info("Logging system initialized with QueueListener.")

def stop_logging() -> None:
    global _queue_listener
    if _queue_listener is not None:
        _queue_listener.stop()
        _queue_listener = None

def get_logger(name: str) -> logging.Logger:
    """Return a logger by name. Call :func:`start_logging` once at process entry with the service dictConfig."""
    if not _logging_started:
        raise RuntimeError(
            "Logging is not initialized. Call start_logging(config) once at service entry "
            "(before any import that uses get_logger)."
        )
    return logging.getLogger(name)


atexit.register(stop_logging)
