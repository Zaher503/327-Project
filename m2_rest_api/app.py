import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Response, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from db import Base, engine, SessionLocal
from models import FileMeta, Share
from mq import MqPublisher

# Initialize DB
Base.metadata.create_all(bind=engine)

STORAGE_DIR = os.path.join(os.getcwd(), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

app = FastAPI(title="File Sync/Share — Milestone 2 REST API")

# Message queue publisher (safe even if broker is down)
publisher = MqPublisher()

# --- Dependency: DB session per request ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Simple "auth" shim: require X-User-Id header ---
def require_user(user_id: Optional[str] = Header(default=None, alias="X-User-Id")) -> str:
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return user_id

class FileOut(BaseModel):
    id: str
    filename: str
    owner_id: str
    version: int
    size_bytes: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ShareIn(BaseModel):
    target_user_id: str

class ShareOut(BaseModel):
    id: str
    target_user_id: str

    class Config:
        from_attributes = True

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.post("/files", response_model=FileOut, status_code=201)
def upload_file(
    response: Response,
    uploaded: UploadFile = File(...),
    user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    # Persist file content to disk
    content = uploaded.file.read()
    size = len(content)

    meta = FileMeta(
        filename=uploaded.filename,
        content_type=uploaded.content_type,
        owner_id=user_id,
        version=1,
        size_bytes=size,
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)

    # Save bytes under STORAGE_DIR/<file_id>
    disk_path = os.path.join(STORAGE_DIR, meta.id)
    with open(disk_path, "wb") as f:
        f.write(content)

    response.headers["ETag"] = f'"{meta.version}"'
    # MQ event (skip quietly if broker down)
    publisher.publish(f'file.uploaded id={meta.id} owner={meta.owner_id} name={meta.filename} version={meta.version}')
    return meta

@app.get("/files", response_model=List[FileOut])
def list_files(
    user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    # Visible if owned OR shared to user
    q = (
        db.query(FileMeta)
        .outerjoin(Share, Share.file_id == FileMeta.id)
        .filter(or_(FileMeta.owner_id == user_id, Share.target_user_id == user_id))
        .distinct()
        .order_by(FileMeta.created_at.desc())
    )
    return q.all()

@app.get("/files/{file_id}")
def download_file(
    file_id: str,
    response: Response,
    user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    meta: FileMeta = db.query(FileMeta).filter(FileMeta.id == file_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")

    # Access control: owner or shared
    shared = (
        db.query(Share)
        .filter(Share.file_id == file_id, Share.target_user_id == user_id)
        .first()
    )
    if meta.owner_id != user_id and not shared:
        raise HTTPException(status_code=403, detail="Not authorized")

    disk_path = os.path.join(STORAGE_DIR, meta.id)
    if not os.path.exists(disk_path):
        raise HTTPException(status_code=410, detail="File content missing")

    response.headers["ETag"] = f'"{meta.version}"'
    return FileResponse(
        path=disk_path,
        media_type=meta.content_type or "application/octet-stream",
        filename=meta.filename,
    )

@app.put("/files/{file_id}", response_model=FileOut)
def update_file(
    file_id: str,
    response: Response,
    uploaded: UploadFile = File(...),
    if_match: Optional[str] = Header(default=None, alias="If-Match"),
    user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    meta: FileMeta = db.query(FileMeta).filter(FileMeta.id == file_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    if meta.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only owner may update")

    # Expect If-Match with the current version
    expected = f'"{meta.version}"'
    if not if_match or if_match.strip() != expected:
        raise HTTPException(
            status_code=409,
            detail=f'Version mismatch. Current ETag is {expected}. Provide If-Match header.',
        )

    # Replace content
    content = uploaded.file.read()
    size = len(content)
    disk_path = os.path.join(STORAGE_DIR, meta.id)
    with open(disk_path, "wb") as f:
        f.write(content)

    # Bump version and timestamps
    meta.version += 1
    meta.size_bytes = size
    meta.updated_at = datetime.utcnow()
    db.add(meta)
    db.commit()
    db.refresh(meta)

    response.headers["ETag"] = f'"{meta.version}"'
    publisher.publish(f'file.updated id={meta.id} owner={meta.owner_id} name={meta.filename} version={meta.version}')
    return meta

@app.post("/shares/{file_id}", response_model=ShareOut, status_code=201)
def share_file(
    file_id: str,
    share: ShareIn,
    user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    meta: FileMeta = db.query(FileMeta).filter(FileMeta.id == file_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    if meta.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only owner may share")

    existing = (
        db.query(Share)
        .filter(Share.file_id == file_id, Share.target_user_id == share.target_user_id)
        .first()
    )
    if existing:
        return existing

    s = Share(file_id=file_id, target_user_id=share.target_user_id)
    db.add(s)
    db.commit()
    db.refresh(s)
    publisher.publish(f'file.shared id={file_id} owner={meta.owner_id} target={share.target_user_id}')
    return s

@app.get("/shares/{file_id}", response_model=List[ShareOut])
def list_shares(
    file_id: str,
    user_id: str = Depends(require_user),
    db: Session = Depends(get_db),
):
    meta: FileMeta = db.query(FileMeta).filter(FileMeta.id == file_id).first()
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    if meta.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only owner can view shares")

    shares = db.query(Share).filter(Share.file_id == file_id).all()
    return shares
