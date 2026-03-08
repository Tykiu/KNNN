from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from tutor_db import Base 

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    MSSV = Column(String, unique=True)
    email = Column(String)
    verified = Column(Boolean, default=False)
    is_tutor = Column(Boolean, default=False)
    subjects_can_teach = Column(String, nullable=True)

class TutorRequest(Base):
    __tablename__ = "tutor_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    mode = Column(String)
    link_or_address = Column(String)
    time = Column(String)
    note = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)