from .root_canvas import controller_services, processor_group_variables, multiple_resources_with_no_connections, multiple_resources_with_connections, processor_group_connection

component_dir = "common"
language_format = ""


def create_component_name(component_name: str) -> str:
    component_full_path = f'{component_dir}/{component_name}_component.{language_format}'
    return component_full_path

def cleanup_multiple_resources_with_no_connections(data: dict) -> dict:
    content = multiple_resources_with_no_connections(data)
    old_data = content["canvas"]
    component_processor_group_data = {
        "name": create_component_name(data["name"]).replace("_", "-").split("/")[1].split(".")[0],
        "process_group": old_data
    }

    return component_processor_group_data

def cleanup_multiple_resources_with_connections(data: dict) -> dict:
    content = multiple_resources_with_connections(child_process_group_data=data)
    old_data = content["canvas"]
    component_processor_group_data = {
        "name": create_component_name(data["name"]).replace("_", "-").split("/")[1].split(".")[0],
        "process_group": old_data
    }

    return component_processor_group_data

def entry_for_parent_data_file_no_connections(data: dict, output_format: str) -> tuple:
    global language_format
    language_format = output_format

    parent_structure = {
        "name": data["name"],
        "type": data["componentType"].lower(),
        "component_path": create_component_name(data["name"].replace("-", "_"))
    }

    if controller_services(data)["controller_services"] is not None:
        parent_structure.update({"controller_services": controller_services(data)})

    if processor_group_variables(data)["global_vars"] is not None:
        parent_structure.update({"bars": processor_group_variables(data)["global_vars"]})

    component_structure = cleanup_multiple_resources_with_no_connections(data)

    return parent_structure, component_structure

def entry_for_parent_data_file_with_connections(data: dict, output_format: str, parent_pg: dict) -> None:
    global language_format
    language_format = output_format

    parent_structure = {
        "name": data["name"],
        "type": data["componentType"].lower(),
        "component_path": create_component_name(data["name"].replace("-", "_"))
    }

    if controller_services(data)["controller_services"] is not None:
        parent_structure.update({"controller_services": controller_services(data)})

    if processor_group_variables(data)["global_vars"] is not None:
        parent_structure.update({"bars": processor_group_variables(data)["global_vars"]})


    pg_connections = processor_group_connection(parent_pg, data)

    if pg_connections:
        parent_structure.update({"connections": pg_connections})

    component_structure = cleanup_multiple_resources_with_connections(data)

    return parent_structure, component_structure