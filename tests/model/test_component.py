# -*- coding: utf-8 -*-
import unittest

from .. import flowlib_test_utils


class TestComponent(unittest.TestCase):

    def test_load_init_components(self):
        for f in ['common/s3_write_with_retry.yaml', 'common/s3_list_fetch_with_retry.yaml', 'pdf/process_pdfs.yaml']:
            flowlib_test_utils.load_init_component(f)
