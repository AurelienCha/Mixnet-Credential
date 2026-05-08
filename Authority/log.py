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

class SenderFilter(logging.Filter):
    def filter(self, record):
        sender = getattr(record, "sender", None)
        if sender is None:
            (record.sender, record.sender_colored) = ('', '')
        else:
            _, _, node, id = sender.split('.')
            if node == '1':
                (record.sender, record.sender_colored) = (f" [AUTH {id}]", f" <-- {COLORS['AUTH']}[AUTH {id}]{COLORS['RESET']} :")
            elif node == '10':
                (record.sender, record.sender_colored) = (f" [MIX {id}]", f" <-- {COLORS['MIX']}[MIX {id}]{COLORS['RESET']} :")
            elif node == '100':
                (record.sender, record.sender_colored) = (f" [CLIENT {id}]", f" <-- {COLORS['CLIENT']}[CLIENT {id}]{COLORS['RESET']} :")
            else:
                (record.sender, record.sender_colored) = (' [?]', '\033[91m[?]\033[0m')
        return True

def create_logger(role, node_id):
    logger = logging.getLogger(f"{role}_{node_id}")
    logger.setLevel(logging.INFO)

    # =========================
    # FILE LOGGER
    # =========================
    file_handler = logging.FileHandler(
        f"logs/{role.lower()}/{role.lower()}_{node_id}.log"
    )

    file_formatter = logging.Formatter(
        "[%(asctime)s]%(sender)s %(message)s",
        datefmt="%H:%M:%S"
    )
    
    file_handler.setFormatter(file_formatter)

    # =========================
    # TERMINAL LOGGER
    # =========================
    color = COLORS.get(role, "")

    console_handler = logging.StreamHandler()

    console_formatter = logging.Formatter(
        f"{color}[{role} {node_id}]{COLORS['RESET']}%(sender_colored)s %(message)s "
    )

    console_handler.setFormatter(console_formatter)
    logger.addFilter(SenderFilter())

    # =========================
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger