import os, uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Text, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
class Base(DeclarativeBase): pass
class Record(Base):
    __tablename__='records'
    id: Mapped[str]=mapped_column(String(100),primary_key=True)
    kind: Mapped[str]=mapped_column(String(30),index=True)
    data: Mapped[dict]=mapped_column(JSON)
    version: Mapped[int]=mapped_column(Integer,default=1)
class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String(100),primary_key=True,default=uid)
    email: Mapped[str]=mapped_column(String(254),unique=True)
    name: Mapped[str]=mapped_column(String(200))
    password: Mapped[str]=mapped_column(Text)
    role: Mapped[str]=mapped_column(String(20),default='member')
    active: Mapped[bool]=mapped_column(Boolean,default=False)
class Login(Base):
    __tablename__='sessions'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(String(100),index=True)
    expires: Mapped[int]=mapped_column(Integer)
class Proposal(Base):
    __tablename__='proposals'
    id: Mapped[str]=mapped_column(String(100),primary_key=True)
    actor: Mapped[str]=mapped_column(String(100))
    kind: Mapped[str]=mapped_column(String(30))
    target: Mapped[str]=mapped_column(String(100))
    base_version: Mapped[int]=mapped_column(Integer,default=0)
    payload: Mapped[dict]=mapped_column(JSON)
    source: Mapped[str]=mapped_column(Text,default='')
    status: Mapped[str]=mapped_column(String(30),default='pending')
    created: Mapped[str]=mapped_column(String(50),default=now)
    reviewer: Mapped[str|None]=mapped_column(String(100),nullable=True)
    reason: Mapped[str]=mapped_column(Text,default='')
class Audit(Base):
    __tablename__='audit'
    id: Mapped[str]=mapped_column(String(100),primary_key=True,default=uid)
    target: Mapped[str]=mapped_column(String(100),index=True)
    actor: Mapped[str]=mapped_column(String(100))
    action: Mapped[str]=mapped_column(String(100))
    data: Mapped[dict]=mapped_column(JSON)
    created: Mapped[str]=mapped_column(String(50),default=now)
class Share(Base):
    __tablename__='shares'
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    name: Mapped[str]=mapped_column(String(200))
    token_hash: Mapped[str]=mapped_column(String(64),unique=True)
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    data: Mapped[dict]=mapped_column(JSON)
class Setting(Base):
    __tablename__='settings'
    id: Mapped[str]=mapped_column(String(100),primary_key=True)
    data: Mapped[dict]=mapped_column(JSON)
class Outbox(Base):
    __tablename__='outbox'
    id: Mapped[str]=mapped_column(String(100),primary_key=True)
    data: Mapped[dict]=mapped_column(JSON)
    status: Mapped[str]=mapped_column(String(30),default='queued')
    error: Mapped[str]=mapped_column(Text,default='')
    created: Mapped[str]=mapped_column(String(50),default=now)

def database(url):
    engine=create_engine(url,connect_args={'check_same_thread':False,'timeout':30} if url.startswith('sqlite') else {},pool_pre_ping=True)
    if url.startswith('sqlite'):
        from sqlalchemy import event
        @event.listens_for(engine,'connect')
        def pragmas(dbapi, _): dbapi.execute('PRAGMA journal_mode=WAL')
    Base.metadata.create_all(engine)
    return engine,sessionmaker(engine,expire_on_commit=False)
