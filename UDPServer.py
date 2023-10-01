#  UDP-Server python file

import socket

# Identify serverPort, create UDP socket, bind socket to port
serverPort = 12500
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSocket.bind(("", serverPort))

# print ready message
print("Waiting for number of Packets...")
numPackets = serverSocket.recv(1024)  # Get number of packets to determine length of for-loop.
print(f"Number of Packets: {numPackets.decode()}")

print("The server is ready to receive.")
file = open('serverside_image.bmp', "wb")  # Open file and write as binary

while True:
    
    for i in range(0, int(numPackets.decode())):
        byte = serverSocket.recv(1024)  # Store packet info into byte variable
        file.write(byte)  # Write received binary packet info into file

    file.close()  # Close file and allows user to open through OS


