import threading
from socket import *
from threading import Thread
from time import sleep, time
import argparse
import os
import math
import random
import pickle
parser = argparse.ArgumentParser()
parser.add_argument("-a", "--ack", type=int, default=0)
parser.add_argument("-d", "--data", type=int, default=0)
parser.add_argument("-al", "--ackloss", type=int, default=0)
parser.add_argument("-dl", "--dataloss", type=int, default=0)

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
        return 1 if cs == calcCS else 0
    
class Timer(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.limit = 0
        self.stopped = 1
        self.status = 0 # Timer status - 1: expired, 0: else
        self.terminated = 0
    
    def set_limit(self, limit):
        self.limit = limit

    def stop(self):
        self.stopped = 1

    def get_status(self):
        return self.status
    
    def terminate(self):
        self.terminated = 1

    def restart(self):
        self.stopped = 0
        self.status = 0
        self.time_start = time()

    def run(self):
        self.time_start = time()
        while not self.terminated:
            if not self.stopped:
                elapsed = time() - self.time_start
                if elapsed >= self.limit:
                    self.stopped = 1
                    self.status = 1
            else:
                pass
            sleep(0.0001) # Needed for other threads to run properly
        

class Server(Thread):
    def __init__(self, data_err, ack_err):
        Thread.__init__(self)
        ip = '127.0.0.1'
        port = 12000
        address = (ip, port)
        self.server_socket = socket(AF_INET, SOCK_DGRAM)
        self.server_socket.bind(address)
        self.packet_size = 1024
        self.data_err = data_err / 100
        self.ack_err = ack_err / 100
        self.image = "penguin.bmp"
        self.timer = Timer()
        self.timer.set_limit(0.05)
        self.timer.start()

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
        with open(self.image, 'rb') as img:
            num_pkts = str(int(math.ceil(os.fstat(img.fileno()).st_size / self.packet_size))).encode()
            # List of packets when to send bad data:
            err_pkts = random.sample(range(1, int(num_pkts) + 1), int(int(num_pkts) * self.data_err))
            ack_err_pkts = random.sample(range(1, int(num_pkts) + 1), int(int(num_pkts) * self.ack_err))
            packet = num_pkts
            print("SERVER | Sending image packets...")
            start_time = time() # Transmission start time

            while packet:

                if counter == int(num_pkts) + 1:
                    break

                self.server_socket.sendto(packet, self.client_address)

                if counter > 0:
                    #  Only once the file size has been transmitted do we start probing
                    #  for acknowledgements and incrementing sequence numbers
                    self.timer.restart()

                    # Will keep attempting to receive data until the timer runs out, after that set ACK to fail and retransmit
                    while True:
                        try:
                            ACK = self.server_socket.recv(self.packet_size)
                            break
                        except:
                            if self.timer.get_status():
                                ACK = b"fail"
                                break
                            else:
                                pass
                    
                    # Drop ACK on purpose leading to a retransmit
                    if counter in ack_err_pkts:
                        ACK = b"fail"
                        ack_err_pkts.remove(counter)

                    self.timer.stop()
                    if ACK.decode() == "fail":
                        continue
                    
                    seqN ^= 1
                
                # Reaching this point means successful ACK on previous packet, setup new packet
                packet = img.read(self.packet_size)
                if counter in err_pkts:
                    # Corrupt the data
                    self.corruptPacket(packet)
                    packet = p.build(self.corruptPacket(packet), seqN, (p.checksum(packet, seqN)))
                    err_pkts.remove(counter)  # remove from list so it doesn't loop infinitely
                else:
                    packet = p.build(packet, seqN, (p.checksum(packet, seqN)))

                counter += 1  # Only increase counter on good ACK

        print("SERVER | Transmission completed")
        end_time = time() # Transmission end time
        print("Completion Time: ", end_time - start_time)
        img.close()
        self.timer.terminate()
        self.timer.join()

    def run(self):
        print("SERVER | Server is up, awaiting client request")
        msg, self.client_address = self.server_socket.recvfrom(self.packet_size)
        if msg.decode() == "download":
            print("SERVER | Download request, sending image")
            # Set builtin socket timeout lower than our thread timer so the try/except actually goes off
            self.server_socket.settimeout(0.01)
            self.send_image()
        self.server_socket.close()

class Client(Thread):
    def __init__(self, ack_err, data_err):
        Thread.__init__(self)
        ip = '127.0.0.1'
        port = 12000
        self.server_address = (ip, port)
        self.client_socket = socket(AF_INET, SOCK_DGRAM)
        self.client_socket.settimeout(2)
        self.packet_size = 4500
        self.ack_err = ack_err / 100
        self.data_err = data_err / 100

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
                data_err_pkts = random.sample(range(1, len + 1), int(len * self.data_err))
            if counter in err_pkts:
                # Switch to bad seqnum (NACK)
                err_pkts.remove(counter)  # remove from list so it doesn't loop infinitely
                msg = "fail"
                # negative ACK, send negative ACK to server & wait for re-send of data.
                self.client_socket.sendto(msg.encode(), self.server_address)
                pass
            elif counter in data_err_pkts:
                # Complete packet loss do not send any ACK
                data_err_pkts.remove(counter)
                continue
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
                elif ACK == 1 & (seqn == lastseq):
                    msg = "pass"
                    # Duplicate packet detection send positive ACK but dont add data and dont iterate counter
                    self.client_socket.sendto(msg.encode(), self.server_address)
                else:
                    msg = "fail"
                    # negative ACK, send negative ACK to server & wait for re-send of data.
                    self.client_socket.sendto(msg.encode(), self.server_address)

                lastseq = seqn

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
    server = Server(args.data, args.ackloss)
    client = Client(args.ack, args.dataloss)
    server.start()
    client.start()
    server.join()
    client.join()
