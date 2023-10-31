from socket import *
from threading import Thread
from time import sleep
import argparse
import os
import math
import random
import pickle
import time
parser = argparse.ArgumentParser()
parser.add_argument("-a", "--ack", type=int, default=0)
parser.add_argument("-d", "--data", type=int, default=0)
class Packet():

    def __init__(self, imagebytes, seqn, checksum):
        self._imagebytes = imagebytes
        self._seqN = seqn
        self._checksum = checksum

    def build(self, curr: bytes, seqn, cs):
        packet = Packet(curr, seqn, cs)
        data = pickle.dumps(packet)

        return data

    def extract(self, packet):
        # use delimiter to separate the data within the packet
        packet = pickle.loads(packet)
        return packet._imagebytes, packet._seqN, packet._checksum
        pass

    def checksum(self, msg: bytes, seq):
        msg = int.from_bytes(msg, "big")
        carry_add = lambda a, b: ((a + b) & 0xffff) + ((a + b) >> 16)
        csum = 0
        csum = carry_add(csum, seq)
        while msg != 0:
            bits = msg & 0xffff
            csum = carry_add(csum, bits)
            msg = msg >> 16
        return ~csum & 0xffff

    def getACK(self, cs, calcCS):
        ack = 0
        if cs == calcCS:
            # checksum passed, send positive ACK
            ack = 1
        else:
            # checksum failed, send negative ACK
            ack = 0

        return ack
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
        self.image = "halloween.jpeg"

    def corruptPacket(self, packet):
        # bytes are immutable; meaning, once they are created, they cannot be changed
        corruptpacket: bytearray = bytearray(packet)
        corruptpacket[0] = (corruptpacket[0] & 0x0)

        return corruptpacket
    def send_image(self):
        packet = b''
        err_pkts = []
        counter = 0
        seqN = 0
        cs = 0
        p = Packet(packet, seqN, cs)
        with open(self.image, 'rb') as img:
            num_pkts = str(int(math.ceil(os.fstat(img.fileno()).st_size / self.packet_size))).encode()
            # List of packets when to send bad data:
            err_pkts = random.sample(range(1, int(num_pkts) + 1), int(int(num_pkts) * self.data_err))
            packet = num_pkts
            print("SERVER | Sending image packets...")
            start_time = time.time()
            while packet:

                if counter == int(num_pkts) + 1:
                    break

                self.server_socket.sendto(packet, self.client_address)

                if counter > 0:
                    #  Only once the file size has been transmitted do we start probing
                    #  for acknowledgements and incrementing sequence numbers

                    ACK = self.server_socket.recv(self.packet_size)

                    if ACK.decode() == "fail":
                        while ACK.decode() == "fail":
                            self.server_socket.sendto(packet,
