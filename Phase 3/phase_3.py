import sys
from socket import *
from threading import Thread
from time import sleep
import argparse
import os
import math
import random
import pickle

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--ack", type=int, default=0)
parser.add_argument("-d", "--data", type=int, default=0)


class Packet():

    def __init__(self, imagebytes, seqn, checksum):
        self._imagebytes = imagebytes
        self._seqN = seqn
        self._checksum = checksum
    def build(self, curr : bytes, seqn, cs):
        # sequence number & check sum are both integers
        # packetsize = sys.getsizeof((curr))
        # packetsize = sys.getsizeof(str(curr))
        # packetsize = sys.getsizeof(bytes(curr))
        # seqnsize = sys.getsizeof(str(curr))
        # cssize = sys.getsizeof(str(curr))
        # msg = curr + ":" + seqn + ":" + cs
        # msgsize = sys.getsizeof(msg)
        # msg = str(curr) + ":" + str(seqn)+ ":" + str(cs) # convert all 3 points of data into strings, separated by a delimiter (in this case, ":")
        # msgsize = sys.getsizeof(msg)

        packet = Packet(curr, seqn, cs)
        data = pickle.dumps(packet)

        return data
        pass
    def extract(self, packet):
        # use delimiter to separate the data within the packet
        packet = pickle.loads(packet)
        return packet._imagebytes, packet._seqN, packet._checksum
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

    def getACK(self, cs, calcCS):
        ack = 0;
        if cs == calcCS:
            #checksum passed, send positive ACK
            ack = 1
        else:
            #checksum failed, send negative ACK
            ack = 0

        return ack
        pass
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
        seqN = 0
        cs = 0
        p = Packet(packet, seqN, cs)
        with open(self.image, 'rb') as img:
            num_pkts = str(int(math.ceil(os.fstat(img.fileno()).st_size / self.packet_size))).encode()
            # List of packets when to send bad data:
            # err_pkts = random.sample(range(1, num_pkts + 1), int(num_pkts * self.data_err))
            # Need new packet making function with seqnum and checksum
            packet = num_pkts
            print("SERVER | Sending image packets...")
            while packet:

                if counter == int(num_pkts) + 1:
                    # print("SERVER | Recursion Detected, aborting loop")
                    break

                self.server_socket.sendto(packet, self.client_address)

                if counter > 0:
                    # ACK = self.server_socket.recv(self.packet_size)
                    #only once the file size has been transmitted do we start probing for acknowledgements and incrementing sequence numbers.
                     #ACK = self.server_socket.recv(self.packet_size)

                     #if (ACK.decode() == "pass"):
                     #    continue
                     #else:
                     #    while ACK.decode() == "fail":
                             # resend data until server receives positive ACK from client.
                     #        self.server_socket.sendto(packet, self.client_address)
                      #       ACK = self.server_socket.recv(self.packet_size)

                     ACK = self.server_socket.recv(self.packet_size)


                     if (ACK.decode() == "fail"):
                         print("fail on loop")
                         print(counter)
                         while ACK.decode() == "fail":
                            self.server_socket.sendto(packet, self.client_address) #TODO: Investigate & verify if this is working...
                            ACK = self.server_socket.recv(self.packet_size)

                     if seqN == 0:
                        seqN += 1  # if sequence number was 0 at the time of the send, cycle it to one
                     else:
                        seqN -= 1  # vice-versa, if the sequence number was 1, cycle it back to zero
                """
                Add recv for ACK, if bad rerun iteration without updating packet

                Add bad data corrupt the data AFTER creating packet
                """
                # Change to new packet making function
                packet = img.read(self.packet_size)
                # size = sys.getsizeof(packet)  # get size of packet to determine threshold on socket
                packet = p.build(packet, seqN, (p.checksum(packet, seqN)))
                # size = sys.getsizeof(newpacket) # get size of packet to determine threshold on socket

                if counter in err_pkts:
                    # Corrupt the data
                    err_pkts.remove(counter) # remove from list so it doesn't loop infinitely
                    pass
                counter += 1 # Only increase counter on good ACK
                sleep(0.05)


        print("SERVER | Transmission completed")
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
        self.packet_size = 4500 #TODO add depth to packet size to allow for sending of checksum & seqN (prev. 1024)
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
                err_pkts.remove(counter) # remove from list so it doesn't loop infinitely
                pass
            elif counter != 0: # Dont add first packet to data as it is the number of packets

                imagebytes, seqn, cs = p.extract(packet) # works perfectly!

                localcs = p.checksum(imagebytes, seqn)

                ACK = p.getACK(cs, localcs)

                if ACK == 1 & (seqn != lastseq):
                    msg = "pass"
                    # positive ACK, send data up and return postive ACK to server!
                    self.client_socket.sendto(msg.encode(), self.server_address)
                    data += imagebytes
                else:
                    msg = "fail"
                    # negative ACK, send negative ACK to server & wait for re-send of data.
                    self.client_socket.sendto(msg.encode(), self.server_address)

                lastseq = seqn
            sleep(0.05)
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
