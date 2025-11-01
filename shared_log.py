# shared_log.py

import threading

log_lock = threading.Lock()
log_file = "system_log.txt"

def write_log(message):
    with log_lock:
        with open(log_file, 'a') as f:
            f.write(message + "\n")
