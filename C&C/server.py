import logging

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from threading import Thread
import smtplib
import urllib.request

DIR = "/"
USER = 'user'
PASS = '12345'
PERM = 'elradfmwMT'
HOST = ''
PORT = 5001
GMAIL_USER = ''
GMAIL_PASSWORD = ''
SUBJECT = "New file has arrived"


def send_email(file_path):
    # host_ip_address = urllib.request.urlopen('https://ident.me').read().decode('utf8')

    file_url = HOST + ':8080/server/' + file_path.split('/')[-1]
    sent_from = GMAIL_USER
    to = [GMAIL_USER]
    message = 'Subject: {}\n\n{}'.format(SUBJECT, file_url)

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(sent_from, to, message)
        server.close()

        print('Email sent!')
    except:
        print('Something went wrong...')


class PythoFtpServer(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        authorizer = DummyAuthorizer()
        # Define a new user having full r/w permissions and a read-only
        # anonymous user
        authorizer.add_user(USER, PASS, DIR, perm=PERM)
        authorizer.add_anonymous(DIR)
        handler = CustomFtpHandler
        handler.authorizer = authorizer
        address = (HOST, PORT)
        self.server = FTPServer(address, handler)

    def run(self):
        Thread.run(self)
        logging.info("starting...")
        self.server.serve_forever()


class CustomFtpHandler(FTPHandler):

    def on_file_sent(self, file):
        """Called every time a file has been succesfully sent.
        "file" is the absolute name of the file just being sent.
        """

    def on_file_received(self, file):
        """Called every time a file has been succesfully received.
        "file" is the absolute name of the file just being received.
        """
        print(file)
        logging.info("got file")
        send_email(file)

    def on_incomplete_file_sent(self, file):
        """Called every time a file has not been entirely sent.
        (e.g. ABOR during transfer or client disconnected).
        "file" is the absolute name of that file.
        """

    def on_incomplete_file_received(self, file):
        """Called every time a file has not been entirely received
        (e.g. ABOR during transfer or client disconnected).
        "file" is the absolute name of that file.
        """

    def on_login(self, username):
        """Called on user login."""

    def on_login_failed(self, username, password):
        """Called on failed user login.
        At this point client might have already been disconnected if it
        failed too many times.
        """

    def on_logout(self, username):
        """Called when user logs out due to QUIT or USER issued twice."""


pyftp = PythoFtpServer()
pyftp.run()
