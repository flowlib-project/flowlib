#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

from tabulate import tabulate

import flowlib.api
from flowlib.cli import FlowLibCLI, FlowLibConfig
from flowlib.new.registry import list_flows, transfer_flows
from flowlib.new.nifi import change_version, toggle_controller_services, list_templates, transfer_templates, \
    create_templates


def main():
    flowlib_cfg = os.getenv('FLOWLIB_CFG', FlowLibConfig.DEFAULT_CFG)
    config = None
    if os.path.exists(flowlib_cfg) and os.path.isfile(flowlib_cfg):
        with open(flowlib_cfg) as f:
            config = FlowLibConfig.new_from_file(f)

    cli = FlowLibCLI(file_config=config)
    if cli.args.list_flows:
        list_flows(cli.config, cli.config.list_flows)
    elif cli.args.transfer_flows:
        transfer_flows(cli.config, cli.config.transfer_flows)
    elif cli.args.change_versions:
        change_version(cli.config, cli.config.change_versions)
    elif cli.args.toggle_controller_services:
        toggle_controller_services(cli.config, cli.config.toggle_controller_services)
    elif cli.args.list_templates:
        list_templates(cli.config)
    elif cli.args.create_templates:
        create_templates(cli.config, cli.config.create_templates)
    elif cli.args.transfer_templates:
        transfer_templates(cli.config, cli.config.transfer_templates)
    elif cli.args.scaffold:
        flowlib.api.gen_flow_scaffold(cli.args.scaffold)
    elif cli.args.generate_docs:
        flowlib.api.gen_flowlib_docs(cli.config, cli.args.generate_docs)
    elif cli.args.validate:
        flowlib.api.validate_flow(cli.config)
    elif cli.args.flow_yaml:
        flowlib.api.deploy_flow(cli.config)
    elif cli.args.deployment_json:
        flowlib.api.deploy_flow(cli.config)
    elif cli.args.export:
        s = flowlib.api.export_flow(cli.config)
        s.seek(0)
        print(s.read())
    elif cli.args.configure_flow_controller:
        flowlib.api.configure_flow_controller(cli.config)
    elif cli.args.list:
        components = flowlib.api.list_components(cli.config, cli.args.list)
        print('\n'.join(components))
    elif cli.args.describe:
        descriptor = flowlib.api.describe_component(cli.config, cli.args.describe.component_type, cli.args.describe.package_id)
        headers = ['Name', 'Default', 'Allowable Values', 'Required', 'Sensitive', 'Supports EL', 'Description']
        items = list()
        for d in descriptor.values():
            name = d.get('name')
            default = d.get('default_value', '')
            values = d.get('allowable_values') or list()
            allowable_values = ','.join(list(map(lambda v: v['allowable_value']['value'], values)))
            required = d.get('required')
            sensitive = d.get('sensitive')
            supports_el = d.get('supports_el')
            description = d.get('description')
            field = [name, default, allowable_values, required, sensitive, supports_el, description]
            items.append(field)
        print(tabulate(items, headers=headers, stralign="left", tablefmt="psql"))
    elif cli.args.registry_export:
        flowlib.api.registry_export_flow(cli.config.registry_export, cli.config.output_format)
        try:
            flowlib.api.registry_convert_flow(cli.config)
        except FileNotFoundError as e:
            print("There were no resources in the specified bucket & flow...")
    elif cli.args.registry_import:
        flowlib.api.registry_import_flow(cli.config)
    else:
        cli.parser.print_usage()


if __name__ == '__main__':
    main()
