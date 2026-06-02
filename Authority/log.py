import logging, os, inspect
from functools import wraps

from hashlib import sha256

COLORS = {
    "AUTH": "\033[92m",   # green
    "MIX": "\033[93m",    # yellow
    "CLIENT": "\033[94m", # blue
    "ERROR": "\033[91m",  # red
    "COMMENT": "\033[90m", # gray
    "RESET": "\033[0m"
}

def small_hash(values):
    h = sha256()
    if not isinstance(values, (list, tuple)):
        values = [values]

    for v in values:
        h.update(str(v).encode())
        h.update(b"|")

    return h.hexdigest()[:8]

class ConsoleFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return bool(getattr(record, "direction", ""))
        
class LogFilter(logging.Filter):

    NODE_TYPES = {
        '1': ("AUTH", COLORS['AUTH']),
        '10': ("MIX", COLORS['MIX']),
        '100': ("CLIENT", COLORS['CLIENT']),
    }

    def filter(self, record: logging.LogRecord) -> bool:

        # Sender / Receiver
        sender = getattr(record, "sender", None)
        recipient = getattr(record, "recipient", None)
        correspondent = sender or recipient

        if correspondent:
            _, _, node, record.id2 = correspondent.split(".")
            record.direction = "<--" if sender else "-->"
            record.role2, record.color2 = self.NODE_TYPES.get(node, ("?", COLORS["ERROR"]))
        else:
            record.direction = ""
            record.id2 = ""
            record.role2 = ""
            record.color2 = ""

        # Data / Type
        data = getattr(record, "data", None)
        if data:
            record.type = type(data).__name__
            record.hash = small_hash(data)
        else:
            record.type = ''
            record.hash = ''


        # Comment
        record.comment = getattr(record, "comment", "")
        if ',' not in record.comment:
            record.comment += ', , '

        return True

class LoggerWrapper:

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def __call__(self, *, data=None, sender=None, recipient=None, comment=None) -> None:
        self.logger.info('', extra={'data': data, 'sender': sender, 'recipient': recipient, 'comment': comment})

# ============================================================
# LOGGING
# ============================================================
LOGGING: LoggerWrapper | None = None
def create_logger(role: str, node_id: int) -> LoggerWrapper:
    logger = logging.getLogger(f"{role}_{node_id}")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return LoggerWrapper(logger)

    # =========================
    # FILE LOGGER
    # =========================
    file_handler = logging.FileHandler(
        f".logs/{role.lower()}/{role.lower()}_{node_id}.csv"
    )

    file_handler.setFormatter(
        logging.Formatter(
            (
                f"[%(asctime)s.%(msecs)03d], {role}, {node_id}, "
                "%(direction)s, %(role2)s, %(id2)s, "
                "%(type)s, %(hash)s, %(comment)s, "
                "1"
            ),
            datefmt="%H:%M:%S",
        )
    )

    # =========================
    # TERMINAL LOGGER
    # =========================

    console_handler = logging.StreamHandler()
    console_handler.addFilter(ConsoleFilter())

    console_handler.setFormatter(
        logging.Formatter(
            (
                f"{COLORS.get(role, '')}{role:<6} {node_id:>2}"
                f"{COLORS['RESET']} %(direction)3s "
                "%(color2)s %(role2)-6s %(id2)2s "
                f"{COLORS['COMMENT']} %(type)6s "
                f"{COLORS['RESET']} %(hash)s "
                f"{COLORS['COMMENT']} %(comment)s "
                f"{COLORS['RESET']}"
            )
        )
    )

    # =========================
    # FILTER / HANDLERS
    # =========================

    logger.addFilter(LogFilter())
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    global LOGGING
    LOGGING = LoggerWrapper(logger)
    return LOGGING



from time import process_time, perf_counter_ns

def timing(func):
    if inspect.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start, start_ns = process_time(), perf_counter_ns()
            try:
                return await func(*args, **kwargs)
            finally:
                end, end_ns = process_time(),perf_counter_ns()
                LOGGING(comment=f"{func.__name__}, CPU: {1000 * (end - start):.6f} ms, wall: {(end_ns - start_ns) / 1_000_000:.6f} ms") 
        return async_wrapper

    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start, start_ns = process_time(), perf_counter_ns()
            try:
                return func(*args, **kwargs)
            finally:
                end, end_ns = process_time(),perf_counter_ns()
                LOGGING(comment=f"{func.__name__}, CPU: {1000 * (end - start):.6f} ms, wall: {(end_ns - start_ns) / 1_000_000:.6f} ms") 
        return sync_wrapper