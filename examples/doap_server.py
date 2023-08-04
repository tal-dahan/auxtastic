import logging

from auxtastic.network.doap.doap import Server

logging.basicConfig(format="[%(name)s] [%(levelname)s] >> %(message)s", level=logging.DEBUG)
doap_server = Server(verbose=True)

doap_server.start()
