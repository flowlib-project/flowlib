import logging
import logging.config
import sys

from cli import FlowGenCLI
from flowgen import deploy_from_yaml

logging.config.fileConfig('logging.conf')

if __name__ == '__main__':
    cli = FlowGenCLI()
    deploy_from_yaml(cli.config)
