# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from models import Base, engine, SessionLocal, User, Message
from core.security import create_access_token, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from core.auth import get_current_user
from pydantic import BaseModel


# Crear tablas al iniciar
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini Twitter")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# ====== DB DEPENDENCY ======
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
class UserCreate(BaseModel):
    username: str
    password: str

# ====== AUTH ENDPOINTS ======
@app.post("/users/register")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(400, "Username already exists")

    new_user = User(username=user.username)
    new_user.set_password(user.password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


@app.post("/users/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user or not db_user.verify_password(user.password):
        raise HTTPException(401, "Invalid username or password")

    access_token = create_access_token(
        data={"sub": db_user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


# ====== MESSAGES ======
@app.post("/messages")
def create_message(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = data.get("content")
    if not content:
        raise HTTPException(400, "content is required")

    msg = Message(user_id=current_user.id, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {"message": "Message created", "id": msg.id}


@app.get("/messages")
def list_messages(db: Session = Depends(get_db)):
    messages = db.query(Message).all()
    return [
        {
            "id": m.id,
            "content": m.content,
            "user": m.author.username,
            "likes": len(m.likes),
            "retweets": len(m.retweets)
        } for m in messages
    ]


# ====== LIKE / RETWEET ======
@app.post("/messages/{message_id}/like")
def like_message(message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(404, "Message not found")

    if current_user in msg.likes:
        raise HTTPException(400, "Already liked")

    msg.likes.append(current_user)
    db.commit()
    return {"message": "Liked"}


@app.post("/messages/{message_id}/retweet")
def retweet_message(message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(404, "Message not found")

    if current_user in msg.retweets:
        raise HTTPException(400, "Already retweeted")

    msg.retweets.append(current_user)
    db.commit()
    return {"message": "Retweeted"}
