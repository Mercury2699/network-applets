#!/usr/bin/python3
import socket
import struct
import os
import sys
import json
import time
import signal
import argparse
# Authored by Alex Ionita taionita@uwaterloo.ca

"""                                ___
                               ,-""   `.
                             ,'  _   e )`-._
                            /  ,' `-._<.===-'
                           /  /
                          /  ;
              _          /   ;
 (`._    _.-"" ""--..__,'    |
 <_  `-""                     \
  <`-                          :
   (__   <__.                  ;
     `-.   '-.__.      _.'    /
        \      `-.__,-'    _,'
         `._    ,    /__,-'
            ""._\__,'< <____
                 | |  `----.`.
                 | |        \ `.
                 ; |___      \-``
                 \   --<
                  `.`.<
                    `-'
                    oh, hello there
"""

# first epoch is the initial time given for all vrouters to converge (first epoch includes init phase and forwarding phase)
# every subsequent epoch, each `CONVERGENCE_EPOCH_TIME` seconds long, corresponds to one network failure scenario
CONVERGENCE_EPOCH_TIME = 5  # length of an epoch in seconds


class MessageType:
    INIT = 1
    INIT_REPLY = 4
    HEARTBEAT = 2
    LSA = 3
    TERMINATE = 5


class LSAMessage:
    class Link:
        def __init__(self, advertising_id, neighbour_id, cost):
            self.advertising_id = advertising_id
            self.neighbour_id = neighbour_id
            self.cost = cost

        def __eq__(self, other):
            return self.advertising_id == other.advertising_id and \
                   self.neighbour_id == other.neighbour_id and \
                   self.cost == other.cost
    # LSA Message -- vrouter to vrouter
    # int32 type (0x3)
    # int32 sender_id
    # int32 destination_id
    # int32 advertising router id
    # int32 sequence number
    # int32 number of links
    # int32 router_neighbour 1
    # int32 link_cost 1
    # int32 router_neighbour N
    # int32 link_cost N
    def __init__(self, buffer):
        len_metadata = (6 * 4) # the first 6 fields (4 bytes each) must exist
        if len(buffer) < len_metadata:
            raise Exception("LSA message expected to be at least 24 bytes long (this accounts for the first 6 fields), this one is {} bytes".format(len(buffer)))

        data = struct.unpack("!iiiiii", buffer[:len_metadata])

        self.sender_id      = data[1]
        self.destination_id = data[2]
        self.advertising_id = data[3]
        self.sequence       = data[4]
        self.links = []
        number_of_links     = data[5]  # todo: we're not checking if number_of_links is too great; what's too great look like?

        if number_of_links < 0:
            raise Exception("LSA message's number_of_links field is negative {}".format(number_of_links))

        payload_len = len(buffer) - len_metadata
        expected_payload_len = number_of_links * 2 * 4 # 2 fields per link, 4 bytes per field

        if expected_payload_len != payload_len:
            raise Exception("LSA message indicated {} links are described ,which would require {} bytes to describe but {} bytes "
                            "have been found describing the links".format(number_of_links, expected_payload_len, payload_len))

        data_links = struct.unpack("!" + "ii" * number_of_links, buffer[len_metadata:])
        for i in range(number_of_links):
            index_neighbour_id = (i * 2)
            index_cost = (i * 2) + 1
            self.links.append(LSAMessage.Link(self.advertising_id, data_links[index_neighbour_id], data_links[index_cost]))

    def __str__(self):
        msg = "type:{},sender_id:{},destination_id:{},advertising_id:{},sequence_number:{}"
        for link in self.links:
            msg += ",neighbour_id:{},cost:{}".format(link.neighbour_id, link.cost)

        return msg


class HeartbeatMessage:
    # Heartbeat Message -- vrouter to vrouter
    # int32 type(0x2)
    # int32 sender_id
    # int32 destination_id
    def __init__(self, buffer):
        if len(buffer) != 12:
            raise Exception("Heartbeat message expected to be 12 bytes long in total, this one is {} bytes".format(len(buffer)))
        data = struct.unpack("!iii", buffer)
        if data[0] != MessageType.HEARTBEAT:
            raise Exception("NFE misidentified Heartbeat message")
        self.sender_id = data[1]
        self.destination_id = data[2]

    def __str__(self):
        return "type:{},sender_id:{},destination_id:{}".format('heartbeat', self.sender_id, self.destination_id)


class VirtualRouter: # holds data pertaining to UDP messages (and links (ip, port) of sender to a virtual router id)
    def __init__(self, address, router_id):
        self.address = address
        self.router_id = router_id


class Neighbour:  # router's neighbour
    def __init__(self, router_id, link_cost):
        self.id = router_id
        self.link_cost = link_cost

    def __eq__(self, other):
        return self.id == other.id and self.link_cost == other.link_cost


class Router:
    def __init__(self, id):
        self.id = id
        self.neighbours = []

    def add_neighbour(self, other_router_id, link_cost):
        self.neighbours.append(Neighbour(other_router_id, link_cost))

    def __str__(self):
        return "Router #{}".format(self.id)

    def __eq__(self, other):
        if self.id != other.id:
            return False
        our_neighbours = sorted(self.neighbours, key=lambda n: n.id)
        their_neighbours = sorted(other.neighbours, key=lambda n: n.id)
        return our_neighbours == their_neighbours

class Failures:
    # Failures file looks like this
    # (1 - 2),(2 - 3)
    # (1 - 2)
    # (2 - 3)
    # ()

    def __init__(self, failures_lines, topology):
        self.current_epoch = 0
        self.epochs = []
        self.current_disconnects = None
        if not failures_lines:
            failures_lines = []

        for line in failures_lines:
            line = line.strip()
            if not line:
                continue

            # in case of classic comments
            if line[0] == '#':
                continue
            line = line.split("#")[0]

            epoch_disconnected_pairs = []
            if self._no_disconnected_links(line):
                self.epochs.append(None)
                continue

            line = line.split(",")
            router_pairs = [change.strip() for change in line] # clean up
            for pair in router_pairs:
                router1 = int(pair.split("-")[0].strip().strip("()").strip())
                router2 = int(pair.split("-")[1].strip().strip("()").strip())
                if router1 not in [r.id for r in topology.routers]:
                    raise Exception("failures file contained an invalid router: \"{}\"".format(router1))

                if router2 not in [r.id for r in topology.routers]:
                    raise Exception("failures file contained an invalid router: \"{}\"".format(router2))

                epoch_disconnected_pairs.append((router1, router2))

            self.epochs.append(epoch_disconnected_pairs)

    def next_epoch(self):
        try:
            self.current_disconnects = self.epochs[self.current_epoch]
        except IndexError:
            raise StopIteration
        self.current_epoch += 1

    def endpoints_disconnected(self, sender_id, destination_id):
        if self.current_disconnects:
            return (sender_id, destination_id) in self.current_disconnects or\
               (destination_id, sender_id) in self.current_disconnects
        return False

    @staticmethod
    def _no_disconnected_links(line):
        # checks for a line in the failures file that looks like this
        # ()
        # or some variation, like this
        # (   )
        return line.strip()[0] == '(' and line.strip().split("(")[1].strip()[0] == ')' \
               and line.strip().split("(")[1].strip()[-1] == ')'


class Topology:
    def __init__(self, topology_description):
        self.routers = []
        self.router_pairs = []

        self.parse_topology_description(topology_description)
        self.validate_no_self_connection()
        self.validate_only_1_link()

    # why json.load() doesn't have a flag for this, I cannot fathom
    @staticmethod
    def dup_key_verify(ordered_pairs):
        dict = {}
        for key, val in ordered_pairs:
            if key in dict:
                raise Exception("JSON contains duplicate link id {}".format(key))
            else:
                dict[key] = val
        return dict

    def parse_topology_description(self, topology_description):
        # JSON part we care about looks like this:
        # {
        #     "links":
        #         [
        #             [["1", "2"], "3"], # router 1 and 2 are connected by a link of cost 3
        #             [["1", "4"], "2"],
        #             [["1", "6"], "10"]
        #         ]
        # }

        if(len(topology_description['links'])) == 0:
            raise Exception("The topology file seems to have no routers connected to each other; emulator needs at least one link between two routers")

        for connection in (topology_description['links']):
            router1_id, router2_id = connection[0]
            router1_id = int(router1_id)
            router2_id = int(router2_id)
            link_cost = int(connection[1])
            self.add_router_connection(router1_id, router2_id, link_cost)
            self.add_router_connection(router2_id, router1_id, link_cost)
            self.router_pairs.append([router1_id, router2_id]) # for later validation

    def validate_no_self_connection(self):
        for r in self.routers:
            for neighbour in r.neighbours:
                if r.id == neighbour.id:
                    raise Exception("Router {} connects to itself".format(r.id))

    def validate_only_1_link(self):
        # validate only 1 link between two routers
        # sorting the pairs so that [2,1] becomes [1,2], such that comparison is simpler
        # it's awkward but sort() is in-place
        [pair.sort() for pair in self.router_pairs]

        # it's n^2 but given the expected size, good enough
        for index1, pair1 in enumerate(self.router_pairs):
            for index2, pair2 in enumerate(self.router_pairs):
                if index1 != index2 and pair1 == pair2:
                    raise Exception("There is more than 1 link between router ids {}".format(pair1))

    def get_router_by_id(self, id):
        for router in self.routers:
            if router.id == id:
                return router
        raise Exception("Emulator has messed something while validating if the topology is connected, I'm sorry. Try another topology")

    def add_router_connection(self, router_id, other_router_id, link_cost):
        router = None
        # does this router already exist?
        for r in self.routers:
            if r.id == router_id:
                router = r
                break
        else:
            # no? let's create it and add it to our collection
            router = Router(router_id)
            self.routers.append(router)
        router.add_neighbour(other_router_id, link_cost)


def main():
    topology, failures, is_log_msg = parse_args()
    listen_loop(topology, failures, is_log_msg)


def parse_args():
    parser = argparse.ArgumentParser(description='NFE')
    parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    required.add_argument("-t", "--topology-file", help="path to the JSON topology file", required=True)
    optional.add_argument("-f", "--failures-file", help="(optional) path to the topology failures file", required=False)
    args = parser.parse_args()
    is_log_msg = os.getenv('NFE_LOG_MSG') # we want to log messages passing through the NFE

    try:
        with open(args.topology_file) as fd:
            topology = Topology(json.load(fd, object_pairs_hook=Topology.dup_key_verify))
    except Exception as e:
        print("Either couldn't open \"{}\" or couldn't parse JSON to construct desired topology: {}".format(args.topology_file, str(e)))
        sys.exit(-1)

    if args.failures_file:
        try:
            with open(args.failures_file) as fd:
                failures = Failures(fd.readlines(), topology)
        except Exception as e:
            print("Either couldn't open \"{}\" or couldn't process failures file: {}".format(args.failures_file, str(e)))
            sys.exit(-2)
    else:
        failures = Failures(None, topology)

    return topology, failures, is_log_msg


def log_message(timestamp_sec, message, is_connected):
    with open("nfe.lsa", 'a') as fd:
        fd.write("[{}],timestamp_sec:{},".format(is_connected, timestamp_sec) + str(message) + "\n")


def log_init_messages(router_id):
    with open("nfe.init_messages", 'a') as fd:
        fd.write("{}\n".format(router_id))


def init_phase(sock, topology, is_log_msg):
    # Init  -- vrouter to NFE
    # int32 type (0x1)
    # int32 router_id

    # Init-reply  -- NFE to vrouter
    # int32 type (0x4)
    # int32 number of links
    # int32 (1) neighbour router id
    # int32 (1) link_cost
    # int32 (n) neighbour router id
    # int32 (n) link_cost

    clients = []
    expected_clients = len(topology.routers)

    # Waiting for init messages; noting down which router id goes with which udp client
    print("Emulator is waiting for init messages from {} virtual routers".format(expected_clients))

    # creating file to log init messages received
    if is_log_msg:
        with open("nfe.init_messages", 'w') as fd:
            fd.write("")

    while len(clients) != expected_clients:
        buffer, address = sock.recvfrom(4096)
        if len(buffer) < 4:
            print(
                "UDP message is only {} byte(s) long. The emulator expects at least 4 bytes as that's the size of the message type. Byte(s) received: {}".format(
                    address, len(buffer), ' '.join('0x{:02x}'.format(byte) for byte in buffer)))
            continue

        message_type_buffer = buffer[:4]
        message_type = struct.unpack("!i", message_type_buffer)[0]
        if message_type != MessageType.INIT:
            print("UDP message has a message type that doesn't correspond to the Init message type. Message type received: {} ({})".format(message_type, ' '.join(
                '0x{:02x}'.format(byte) for byte in message_type_buffer)))
            continue

        if len(buffer) != 8:
            print("Message type is 'Init'(0x01) but it is {} bytes long, and it's expected to actually be 8 bytes".format(len(buffer)))
            continue

        router_id = struct.unpack("!i", buffer[4:8])[0]

        if router_id not in [r.id for r in topology.routers]:
            print("Received Init from virtual router id {} but that router id is not in the topology, ignoring".format(router_id))
            continue

        if router_id in [c.router_id for c in clients]:
            print("Received Init from virtual router id {} but that router id has already been received, ignoring".format(router_id))
            continue

        print("Received Init from virtual router id {} correctly, from udp client (ip, port) {})".format(router_id, address))
        if is_log_msg:
            log_init_messages(router_id)
        clients.append(VirtualRouter(address, router_id))

    # Sending the clients their info
    print("Emulator sending neighbour info to virtual routers")
    for client in clients:
        router = topology.get_router_by_id(client.router_id)

        data = struct.pack("!i", MessageType.INIT_REPLY)  # message type, 0x4
        data += struct.pack("!i", len(router.neighbours))  # nbr neighbours

        for neighbour in router.neighbours:
            data += struct.pack("!i", neighbour.id)  # neighbour_id
            data += struct.pack("!i", neighbour.link_cost)  # link_cost
        print("Sending data to virtual router {}".format(client.router_id))
        sock.sendto(data, client.address)
    return clients


def termination_phase(sock, vrouter_clients):
    for client in vrouter_clients:
        sock.sendto(struct.pack("!i", MessageType.TERMINATE), client.address)
    sock.close()


def forwarding_phase(sock, topology, failures, vrouter_clients, is_log_msg):
    # Forwarding phase
    if is_log_msg:
        with open("nfe.lsa", 'w') as fd:
            fd.write("")
    print("Emulator forwarding traffic between virtual routers")

    time_global = time.time()
    time_t0 = int(time.time())
    while True:
        if time.time() - time_t0 >= CONVERGENCE_EPOCH_TIME:
            time_t0 = int(time.time())
            try:
                failures.next_epoch()
                print("\nConnecting/disconnecting links in the topology")
            except StopIteration:
                print("\nDone, sending termination message")
                termination_phase(sock, vrouter_clients)
                return

        time_to_next_epoch = (CONVERGENCE_EPOCH_TIME + time_t0) - time.time()
        if time_to_next_epoch < 1:
            time_to_next_epoch = 1
        sock.settimeout(time_to_next_epoch)
        try:
            buffer, address = sock.recvfrom(4096)
        except socket.timeout:
            continue

        # let's find the topology vrouter corresponding to the udp source (ip, port)
        for client in vrouter_clients:
            if client.address == address:
                router = topology.get_router_by_id(client.router_id)
                break
        else:
            print("Received data from virtual router (ip, port) {} but that virtual router did not send an init message during the init phase, ignoring".format(
                address))
            continue

        # Termination Message -- NFE to vrouter
        # int32 type (0x5)

        if len(buffer) < 4:
            print("Virtual Router {} has sent a udp message with less than 4 bytes; 4 bytes which is the minimum to specify a message type".format(router.id))
            continue

        # let's just unpack 4 bytes, message type
        message_type = struct.unpack("!i", buffer[:4])[0]

        # we unpack a second time for the rest
        if message_type == MessageType.HEARTBEAT:
            try:
                message = HeartbeatMessage(buffer)
            except Exception as e:
                print("Virtual Router {} - message type is {} (Heartbeat) but the rest of the message could not be parsed, ignoring: {}".format(router.id, message_type, str(e)))
                continue

        elif message_type == MessageType.LSA:
            try:
                message = LSAMessage(buffer)
            except Exception as e:
                print("Virtual Router {} - message type is {} (LSA) but the rest of the message could not be parsed, ignoring: {}".format(router.id, message_type, str(e)))
                continue
        else:
            print("Virtual Router {} - message type is {} but that that's not the expected message type, ignoring".format(router.id, message_type))
            continue

        # does the sender id in the LSA match the UDP client we've exchanged Init messages with?
        if message.sender_id != router.id:
            print(
                "Virtual Router {} - message cannot be forwarded: message indicates the sender id is {} but the UDP source of the message corresponds to"
                " sender id {} with which the emulator spoke during the init phase. Ignoring message".format(router.id, message.sender_id, router.id))
            continue

        # the virtual router whose LSA/heartbeat message we just received wants that LSA/hearbeat forwarded to some neighbouring router
        # let's make sure the destination of the message is an actual neighbour
        if message.destination_id not in [neighbour.id for neighbour in router.neighbours]:
            print(
                "Virtual Router {} - message cannot be forwarded, the router destination id {} is invalid: it's not a neighbour. Ignoring message".format(router.id,
                                                                                                                            message.destination_id))
            continue

        # let's find that neighbour's UDP address in clients
        for client in vrouter_clients:
            if message.destination_id == client.router_id:
                neighbour_address = client.address
                break
        else:
            raise Exception("The emulator couldn't find an address it should have been able to find, sorry. This is a bug. Try another topology")

        # let's see if failures in the topology make this forwarding impossible
        if failures.endpoints_disconnected(message.sender_id, message.destination_id):
            print("x", end='', flush=True)  # show the user forwarding activity would have happened if not for disconnection
            if is_log_msg:
                log_message(time.time() - time_global, message, "disconnected")
            continue

        if is_log_msg:
            log_message(time.time() - time_global, message, "connected")
        sock.sendto(buffer, neighbour_address)
        print(".", end='', flush=True)  # show the user forwarding activity is happening


def listen_loop(topology, failures, is_log_msg):
    # Bind to port, write it to file
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 0))
    port_used = sock.getsockname()[1]
    with open("port", 'w') as fd:
        fd.write(str(port_used))
    print("Emulator is listening on port {} (and has also written this port number to a file named 'port')".format(str(port_used)))

    vrouter_clients = init_phase(sock, topology, is_log_msg)
    forwarding_phase(sock, topology, failures, vrouter_clients, is_log_msg)


if __name__ == '__main__':
    main()
