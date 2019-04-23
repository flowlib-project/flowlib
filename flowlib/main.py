#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging.config
import os.path
import sys

from flowlib.cli import FlowLibCLI
from flowlib.flowgen import deploy_flow_yaml

log_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
logging.config.fileConfig(log_config)

def main():
    cli = FlowLibCLI()
    deploy_flow_yaml(cli.config)

if __name__ == '__main__':
    main()
