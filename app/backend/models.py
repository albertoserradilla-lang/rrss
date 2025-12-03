from sqlalchemy import Column, Integer, String, ForeignKey, Table, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from passlib.context import CryptContext

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

likes_table = Table(
    "likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("message_id", Integer, ForeignKey("messages.id"), primary_key=True)
)

retweets_table = Table(
    "retweets",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("message_id", Integer, ForeignKey("messages.id"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    messages = relationship("Message", back_populates="author", cascade="all, delete-orphan", lazy="selectin")
    liked_messages = relationship("Message", secondary=likes_table, back_populates="likes", lazy="selectin")
    retweeted_messages = relationship("Message", secondary=retweets_table, back_populates="retweets", lazy="selectin")

    def set_password(self, password: str):
        self.hashed_password = pwd_context.hash(password)

    def verify_password(self, password: str):
        return pwd_context.verify(password, self.hashed_password)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)

    author = relationship("User", back_populates="messages", lazy="joined")
    likes = relationship("User", secondary=likes_table, back_populates="liked_messages", lazy="selectin")
    retweets = relationship("User", secondary=retweets_table, back_populates="retweeted_messages", lazy="selectin")

DATABASE_URL = "postgresql://mini_twitter:password@postgres-service:5432/mini_twitter"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
