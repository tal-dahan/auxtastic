import logging

from auxtastic.network.doap.doap import Client

logging.basicConfig(format="[%(name)s] [%(levelname)s] >> %(message)s", level=logging.DEBUG)
doap_client = Client(verbose=True)

doap_client.connect()
doap_client.send_file(r"C:\Users\X\Downloads\top_secret.txt")
doap_client.close()
