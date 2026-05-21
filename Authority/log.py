import logging
import os

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
            record.correspondent = ''
            record.correspondent_colored = ''
            return

        _, _, node, node_id = correspondent.split('.')
        arrow = '<--' if sender is not None else '-->'
        role, color = self.NODE_TYPES.get(node,("?", COLORS['ERROR']))
        record.correspondent = f" {arrow} [{role} {node_id}]"
        record.correspondent_colored = (f" {arrow} {color}[{role} {node_id}]{COLORS['RESET']} :")

    def filter_stage(self, record):
        stage = getattr(record, "stage", None)
        if stage is not None:
            record.stage = f"({stage})"
            record.stage_colored = f"\033[90m({stage})\033[0m"
        else:
            record.stage = ''
            record.stage_colored = ''


    def filter(self, record):
        self.filter_correspondent(record)
        self.filter_stage(record)
        return True

class LoggerWrapper:

    def __init__(self, logger):
        self.logger = logger

    def __call__(self, msg, *, extra_param=None):
        if isinstance(msg, list):
            msg = ' '.join([str(type(m))[8:-2].split('.')[-1] for m in msg])
        elif not isinstance(msg, str):
            msg = str(type(msg))[8:-2].split('.')[-1]
        self.logger.info(msg, extra=extra_param)


def create_logger(role, node_id):
    logger = logging.getLogger(f"{role}_{node_id}")
    logger.setLevel(logging.INFO)

    # =========================
    # FILE LOGGER
    # =========================
    file_handler = logging.FileHandler(
        f".logs/{role.lower()}/{role.lower()}_{node_id}.log"
    )

    file_formatter = logging.Formatter(
        "[%(asctime)s.%(msecs)03d]%(correspondent)s %(stage)s %(message)s",
        datefmt="%H:%M:%S"
    )
    
    file_handler.setFormatter(file_formatter)

    # =========================
    # TERMINAL LOGGER
    # =========================
    color = COLORS.get(role, "")

    console_handler = logging.StreamHandler()

    console_formatter = logging.Formatter(
        f"{color}[{role} {node_id}]{COLORS['RESET']}%(correspondent_colored)s %(stage_colored)s %(message)s"
    )

    console_handler.setFormatter(console_formatter)
    logger.addFilter(Filters())

    # =========================
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return LoggerWrapper(logger)
