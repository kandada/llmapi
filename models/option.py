from sqlalchemy import Column, String, Text
from .base import BaseModel


class Option(BaseModel):
    __tablename__ = "options"

    key = Column(String(255), primary_key=True)
    value = Column(Text)
