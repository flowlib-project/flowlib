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
        processor_group_data = [_root_key for _root_key in [x for x in self.global_content] if parent_processor_group == _root_key.split("_")[1]]
        if len(processor_group_data) == 1:
            old_data = self.global_content[processor_group_data[0]]["canvas"]
            old_data.append(data)
        else:
            msg = "* Process Group Names Not Unique *"
            totalMsg = "%s\n%s\n%s\n" % ("*"*len(msg), msg, "*"*len(msg))
            sys.exit(totalMsg)

    def append_component(self, data: dict) -> None:
        self.global_content.setdefault(data["name"], {}).update(data)

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

                    if [x for x in child_pgs if x["processGroups"]]:
                        self.construct_flowlib_format(parent_pg=child_pgs, child_pgs=[x["processGroups"] for x in child_pgs if x["processGroups"]][0])

            else:
                if process_group["connections"]:
                    pass

                else:
                    structures = entry_for_parent_data_file_no_connections(process_group, language_format)
                    self.append_to_parent_canvas(structures[0], [x["name"] for x in parent_pg][0])
                    self.append_component(structures[1])





            # The below is the old way of doing it for the moment
            #     self.append_to_file_body(process_group_identity(process_group))
            #     self.append_to_file_body(multiple_resources_with_no_connections(process_group))
            #     self.append_to_file_body(controller_services(process_group))
            #     self.append_to_file_body(processor_group_variables(process_group))
            #
            #     write_to_file(self.file_body, self.create_component(process_group['name'], parent_pg))
            #
            # # if [x for x in child_pgs if x["processGroups"]]:
            # #     self.construct_flowlib_format(parent_pg=child_pgs, child_pgs=[x["processGroups"] for x in child_pgs
            # #                                                                   if x["processGroups"]][0])

