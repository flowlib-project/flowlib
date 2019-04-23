#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import logging.config
import sys

from cli import FlowLibCLI
from flowgen import deploy_flow_yaml

logging.config.fileConfig('logging.conf')

if __name__ == '__main__':
    cli = FlowLibCLI()
    deploy_flow_yaml(cli.config)
