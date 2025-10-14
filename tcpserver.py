import argparse, os, socket, struct, hashlib, pathlib
CHUNK = 64 * 1024
def recv_exact(conn, n):
    data = bytearray()
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk: raise ConnectionError("Socket closed early")
        data.extend(chunk)
    return bytes(data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5001)
    ap.add_argument("--save-dir", default="received")
    args = ap.parse_args()

    os.makedirs(args.save_dir, exist_ok=True)
    with socket.create_server((args.host, args.port)) as srv:
        print(f"[TCP SERVER] Listening on {args.host}:{args.port}")
        while True:
            conn, addr = srv.accept()
            with conn:
                print(f"[TCP SERVER] Connected: {addr}")
                name_len = struct.unpack(">I", recv_exact(conn, 4))[0]
                name = recv_exact(conn, name_len).decode()
                size = struct.unpack(">Q", recv_exact(conn, 8))[0]
                md5_bytes = recv_exact(conn, 16)

                out_path = pathlib.Path(args.save_dir) / name
                hasher = hashlib.md5(); received = 0
                with open(out_path, "wb") as f:
                    while received < size:
                        chunk = conn.recv(min(CHUNK, size - received))
                        if not chunk: break
                        f.write(chunk); hasher.update(chunk)
                        received += len(chunk)

                ok = hasher.digest() == md5_bytes
                conn.sendall(b"OK" if ok else b"BAD")
                print(f"[TCP SERVER] Saved {out_path} ({size} bytes) Integrity: {'OK' if ok else 'BAD'}")

if __name__ == "__main__":
    main()
