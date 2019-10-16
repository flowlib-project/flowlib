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
            config = FlowLibConfig.new_from_file(f)

    cli = FlowLibCLI(config)
    if cli.args.scaffold:
        flowlib.api.init_flow_scaffold(cli.args.scaffold)
    elif cli.args.validate:
        flowlib.api.validate_flow(cli.config)
    elif cli.args.flow_yaml:
        flowlib.api.deploy_flow(cli.config)
    elif cli.args.export:
        flowlib.api.export_flow(cli.config)
    elif cli.args.configure_flow_controller:
        flowlib.api.configure_flow_controller(cli.config)
    elif cli.args.list:
        flowlib.api.list_components(cli.config, cli.args.list)
    elif cli.args.describe:
        flowlib.api.describe_component(cli.config, cli.args.describe.component_type, cli.args.describe.package_id)
    else:
        cli.parser.print_usage()

if __name__ == '__main__':
    main()
