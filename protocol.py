import socket
import struct
from pathlib import Path

HEADER = struct.Struct("!BH")
CONNECT_STRUCT = struct.Struct("!4sH")
TUPLE_STRUCT = struct.Struct("!c4sHI")

CONNECT = 1
LINK_STATE = 2

def load_topology(path: str | Path) -> list[list[int]]:
    data_rows = []
    with open(path, "r", encoding = "utf-8") as file:
        for line_no, raw_line in enumerate(file):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            
            values = [int(token) for token in line.split()]
            data_rows.append(values)
    
    n = len(data_rows) + 1
    matrix = [
        [0 if i ==j else -1 for j in range(n)]
        for i in range(n)
    ]
    for i, values in enumerate(data_rows):
        for offset, cost in enumerate(values):
            j = i + offset + 1
            matrix[i][j] = cost
            matrix[j][i] = cost
            
    return matrix 

def get_link_state(
    matrix: list[list[int]],
    endpoints: list[tuple[str, int]],
    node_index: int,
) -> list[tuple[str, str, int, int]]:
    n = len(matrix)
    result = []

    for j, cost in enumerate(matrix[node_index]):
        if j != node_index and cost > 0:
            ip, port = endpoints[j]
            label = chr(ord("A") + j)
            result.append((label, ip, port, cost))
    
    my_ip, my_port = endpoints[node_index]
    my_label = chr(ord("A") + node_index)
    result.append((my_label, my_ip, my_port, 0))

    return result

def recv_exact(sock: socket.socket, n: int) -> bytes:
    #keeps recieveing until n bytes are accepted 
    chunks = []
    remaining = n

    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError(
                f"Connection closed; received {n - remaining} bytes instead of {n}"
            )
        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)

def send_message(
    sock: socket.socket,
    message_type: int,
    payload: bytes,
) -> None:
    #sends the payload in a byte stream with a header 
    if len(payload) > 65535:
        raise ValueError("too large payload")

    header = HEADER.pack(message_type, len(payload))
    sock.sendall(header + payload)

def recv_message(sock: socket.socket) -> tuple[int, bytes]:
    header = recv_exact(sock, HEADER.size)
    message_type, payload_lenght = HEADER.unpack(header)
    
    payload = recv_exact(sock, payload_lenght)
    return message_type, payload

def encode_connect(ip: str, udp_port: int) -> bytes:
    #converts ip and udp prot into bytes
    packed_ip = socket.inet_pton(socket.AF_INET, ip)
    return CONNECT_STRUCT.pack(packed_ip, udp_port)

def decode_connect(payload: bytes) -> tuple[str, int]:
    # converts bytes into ip and port no
    packed_ip, udp_port = CONNECT_STRUCT.unpack(payload)
    ip = socket.inet_ntop(socket.AF_INET, packed_ip)
    return ip, udp_port

def encode_link_state(
    rows: list[tuple[str, str, int, int]],
) -> bytes:
    parts = [struct.pack("!B", len(rows))]
    
    for label, ip, port, cost in rows:
        packed_ip = socket.inet_pton(socket.AF_INET, ip)
        parts.append(
            TUPLE_STRUCT.pack(
                label.encode("ascii"),
                packed_ip,
                port,
                cost
            )
        )
    
    return b"".join(parts)

def decode_link_state(
    payload: bytes,
) -> list[tuple[str, str, int, int]]:

    count = payload[0]

    expected_length = 1 + count * TUPLE_STRUCT.size

    if len(payload) != expected_length:
        raise ValueError("check link state payload passed")

    result = []
    offset = 1

    for _ in range(count):
        label_raw, packed_ip, port, cost = (
            TUPLE_STRUCT.unpack_from(payload, offset)
        )
        offset += TUPLE_STRUCT.size

        label = label_raw.decode("ascii")
        ip = socket.inet_ntop(socket.AF_INET, packed_ip)

        result.append((label, ip, port, cost))

    return result