# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound

__author__ = "B23"

try:
    __version__ = get_distribution('b23-flowlib').version
except DistributionNotFound:
    # package is not installed
    pass
