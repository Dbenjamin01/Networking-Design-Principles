#UDP-Client python file
import socket
from PIL import Image


#Use similar setup for communication in phase 1

# create server name, identify server port, and create UDP socket for server
serverName = '127.0.0.1'

# clients should use an ephemeral  port and CONNECT to the server port.
ephemeralPort = (serverName,12000)  # ref: https://stackoverflow.com/questions/68548331/client-and-server-connection-with-different-port-numbers
serverPort = 12500  # identify the server port within the client, but have the client initialize its own port

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# import image using relative directory of image file path
# "bitmap-img.bmp" <- file name
img = open("bitmap-img.bmp", "rb")
# img.show() test to verify that the image is properly found and imported into pycharm, is working.

# simulate conversion of the file into packets to send over to the server.

# to do so, break up the file into bytes, and send each byte to the server

byte = img.read(1024)

print("Sending bytes to Server...")
while byte:
    # send the outstanding byte
    # once sent, get a new byte, of size 1024, from the image,
    # repeat loop until there are no bytes left within the image.

    # we must send by one byte at a time.
    clientSocket.sendto(byte, (serverName, serverPort))
    byte = img.read(1024)


# await reply
print("No more bytes left to send")
# read reply characters from previously created socket into string, print string
modifiedMessage, serverAddress = clientSocket.recvfrom(2048)
print("From server: ", modifiedMessage.decode())
clientSocket.close()

