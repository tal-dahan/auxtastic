"""
Client that sends the file (uploads)
"""

import ftplib
from io import BytesIO
from datetime import datetime

PORT = 5001
HOST = "192.168.68.115"
USER = 'user'
PASS = '12345'


def send_to_ftp(data):
    now = datetime.now()
    fname = now.strftime("%d-%m-%Y-%H-%M-%S.zip")
    ftp = ftplib.FTP()
    ftp.connect(HOST, PORT)
    ftp.login(USER, PASS)
    ftp.storbinary(f'STOR {fname}', BytesIO(data))  # send the file
    ftp.close()


if __name__ == "__main__":
    file = open("/Users/avivrabinovich/Desktop/temp/a.jpeg", 'rb')
    send_to_ftp(file)
    file.close()
