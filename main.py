from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import hashlib
import os
from together import Together
from dotenv import load_dotenv

load_dotenv()

# Together AI client
client = Together(api_key=os.getenv("TOGETHER_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

# Database setup
def init_db():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            business_name TEXT,
            business_info TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            user_message TEXT,
            bot_reply TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Models
class SignupModel(BaseModel):
    name: str
    email: str
    password: str

class LoginModel(BaseModel):
    email: str
    password: str

class BusinessModel(BaseModel):
    user_email: str
    business_name: str
    business_info: str

class ChatModel(BaseModel):
    business_id: int
    user_message: str

# Routes
@app.get("/")
def home():
    return {"message": "Welcome to ChatBot SaaS!"}

@app.get("/health")
def health_check():
    return {
        "status": "Server is running!",
        "database": "SQLite connected!"
    }

@app.post("/signup")
def signup(user: SignupModel):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (user.email,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered!")
    hashed_password = hash_password(user.password)
    cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                   (user.name, user.email, hashed_password))
    conn.commit()
    conn.close()
    return {"message": f"Welcome {user.name}! Account created successfully!"}

@app.post("/login")
def login(user: LoginModel):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (user.email,))
    db_user = cursor.fetchone()
    conn.close()
    if not db_user:
        raise HTTPException(status_code=400, detail="Email not found!")
    if not verify_password(user.password, db_user[3]):
        raise HTTPException(status_code=400, detail="Wrong password!")
    return {
        "message": "Login successful!",
        "name": db_user[1],
        "email": db_user[2]
    }

@app.post("/business/create")
def create_business(business: BusinessModel):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO businesses (user_email, business_name, business_info) VALUES (?, ?, ?)",
                   (business.user_email, business.business_name, business.business_info))
    conn.commit()
    business_id = cursor.lastrowid
    conn.close()
    return {
        "message": f"{business.business_name} chatbot created!",
        "business_id": business_id
    }

@app.post("/chat")
def chat(chat: ChatModel):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM businesses WHERE id = ?", (chat.business_id,))
    business = cursor.fetchone()
    conn.close()
    if not business:
        raise HTTPException(status_code=400, detail="Business not found!")

    business_name = business[2]
    business_info = business[3]

    prompt = f"""You are a helpful customer support agent for {business_name}.
Here is the business information: {business_info}
Answer customer questions based only on this information. Be friendly and helpful.

Customer question: {chat.user_message}"""

    bot_reply = f"Thank you for contacting {business_name}! Our team will get back to you shortly. For urgent queries please visit us directly."

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (business_id, user_message, bot_reply) VALUES (?, ?, ?)",
                   (chat.business_id, chat.user_message, bot_reply))
    conn.commit()
    conn.close()

    return {
        "business": business_name,
        "user_message": chat.user_message,
        "bot_reply": bot_reply
    }

          


    


