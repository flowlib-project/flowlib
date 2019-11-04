# -*- coding: utf-8 -*-
import re

from flowlib.exceptions import FlowValidationException
from flowlib.model.flow import InputPort, OutputPort, ProcessGroup, RemoteProcessGroup, Processor


def check_connections(flow, elements):
    """
    Recursively checks the connections between elements defined in the Flow to see if they are valid
    :param flow: The Flow to check connections for
    :type flow: Flow
    :param elements: a list of FlowElements to connect together
    :type elements: list(FlowElement)
    """
    for el in elements.values():
        if isinstance(el, ProcessGroup):

            # Check that every connection defines a from_port and that the from_port exists as an OutputPort in the component
            if isinstance(el, ProcessGroup):
                for c in el.connections:
                    if not c.from_port:
                        raise FlowValidationException('ProcessGroup {} does not define a from_port for connection {}'.format(el.name, c.name))

                    ops = [op.name for op in el._elements.values() if isinstance(op, OutputPort)]
                    if not c.from_port in ops:
                        raise FlowValidationException('ProcessGroup {} does not define an OutputPort named {}, must be one of: {}'.format(el.name, c.from_port, ops))


            # Recursively check the connections for the children elements of the ProcessGroup
            check_connections(flow, el._elements)
        elif el.type in ['input_port', 'output_port', 'remote_process_group', 'processor']:
            _check_element_connections(flow, el)
        else:
            raise FlowValidationException("Unsupported Element Type: {}".format(el.type))


def check_name(name):
    name_regex = '^[a-zA-Z0-9-_]+$'
    pattern = re.compile(name_regex)
    if not pattern.match(name):
        raise FlowValidationException("Invalid name '{}'. Names must match the regular expression: '{}'".format(name, name_regex))


def is_component_circular(flow, pg_element):
    """
    Check whether any of the ProcessGroup's ancestors are an instance of this
    component. That would mean that there is a circular component relationship which
    would cause a recursive depth exception to be raised.
    """
    this_component = pg_element.component_path
    parent = flow.get_parent_element(pg_element)
    while parent:
        if hasattr(parent, 'component_path'):
            if parent.component_path == this_component:
                return True
        parent = flow.get_parent_element(parent)
    return False


def _check_element_connections(flow, source_element):
    """
    Validate the connections for a single element
    :param flow: The Flow to check connections for
    :type flow: Flow
    :param element: A FlowElement with to validate
    :type element: FlowElement
    """
    parent = flow.get_parent_element(source_element)

    # TODO: See https://github.com/B23admin/b23-flowlib/issues/50
    # We should consider allowing input/output port connections for a flow
    # so they can be referenced via a jinja helper lookup similar to the controller lookup

    # Validate no inputs or outputs on the root canvas
    if not parent and (isinstance(source_element, InputPort) or isinstance(source_element, OutputPort)):
        raise FlowValidationException("Input and Output ports are not allowed in the root process group")

    # If source is an output_port then the downstream connections are the parent's connections
    if isinstance(source_element, OutputPort):
        # We're only interested in connections from the current output port
        if parent.connections:
            connections = [c for c in parent.connections if c.from_port == source_element.name]
        else:
            connections = None
    else:
        connections = source_element.connections

    if connections:
        for c in connections:
            if isinstance(source_element, (InputPort, Processor, RemoteProcessGroup)):
                elements = parent._elements
            elif isinstance(source_element, OutputPort):
                # If source is an output port then we need to to search the
                # parent's elements for the destination element
                elements = flow.get_parent_element(parent)._elements
            else:
                raise FlowValidationException("Elements of type {} do not support downstream connections".format(type(source_element)))

            dest_element = elements.get(c.name)
            if not dest_element:
                raise FlowValidationException("The destination element {} is not defined, must be one of: {}".format(c.name, elements.keys()))

            if isinstance(dest_element, ProcessGroup):
                if not c.to_port:
                    raise FlowValidationException('ProcessGroup {} does not define a to_port for connection {}'.format(source_element.name, c.name))
                ips = [ip.name for ip in dest_element._elements if isinstance(ip, InputPort)]
                if not c.to_port in ips:
                    raise FlowValidationException('ProcessGroup {} does not define an InputPort named {}, must be one of: {}'.format(dest_element.name, c.to_port, ips))
