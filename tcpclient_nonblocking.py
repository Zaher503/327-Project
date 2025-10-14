import argparse, socket, struct, hashlib, pathlib, time
CHUNK = 64 * 1024
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5001)
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    path = pathlib.Path(args.file)
    data = path.read_bytes()
    md5 = hashlib.md5(data).digest()

with socket.create_connection((args.host, args.port)) as s:
        name_bytes = path.name.encode()
        header = struct.pack(">I", len(name_bytes)) + name_bytes + struct.pack(">Q", len(data)) + md5
        s.sendall(header)
        s.sendall(data)

        # Set the socket to non-blocking before receiving
        s.setblocking(False)

        # Loop until the response is received
        status = None
        while not status:
            try:
                status = s.recv(3).decode()
            except BlockingIOError:
                # No data yet, wait a moment and try again
                print("[TCP CLIENT] Waiting for server response...")
                # added a sleep period to not consume 100% of CPU
                time.sleep(0.1) 
                continue
        print(f"[TCP CLIENT] Transfer status: {status}")

if __name__ == "__main__":
    main()
