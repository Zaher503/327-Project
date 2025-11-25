"""
   Running each node on sepearte terminal
   python ricart_agrawala.py --id 1 --port 6001 --peers 127.0.0.1:6002,127.0.0.1:6003
   python ricart_agrawala.py --id 2 --port 6002 --peers 127.0.0.1:6001,127.0.0.1:6003
   python ricart_agrawala.py --id 3 --port 6003 --peers 127.0.0.1:6001,127.0.0.1:6002"""


import asyncio
import json
import argparse
import random
import time

class RANode:
    def __init__(self, node_id, host, port, peers):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.addr = f"{host}:{port}"
        self.peers = peers  

        #lamport clock stuff
        self.clock = 0

        #state
        self.state = "RELEASED"  # RELEASED, WANTED, HELD
        self.request_ts = None

        self.pending_replies = set()
        self.deferred_replies = set()

        # event for when all replies come in
        self.got_all_replies = asyncio.Event()

    # Clock Helpers

    def bump_clock(self):
        self.clock += 1
        return self.clock

    def adjust_clock(self, ts):
        # lamport rule
        self.clock = max(self.clock, ts) + 1

    # Network Stuff

    async def send_msg(self, h, p, msg):
        try:
            reader, writer = await asyncio.open_connection(h, p)
            writer.write((json.dumps(msg) + "\n").encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except:
            print(f"[{self.node_id}] couldn't send to {h}:{p}")

    async def send_to_all(self, msg):
        tasks = []
        for (h, p) in self.peers:
            tasks.append(self.send_msg(h, p, msg))
        await asyncio.gather(*tasks)

    # this handles incoming connections from other nodes
    async def handle_conn(self, reader, writer):
        try:
            data = await reader.readline()
            if not data:
                return
            msg = json.loads(data.decode().strip())
            await self.on_message(msg)
        except Exception as e:
            print(f"[{self.node_id}] error reading msg:", e)
        finally:
            writer.close()
            await writer.wait_closed()

    async def start_server(self):
        server = await asyncio.start_server(self.handle_conn, self.host, self.port)
        print(f"[{self.node_id}] listens on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

    # Ricart-Agrawala Algorithm

    async def on_message(self, msg):
        mtype = msg.get("type")
        ts = msg.get("ts", 0)

        #clock synced
        self.adjust_clock(ts)

        if mtype == "REQUEST":
            await self.handle_request(msg)
        elif mtype == "REPLY":
            await self.handle_reply(msg)

    async def handle_request(self, msg):
        other_id = msg["from"]
        other_addr = msg["addr"]
        h, p = other_addr.split(":")
        p = int(p)
        other_ts = msg["ts"]

        my_pri = (self.request_ts, self.node_id) if self.request_ts else (None, self.node_id)
        other_pri = (other_ts, other_id)

        send_now = False

        if self.state == "RELEASED":
            send_now = True
        elif self.state == "HELD":
            send_now = False
        elif self.state == "WANTED":
            # RA rule
            if my_pri[0] is None:
                send_now = True
            else:
                send_now = other_pri < my_pri

        if send_now:
            reply = {
                "type": "REPLY",
                "from": self.node_id,
                "addr": self.addr,
                "ts": self.bump_clock()
            }
            print(f"[{self.node_id}] sending REPLY to {other_addr}")
            await self.send_msg(h, p, reply)
        else:
            print(f"[{self.node_id}] deferring REPLY to {other_addr}")
            self.deferred_replies.add((h, p))

    async def handle_reply(self, msg):
        addr = msg["addr"]
        h, p = addr.split(":")
        p = int(p)
        key = (h, p)

        if key in self.pending_replies:
            self.pending_replies.remove(key)
            print(f"[{self.node_id}] REPLY from {addr}")

        if len(self.pending_replies) == 0:
            self.got_all_replies.set()

    # Critical Section

    async def request_cs(self):
        self.state = "WANTED"
        self.request_ts = self.bump_clock()
        self.pending_replies = set(self.peers)
        self.deferred_replies = set()
        self.got_all_replies.clear()

        req = {
            "type": "REQUEST",
            "from": self.node_id,
            "addr": self.addr,
            "ts": self.request_ts
        }

        print(f"[{self.node_id}] REQUEST...")
        await self.send_to_all(req)

        # wait til all replies are here
        await self.got_all_replies.wait()

        self.state = "HELD"
        await self.critical_section()

        # done
        self.state = "RELEASED"
        self.request_ts = None

        # send deferred replies
        for (h, p) in list(self.deferred_replies):
            reply = {
                "type": "REPLY",
                "from": self.node_id,
                "addr": self.addr,
                "ts": self.bump_clock()
            }
            print(f"[{self.node_id}] sending deferred REPLY to {h}:{p}")
            await self.send_msg(h, p, reply)
            self.deferred_replies.remove((h, p))

    async def critical_section(self):
        print(f"\n[{self.node_id}] entered crit section\n")
        await asyncio.sleep(1.2)  # fake work
        print(f"\n[{self.node_id}]  exited crit section\n")

    # Main

    async def run(self, attempts=3):
        asyncio.create_task(self.start_server())
        await asyncio.sleep(3)  # wait for all servers to start

        for i in range(attempts):
            await asyncio.sleep(random.uniform(0.5, 2))
            print(f"[{self.node_id}] trying to enter CS (attempt {i+1})")
            await self.request_cs()

        print(f"[{self.node_id}] finished all attempts. Exiting.")
        while True:
            await asyncio.sleep(9999)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--peers", default="")
    return ap.parse_args()


async def main():
    args = parse_args()
    peer_list = []
    if args.peers.strip():
        for p in args.peers.split(","):
            h, prt = p.split(":")
            peer_list.append((h, int(prt)))

    node = RANode(args.id, args.host, args.port, peer_list)
    await node.run(attempts=3)


if __name__ == "__main__":
    asyncio.run(main())
