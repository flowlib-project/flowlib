# -*- coding: utf-8 -*-
import re

from flowlib.exceptions import FlowValidationException


def check_connections(flow):
    pass

def check_name(name):
    name_regex = '^[a-zA-Z0-9-_]+$'
    pattern = re.compile(name_regex)
    if not pattern.match(name):
        raise FlowValidationException("Invalid name. '{}' must match the regular expression: '{}'".format(name, name_regex))


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
