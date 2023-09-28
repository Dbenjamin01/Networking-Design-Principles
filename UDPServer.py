#UDP-Server python file
import socket
import rdt

# identify serverPort, create UDP socket, bind socket to port
serverPort = 12500
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSocket.bind(("", serverPort))

# print ready message
print("The server is ready to receive.")

while True:
    # message, clientAddress = serverSocket.recvfrom(2048)
    rdt.rdt_rcv(2048)
    print("Image received...")
    rdt.extract()
    print("Sending: ", modifiedMessage, " to Client")
    serverSocket.sendto(modifiedMessage.encode(), clientAddress)