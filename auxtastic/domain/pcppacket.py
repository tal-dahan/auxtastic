import hashlib

from auxtastic.utils.serialization import serialize_int, deserialize_int
import io

PCP_MAGIC = 0x69

ACK = 0b00000001
SYN = 0b00000010
FIN = 0b00000100
NACK = 0b00001000
FLAGS = [ACK, SYN, FIN, NACK]

DEFAULT_SEQ_NUM = 0
DEFAULT_ACK_NUM = 0
DEFAULT_FLAGS = []

MAGIC_LENGTH = 1
SEQ_NUM_LENGTH = 4
ACK_NUM_LENGTH = 4
FLAGS_LENGTH = 2
CHECKSUM_LENGTH = 2


class PCPHeader:
    SIZE = MAGIC_LENGTH + SEQ_NUM_LENGTH + ACK_NUM_LENGTH + FLAGS_LENGTH + CHECKSUM_LENGTH

    def __init__(self,
                 seq_number: int = DEFAULT_SEQ_NUM,
                 ack_number: int = DEFAULT_ACK_NUM,
                 flags: int = DEFAULT_FLAGS):
        self.magic = PCP_MAGIC
        self.seq_number = seq_number
        self.ack_number = ack_number
        self._flags = flags
        self.checksum = None    # to be calculated

    @property
    def flags(self):
        return PCPHeader.__extract_flags_from_number(self._flags)

    @flags.setter
    def flags(self, flags):
        self._flags = flags

    @staticmethod
    def __extract_flags_from_number(flags_byte: int):
        flags = [flag for flag in FLAGS if flags_byte & flag]

        return flags

    @classmethod
    def from_bytes(cls, header_bytes: bytes):
        header_bytes_stream = io.BytesIO(header_bytes)

        magic = header_bytes_stream.read(MAGIC_LENGTH)

        if deserialize_int(magic) != PCP_MAGIC:
            raise ValueError('invalid PCP bytes format')
        else:
            seq_number = deserialize_int(header_bytes_stream.read(SEQ_NUM_LENGTH))
            ack_number = deserialize_int(header_bytes_stream.read(ACK_NUM_LENGTH))
            flags = deserialize_int(header_bytes_stream.read(FLAGS_LENGTH))
            checksum = deserialize_int(header_bytes_stream.read(CHECKSUM_LENGTH))

            header = cls(seq_number, ack_number, flags)
            header.checksum = checksum

            return header

    def to_bytes(self) -> bytes:
        magic = serialize_int(self.magic, MAGIC_LENGTH)
        seq_number_bytes = serialize_int(self.seq_number, SEQ_NUM_LENGTH)
        ack_number = serialize_int(self.ack_number, ACK_NUM_LENGTH)
        flags = serialize_int(self._flags, FLAGS_LENGTH)
        checksum = serialize_int(self.checksum, CHECKSUM_LENGTH)

        return magic + seq_number_bytes + ack_number + flags + checksum


class PCPPacket:
    MAGIC_LENGTH = 1

    def __init__(self, headers: PCPHeader, payload: bytes = None):
        self.headers = headers
        self.payload = payload
        self.headers.checksum = self.calc_checksum()

    def __sum_16bit(self):
        pck_bytes = self.to_bytes()
        bytes_length = len(pck_bytes)
        acc = 0

        # sum all 16-bit chunks
        for i in range(bytes_length, 1, -2):
            word = pck_bytes[bytes_length - i] + (pck_bytes[bytes_length - i + 1] << 8)  # takes 2-bytes chunk
            acc += word

        # if there is a single 8-bytes left at the end, add it
        if i > 2:
            acc += pck_bytes[bytes_length - 1]

        return (acc >> 16) + (acc & 0xffff)  # takes all the overflowed bits and adds them into a 2-bytes sum

    def calc_checksum(self) -> int:
        cur_checksum_value = self.headers.checksum  # saved for restoration
        self.headers.checksum = 0   # dummy checksum header value

        try:
            acc = self.__sum_16bit()
            checksum = ~acc & 0xffff   # make 2's complement

            return checksum
        except Exception:
            raise Exception('error calculating packet\'s checksum')
        finally:
            self.headers.checksum = cur_checksum_value  # restore checksum value

    def validate_checksum(self):
        acc = self.__sum_16bit()

        return acc == 0xffff

    def contains_only_flags(self, *args):
        return len(args) == len(self.headers.flags) and [flag for flag in args if flag not in self.headers.flags] == []

    @classmethod
    def from_bytes(cls, packet_bytes: bytes):
        packet_bytes_stream = io.BytesIO(packet_bytes)

        headers_bytes = packet_bytes_stream.read(PCPHeader.SIZE)
        headers = PCPHeader.from_bytes(headers_bytes)
        payload = packet_bytes_stream.read(512)  # examine the size, may be empty

        return cls(headers=headers, payload=payload)

    def to_bytes(self) -> bytes:
        serialized_headers = self.headers.to_bytes()
        serialized_pck = serialized_headers

        if self.payload:
            serialized_pck += self.payload

        return serialized_pck
