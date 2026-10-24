import argparse
import socket
import time

from protocol import (
    CONNECT,
    LINK_STATE,
    load_topology,
    get_link_state,
    recv_message,
    decode_connect,
    send_message,
    encode_link_state,
)


ON_PORT = 5000


def run_oracle(config_path: str, bind_ip: str) -> None:
    # load the graph before accepting clients.
    matrix = load_topology(config_path)
    n = len(matrix)

    connections = []
    endpoints = []

    listener = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    listener.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    try:
        # startog tcp server server.
        listener.bind((bind_ip, ON_PORT))
        listener.listen(128)

        print(f"listening on {bind_ip}:{ON_PORT}")
        print(f"Waiting for {n} virtual nodes...")

        # connecting to all n vn
        for i in range(n):
            conn, peer_address = listener.accept()

            try:
                message_type, payload = recv_message(conn)

                if message_type != CONNECT:
                    raise ValueError(
                        "Expected CONNECT from new VN"
                    )

                endpoint = decode_connect(payload)

                if endpoint in endpoints:
                    raise ValueError(
                        f"Duplicate VN endpoint: {endpoint}"
                    )

            except Exception:
                conn.close()
                raise

            connections.append(conn)
            endpoints.append(endpoint)

            label = chr(ord("A") + i)

            print(
                f"Registered {label}: "
                f"{endpoint[0]}:{endpoint[1]} "
                f"(TCP peer {peer_address})"
            )

        print(f"All {n} VNs registered")

        for i, conn in enumerate(connections):
            rows = get_link_state(matrix, endpoints, i)
            payload = encode_link_state(rows)

            send_message(conn, LINK_STATE, payload)

            label = chr(ord("A") + i)
            print(f"Sent LINK-STATE to {label}: {rows}")

        time.sleep(1)

    finally:
        for conn in connections:
            conn.close()

        listener.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file")
    parser.add_argument("bind_ip")
    args = parser.parse_args()

    run_oracle(args.config_file, args.bind_ip)