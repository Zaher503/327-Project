import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db import Base

class FileMeta(Base):
    __tablename__ = "file_meta"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    owner_id = Column(String, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    size_bytes = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    shares = relationship("Share", back_populates="file", cascade="all, delete-orphan")

class Share(Base):
    __tablename__ = "shares"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, ForeignKey("file_meta.id"), nullable=False, index=True)
    target_user_id = Column(String, nullable=False, index=True)

    file = relationship("FileMeta", back_populates="shares")
