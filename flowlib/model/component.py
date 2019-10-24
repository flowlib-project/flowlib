# -*- coding: utf-8 -*-

class FlowComponent:
    def __init__(self, name, source_file, process_group, defaults=None, required_controllers=None, required_vars=None):
        """
        A reuseable component of a flow. Referenced by a ProcessGroup which is an instantiation of a FlowComponent
        """
        self.name = name
        self.source_file = source_file
        self.process_group = process_group
        self.defaults = defaults or dict()
        self.required_controllers = required_controllers or dict()
        self.required_vars = required_vars or list()

    def __repr__(self):
        return str(vars(self))
