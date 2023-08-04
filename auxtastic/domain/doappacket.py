import dataclasses
from io import BytesIO

from auxtastic.utils.serialization import serialize_int, deserialize_int

DOAP_DELIMITER = ":doap:".encode('utf-8')


@dataclasses.dataclass
class DOAPType:
    FILE = 0b00000001


class DOAPHeader:
    DOAP_TYPE_LENGTH = 1
    DOAP_HEADER_SIZE = DOAP_TYPE_LENGTH

    def __init__(self, doap_type: DOAPType):
        self.type = doap_type

    def __str__(self):
        return f"[TYPE: {self.type}]"

    @classmethod
    def from_bytes(cls, doap_header_bytes: bytes):
        doap_header_bytes_stream = BytesIO(doap_header_bytes)
        doap_type = deserialize_int(doap_header_bytes_stream.read(DOAPHeader.DOAP_TYPE_LENGTH))

        return cls(doap_type)

    def to_bytes(self) -> bytes:
        doap_type_bytes = serialize_int(self.type, DOAPHeader.DOAP_TYPE_LENGTH)

        return doap_type_bytes


class DOAPPacket:
    def __init__(self, header: DOAPHeader, body: bytes):
        self.header = header
        self.body = body

    def __str__(self):
        return f"{str(self.header)} // {len(self.body)} bytes of payload"

    @classmethod
    def from_bytes(cls, doap_bytes: bytes):
        doap_bytes_stream = BytesIO(doap_bytes)

        header = DOAPHeader.from_bytes(doap_bytes_stream.read(DOAPHeader.DOAP_HEADER_SIZE))
        body = doap_bytes_stream.read()
        body = body[:(-1 * len(DOAP_DELIMITER))]  # remove delimiter from the end

        return cls(header, body)

    def to_bytes(self):
        return self.header.to_bytes() + self.body + DOAP_DELIMITER
