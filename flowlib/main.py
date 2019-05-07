#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import flowlib.api
from flowlib.cli import FlowLibCLI


def main():
    cli = FlowLibCLI()

    if cli.config.scaffold:
        flowlib.api.init_flow_scaffold(cli.config.scaffold)
    elif cli.config.validate:
        flowlib.api.validate_flow_yaml(cli.config)
    elif cli.config.flow_yaml:
        flowlib.api.deploy_flow_yaml(cli.config)
    elif cli.config.export_yaml:
        flowlib.api.export_flow_yaml(cli.config)

if __name__ == '__main__':
    main()
