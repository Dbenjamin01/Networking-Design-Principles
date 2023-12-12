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
parser.add_argument("-w", "--win_s", type=int, default=10)
parser.add_argument("-t", "--timeout", type=float, default=0.05,
                    help="Float format in seconds: 0.05 = 50ms")


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
        self.status = 0  # Timer status - 1: expired, 0: else
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
            sleep(0.0001)  # Needed for other threads to run properly


class Server(Thread):
    def __init__(self, data_err, ack_err, window_size, timeout):
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
        self.timer.set_limit(timeout)
        self.timer.start()
        self.window_size = window_size

    def send_image(self):
        packet = b''
        err_pkts = []
        packet_window = []
        acks = []
        seq_nums = []
        counter = 0
        corruption_counter = 0
        seqN = 0
        cs = 0
        eof = 0
        window_size = self.window_size
        seqnum_bound = 2 * window_size
        open_slots = window_size

        p = Packet(packet, seqN, cs)
        with open(self.image, 'rb') as img:
            num_pkts = str(int(math.ceil(os.fstat(img.fileno()).st_size / self.packet_size))).encode()
            # List of packets when to send bad data:
            err_pkts = random.sample(range(1, int(num_pkts) + 1), int(int(num_pkts) * self.data_err))
            ack_err_pkts = random.sample(range(1, int(num_pkts) + 1), int(int(num_pkts) * self.ack_err))
            packet = num_pkts
            self.server_socket.sendto(packet, self.client_address)
            print("SERVER | Sending image packets...")
            start_time = time()  # Transmission start time

            while True:

                # Fill window (seqN, data) format
                if not eof:
                    for _ in range(open_slots):
                        data = img.read(self.packet_size)
                        if data == "":  # Empty data indicates end of file
                            eof = 1
                            break
                        packet_window.append((seqN, data))
                        seqN = (seqN + 1) % (seqnum_bound)
                    open_slots = 0

                # Send packet burst
                for item in packet_window:
                    seq, data = item
                    if corruption_counter in err_pkts:
                        packet = p.build(b"".join([data[0:1023], b"\0x00"]), seq,
                                         (p.checksum(data, seq)))  # Corrupt data
                        err_pkts.remove(corruption_counter)
                        pass
                    else:
                        corruption_counter += 1
                        packet = p.build(data, seq, (p.checksum(data, seq)))  # Good data
                    self.server_socket.sendto(packet, self.client_address)

                # Await acks
                acks.clear()
                self.timer.restart()
                while True:
                    try:
                        # Append all acks received to a list to be extracted later
                        ack = self.server_socket.recv(self.packet_size)
                        acks.append(ack)
                        self.timer.restart()
                        if (len(acks)) == window_size:
                            break
                    except:
                        if self.timer.get_status():
                            break
                        else:
                            pass
                self.timer.stop()

                # Handle ACKs and prepare for retransmit
                seq_nums.clear()
                for packet in acks:
                    rec_data, rec_seq, rec_cs = p.extract(packet)
                    localcs = p.checksum(rec_data, rec_seq)
                    ack = p.getACK(rec_cs, localcs)
                    if ack:
                        seq_nums.append(rec_seq)  # Append all successful ack seq_nums to be checked
                while True:
                    _seq, _ = packet_window[0]  # Get seqnum from first element of window
                    if counter in ack_err_pkts:
                        ack_err_pkts.remove(counter)
                        try:
                            seq_nums.remove(_seq)
                        except:
                            pass
                    elif _seq in seq_nums:  # Check that desired seqnum was ACKed
                        seq_nums.remove(_seq)
                        packet_window.pop(0)  # Remove data from window if ACKed
                        open_slots += 1  # Advertise open slots
                        counter += 1
                        if len(packet_window) == 0:
                            break
                    else:
                        break

                if counter >= int(num_pkts):
                    break

        print("SERVER | Transmission completed")
        end_time = time()  # Transmission end time
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
    def __init__(self, ack_err, data_err, window_size):
        Thread.__init__(self)
        ip = '127.0.0.1'
        port = 12000
        self.server_address = (ip, port)
        self.client_socket = socket(AF_INET, SOCK_DGRAM)
        self.client_socket.settimeout(2)
        self.packet_size = 4500
        self.ack_err = ack_err / 100
        self.data_err = data_err / 100
        self.window_size = window_size

    def recv_img(self):
        data = b''
        imagebytes = 0
        cs = 0
        seqN = 0
        seqn = 0
        exp_seqN = 0
        p = Packet(imagebytes, seqn, cs)
        len = 0
        counter = 0
        window_size = self.window_size
        seqnum_bound = 2 * window_size
        prev_acks = [seqnum_bound] * window_size # List of previously acked seqns

        # Receive number of packet first
        packet = self.client_socket.recv(self.packet_size)
        len = int(packet.decode())
        err_pkts = random.sample(range(1, len + 1), int(len * self.ack_err))
        data_err_pkts = random.sample(range(1, len + 1), int(len * self.data_err))

        while True:
            try:
                packet = self.client_socket.recv(self.packet_size)
            except:
                break

            # Extract packet
            imagebytes, seqn, cs = p.extract(packet)
            localcs = p.checksum(imagebytes, seqn)
            ack = p.getACK(cs, localcs)

            # Client side forced errors
            if counter in err_pkts:
                err_pkts.remove(counter)
                ack = 0
            elif counter in data_err_pkts:
                data_err_pkts.remove(counter)
                continue

            # Packet is good
            if ack and (seqn == exp_seqN):
                data += imagebytes
                packet = p.build("ACK".encode(), seqN, (p.checksum("ACK".encode(), seqN)))
                self.client_socket.sendto(packet, self.server_address)
                prev_acks.pop(0)
                prev_acks.append(seqN)
                seqN = (seqN + 1) % (seqnum_bound)
                exp_seqN = seqN
                counter += 1
            # Previously acked packet, sender dropped ack but client kept moving look specifically for this type of problem
            elif ack and (seqn in prev_acks):
                packet = p.build("ACK".encode(), seqn, (p.checksum("ACK".encode(), seqn)))
                self.client_socket.sendto(packet, self.server_address)
            # Packet is out of order or bad
            else:
                # Send ACK with bad seq_num since sender retransmits entire window anyway
                bad_seq = (exp_seqN - 1) % (seqnum_bound)
                packet = p.build("ACK".encode(), bad_seq, (p.checksum("ACK".encode(), bad_seq)))
                self.client_socket.sendto(packet, self.server_address)

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
    server = Server(args.data, args.ackloss, args.win_s, args.timeout)
    client = Client(args.ack, args.dataloss, args.win_s)
    server.start()
    client.start()
    server.join()
    client.join()
