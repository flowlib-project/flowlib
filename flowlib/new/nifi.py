# -*- coding: utf-8 -*-
from flowlib.new.util import call_cmd, call_api, call_multi_cmd
import json


def list_templates(config):
    all_templates = call_cmd(config.container, config.nifi_endpoint, "nifi list-templates")['templates']
    if all_templates:
        print("Templates:")
        for template in all_templates:
            print("\t{}".format(template['template']['name']))
    else:
        print("\t! No templates available")


def create_templates(config, process_groups_templates):
    names_map = {}
    for name_and_template in process_groups_templates:
        split = name_and_template.split(":")
        names_map[split[0]] = split[1]

    process_groups_by_name = __obtain_multi_process_groups_info(config, names_map.keys())
    all_templates = call_cmd(config.container, config.nifi_endpoint, "nifi list-templates")['templates']

    for name in names_map:
        template_name = names_map[name]
        process_group = process_groups_by_name[name]
        template = __filter_templates(all_templates, template_name)
        if template:
            call_api(config.nifi_endpoint, 'delete', "templates/{}".format(template['id']))

        snippet = {"snippet": {"parentGroupId": process_group['parentGroupId'],
                               "processGroups": {process_group['id']: {"version": 1}}}}

        snippet_info = call_api(config.nifi_endpoint, 'POST', "snippets", snippet)
        if isinstance(snippet_info, dict):
            response = call_api(config.nifi_endpoint, 'POST', "process-groups/{}/templates".format(process_group['id']),
                                {"name": template_name, "snippetId": snippet_info['snippet']['id'],
                                 "description": "{}".format(process_group['position']).replace('\'', '\"')})
            if isinstance(response, dict):
                print("Created {} template for {} processor group".format(template_name, name))
            else:
                print("Could not create {} template for {} processor group: {}".format(template_name, name, response))
        else:
            print("Could not create {} template for {} processor group: {}".format(template_name, name, snippet_info))


def transfer_templates(config, templates):
    root_id = call_cmd(config.container, config.dest_nifi_endpoint, "nifi get-root-id")
    all_templates = call_cmd(config.container, config.nifi_endpoint, "nifi list-templates")['templates']
    dest_templates = call_cmd(config.container, config.dest_nifi_endpoint, "nifi list-templates")['templates']
    for template_name in templates:
        template = __filter_templates(all_templates, template_name)
        dest_template = __filter_templates(dest_templates, template_name)
        if dest_template:
            call_api(config.dest_nifi_endpoint, 'delete', "templates/{}".format(dest_template['id']))

        if template:
            commands = ["nifi download-template --templateId {} --outputFile /tmp/template --baseUrl {}"
                            .format(template['id'], config.nifi_endpoint),
                        "nifi upload-template --processGroupId {} --input /tmp/template --baseUrl {}"
                            .format(root_id,config.dest_nifi_endpoint)]
            call_multi_cmd(config.container, config.nifi_endpoint, commands)
        else:
            print("! Could not find template in {} instance".format(config.nifi_endpoint))


def change_version(config, names_and_versions):
    names_map = {}
    for name_and_version in names_and_versions:
        if ":" in name_and_version:
            split = name_and_version.split(":")
            names_map[split[0]] = split[1]
        else:
            names_map[name_and_version] = "latest"

    process_groups_by_name = __obtain_multi_process_groups_info(config, names_map.keys())

    for name in names_map:
        version = names_map[name]
        process_group = process_groups_by_name[name]

        if version != "latest":
            call_cmd(config.container, config.nifi_endpoint,
                     "nifi pg-change-version --processGroupId {id} --flowVersion {version}".format(
                         id=process_group['id'], version=version))
            print("{} changed to version {}".format(name, version))
        else:
            call_cmd(config.container, config.nifi_endpoint,
                     "nifi pg-change-version --processGroupId {id}".format(id=process_group['id']))
            print("{} changed to latest version".format(name))


def toggle_controller_services(config, names_and_action):
    names_map = {}
    for name_and_version in names_and_action:
        split = name_and_version.split(":")
        names_map[split[0]] = split[1]

    process_groups_by_name = __obtain_multi_process_groups_info(config, names_map.keys())

    for name in names_map:
        action = names_map[name]
        process_group = process_groups_by_name[name]

        process_groups = [process_group]

        if action == "disable":
            call_cmd(config.container, config.nifi_endpoint,
                     "nifi pg-stop --processGroupId {}".format(process_group['id']))

            while len(process_groups) > 0:
                process_group = process_groups.pop(0)
                call_cmd(config.container, config.nifi_endpoint,
                         "nifi pg-disable-services --processGroupId {}".format(process_group['id']))
                process_groups.extend(__obtain_process_groups(config, process_group['id']))

        elif action == "enable":
            while len(process_groups) > 0:
                process_group = process_groups.pop(0)
                call_cmd(config.container, config.nifi_endpoint,
                         "nifi pg-enable-services --processGroupId {}".format(process_group['id']))
                process_groups.extend(__obtain_process_groups(config, process_group['id']))
        else:
            print("Invalid action: {} for process group {}; must be enable or disable".format(action, name))


def __obtain_multi_process_groups_info(config, names):
    all_process_groups = []
    process_groups = {}
    while len(process_groups) < len(names) or not all_process_groups:
        if not all_process_groups:
            all_process_groups.extend(__obtain_process_groups(config))
        else:
            id = all_process_groups.pop(0)['id']
            all_process_groups.extend(__obtain_process_groups(config, id))

        process_groups.update(__filter_process_groups_by_names(all_process_groups, names))
    return process_groups


def __filter_process_groups_by_names(process_groups, names):
    matched_groups = {}
    for group in process_groups:
        if group['name'] in names:
            matched_groups[group['name']] = group

    return matched_groups


def __obtain_process_groups(config, process_group_id=None):
    cmd = "nifi pg-list"
    if process_group_id:
        cmd = cmd + " --processGroupId " + process_group_id
    return call_cmd(config.container, config.nifi_endpoint, cmd)


def __filter_templates(templates, template_name):
    for template in templates:
        if template['template']['name'] == template_name:
            return template
    return None
