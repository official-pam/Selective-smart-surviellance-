from loguru import logger
import sys
from config import LOGS_DIR

def setup_logger():
    logger.remove()  # remove default stderr handler
    # Console: INFO and above
    logger.add(sys.stdout, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    # File: DEBUG and above, rotated daily
    logger.add(f"{LOGS_DIR}/security_{{time:YYYY-MM-DD}}.log",
               level="DEBUG", rotation="1 day", retention="7 days",
               compression="zip")