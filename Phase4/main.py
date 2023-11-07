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

class Timer(Thread):

    def __init__(self):
        Thread.__init__(self)
        pass

    def runTimer(self):
        start_time = time.time()

        end_time = time.time()

        while (((end_time - start_time) < 0.025)):
            end_time = time.time()  # constantly get cpu-time and re-compare it to start time until the value
                                    # is greater than or equal to 0.025 (window-size)
        return (end_time - start_time)

    def run(self):
        self.runTimer()
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
        self.image = "image.bmp"

    def corruptPacket(self, packet):
        # bytes are immutable; meaning, once they are created, they cannot be changed
        try:
            corruptpacket: bytearray = bytearray(packet)
            corruptpacket[0] = (corruptpacket[0] & 0x0)

        except IndexError:
            pass

        return corruptpacket
    def send_image(self):
        packet = b''
        err_pkts = []
        counter = 0
        seqN = 0
        cs = 0
        p = Packet(packet, seqN, cs)
        timer = Timer()
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
                                                      self.client_address)
                            ACK = self.server_socket.recv(self.packet_size)

                    if seqN == 0:
                        seqN += 1  # if sequence number was 0 at the time of the send, cycle it to one
                    else:
                        seqN -= 1  # vice-versa, if the sequence number was 1, cycle it back to zero
                """
                Add recv for ACK, if bad rerun iteration without updating packet

                Add bad data corrupt the data AFTER creating packet
                """
                packet = img.read(self.packet_size)
                if counter in err_pkts:
                    # Corrupt the data
                    self.corruptPacket(packet)
                    packet = p.build(self.corruptPacket(packet), seqN, (p.checksum(packet, seqN)))
                    err_pkts.remove(counter)  # remove from list so it doesn't loop infinitely
                else:
                    packet = p.build(packet, seqN, (p.checksum(packet, seqN)))

                counter += 1  # Only increase counter on good ACK
                sleep(0.05)

        print("SERVER | Transmission completed")
        end_time = time.time()

        print("Completion Time: ", end_time - start_time)
        img.close()

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
        self.packet_size = 4500
        self.ack_err = ack_err / 100

    def recv_img(self):
        data = b''
        imagebytes = 0
        cs = 0
        seqn = 0
        lastseq = 1
        p = Packet(imagebytes, seqn, cs)
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
                err_pkts.remove(counter)  # remove from list so it doesn't loop infinitely
                msg = "fail"
                # negative ACK, send negative ACK to server & wait for re-send of data.
                self.client_socket.sendto(msg.encode(), self.server_address)
                pass
            elif counter != 0:  # Dont add first packet to data as it is the number of packets

                imagebytes, seqn, cs = p.extract(packet)  # works perfectly!

                localcs = p.checksum(imagebytes, seqn)

                ACK = p.getACK(cs, localcs)

                if ACK == 1 & (seqn != lastseq):
                    msg = "pass"
                    # positive ACK, send data up and return postive ACK to server!
                    self.client_socket.sendto(msg.encode(), self.server_address)
                    data += imagebytes

                    # move counter location to only increment on successful ACK
                    counter += 1  # Only increase counter on good data
                else:
                    msg = "fail"
                    # negative ACK, send negative ACK to server & wait for re-send of data.
                    self.client_socket.sendto(msg.encode(), self.server_address)

                lastseq = seqn

            sleep(0.05)

            if counter == 0:
                counter += 1

        with open('server_to_client_image.bmp', 'wb+') as img:
            img.write(data)
        print("CLIENT | Image saved successfully")

    def run(self):
        sleep(1)
        print("CLIENT | Client is up, sending request to server")
        self.client_socket.sendto("download".encode(), self.server_address)
        self.recv_img()
if __name__ == "__main__":
    args = parser.parse_args()
    server = Server(args.data)
    client = Client(args.ack)
    server.start()
    client.start()
    server.join()
    client.join()
