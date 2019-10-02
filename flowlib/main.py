#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import flowlib.api
from flowlib.cli import FlowLibCLI, FlowLibConfig

def main():
    flowlib_cfg = os.getenv('FLOWLIB_CFG', FlowLibConfig.DEFAULT_CFG)
    config = None
    if os.path.exists(flowlib_cfg) and os.path.isfile(flowlib_cfg):
        with open(flowlib_cfg) as f:
            config = FlowLibConfig.from_file(f)

    cli = FlowLibCLI(config)
    if cli.config.scaffold:
        flowlib.api.init_flow_scaffold(cli.config.scaffold)
    elif cli.config.validate:
        flowlib.api.validate_flow_yaml(cli.config)
    elif cli.config.flow_yaml:
        flowlib.api.deploy_flow_yaml(cli.config)
    elif cli.config.export_yaml:
        flowlib.api.export_flow_yaml(cli.config)
    else:
        cli.parser.print_usage()

if __name__ == '__main__':
    main()
