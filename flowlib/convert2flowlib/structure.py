import json
from .functions import process_group_identity, multiple_resources_with_no_connections, controller_services, processor_group_variables
from nipyapi.utils import fs_read, fs_write, dump

language_format = "yaml"


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

    def append_to_file_body(self, data: dict) -> None:
        for _y in [x for x in data]:
            if data[_y] is not None:
                self.file_body.update(data)

    def construct_flowlib_format(self, parent_pg=None, child_pgs=None) -> None:
        for process_group in child_pgs:
            if process_group["connections"]:
                self.append_to_file_body(process_group_identity(process_group))
                self.append_to_file_body(multiple_resources_with_no_connections(process_group))
                self.append_to_file_body(controller_services(process_group))
                self.append_to_file_body(processor_group_variables(process_group))
            else:
                self.append_to_file_body(process_group_identity(process_group))
                self.append_to_file_body(multiple_resources_with_no_connections(process_group))
                self.append_to_file_body(controller_services(process_group))
                self.append_to_file_body(processor_group_variables(process_group))

            # print(yaml.dump(self.file_body))
            # fs_write(yaml.dump(self.file_body), f"./flow.{language_format}")
            fs_write(dump(self.file_body, mode=language_format), f"./flow.{language_format}")
