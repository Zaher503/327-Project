Milestone 3 — Concurrency and Peer-to-Peer Integration
=========================================================

Overview
------------
This milestone extends the distributed system from Milestone 2 by introducing:

• OS-level concurrency — thread-safe multitasking using locks, semaphores, and queues.  
• Peer-to-Peer (P2P) communication — decentralized data exchange without a central coordinator.

Together, these improvements enhance scalability, responsiveness, and fault tolerance across all nodes.


Concurrency Component
-------------------------
File: concurrency/concurrency.py  
Purpose: Demonstrates safe concurrent execution using multiple producer and consumer threads.

Description:
- Uses threading.Thread to simulate multiple producers and consumers.  
- Employs a Lock to protect shared resources (shared_log).  
- Implements a Semaphore(2) to restrict simultaneous producers.  
- Utilizes a Queue to safely pass messages between threads.  
- Includes a mini race-condition demonstration with proper synchronization.

Run:
cd ~/327-Project-main
python3 concurrency/concurrency.py

Expected output:
Alternating log messages from producers and consumers, confirming thread-safe operations and controlled concurrency.


Peer-to-Peer (P2P) System
-----------------------------
Files:
- m3_p2p/p2p_peer.py — runs a peer node that can both send and receive messages.  
- m3_p2p/mq_to_p2p_bridge.py — connects RabbitMQ events from the REST API to the peer network.

Description:
- Each peer acts as both client and server using TCP sockets.  
- Implements decentralized discovery: peers learn new addresses from neighbors (no central registry).  
- Uses a lightweight gossip protocol to share file updates and peer lists.  
- Handles dropped peers gracefully and allows rejoining without full restarts.  
- Inspired by the Gnutella-style unstructured P2P overlay.


Run Instructions
--------------------

Start RabbitMQ
-------------------
docker run -it --rm -p 5672:5672 -p 15672:15672 --name rabbitmq rabbitmq:3-management

Start the REST API
-----------------------
cd ~/327-Project-main/m2_rest_api
uvicorn app:app --reload --host 0.0.0.0 --port 8000

Start Multiple Peers
-------------------------
cd ~/327-Project-main
python3 m3_p2p/p2p_peer.py --port 9001 --inject track_a:1
python3 m3_p2p/p2p_peer.py --port 9002 --peer 127.0.0.1:9001
python3 m3_p2p/p2p_peer.py --port 9003 --peer 127.0.0.1:9002

Start the Message Bridge
-----------------------------
python3 m3_p2p/mq_to_p2p_bridge.py --peer 127.0.0.1:9001

Trigger an Upload (from REST API)
-------------------------------------
curl -i -X POST http://localhost:8000/files \
  -H "X-User-Id: alice" \
  -F "uploaded=@README.md"

Expected result:
- The bridge logs show a forwarded event.
- Peers log messages like:
  [P2P] event applied <file_id> -> v1
  [P2P] learned peer 127.0.0.1:9002

This confirms that file updates are propagated across peers through decentralized routing.


Component Summary
---------------------
Layer             | Component                                  | Function
------------------|--------------------------------------------|---------------------------
Concurrency        | concurrency/concurrency.py                 | Multi-threaded task simulation with safe synchronization
REST API           | m2_rest_api/app.py                         | Handles user file uploads and actions
Message Queue      | RabbitMQ                                   | Relays reliable update events
P2P Layer          | p2p_peer.py, mq_to_p2p_bridge.py           | Distributes updates among peers without central coordination


Outcome
-----------
• Concurrency: Improved responsiveness and thread safety using locks and queues.  
• P2P Networking: Fully decentralized, fault-tolerant file propagation.  
• Integration: REST → RabbitMQ → P2P → Peers pipeline ensures end-to-end synchronization and resilience.
