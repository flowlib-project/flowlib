import logging.config
import os

__all__ = ['log']

log_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
logging.config.fileConfig(log_config)
log = logging.getLogger()
