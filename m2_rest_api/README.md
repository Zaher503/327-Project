## Milestone 2 — RESTful API (File Sync/Share)

- File upload & download (HTTP over TCP)
- Metadata persistence (SQLite + SQLAlchemy)
- Optimistic concurrency with `ETag` + `If-Match` headers
- Simple sharing (grant permission to another user id)
- RabbitMQ publishing of events: `file.uploaded`, `file.updated`, `file.shared`
- Health checks and OpenAPI docs
- A small Python client to validate flows

## Quickstart

```bash
# 1) (optional) Create and activate a venv
python3 -m venv .venv && source .venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run RabbitMQ (Docker recommended)
docker run -it --rm -p 5672:5672 -p 15672:15672 --name rabbitmq rabbitmq:3-management
# UI: http://localhost:15672  (user: guest, pass: guest)

# 4) Run the API
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open the interactive docs at: `http://localhost:8000/docs`

## Endpoints (summary)

- `GET  /health` — liveness check
- `POST /files` — multipart upload (`file`), requires `X-User-Id` header
- `GET  /files` — list files visible to caller (owner or shared)
- `GET  /files/{file_id}` — download file (sets `ETag` header with version)
- `PUT  /files/{file_id}` — replace file content (requires `If-Match: <ETag>` and ownership)
- `POST /shares/{file_id}` — grant share access to another `user_id`
- `GET  /shares/{file_id}` — list current shares

### Optimistic Concurrency via ETag

- On `GET /files/{id}`, response includes `ETag: <version>`
- On `PUT /files/{id}`, the client **must** pass `If-Match: <version>`
- If versions mismatch, server returns **409 Conflict**

## RabbitMQ Integration

This API publishes events to a RabbitMQ queue (default: `file_alerts`) on:
- `POST /files` → `file.uploaded`
- `PUT /files/{id}` → `file.updated`
- `POST /shares/{id}` → `file.shared`

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

## Client Script

Run an end-to-end using the client helper:

```bash
python client_example.py
```

## Design Notes

- **Transport:** HTTP (over TCP), HTTPS in production.
- **Heterogeneity:** Any platform with HTTP can interact with the service.
- **Concurrency:** Versioning + optimistic concurrency for conflict safety.
- **Scalability:** API is stateless; storage is pluggable. Replace SQLite/local FS with managed DB/object storage later.
- **Failure Handling:** Clear error codes, idempotent downloads, version checks on updates.
- **Transparency:** Simple REST interfaces; internal policies can evolve behind the API.
- **Openness:** OpenAPI schema available at `/openapi.json` and `/docs`.
