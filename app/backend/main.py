from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from models import Base, engine, SessionLocal, User, Message
from passlib.context import CryptContext
from pydantic import BaseModel
import logging

# Crear tablas nuevas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini Twitter", root_path="/backend")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CONFIGURAR LOGGING ---
logging.basicConfig(
    level=logging.INFO,              # nivel mínimo de mensajes
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schemas ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

class MessageCreate(BaseModel):
    username: str
    content: str

# --- Auth Endpoints ---
@app.post("/users/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    logging.info(f"Intentando registrar usuario: {user.username}")
    if db.query(User).filter(User.username == user.username).first():
        logging.info(f"Intentando registrar usuario: {user.username}")
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = pwd_context.hash(user.password)
    user_db = User(username=user.username, hashed_password=hashed)
    db.add(user_db)
    db.commit()
    db.refresh(user_db)
    logging.info(f"Intentando registrar usuario: {user.username}")
    return {"id": user_db.id, "username": user_db.username}

@app.post("/users/login")
def login_user(username: str, password: str, db: Session = Depends(get_db)):
    logging.info(f"Login attempt for username: {username}")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        logging.warning(f"Login failed: username '{username}' not found")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not pwd_context.verify(password, user.hashed_password):
        logging.warning(f"Login failed: incorrect password for username '{username}'")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    logging.info(f"Login successful for username: {username}")
    return {"id": user.id, "username": user.username}


# --- Users Endpoints ---
@app.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# --- Messages ---
@app.post("/messages")
def post_message(msg: MessageCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == msg.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_msg = Message(username=msg.username, content=msg.content)
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return {
        "id": new_msg.id,
        "username": new_msg.username,
        "content": new_msg.content
    }

@app.get("/messages")
def get_messages(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    messages = db.query(Message).order_by(Message.id.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": m.id,
            "username": m.username,
            "content": m.content,
            "likes": len(m.likes),
            "retweets": len(m.retweets),
        }
        for m in messages
    ]

# --- Like endpoint ---
@app.post("/messages/{msg_id}/like")
def like_message(msg_id: int, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    msg = db.query(Message).options(joinedload(Message.likes)).filter(Message.id == msg_id).first()
    if not user or not msg:
        raise HTTPException(status_code=404, detail="User or message not found")
    if user not in msg.likes:
        msg.likes.append(user)
        db.commit()
        db.refresh(msg)
    return {"id": msg.id, "likes": len(msg.likes)}

@app.post("/messages/{msg_id}/retweet")
def retweet_message(msg_id: int, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    msg = db.query(Message).options(joinedload(Message.retweets)).filter(Message.id == msg_id).first()
    if not user or not msg:
        raise HTTPException(status_code=404, detail="User or message not found")
    if user not in msg.retweets:
        msg.retweets.append(user)
        db.commit()
        db.refresh(msg)
    return {"id": msg.id, "retweets": len(msg.retweets)}
