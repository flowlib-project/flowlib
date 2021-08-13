import json
from .root_canvas import process_group_identity, multiple_resources_with_no_connections, controller_services, processor_group_variables
from .component_canvas import entry_for_parent_data_file_no_connections
from nipyapi.utils import fs_read, fs_write, dump
import os
import sys

language_format = "yaml"


def write_to_file(data, file_name) -> None:
    fs_write(dump(data, mode=language_format), f'{file_name}.{language_format}')


class NIFIFILECONTENTS:
    def __init__(self, registry_content_file, output_format):
        global language_format
        language_format = output_format

        self.flow_file_content = json.loads(fs_read(registry_content_file))

    def return_root_processor_group(self) -> list:
        if self.flow_file_content["flowContents"]:
            return [self.flow_file_content["flowContents"]]
        else:
            print("Did not find a root processor group")


class STRUCTURE:
    file_body = {}
    global_content = {}

    def component_directory(self, file_path: str) -> None:
        directories = file_path.split('/')[:-1]

        if directories[0] not in os.listdir():
            os.mkdir(directories[0])

        if directories[1] not in os.listdir(directories[0]):
            os.mkdir("/".join(directories))

    def append_to_file_body(self, data: dict) -> None:
        for _y in [x for x in data]:
            if data[_y] is not None:
                self.file_body.update(data)

    def write_to_files(self):
        for _keys in [x for x in self.global_content]:
            if "root" in _keys:
                write_to_file(self.global_content[_keys], "flow")

            elif "component" in _keys:
                file_path = f"components/common/{_keys.replace('-', '_')}"
                self.component_directory(file_path)
                write_to_file(self.global_content[_keys], file_path)

    def append_to_parent_canvas(self, data: dict, parent_processor_group: str) -> None:
        processor_group_data = {}

        for x in self.global_content:
            if parent_processor_group in x:
                processor_group_data.update(self.global_content[x])

        if "canvas" in [_x for _x in processor_group_data]:
            old_data = processor_group_data["canvas"]
            old_data.append(data)

        elif "process_group" in [_x for _x in processor_group_data]:
            old_data = processor_group_data["process_group"]
            old_data.append(data)

        else:
            msg = "* Process Group Names Not Unique *"
            totalMsg = "%s\n%s\n%s\n" % ("*"*len(msg), msg, "*"*len(msg))
            sys.exit(totalMsg)

    def append_component(self, data: dict) -> None:
        self.global_content.setdefault(data["name"].replace("-", "_"), {}).update(data)

    def construct_flowlib_format(self, parent_pg=None, child_pgs=None) -> None:
        def append_to_tmp(data):
            for _y in [_x for _x in data]:
                if data[_y] is not None:
                    _tmp.update(data)

        for process_group in child_pgs:
            if parent_pg is None:
                _tmp = {}

                if process_group["connections"]:
                    self.append_to_file_body(process_group_identity(process_group))
                    self.append_to_file_body(multiple_resources_with_no_connections(process_group))
                    self.append_to_file_body(controller_services(process_group))
                    self.append_to_file_body(processor_group_variables(process_group))
                else:
                    append_to_tmp(process_group_identity(process_group))
                    append_to_tmp(multiple_resources_with_no_connections(process_group))
                    append_to_tmp(controller_services(process_group))
                    append_to_tmp(processor_group_variables(process_group))

                    self.global_content.setdefault(
                        f'{process_group["name"]}_component'
                        if parent_pg is not None else f'root_{process_group["name"]}', {}).update(_tmp)

                    del _tmp

                    if process_group["processGroups"]:
                        self.construct_flowlib_format(parent_pg=process_group, child_pgs=process_group["processGroups"])

            else:
                if process_group["connections"]:
                    pass

                else:
                    structures = entry_for_parent_data_file_no_connections(process_group, language_format)
                    self.append_to_parent_canvas(structures[0], parent_pg["name"])
                    self.append_component(structures[1])

                    if process_group["processGroups"]:
                        self.construct_flowlib_format(parent_pg=process_group, child_pgs=process_group["processGroups"])
