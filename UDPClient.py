#UDP-Client python file
import socket
import rdt
from PIL import Image


#Use similar setup for communication in phase 1

# create server name, identify server port, and create UDP socket for server
serverName = '127.0.0.1'

# clients should use an ephemeral  port and CONNECT to the server port.
ephemeralPort = (serverName,12000)  # ref: https://stackoverflow.com/questions/68548331/client-and-server-connection-with-different-port-numbers
serverPort = 12500  # identify the server port within the client, but have the client initialize its own port

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# import image using relative directory of image file path
img = Image.open("bitmap-img.bmp")
# img.show() test to verify that the image is properly found and imported into pycharm, is working.

rdt.rdt_send(img)

packet = rdt.make_pkt(img)

rdt.udt_send(packet)

