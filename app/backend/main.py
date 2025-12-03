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
    
class UserLogin(BaseModel):
    username: str
    password: str
    
class UserOut(BaseModel):
    id: int
    username: str

class MessageCreate(BaseModel):
    username: str
    content: str

# --- Auth Endpoints ---
@app.post("/users/register", response_model=UserOut)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    logging.info(f"Attempting to register user: {user.username}")

    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        logging.warning(f"Registration failed: username '{user.username}' already exists")
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logging.info(f"User registered successfully: {user.username}")
    return db_user


@app.post("/users/login", response_model=UserOut)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    logging.info(f"Login attempt for username: {user.username}")

    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user:
        logging.warning(f"Login failed: username '{user.username}' not found")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not pwd_context.verify(user.password, db_user.hashed_password):
        logging.warning(f"Login failed: incorrect password for username '{user.username}'")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    logging.info(f"Login successful for username: {user.username}")
    return db_user



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
        "likes_users": [u.username for u in m.likes],        # <-- agregado
        "retweets_users": [u.username for u in m.retweets],  # <-- agregado
    }
    for m in messages
]



# Like/unlike endpoint
@app.post("/messages/{msg_id}/like")
def toggle_like(msg_id: int, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    msg = db.query(Message).options(joinedload(Message.likes)).filter(Message.id == msg_id).first()
    if not user or not msg:
        raise HTTPException(status_code=404, detail="User or message not found")
    
    if user in msg.likes:
        msg.likes.remove(user)
    else:
        msg.likes.append(user)
    
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "likes": len(msg.likes)}

# Retweet/un-retweet endpoint
@app.post("/messages/{msg_id}/retweet")
def toggle_retweet(msg_id: int, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    msg = db.query(Message).options(joinedload(Message.retweets)).filter(Message.id == msg_id).first()
    if not user or not msg:
        raise HTTPException(status_code=404, detail="User or message not found")
    
    if user in msg.retweets:
        msg.retweets.remove(user)
    else:
        msg.retweets.append(user)
    
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "retweets": len(msg.retweets)}
