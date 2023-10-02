#  UDP-Client python file
import socket
import os  # Used to create file statistics such as name
import time  # Used to sleep threads in real time
import math  # Used to fix rounding error

# Create server name, identify server port, and create UDP socket for server
serverName = '127.0.0.1'

# Clients should use an ephemeral  port and CONNECT to the server port.
ephemeralPort = (serverName,12000)  # ref: https://stackoverflow.com/questions/68548331/client-and-server-connection-with-different-port-numbers
serverPort = 12500  # Identify the server port within the client, but have the client initialize its own port

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# import image using relative directory of image file path
# "bitmap-img.bmp" <- file name
imgName = "bitmap-img.bmp"  # ref: https://www.digitalocean.com/community/tutorials/how-to-get-file-size-in-python
img = open("bitmap-img.bmp", "rb")
file_statistics = os.stat(imgName)
numbPackets = int(math.ceil((file_statistics.st_size / 1024)))  # This ensures that there is room for remaining datagram
                                                                # to be sent if division does not result in int

clientSocket.sendto((str(numbPackets).encode()), (serverName, serverPort))  # Send file size to server to prepare for loop for receiving data.
time.sleep(3)  # Sleep thread to allow time for server to process information

byte = img.read(1024)  # Creates packet size of 1024

print("Sending bytes to Server...")
while byte:
    # Send the outstanding byte
    # once sent, get a new byte, of size 1024, from the image,
    # repeat loop until there are no bytes left within the image.

    # Must send by one byte at a time.
    clientSocket.sendto(byte, (serverName, serverPort))
    byte = img.read(1024)

print("No more bytes left to send")
img.close()
clientSocket.close()



