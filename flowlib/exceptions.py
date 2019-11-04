# -*- coding: utf-8 -*-
class FlowLibException(Exception):
    pass

class FlowNotFoundException(FlowLibException):
    pass

class FlowValidationException(FlowLibException):
    pass
