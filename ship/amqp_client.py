#!/usr/bin/env python3
"""
Zero-dependency Pure-Python AMQP 0-9-1 Client.
Directly connects to RabbitMQ on port 2014 or 5672 without pip/pika.
"""
import socket
import struct
import json
import time
import threading

def pack_shortstr(s):
    b = s.encode('utf-8')
    return struct.pack('!B', len(b)) + b

def pack_longstr(s):
    b = s.encode('utf-8') if isinstance(s, str) else s
    return struct.pack('!I', len(b)) + b

def pack_table(t):
    # Empty field table
    return struct.pack('!I', 0)

class SimpleAMQPClient:
    def __init__(self, host, port, user='guest', password='guest'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sock = None
        self.channel = 1
        self.running = False

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((self.host, self.port))
        
        # 1. Protocol Header
        self.sock.sendall(b'AMQP\x00\x00\x09\x01')
        
        # 2. Expect Connection.Start
        frame_type, channel, size, payload = self.read_frame()
        
        # 3. Send Connection.StartOk
        # Method: Class 10 (Connection), Method 11 (StartOk)
        auth_response = f"\x00{self.user}\x00{self.password}".encode('latin1')
        body = struct.pack('!HH', 10, 11) + pack_table({}) + pack_shortstr('PLAIN') + pack_longstr(auth_response) + pack_shortstr('en_US')
        self.send_frame(1, 0, body)
        
        # 4. Expect Connection.Tune
        frame_type, channel, size, payload = self.read_frame()
        
        # 5. Send Connection.TuneOk
        # Method: Class 10, Method 31 (TuneOk)
        tune_ok = struct.pack('!HHHII', 10, 31, 0, 131072, 60)
        self.send_frame(1, 0, tune_ok)
        
        # 6. Send Connection.Open
        # Method: Class 10, Method 40 (Open)
        open_body = struct.pack('!HH', 10, 40) + pack_shortstr('/') + pack_shortstr('') + struct.pack('!B', 0)
        self.send_frame(1, 0, open_body)
        
        # 7. Expect Connection.OpenOk
        self.read_frame()
        
        # 8. Open Channel 1
        # Method: Class 20 (Channel), Method 10 (Open)
        ch_open = struct.pack('!HH', 20, 10) + pack_shortstr('')
        self.send_frame(1, self.channel, ch_open)
        
        # 9. Expect Channel.OpenOk
        self.read_frame()

    def send_frame(self, frame_type, channel, payload):
        frame = struct.pack('!BHI', frame_type, channel, len(payload)) + payload + b'\xce'
        self.sock.sendall(frame)

    def read_frame(self):
        header = self._recv_exact(7)
        frame_type, channel, size = struct.unpack('!BHI', header)
        payload = self._recv_exact(size)
        end = self._recv_exact(1)
        if end != b'\xce':
            raise Exception("Invalid frame end")
        return frame_type, channel, size, payload

    def _recv_exact(self, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed")
            buf.extend(chunk)
        return bytes(buf)

    def subscribe_scanner(self, callback):
        # 1. Exchange.Declare (scanner/detected_objects, fanout)
        # Class 40, Method 10
        ex_declare = struct.pack('!HHH', 40, 10, 0) + pack_shortstr('scanner/detected_objects') + pack_shortstr('fanout') + struct.pack('!B', 0) + pack_table({})
        self.send_frame(1, self.channel, ex_declare)
        self.read_frame()  # Exchange.DeclareOk
        
        # 2. Queue.Declare (exclusive=True)
        # Class 50, Method 10
        q_declare = struct.pack('!HHH', 50, 10, 0) + pack_shortstr('') + struct.pack('!B', 2) + pack_table({})  # bit 1 = exclusive
        self.send_frame(1, self.channel, q_declare)
        _, _, _, q_ok = self.read_frame()
        # Parse queue name from Queue.DeclareOk
        q_len = q_ok[4]
        queue_name = q_ok[5:5+q_len].decode('utf-8')
        
        # 3. Queue.Bind
        # Class 50, Method 20
        q_bind = struct.pack('!HHH', 50, 20, 0) + pack_shortstr(queue_name) + pack_shortstr('scanner/detected_objects') + pack_shortstr('') + struct.pack('!B', 0) + pack_table({})
        self.send_frame(1, self.channel, q_bind)
        self.read_frame()  # Queue.BindOk
        
        # 4. Basic.Consume (no_ack=True)
        # Class 60, Method 20
        consume = struct.pack('!HHH', 60, 20, 0) + pack_shortstr(queue_name) + pack_shortstr('') + struct.pack('!B', 2) + pack_table({})  # bit 1 = no_ack
        self.send_frame(1, self.channel, consume)
        self.read_frame()  # Basic.ConsumeOk

        self.running = True
        body_buffer = bytearray()
        expected_body_size = 0

        while self.running:
            frame_type, channel, size, payload = self.read_frame()
            if frame_type == 1:  # Method (Basic.Deliver)
                pass
            elif frame_type == 2:  # Content Header
                class_id, weight, body_size = struct.unpack('!HHQ', payload[:12])
                expected_body_size = body_size
                body_buffer.clear()
                if expected_body_size == 0:
                    callback(b'')
            elif frame_type == 3:  # Content Body
                body_buffer.extend(payload)
                if len(body_buffer) >= expected_body_size:
                    msg = bytes(body_buffer)
                    try:
                        callback(msg)
                    except Exception:
                        pass
                    body_buffer.clear()
            elif frame_type == 8:  # Heartbeat
                self.send_frame(8, 0, b'')

if __name__ == '__main__':
    def on_obj(raw):
        try:
            data = json.loads(raw.decode('utf-8'))
            print("Received Object:", data)
        except Exception:
            print("Raw:", raw)

    print("Testing SimpleAMQPClient on 192.168.103.40:2014 and 127.0.0.1:5672...")
    for h, p in [('192.168.103.40', 2014), ('127.0.0.1', 5672), ('192.168.103.40', 5672)]:
        try:
            print(f"Connecting to {h}:{p}...")
            client = SimpleAMQPClient(h, p)
            client.connect()
            print(f"Connected to {h}:{p}! Subscribing to scanner/detected_objects...")
            client.subscribe_scanner(on_obj)
            break
        except Exception as e:
            print(f"Failed {h}:{p}: {e}")
