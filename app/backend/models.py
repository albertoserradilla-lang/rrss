from sqlalchemy import Column, Integer, String, ForeignKey, Table, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker

Base = declarative_base()

# --- Association tables for many-to-many relationships ---

# Likes: users can like messages
likes_table = Table(
    'likes',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('message_id', Integer, ForeignKey('messages.id'), primary_key=True)
)

# Retweets: users can retweet messages
retweets_table = Table(
    'retweets',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('message_id', Integer, ForeignKey('messages.id'), primary_key=True)
)

# --- Models ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)

    # Eager load messages (joined), so accessing user.messages does not trigger extra query
    messages = relationship(
        "Message",
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="joined"  # joined loading
    )

    # Likes and retweets loaded in batches (selectin) for efficiency
    liked_messages = relationship(
        "Message",
        secondary=likes_table,
        back_populates="likes",
        lazy="selectin"
    )

    retweeted_messages = relationship(
        "Message",
        secondary=retweets_table,
        back_populates="retweets",
        lazy="selectin"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, ForeignKey("users.username"))
    content = Column(String)

    # Author loaded via joined
    author = relationship(
        "User",
        back_populates="messages",
        lazy="joined"
    )

    # Likes and retweets loaded in batches (selectin)
    likes = relationship(
        "User",
        secondary=likes_table,
        back_populates="liked_messages",
        lazy="selectin"
    )

    retweets = relationship(
        "User",
        secondary=retweets_table,
        back_populates="retweeted_messages",
        lazy="selectin"
    )


# --- Engine and session ---
DATABASE_URL = "postgresql://mini_twitter:password@postgres-service:5432/mini_twitter"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)