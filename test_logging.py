#!/usr/bin/env python3
"""
Test script to demonstrate the logging system
"""

import logging
from app.config import settings  # This initializes logging

def test_logging_levels():
    """Test different logging levels"""
    logger = logging.getLogger(__name__)
    
    print(f"Current log level: {settings.LOG_LEVEL}")
    print("Testing different log levels:")
    print("-" * 50)
    
    logger.debug("This is a DEBUG message - detailed information for debugging")
    logger.info("This is an INFO message - general information about program execution")
    logger.warning("This is a WARNING message - something unexpected happened")
    logger.error("This is an ERROR message - a serious problem occurred")
    
    print("-" * 50)
    print("To see DEBUG messages, set LOG_LEVEL=DEBUG in your .env file")

if __name__ == "__main__":
    test_logging_levels()
