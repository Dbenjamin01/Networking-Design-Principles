#UDP-Server python file
import socket
from PIL import Image

# identify serverPort, create UDP socket, bind socket to port
serverPort = 12500
imagebytes = bytearray()
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSocket.bind(("", serverPort))

# print ready message
print("The server is ready to receive.")

while True:
    # message, clientAddress = serverSocket.recvfrom(2048)
    loopcounter = 0 #loop counter that checks the while loop when adding broken up byte array to server-side array

    byte, clientAddress = serverSocket.recvfrom(2048) #receive byte from client
    if not byte: # if the server is no longer receiving data from the client, exit the receive loop
        #TODO: Loop should be exiting here, figure out why it isn't.
        break


    while loopcounter < len(byte): # byte comes in form of bytes. Bytes can be accessed like an array so go through byte[0]... byte[1]... and add them to an existing array
        imagebytes.append(byte[loopcounter])
        loopcounter += 1


    # byte is received from the client, begin reconstructing the image within the server here.
    print("Byte received...")
    print("Array Size: ")
    print(len(imagebytes))

print("Loop exited")

#TODO Exit the loop, add the bytes recevied from client and create an image out of them through PIL library
# repair image here, add the data together and create/show the image
img = Image.Image.frombytes("L", imagebytes)

# created image, show image here
print("Image Created")

#TODO Show image.
img.show()
