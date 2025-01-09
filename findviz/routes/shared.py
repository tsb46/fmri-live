"""
Shared resources for the application.
"""
from findviz.logger_config import get_logger

logger = get_logger(__name__)

from findviz.viz.viewer.data_manager import DataManager

# Create the single shared instance
try:
    data_manager = DataManager()
    logger.info("Data manager initialized")
except Exception as e:
    logger.error("Error initializing data manager: %s", str(e), exc_info=True)
    raise