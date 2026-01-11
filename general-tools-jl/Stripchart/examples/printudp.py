import socket, struct

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# multicast group address and port
local_addr = '0.0.0.0'
# local_addr = '192.168.1.118'
mcast_grp = '224.1.1.118'
mcast_port = 9999

# bind socket to mcast_grp on mcast_port
sock.bind((local_addr, mcast_port))
# convert multicast address to binary form, INADDR_ANY means any interface
# mreq = struct.pack("4sl", socket.inet_aton(mcast_grp), socket.INADDR_ANY)
mreq = socket.inet_aton(mcast_grp) + socket.inet_aton(local_addr)
# join the multicast group (adding membership)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

print("running...")
while True:
	data, sender_endpoint = sock.recvfrom(1500)  #receive data
	print(str(sender_endpoint[0]) + ":" + str(sender_endpoint[1]) + " sent " + data.hex())
