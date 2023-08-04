import os
import logging
from zipfile import ZipFile
from datetime import datetime as dt

from auxtastic.network.socket import socket
from auxtastic.domain.doappacket import DOAPPacket, DOAPHeader, DOAPType, DOAP_DELIMITER
from auxtastic.utils.ftp import send_to_ftp


def index_of(target, val):
    try:
        return target.index(val)
    except ValueError:
        return None


class Client:
    def __init__(self, verbose=False):
        self.__soc = socket.socket(verbose=verbose)
        self.__logger = logging.getLogger('DOAP Client')

    def connect(self):
        try:
            self.__soc.connect()
            self.__logger.info("connected to server")
        except TimeoutError as e:
            self.__logger.exception(e)
            raise Exception("error connection to server")

    def close(self):
        self.__soc.close()
        self.__logger.info("exiting...")

    def send_file(self, file_path):
        self.__logger.info(f"sending file '{file_path}'")
        temp_zip_name = f"{dt.now().strftime('%m-%d-%Y-%H-%M-%S')}.zip"

        with ZipFile(temp_zip_name, 'w') as temp_zip:
            temp_zip.write(file_path)

        with open(temp_zip_name, 'rb') as sent_file:
            file_bytes = sent_file.read()
            doap_pck = DOAPPacket(header=DOAPHeader(doap_type=DOAPType.FILE), body=file_bytes)  # build doap file packet
            self.__soc.send(doap_pck.to_bytes())  # send it through the socket

        self.__logger.info("finished sending file")
        os.remove(temp_zip_name)  # deletes the temp-zip file
        self.__logger.info("cleaning up...")


class Server:
    def __init__(self, verbose=False):
        self.__logger = logging.getLogger('DOAP Server')
        self.__soc = socket.socket(verbose=verbose)
        self.__ftp_client = None

    def start(self):
        # forever server clients
        while True:
            self.__logger.info("start listening...")
            self.__soc.listen()
            self.__logger.info("waiting for connection")
            self.__soc.accept()
            self.__logger.info("client connected")

            raw_doap_pck = b''

            # serve single client as long as he hasn't closed the connection
            while True:
                data = self.__soc.recv(1024)

                if not data:
                    self.__logger.info("client disconnected")
                    break
                else:
                    delimiter_idx = index_of(data, DOAP_DELIMITER)

                    # the whole packet in bigger than the read bytes
                    if not delimiter_idx:
                        raw_doap_pck += data
                    else:  # we have found the end of the packet
                        raw_doap_pck += data[:delimiter_idx + len(DOAP_DELIMITER)]  # we read to the end
                        doap_pck = DOAPPacket.from_bytes(raw_doap_pck)  # we convert to DOAPPacket object
                        self.__handle_incoming_pck(doap_pck)
                        raw_doap_pck = data[delimiter_idx:delimiter_idx + len(DOAP_DELIMITER)]  # we start buffering the next packet received by the socket

    def __handle_incoming_pck(self, doap_pck: DOAPPacket):
        self.__logger.info(f"handle packet {str(doap_pck)}")

        if doap_pck.header.type == DOAPType.FILE:
            self.__file_handler(doap_pck)

    def __file_handler(self, doap_pck):
        self.__logger.info(f"sending to FTP Server")
        file = doap_pck.body

        send_to_ftp(file)
