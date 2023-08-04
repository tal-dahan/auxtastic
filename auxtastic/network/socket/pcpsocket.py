import os
import queue
import signal
import logging
from io import BytesIO
from threading import Thread, Lock

from auxtastic.domain.audiosocket import AudioSocket
from auxtastic.domain.pcppacket import PCPPacket, PCPHeader, ACK, SYN, FIN, NACK
from auxtastic.network.modem.modem import Modem

ACK_TIMEOUT_SEC = 10
CONNECT_TIMEOUT_SEC = 10
MAX_TRIES = 5
MAX_FRAG_SIZE = 140


def required_state(func, state, self, error, *args, **kwargs):
    if state:
        return func(self, *args, **kwargs)
    else:
        raise Exception(error)


def required_connected(func):
    def wrapper(self, *args, **kwargs):
        return required_state(func, self.connected, self, 'socket isn\'t connected', *args, **kwargs)

    return wrapper


def required_listening(func):
    def wrapper(self, *args, **kwargs):
        return required_state(func, self.listening, self, 'socket isn\'t listening', *args, **kwargs)

    return wrapper


def required_not_connected(func):
    def wrapper(self, *args, **kwargs):
        return required_state(func, not self.connected, self, 'socket is connected', *args, **kwargs)

    return wrapper


def required_not_listening(func):
    def wrapper(self, *args, **kwargs):
        return required_state(func, not self.listening, self, 'socket is listening', *args, **kwargs)

    return wrapper


class Stream:
    def __init__(self, verbose=False):
        self.__logger = logging.getLogger('Stream')
        self.__logger.disabled = not verbose
        self.__buf = b''
        self.__lock = Lock()

    def read(self, n=-1):
        try:
            self.__lock.acquire()
            inp = BytesIO(self.__buf)
            b = inp.read(n)
            self.__buf = self.__buf[len(b):]

            return b
        except Exception as e:
            self.__logger.exeption(e)
        finally:
            self.__lock.release()

    def write(self, b):
        try:
            self.__lock.acquire()
            self.__logger.debug(f"write {len(b)}")
            outp = BytesIO()
            l = outp.write(b)
            self.__buf += outp.getvalue()

            return l
        except Exception as e:
            self.__logger.exeption(e)
        finally:
            self.__lock.release()


class RecvWorker(Thread):
    def __init__(self, modem, verbose=False):
        super().__init__()
        self.__logger = logging.getLogger('Socket|RecvWorker')
        self.__logger.disabled = not verbose
        self.modem = modem
        self.__stream = Stream(verbose=verbose)
        self.__is_alive = False
        self.__fin = False
        self.__last_seq_num = -1
        self.__acks = queue.Queue()

    def recv(self, buf_size):
        while True:
            d = self.__stream.read(buf_size)

            if d:
                self.__logger.debug(f"read {len(d)}")
                return d
            elif self.__fin:  # connection closed while recv
                return None

    def last_ack(self):
        return self.__acks.get()

    def start(self):
        self.__logger.debug(f"start")
        self.__is_alive = True
        super().start()

    def run(self):
        self.__logger.debug("run")

        while self.__is_alive:
            self.__logger.debug("wait for incoming")
            raw_pck = self.modem.recv(1024)
            pcp_pck = PCPPacket.from_bytes(raw_pck)

            if pcp_pck.validate_checksum():
                if FIN in pcp_pck.headers.flags:
                    self.__logger.debug(f"got FIN")
                    fin_ack_pcp = PCPPacket(headers=PCPHeader(flags=FIN | ACK))
                    self.modem.send(fin_ack_pcp.to_bytes())
                    self.__logger.debug("sent FIN ACK")
                    self.__fin = True
                elif ACK in pcp_pck.headers.flags:
                    self.__logger.debug("got ack")
                    self.__acks.put(pcp_pck)
                else:
                    # if we got a new packet
                    if self.__last_seq_num != pcp_pck.headers.seq_number:
                        payload = pcp_pck.payload
                        self.__logger.debug(f"{pcp_pck.headers.seq_number} | {payload} ({len(payload)})")
                        self.__stream.write(payload)
                    else:
                        self.__logger.debug(f"received duplicated packet {pcp_pck.headers.seq_number}. pass it")

                    # send ack for the received packet
                    pck_seq_number = pcp_pck.headers.seq_number
                    self.modem.send(PCPPacket(headers=PCPHeader(seq_number=pck_seq_number,
                                                                ack_number=pck_seq_number + 1,
                                                                flags=ACK)).to_bytes())
                    self.__last_seq_num = pck_seq_number
            else:
                self.modem.send(PCPPacket(headers=PCPHeader(seq_number=pcp_pck.headers.seq_number, flags=NACK)))

        self.__logger.debug("got killed")

    def kill(self):
        self.__logger.debug("killing")
        self.__is_alive = False


class PCPSocket(AudioSocket):
    def __init__(self, verbose=False):
        self.__logger = logging.getLogger("Socket")
        self.__logger.disabled = not verbose
        self.connected = False
        self.listening = False
        self.modem = Modem()
        self.__recv_thread = RecvWorker(self.modem, verbose=verbose)
        self.__timer = None

    @required_connected
    def recv(self, buf_size: int) -> bytes:
        d = self.__recv_thread.recv(buf_size)

        # connection closed
        if not d:
            self.connected = False
            self.listening = False
            self.__recv_thread.kill()

        return d

    @staticmethod
    def __timeout_callback(*args, **kwargs):
        raise TimeoutError

    def __start_timeout(self, secs):
        if os.name == 'posix':
            signal.signal(signal.SIGALRM, PCPSocket.__timeout_callback)
            signal.alarm(secs)
        elif os.name == 'nt':
            # self.__timer = threading.Timer(secs, self.__timeout_callback)
            # self.__timer.start()
            pass

    def __stop_timeout(self):
        if os.name == 'posix':
            signal.alarm(0)
        elif os.name == 'nt':
            #self.__timer.cancel()
            pass

    def __send_and_recv(self, pcp, buff_size) -> PCPPacket:
        self.modem.send(pcp.to_bytes())

        # set timeout for receiving ACK
        self.__start_timeout(ACK_TIMEOUT_SEC)

        # wait for ACK
        response = self.modem.recv(buff_size)
        #ack = self.__recv_thread.last_ack()

        self.__stop_timeout()

        pcp_res = PCPPacket.from_bytes(response)

        return pcp_res

    @required_connected
    def send(self, data: bytes) -> None:
        FIRST_SEQ = 1

        with BytesIO(data) as data_stream:
            cur_frag = data_stream.read(MAX_FRAG_SIZE - PCPHeader.SIZE)
            cur_seq = FIRST_SEQ

            while cur_frag:
                cur_try = 0
                pcp = PCPPacket(headers=PCPHeader(cur_seq), payload=cur_frag)

                while cur_try < MAX_TRIES:
                    try:
                        pcp_res = self.__send_and_recv(pcp, 1024)  # TODO: Change 1024
                    except TimeoutError:
                        self.__logger.debug(f"timeout {cur_try + 1}")
                        cur_try += 1
                    else:
                        if NACK in pcp_res.headers.flags:
                            self.__logger.debug(f"NACK {cur_try + 1}")
                            cur_try += 1
                        else:
                            break

                if cur_try == MAX_TRIES:
                    raise Exception("Failed to send packet")

                cur_seq += len(cur_frag)
                cur_frag = data_stream.read(MAX_FRAG_SIZE - 13)  # TODO: use pcp header size instead of zero

    @required_not_listening
    def listen(self) -> None:
        self.listening = True

    @required_listening
    def accept(self):
        self.__logger.debug(f'waiting for incoming connections')
        pck_bytes1 = self.modem.recv(1024)   # TODO: change to read the size of SYN packet
        pck_bytes1 = PCPPacket.from_bytes(pck_bytes1)
        self.__logger.debug(f'got connection')
        if pck_bytes1.contains_only_flags(SYN):    # received SYN packet
            self.__logger.debug(f'-> SYN')
            syn_ack_pck = PCPPacket(headers=PCPHeader(flags=SYN | ACK))
            self.modem.send(syn_ack_pck.to_bytes())    # send SYN ACK packet
            self.__logger.debug(f'<- SYN ACK')
            pck_bytes2 = self.modem.recv(1024)   # TODO: change to read the size of ACK packet
            pck_bytes2 = PCPPacket.from_bytes(pck_bytes2)

            if pck_bytes2.contains_only_flags(ACK):     # received SYN ACK packet
                self.__logger.debug(f'-> ACK')
                self.__recv_thread.start()
                self.connected = True
            else:
                raise Exception("didn't received ACK")
        else:
            raise Exception("first packet isn't SYN")

        self.__logger.debug(f'connection established')

    @required_not_connected
    def connect(self, timeout_secs=CONNECT_TIMEOUT_SEC) -> None:
        self.__start_timeout(timeout_secs)

        syn_pck = PCPPacket(headers=PCPHeader(flags=SYN))
        self.modem.send(syn_pck.to_bytes())
        self.__logger.debug(f'<- SYN')
        pck_bytes = self.modem.recv(1024)  # TODO: change to read the size of a SYN ACK packet
        pck_bytes = PCPPacket.from_bytes(pck_bytes)

        if pck_bytes.contains_only_flags(SYN, ACK):
            self.__logger.debug(f'-> SYN ACK')
            ack_pck = PCPPacket(headers=PCPHeader(flags=ACK))
            self.modem.send(ack_pck.to_bytes())
            self.__logger.debug(f'<- ACK')
            self.connected = True
            # self.__recv_thread.start()
        else:
            raise 'three-way handshake failure'

        self.__stop_timeout()

    @required_connected
    def close(self):
        fin_pck = PCPPacket(headers=PCPHeader(flags=FIN))
        self.modem.send(fin_pck.to_bytes())

        pck_bytes = self.recv(1024)  # TODO: change to FIN ACK pck size
        pck_bytes = PCPPacket.from_bytes(pck_bytes)

        if pck_bytes.contains_only_flags(FIN, ACK):
            self.listening = False
            self.connected = False
            self.__recv_thread.kill()
        else:
            raise "didn't get FIN ACK"
