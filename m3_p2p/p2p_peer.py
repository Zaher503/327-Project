import asyncio
import json
import time
import random
import argparse
from typing import Dict, Set, Tuple
from logical_clock import LamportClock

# JSON-line protocol messages:
# {"type":"hello","from":"host:port"}
# {"type":"state","from":"host:port","files":{"id":ver,...},"peers":["h1:p1","h2:p2"]}
# {"type":"event","file_id":"...", "version": N, "ts": T}

class Peer:
    def __init__(self, host: str, port: int, bootstrap: Set[Tuple[str,int]]):
        self.host, self.port = host, port
        self.addr = f"{host}:{port}"
        self.files: Dict[str, int] = {}      # file_id -> version
        self.peers: Set[Tuple[str,int]] = set(bootstrap)
        self.connections = {}                # (h,p) -> writer
        self.backoff_until = {}              # (h,p) -> unix timestamp

        # logical clock for event ordering
        self.clock = LamportClock()

    async def start(self):
        server = await asyncio.start_server(self._handle_conn, self.host, self.port)
        print(f"[P2P] listening {self.addr}")
        asyncio.create_task(self._dial_loop())
        asyncio.create_task(self._gossip_loop())
        async with server:
            await server.serve_forever()

    async def _handle_conn(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peername = writer.get_extra_info("peername")
        print(f"[P2P] incoming {peername}")
        try:
            await self._send(writer, {"type":"hello","from":self.addr})
            while True:
                line = await reader.readline()
                if not line: break
                msg = json.loads(line.decode().strip())
                await self._on_msg(msg, writer)
        except Exception:
            pass
        finally:
            writer.close(); await writer.wait_closed()

    async def _dial_loop(self):
        while True:
            now = time.time()
            for (h,p) in list(self.peers):
                if (h,p) in self.connections: continue
                if now < self.backoff_until.get((h,p), 0): continue
                try:
                    r,w = await asyncio.wait_for(asyncio.open_connection(h,p), 1.0)
                    self.connections[(h,p)] = w
                    print(f"[P2P] connected {h}:{p}")
                    await self._send(w, {"type":"hello","from":self.addr})
                except Exception:
                    self.backoff_until[(h,p)] = now + random.uniform(0.5, 2.0)
            await asyncio.sleep(0.5)

    async def _gossip_loop(self):
        while True:
            await asyncio.sleep(2.0)
            if not self.connections: continue
            state = {"type":"state","from":self.addr,
                     "files": self.files,
                     "peers": [f"{h}:{p}" for (h,p) in self.peers]}
            for key, w in list(self.connections.items()):
                try:
                    await self._send(w, state)
                except Exception:
                    self.connections.pop(key, None)

    async def _on_msg(self, msg, writer):
        # merge logical time (Lamport) for any incoming message
        incoming_ts = msg.get("ts")
        if incoming_ts is not None:
            local_time = self.clock.recv_event(incoming_ts)
            print(f"[P2P] clock update -> {local_time}")
        else:
            self.clock.tick()

        t = msg.get("type")
        if t == "hello":
            frm = msg.get("from")
            if frm and frm != self.addr:
                h,p = frm.split(":"); self.peers.add((h,int(p)))
        elif t == "state":
            # merge files: last-write-wins by version
            for fid, ver in msg.get("files", {}).items():
                if ver > self.files.get(fid, 0):
                    self.files[fid] = ver
                    print(f"[P2P] merge {fid} -> v{ver} (from {msg.get('from')})")
            for ps in msg.get("peers", []):
                try:
                    h,p = ps.split(":"); p = int(p)
                    if (h,p) != (self.host,self.port):
                        if (h,p) not in self.peers:
                            print(f"[P2P] learned peer {h}:{p}")
                        self.peers.add((h,p))
                except: pass
        elif t == "event":
            fid = msg["file_id"]; ver = int(msg["version"])
            newv = max(ver, self.files.get(fid, 0))
            if newv != self.files.get(fid, 0):
                self.files[fid] = newv
                print(f"[P2P] event applied {fid} -> v{newv} (ts={self.clock.time})")

    async def _send(self, writer: asyncio.StreamWriter, obj):
        # attach Lamport timestamp to every outgoing message
        obj["ts"] = self.clock.send_event()
        writer.write((json.dumps(obj)+"\n").encode()); await writer.drain()

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--peer", action="append", default=[], help="bootstrap host:port (repeat)")
    ap.add_argument("--inject", action="append", default=[], help="seed: file_id:version (repeat)")
    return ap.parse_args()

async def main():
    args = parse_args()
    boots = set()
    for s in args.peer:
        h,p = s.split(":"); boots.add((h,int(p)))
    node = Peer(args.host, args.port, boots)
    for inj in args.inject:
        fid,ver = inj.split(":"); node.files[fid] = int(ver)
    await node.start()

if __name__ == "__main__":
    asyncio.run(main())

