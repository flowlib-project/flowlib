# -*- coding: utf-8 -*-

class FlowLibBaseException(Exception):
    pass

class FlowLibException(FlowLibBaseException):
    pass

class FlowNotFoundException(FlowLibBaseException):
    pass

class FlowValidationException(FlowLibBaseException):
    pass
