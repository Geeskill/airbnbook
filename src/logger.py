"""Configuration centralisée du logging."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from config import LOG_LEVEL, LOG_FILE, APP_NAME


def setup_logger(name: str = APP_NAME) -> logging.Logger:
    """Configure et retourne un logger."""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Format des logs
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler fichier avec rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Logger par défaut
logger = setup_logger()
