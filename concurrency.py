"""
==============================================================
 Milestone 3 – Concurrency Implementation (Producer/Consumer)
==============================================================
This program demonstrates internal concurrency and synchronization
inside a distributed system component (Smart Transportation example).

Concepts Shown:
- Thread-based concurrency using Python's `threading` module
- Race condition prevention using `Lock`
- Shared resource protection (shared_log)
- Coordination via `Queue` and `Semaphore`
==============================================================
"""

import threading
import queue
import random
import time

# Shared resources
shared_log = []
log_lock = threading.Lock()
message_queue = queue.Queue()
semaphore = threading.Semaphore(2)  # limit number of active producers

# Producer class simulating a vehicle or data generator
class Producer(threading.Thread):
    def __init__(self, pid):
        super().__init__()
        self.pid = pid

    def run(self):
        for i in range(5):
            # Acquire semaphore (simulates limited resources, e.g., communication channel)
            with semaphore:
                msg = f"[Producer {self.pid}] generated data packet {i}"
                message_queue.put(msg)
                print(f"{msg}")
                time.sleep(random.uniform(0.2, 1.0))

# Consumer class simulating a data processing or traffic hub thread
class Consumer(threading.Thread):
    def __init__(self, cid):
        super().__init__()
        self.cid = cid

    def run(self):
        while True:
            try:
                msg = message_queue.get(timeout=3)  # wait for message
                # CRITICAL SECTION — protect shared resource
                with log_lock:
                    shared_log.append((self.cid, msg))
                    print(f"[Consumer {self.cid}] logged message → {msg}")
                message_queue.task_done()
                time.sleep(random.uniform(0.3, 1.2))
            except queue.Empty:
                break

# Race condition demo (if you comment out the lock)
def race_condition_demo():
    temp = []
    def unsafe_add():
        for _ in range(1000):
            temp.append(1)
            temp.pop() if len(temp) > 500 else None
    threads = [threading.Thread(target=unsafe_add) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    print("Race condition demo finished (no crash = safe handling example)")

# Main entry
if __name__ == "__main__":
    producers = [Producer(i) for i in range(3)]
    consumers = [Consumer(i) for i in range(2)]

    # Start all threads
    for p in producers: p.start()
    for c in consumers: c.start()

    # Wait for producers to finish
    for p in producers: p.join()

    # Wait for consumers to drain the queue
    message_queue.join()

    print("\nAll messages processed.")
    print("Final shared_log contents:")
    for cid, entry in shared_log:
        print(f"  {cid}: {entry}")

    print("\nRunning race condition demonstration...")
    race_condition_demo()
