# -*- coding: utf-8 -*-
import io
import struct

from kazoo.client import KazooClient
from kazoo.security import CREATOR_ALL_ACL, OPEN_ACL_UNSAFE

from flowlib.model import FlowLibException

MAX_STATE_SIZE = 1024 * 1024
ENCODING_VERSION = b'\x01'


class ZookeeperClient:

    def __init__(self, connection, root_node='/nifi', acl='open'):
        """
        A zookeeper client for connecting to NiFi's zookeeper state backend
        :param connection: Zookeeper connection string
        :type connection: str
        :param root_node: The root zookeeper node where NiFi stores its state (defaults to /nifi)
        :type root_node: str
        :param acl: The zookeeper ACL to set when creating the znode
        :type acl: kazoo.security.ACL
        """
        self.connection = connection
        self.root_node = root_node

        if acl not in ['open', 'creator']:
            raise FlowLibException("Invalid zookeeper ACL, must be one of [open, creator]")
        self.acl = CREATOR_ALL_ACL if acl == 'creator' else OPEN_ACL_UNSAFE

        self.client = KazooClient(hosts=self.connection)
        self.client.start()

    def set_processor_state(self, processor_id, state):
        """
        Set the state in zookeeper for a given processor
        :param processor_id: The NiFi uuid of the processor
        :type processor_id: str
        :param state: The state k,v pairs to set in zookeeper
        :type state: dict(str:str)
        """
        serialized = _serialize(state)
        size = serialized.seek(0, 2)
        if size > MAX_STATE_SIZE:
            raise FlowLibException("Processor state size cannot exceed {} bytes but the serialized size is {} bytes".format(MAX_STATE_SIZE, size))

        # ensure node exists with the specified acl
        path = '{}/components/{}'.format(self.root_node, processor_id)
        if self.client.exists(path):
            self.client.set_acls(path, acls=self.acl)
        else:
            self.client.create(path, acl=self.acl, makepath=True)

        # set value
        self.client.set(path, serialized.getvalue())

    def get_processor_state(self, processor_id):
        """
        Get the state from zookeeper for a given processor
        :param processor_id: The NiFi uuid of the processor
        :type processor_id: str
        :returns: dict(str:str) The state k,v pairs to set in zookeeper
        """
        path = '{}/components/{}'.format(self.root_node, processor_id)
        if self.client.exists(path):
            return _deserialize(self.client.get(path)[0])
        else:
            raise FlowLibException("Processor state does not exist at: {}".format(path))


def _serialize(state):
    """
    Serialize the k,v pairs so they can be written to zookeeper.
      NiFi k,v serializer: https://github.com/apache/nifi/blob/d148fb18540b410361a91f22e421867910d2f7c9/nifi-nar-bundles/nifi-framework-bundle/nifi-framework/nifi-framework-core/src/main/java/org/apache/nifi/controller/state/providers/zookeeper/ZooKeeperStateProvider.java#L232

    :param state: The state for a given processor as k,v pairs
    :type state: dict(str:str)
    :returns: io.BytesIO
    """
    def encode_and_write_string(b, s):
        """
        Writing modified-utf-8 in python: https://stackoverflow.com/a/1393579
        :type b: io.BytesIO
        :type s: str
        """
        encoded = s.encode('utf-8')
        length = len(encoded)
        b.write(struct.pack('>H', length))
        fmt = '>' + str(length) + 's'
        b.write(struct.pack(fmt, encoded))

    buf = io.BytesIO()
    buf.write(ENCODING_VERSION)
    buf.write(struct.pack(">I", len(state.keys())))
    for k,v in state.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
        has_key = True if k else False
        has_value = True if v else False

        buf.write(struct.pack(">?", has_key))
        if has_key:
            encode_and_write_string(buf, k)

        buf.write(struct.pack(">?", has_value))
        if has_value:
            encode_and_write_string(buf, v)

    return buf


def _deserialize(b):
    """
    Deserialize the binary value read from zookeeper back to a processor's state k,v pairs.
      NiFi k,v deserializer: https://github.com/apache/nifi/blob/d148fb18540b410361a91f22e421867910d2f7c9/nifi-nar-bundles/nifi-framework-bundle/nifi-framework/nifi-framework-core/src/main/java/org/apache/nifi/controller/state/providers/zookeeper/ZooKeeperStateProvider.java#L254

    :param b: The state for a given processor as binary
    :type b: bytes
    :returns: dict(str:str)
    """
    def read_and_decode_string(buf):
        """
        :type buf: io.BytesIO
        """
        length = struct.unpack('>H', buf.read(struct.calcsize('>H')))[0]
        fmt = '>' + str(length) + 's'
        b = struct.unpack(fmt, buf.read(struct.calcsize(fmt)))[0]
        return b.decode('utf-8')

    buf = io.BytesIO(b)
    state = dict()

    encoding_version = buf.read(1)
    if encoding_version > ENCODING_VERSION:
        raise FlowLibException("The processor's state in zookeeper was encoded with {} but FlowLib can only decode messages up to version {}".format(encoding_version, ENCODING_VERSION))

    num_keys = struct.unpack(">I", buf.read(struct.calcsize(">I")))[0]
    for i in range(num_keys):
        has_key = struct.unpack(">?", buf.read(struct.calcsize(">?")))[0]
        key = read_and_decode_string(buf) if has_key else None
        has_value = struct.unpack(">?", buf.read(struct.calcsize(">?")))[0]
        value = read_and_decode_string(buf) if has_value else None
        state[key] = value

    return state
