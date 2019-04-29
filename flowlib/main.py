#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging.config
import os.path

import flowlib.api
from flowlib.cli import FlowLibCLI

log_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logging.conf')
logging.config.fileConfig(log_config)

def main():
    cli = FlowLibCLI()

    if cli.config.flow_yaml:
        flowlib.api.deploy_flow_yaml(cli.config)
    elif cli.config.export_yaml:
        flowlib.api.export_flow_yaml(cli.config)
    # elif cli.config.validate:
    #     flowlib.api.validate_flow(cli.config)

if __name__ == '__main__':
    main()
