import pika
import json
import socket
import argparse

def send_p2p_event(peer_host, peer_port, file_id, version, ts):
    msg = json.dumps({
        "type": "event",
        "file_id": file_id,
        "version": int(version),
        "ts": int(ts)
    }) + "\n"
    with socket.create_connection((peer_host, peer_port), timeout=1.0) as s:
        s.sendall(msg.encode())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peer", default="127.0.0.1:9001", help="p2p peer to forward to")
    ap.add_argument("--queue", default="file_alerts")
    args = ap.parse_args()
    ph, pp = args.peer.split(":"); pp = int(pp)

    conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    ch = conn.channel()
    ch.queue_declare(queue=args.queue)

    print(f"[Bridge] Subscribed to '{args.queue}', forwarding to {ph}:{pp}")

    def callback(chd, method, properties, body):
        txt = body.decode()
        try:
            data = json.loads(txt)
            file_id = data.get("file_id")
            version = data.get("version", 1)
            ts = data.get("ts", 0)
        except json.JSONDecodeError:
            # fallback: look for "id=" and "version="
            file_id, version, ts = None, 1, 0
            parts = txt.replace(",", " ").split()
            for p in parts:
                if p.startswith("id="): file_id = p.split("=",1)[1]
                if p.startswith("version="): version = p.split("=",1)[1]
            if not file_id:
                print(f"[Bridge] Unrecognized message: {txt}")
                return
        try:
            send_p2p_event(ph, pp, file_id, version, ts)
            print(f"[Bridge] forwarded event: {file_id} -> v{version} ts={ts}")
        except Exception as e:
            print(f"[Bridge] forward failed: {e}")

    ch.basic_consume(queue=args.queue, on_message_callback=callback, auto_ack=True)
    try:
        print("[Bridge] Waiting for messages... Ctrl+C to exit")
        ch.start_consuming()
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()

if __name__ == "__main__":
    main()
