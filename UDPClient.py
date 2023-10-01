#UDP-Client python file
import socket
import os
import time
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
imgname = "bitmap-img.bmp" # ref: https://www.digitalocean.com/community/tutorials/how-to-get-file-size-in-python
img = open("bitmap-img.bmp", "rb")
file_statistics = os.stat(imgname)
numbPackets = int((file_statistics.st_size / 1024 + 1))

clientSocket.sendto((str(numbPackets).encode()), (serverName, serverPort))# send file size to server to prepare for loop for receiving data.
time.sleep(3)
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
img.close()
clientSocket.close()
# read reply characters from previously created socket into string, print string
# modifiedMessage, serverAddress = clientSocket.recvfrom(2048)
# print("From server: ", modifiedMessage.decode())


