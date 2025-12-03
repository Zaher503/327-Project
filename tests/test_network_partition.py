import asyncio
import json
import sys
import os


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ricart_agrawala import RANode

# Mock Transport to simulate partition
class MockTransport:
    def __init__(self):
        self.partitioned_nodes = set()
        self.nodes = {} # port -> node_instance

    async def send_msg(self, sender_port, target_host, target_port, msg):
        if sender_port in self.partitioned_nodes or target_port in self.partitioned_nodes:
            print(f"[Network] DROP: {sender_port} -> {target_port}")
            return # Drop packet
        
        # Deliver directly to target node instance for simulation
        if target_port in self.nodes:
            await self.nodes[target_port].on_message(msg)

transport = MockTransport()

class TestNode(RANode):
    async def send_msg(self, h, p, msg):
        # Override real network call to use mock transport
        await transport.send_msg(self.port, h, p, msg)

async def run_partition_test():
    # Setup 3 Nodes
    p1, p2, p3 = 6001, 6002, 6003
    peers_map = {
        p1: [( "127.0.0.1", p2), ("127.0.0.1", p3)],
        p2: [( "127.0.0.1", p1), ("127.0.0.1", p3)],
        p3: [( "127.0.0.1", p1), ("127.0.0.1", p2)],
    }
    
    n1 = TestNode(1, "127.0.0.1", p1, peers_map[p1])
    n2 = TestNode(2, "127.0.0.1", p2, peers_map[p2])
    n3 = TestNode(3, "127.0.0.1", p3, peers_map[p3])
    
    transport.nodes = {p1: n1, p2: n2, p3: n3}

    print("--- 1. Partitioning Node 3 ---")
    transport.partitioned_nodes.add(p3)

    print("--- 2. Node 1 requests CS (Should succeed via N2) ---")
    # In a 3 node system, standard RA needs replies from ALL peers.
    # Since N3 is partitioned, N1 will hang waiting for reply from N3.
    # This proves the system prefers Consistency over Availability (CP).
    
    task = asyncio.create_task(n1.request_cs())
    
    await asyncio.sleep(2)
    
    if n1.state == "HELD":
        print("FAIL: Node 1 entered CS despite partition (Violation of RA Algorithm)")
    else:
        print("PASS: Node 1 correctly blocked waiting for partitioned Node 3")

    print("--- 3. Heal Partition ---")
    transport.partitioned_nodes.remove(p3)
    
    # Now N1 should eventually get reply from N3 (assuming N3 processes queue or retry)
    # Note: Standard RA doesn't retry automatically, so in this mock we'd need N1 to retry 
    # or N3 to come alive. For this test, verifying the BLOCK is the success condition.

if __name__ == "__main__":
    asyncio.run(run_partition_test())