from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from models import Base, engine, SessionLocal, User, Message

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini Twitter", root_path="/backend")

# --- CORS middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir cualquier origen (para desarrollo local)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencia de DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoints de usuarios ---
@app.post("/users")
def create_user(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(username=username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username}

# --- Endpoints de mensajes ---
@app.post("/messages")
def post_message(username: str, content: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    message = Message(username=username, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"id": message.id, "username": message.username, "content": message.content}

@app.get("/messages")
def get_messages(db: Session = Depends(get_db)):
    messages = db.query(Message).all()
    return [{"id": m.id, "username": m.username, "content": m.content} for m in messages]
