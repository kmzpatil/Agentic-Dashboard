import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """Creates and returns a configured logger."""
    logger = logging.getLogger(name)
    
    # Only configure if there are no handlers (prevent duplicate logging)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        fh = logging.FileHandler('system.log', mode='w')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger
