# Milestone 2
## Message Queue Demo (Indirect Communication)

## Purpose
Demonstrates asynchronous, indirect communication between decoupled components using RabbitMQ.  
- Producer: sends file update notifications  
- Consumer: receives notifications when online  

This satisfies the "message queue" requirement.

## Component Guide and Execution

This project contains several distinct components. Here is a breakdown of what each component does, its dependencies, and how to run it.

### General Requirements
* **Python 3.8+** is required for all scripts.
* **[RabbitMQ](https://www.rabbitmq.com/install-windows.html)** server must be running for the *RESTful API* and the *Message Queue Demo*. See the **Quickstart** section for instructions.
* **[Erlang](https://www.erlang.org/downloads)**


---

### 1. RESTful API (Main Application)
- File upload & download (HTTP over TCP)
- Metadata persistence (SQLite + SQLAlchemy)
- Concurrency with `ETag` + `If-Match` headers
- Simple sharing (gives permission to another user id)
- RabbitMQ publishing of events: `file.uploaded`, `file.updated`, `file.shared`
- Health checks and OpenAPI docs
- A small Python client to validate flows

## Quickstart

```bash
# 1) (optional) Create and activate a venv
python3 -m venv .venv && source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run RabbitMQ
docker run -it --rm -p 5672:5672 -p 15672:15672 --name rabbitmq rabbitmq:3-management
# UI: http://localhost:15672  (user: guest, pass: guest)

# 4) Run the API
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open the interactive docs at: `http://localhost:8000/docs`

## Endpoints

- `GET  /health` — liveness check
- `POST /files` — multipart upload (`file`), requires `X-User-Id` header
- `GET  /files` — list files visible to caller (owner or shared)
- `GET  /files/{file_id}` — download file (sets `ETag` header with version)
- `PUT  /files/{file_id}` — replace file content (requires `If-Match: <ETag>` and ownership)
- `POST /shares/{file_id}` — grant share access to another `user_id`
- `GET  /shares/{file_id}` — list current shares

### Concurrency via ETag

- On `GET /files/{id}`, response includes `ETag: <version>`
- On `PUT /files/{id}`, the client **must** pass `If-Match: <version>`
- If versions mismatch, server returns **409 Conflict**

## RabbitMQ Integration

This API publishes events to a RabbitMQ queue (default: `file_alerts`) on:
- `POST /files` -> `file.uploaded`
- `PUT /files/{id}` -> `file.updated`
- `POST /shares/{id}` -> `file.shared`

### Env Vars
- `RABBITMQ_HOST` (default: `localhost`)
- `RABBITMQ_QUEUE` (default: `file_alerts`)

### Validate with `curl`

```bash
# Health
curl -i http://localhost:8000/health

# Upload (as user alice)
curl -i -X POST http://localhost:8000/files   -H "X-User-Id: alice"   -F "file=@README.md"

# List files (alice)
curl -s http://localhost:8000/files -H "X-User-Id: alice" | jq

# Get one file's id
FILE_ID=$(curl -s http://localhost:8000/files -H "X-User-Id: alice" | jq -r '.[0].id')

# Download + capture ETag (version)
curl -i http://localhost:8000/files/$FILE_ID -H "X-User-Id: alice"

# Suppose ETag returned: ETag: "1"
# Update content (requires If-Match)
curl -i -X PUT http://localhost:8000/files/$FILE_ID   -H "X-User-Id: alice"   -H 'If-Match: "1"'   -F "file=@requirements.txt"

# Share with bob
curl -i -X POST http://localhost:8000/shares/$FILE_ID   -H "Content-Type: application/json"   -H "X-User-Id: alice"   -d '{"target_user_id":"bob"}'

# List files as bob (should now include shared file)
curl -s http://localhost:8000/files -H "X-User-Id: bob" | jq
```

## Design Notes

- **Transport:** HTTP (over TCP), HTTPS in production.
- **Heterogeneity:** Any platform with HTTP can interact with the service.
- **Concurrency:** Versioning + optimistic concurrency for conflict safety.
- **Scalability:** API is stateless; storage is pluggable. Replace SQLite/local FS with managed DB/object storage later.
- **Failure Handling:** Clear error codes, idempotent downloads, version checks on updates.
- **Transparency:** Simple REST interfaces; internal policies can evolve behind the API.
- **Openness:** OpenAPI schema available at `/openapi.json` and `/docs`.


### 2. Message Queue Demo (producer.py, consumer.py)
* **Files:** `producer.py`, `consumer.py`
* **Purpose:** A simple, standalone demonstration of indirect communication using RabbitMQ. `producer.py` sends several hardcoded messages to the `file_alerts` queue, and `consumer.py` listens for and prints any messages it receives from that queue.
* **Dependencies:** `pip install pika`
* **How to Run:**
    1.  Ensure your RabbitMQ server is running.
    2.  In one terminal, start the consumer to listen for messages:
        ```bash
        python consumer.py
        ```
    3.  In a second terminal, run the producer to send the messages:
        ```bash
        python producer.py
        ```

---

### 3. Non-Blocking TCP File Transfer Demo
* **Files:** `tcpserver_nonblocking.py`, `tcpclient_nonblocking.py`
* **Purpose:** Demonstrates a direct file transfer using **non-blocking** TCP sockets. The server (`tcpserver_nonblocking.py`) is set to non-blocking mode so it doesn't "hang" while waiting for a connection, allowing it to remain responsive. The client (`tcpclient_nonblocking.py`) sends a specified file, including its name, size, and an MD5 hash for integrity verification.
* **Dependencies:** None (uses only Python standard libraries).
* **How to Run:**
    1.  In one terminal, start the server. You can specify where to save files:
        ```bash
        # Creates an 'uploads' directory if it doesn't exist
        python tcpserver_nonblocking.py --save-dir ./uploads
        ```
    2.  In a second terminal, create a test file and send it with the client:
        ```bash
        # Create a dummy file to send
        echo "this is a test file" > sample.txt
        
        # Run the client
        python tcpclient_nonblocking.py --file sample.txt
        ```
    3.  The server will print the save status, and the client will print the transfer status (`OK` or `BAD`).

---

### 4. Simple Blocking TCP Demo
* **Files:** `server.py`, `client.py`
* **Purpose:** A minimal, "hello world" example of a basic **blocking** TCP socket connection. `server.py` waits for a single connection and prints whatever data it receives. `client.py` connects, sends one hardcoded message, and then disconnects. This is the simplest form of client-server communication.
* **Dependencies:** None (uses only Python standard libraries).
* **How to Run:**
    1.  In one terminal, start the server:
        ```bash
        python server.py
        ```
    2.  In a second terminal, run the client:
        ```bash
        python client.py
        ```
    3.  The server will print the received message and both scripts will exit.