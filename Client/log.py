import logging
import os
from crypto import Crypto

# ANSI colors (value-60 =  darker/discret, e.g. 30=black)
# FG    BG      COLOR
# 90	100     Gray
# 91	101	    Red	
# 92	102	    Green	
# 93	103	    Yellow	
# 94	104	    Blue	
# 95	105	    Magenta	
# 96	106	    Cyan	
# 97	107	    White
COLORS = {
    "AUTH": "\033[92m",   # green
    "MIX": "\033[93m",    # yellow
    "CLIENT": "\033[94m", # blue
    "ERROR": "\033[91m",  # red
    "RESET": "\033[0m"
}

class Filters(logging.Filter):

    NODE_TYPES = {
        '1': ("AUTH", COLORS['AUTH']),
        '10': ("MIX", COLORS['MIX']),
        '100': ("CLIENT", COLORS['CLIENT']),
    }

    def filter_correspondent(self, record):

        sender = getattr(record, "sender", None)
        recipient = getattr(record, "recipient", None)

        correspondent = sender or recipient
        if correspondent is None:
            record.direction = ''
            record.correspondent = ', '
            record.correspondent_colored = ''
            return

        _, _, node, node_id = correspondent.split('.')
        record.direction = '<--' if sender is not None else '-->'
        role, color = self.NODE_TYPES.get(node,("?", COLORS['ERROR']))
        record.correspondent = f"{role}, {node_id}"
        record.correspondent_colored = f"{color}[{role} {node_id}]{COLORS['RESET']}"

    def filter_comment(self, record):
        comment = getattr(record, "comment", None)
        if comment is not None:
            record.comment = f"{comment}"
            record.comment_colored = f"\033[90m({comment})\033[0m"
        else:
            record.comment = ''
            record.comment_colored = ''
    
    def filter_hash(self, record):
        record.hash = Crypto.hash(getattr(record, "data", ''), short=True)


    def filter(self, record):
        self.filter_correspondent(record)
        self.filter_comment(record)
        self.filter_hash(record)
        record.type = getattr(record, "data", '')
        return True

class LoggerWrapper:

    def __init__(self, logger):
        self.logger = logger

    def __call__(self, extra_param):
        self.logger.info('', extra=extra_param)


def create_logger(role, node_id):
    logger = logging.getLogger(f"{role}_{node_id}")
    logger.setLevel(logging.INFO)

    # =========================
    # FILE LOGGER
    # =========================
    file_handler = logging.FileHandler(
        f".logs/{role.lower()}/{role.lower()}_{node_id}.csv"
    )

    file_formatter = logging.Formatter(
        f"[%(asctime)s.%(msecs)03d], {role}, {node_id}, %(direction)s, %(correspondent)s, %(type)s, %(hash)s, %(comment)s",
        datefmt="%H:%M:%S"
    )
    
    file_handler.setFormatter(file_formatter)

    # =========================
    # TERMINAL LOGGER
    # =========================
    console_formatter = logging.Formatter(
        f"{COLORS.get(role, "")}[{role} {node_id}]{COLORS['RESET']} %(direction)s %(correspondent_colored)s %(type)s %(hash)s %(comment_colored)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addFilter(Filters())

    # =========================
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return LoggerWrapper(logger)
