from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from models import Base, engine, SessionLocal, User, Message

# Crear tablas nuevas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini Twitter", root_path="/backend")

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

# --- Users ---
@app.post("/users")
def create_user(username: str, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username}

@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return [{"id": u.id, "username": u.username} for u in db.query(User).all()]

# --- Messages ---
@app.post("/messages")
def post_message(username: str, content: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    msg = Message(username=username, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "username": msg.username, "content": msg.content}

@app.get("/messages")
def get_messages(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    messages = db.query(Message).order_by(Message.id.desc()).offset(skip).limit(limit).all()
    return [{"id": m.id, "username": m.username, "content": m.content} for m in messages]


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

