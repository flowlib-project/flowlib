# -*- coding: utf-8 -*-

class FlowComponent:
    def __init__(self, name, source_file, process_group, raw, defaults=dict(), required_controllers=dict(), required_vars=[]):
        """
        A reuseable component of a flow. Referenced by a ProcessGroup which is an instantiation of a FlowComponent
        """
        self.name = name
        self.source_file = source_file
        self.defaults = defaults
        self.required_controllers = required_controllers
        self.required_vars = required_vars
        self.process_group = process_group
        self.raw = raw

    def __repr__(self):
        return str(vars(self))
