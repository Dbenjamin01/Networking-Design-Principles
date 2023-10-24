from socket import *
from threading import Thread
from time import sleep
import argparse
import os
import math
import random

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--ack", type=int, default=0)
parser.add_argument("-d", "--data", type=int, default=0)


class Packet():
    def build():
        pass
    def extract():
        pass
    def checksum(self, msg: bytes, seq):
        msg = int.from_bytes(msg, "big")
        carry_add = lambda a,b: ((a + b) & 0xffff) + ((a + b) >> 16)
        csum = 0
        csum = carry_add(csum, seq)
        while msg != 0:
            bits = msg & 0xffff
            csum = carry_add(csum, bits)
            msg = msg >> 16
        return ~csum & 0xffff

class Server(Thread):
    def __init__(self, data_err):
        Thread.__init__(self)
        ip = '127.0.0.1'
        port = 12000
        address = (ip, port)
        self.server_socket = socket(AF_INET, SOCK_DGRAM)
        self.server_socket.bind(address)
        self.packet_size = 1024
        self.data_err = data_err / 100
        self.image = "penguin.bmp"

    def send_image(self):
        packet = b''
        err_pkts = []
        counter = 0
        with open(self.image, 'rb') as img:
            num_pkts = str(int(math.ceil(os.fstat(img.fileno()).st_size / self.packet_size))).encode()
            # List of packets when to send bad data:
            err_pkts = random.sample(range(1, num_pkts + 1), int(num_pkts * self.data_err))
            # Need new packet making function with seqnum and checksum
            packet = num_pkts
            print("SERVER | Sending image packets...")
            while packet:
                self.server_socket.sendto(packet, self.client_address)
                """
                Add recv for ACK, if bad rerun iteration without updating packet

                Add bad data corrupt the data AFTER creating packet
                """
                # Change to new packet making function
                packet = img.read(self.packet_size)
                if counter in err_pkts:
                    # Corrupt the data
                    err_pkts.remove(counter) # remove from list so it doesn't loop infinitely
                    pass
                counter += 1 # Only increase counter on good ACK
                sleep(0.05)
        print("SERVER | Transmission completed")

    def run(self):
        print("SERVER | Server is up, awaiting client request")
        msg, self.client_address = self.server_socket.recvfrom(self.packet_size)
        if msg.decode() == "download":
            print("SERVER | Download request, sending image")
            self.send_image()
        self.server_socket.close()

class Client(Thread):
    def __init__(self, ack_err):
        Thread.__init__(self)
        ip = '127.0.0.1'
        port = 12000
        self.server_address = (ip, port)
        self.client_socket = socket(AF_INET, SOCK_DGRAM)
        self.client_socket.settimeout(2)
        self.packet_size = 1024
        self.ack_err = ack_err / 100

    def recv_img(self):
        data = b''
        len = 0
        counter = 0
        err_pkts = []
        while True:
            if counter == (len + 1):
                break

            packet = self.client_socket.recv(self.packet_size)
            """
            Need to extract proper data from the packet: data, seqnum, checksum
            Check for bad seqnum and bad checksum 
            If bad resend ACK with bad seqnum

            Add error on ACK just send bad seqnum
            """
            if len == 0:
                len = int(packet.decode())
                # List of packets to send bad ACK:
                err_pkts = random.sample(range(1, len + 1), int(len * self.ack_err))
            if counter in err_pkts:
                # Switch to bad seqnum (NACK)
                err_pkts.remove(counter) # remove from list so it doesn't loop infinitely
                pass
            elif counter != 0: # Dont add first packet to data as it is the number of packets
                data += packet
            counter += 1 # Only increase counter on good data

        with open('server_to_client_image.bmp', 'wb+') as img:
            img.write(data)
        print("CLIENT | Image saved successfully")

    def run(self):
        sleep(1)
        print("CLIENT | Client is up, sending request to server")
        self.client_socket.sendto("download".encode(), self.server_address)
        self.recv_img()
        self.client_socket.close()

if __name__ == "__main__":
    args = parser.parse_args()
    server = Server(args.data)
    client = Client(args.ack)
    server.start()
    client.start()
    server.join()
    client.join()