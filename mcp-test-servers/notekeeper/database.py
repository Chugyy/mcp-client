from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from typing import List, Optional
import os

Base = declarative_base()

class Note(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    user_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_archived = Column(Boolean, default=False)

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/notes.db")

def get_engine():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH}")

def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return engine

def get_session():
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

class NoteRepository:
    @staticmethod
    def get_notes_by_user(user_id: str, category: str = "", search: str = "", limit: int = 10) -> List[Note]:
        session = get_session()
        try:
            query = session.query(Note).filter(
                Note.user_id == user_id,
                Note.is_archived == False
            )
            
            if category.strip():
                query = query.filter(Note.category == category.strip().lower())
            
            if search.strip():
                search_term = f"%{search.strip()}%"
                query = query.filter(
                    Note.title.ilike(search_term) | Note.content.ilike(search_term)
                )
            
            return query.order_by(Note.updated_at.desc()).limit(min(limit, 50)).all()
        finally:
            session.close()

    @staticmethod
    def create_note(user_id: str, title: str, content: str, category: str = "general") -> Note:
        session = get_session()
        try:
            note = Note(
                user_id=user_id,
                title=title.strip(),
                content=content.strip(),
                category=category.strip().lower()
            )
            session.add(note)
            session.commit()
            session.refresh(note)
            return note
        finally:
            session.close()

    @staticmethod
    def get_note_by_id(user_id: str, note_id: int) -> Optional[Note]:
        session = get_session()
        try:
            return session.query(Note).filter(
                Note.id == note_id,
                Note.user_id == user_id
            ).first()
        finally:
            session.close()

    @staticmethod
    def update_note(user_id: str, note_id: int, title: str = "", content: str = "", category: str = "") -> Optional[Note]:
        session = get_session()
        try:
            note = session.query(Note).filter(
                Note.id == note_id,
                Note.user_id == user_id
            ).first()
            if note:
                if title.strip():
                    note.title = title.strip()
                if content.strip():
                    note.content = content.strip()
                if category.strip():
                    note.category = category.strip().lower()
                note.updated_at = datetime.now(timezone.utc)
                session.commit()
                session.refresh(note)
            return note
        finally:
            session.close()

    @staticmethod
    def delete_note(user_id: str, note_id: int) -> bool:
        session = get_session()
        try:
            note = session.query(Note).filter(
                Note.id == note_id,
                Note.user_id == user_id
            ).first()
            if note:
                note.is_archived = True
                session.commit()
                return True
            return False
        finally:
            session.close()

    @staticmethod
    def get_categories(user_id: str) -> List[tuple]:
        session = get_session()
        try:
            return session.query(Note.category, session.query(Note).filter(
                Note.user_id == user_id,
                Note.is_archived == False,
                Note.category == Note.category
            ).count().label('count')).filter(
                Note.user_id == user_id,
                Note.is_archived == False
            ).group_by(Note.category).all()
        finally:
            session.close()