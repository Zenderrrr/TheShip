import socket
import struct
import json
import time

def connect_socks5(proxy_host, proxy_port, target_host, target_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect((proxy_host, proxy_port))
    # 1. Greeting
    s.sendall(b'\x05\x01\x00')
    res = s.recv(2)
    if res != b'\x05\x00':
        raise Exception(f"SOCKS5 auth negotiation failed: {res}")
    # 2. Connect
    req = b'\x05\x01\x00\x01' + socket.inet_aton(target_host) + struct.pack('!H', target_port)
    s.sendall(req)
    reply = s.recv(10)
    if len(reply) < 4 or reply[1] != 0:
        raise Exception(f"SOCKS5 connect to {target_host}:{target_port} failed (reply: {reply})")
    return s

print("Testing SOCKS5 proxy on 127.0.0.1:2081 -> 192.168.103.40:2014...")
try:
    sock = connect_socks5('127.0.0.1', 2081, '192.168.103.40', 2014)
    print("SUCCESS: Connected to 192.168.103.40:2014 via SOCKS5!")
    sock.close()
except Exception as e:
    print("SOCKS5 test result:", e)
