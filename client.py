import socket			 
import psutil

# def get_ethernet_ip():
#     for interface, addrs in psutil.net_if_addrs().items():
#         if 'Ethernet' in interface:
#             for addr in addrs:
#                 if addr.family == socket.AF_INET:
#                     return addr.address
#     return None

# ethernet_ip = get_ethernet_ip() 
# if ethernet_ip[-1] != '0':
#     ethernet_ip += '0'
# print(ethernet_ip)

server_ip = ''
server_port = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))

file_name = 'image.png'
client_socket.send(file_name.encode())

f = open(file_name, 'rb')
l = f.read()
while(l):
    client_socket.send(l)
    l = f.read()
f.close()


client_socket.close()
