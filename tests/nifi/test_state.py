# -*- coding: utf-8 -*-
import unittest

from flowlib.nifi.state import MAX_STATE_SIZE, ENCODING_VERSION, _serialize, _deserialize

class TestZookeeperSerDe(unittest.TestCase):

    def test_encode_decode(self):
        state = {
            'some-stateful-thing': 'a-stateful-value',
            'other-state': 'random stuff'
        }

        # check constants
        self.assertEqual(MAX_STATE_SIZE, 1024 * 1024)
        self.assertEqual(ENCODING_VERSION, b'\x01')

        encoded = _serialize(state)
        decoded = _deserialize(encoded.getvalue())
        self.assertEqual(decoded, state)


    def test_encode_invalid_state(self):
        state = {
            'invalid': 1,
        }
        self.assertRaises(AssertionError, _serialize, state)
        state = {
            1: 'invalid',
        }
        self.assertRaises(AssertionError, _serialize, state)
