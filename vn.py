# vn.py

import argparse
import socket

from protocol import (
    CONNECT,
    LINK_STATE,
    encode_connect,
    send_message,
    recv_message,
    decode_link_state,
)


ON_PORT = 5000


def run_vn(
    on_ip: str,
    self_ip: str,
    self_udp_port: int,
) -> None:
    # binding the udp port 
    udp_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
    )

    try:
        udp_sock.bind((self_ip, self_udp_port))
        print(
            f"VN UDP endpoint bound to "
            f"{self_ip}:{self_udp_port}"
        )

        
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        ) as control_sock:

            control_sock.connect((on_ip, ON_PORT))

            
            connect_payload = encode_connect(
                self_ip,
                self_udp_port,
            )

            send_message(
                control_sock,
                CONNECT,
                connect_payload,
            )

            
            message_type, payload = recv_message(control_sock)

            if message_type != LINK_STATE:
                raise ValueError(
                    "Expected LINK-STATE from ON"
                )

            rows = decode_link_state(payload)

            
            self_rows = [
                row for row in rows if row[3] == 0
            ]

            if len(self_rows) != 1:
                raise ValueError(
                    "Expected exactly one self tuple"
                )

            self_label, ip, port, _ = self_rows[0]

            if (ip, port) != (self_ip, self_udp_port):
                raise ValueError(
                    "Self tuple does not match this VN's endpoint"
                )

            
            neighbours = [
                row for row in rows if row[3] > 0
            ]

            if len(self_rows) + len(neighbours) != len(rows):
                raise ValueError(
                    "Unexpected link-state cost"
                )

            output = [f"{self_label}=0"]
            output.extend(
                f"{label}={cost}"
                for label, _, _, cost in neighbours
            )

            print(", ".join(output))

    finally:
        udp_sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("on_ip")
    parser.add_argument("self_ip")
    parser.add_argument("udp_port", type=int)
    args = parser.parse_args()

    run_vn(
        args.on_ip,
        args.self_ip,
        args.udp_port,
    )