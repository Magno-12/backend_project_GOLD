from sqlalchemy import Column, String, DateTime
from app.db.base_class import Base


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    id = Column(String, primary_key=True, index=True)
    blacklisted_on = Column(DateTime, nullable=False)
