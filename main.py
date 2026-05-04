from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

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

@app.get("/widget.js")
def widget_js(id: int):
    js_code = f"""
(function() {{
    var bubble = document.createElement('div');
    bubble.innerHTML = '💬';
    bubble.style.cssText = 'position:fixed;bottom:20px;right:20px;width:60px;height:60px;background:#6366F1;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:28px;box-shadow:0 4px 12px rgba(0,0,0,0.3);z-index:99999;';
    document.body.appendChild(bubble);

    var chatWindow = document.createElement('div');
    chatWindow.style.cssText = 'position:fixed;bottom:90px;right:20px;width:320px;height:420px;background:white;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,0.2);display:none;flex-direction:column;z-index:99999;overflow:hidden;font-family:Segoe UI,sans-serif;';
    chatWindow.innerHTML = '<div style="background:#6366F1;color:white;padding:16px;font-weight:bold;font-size:15px;">🤖 AI Support</div><div id="botbuddy-messages" style="flex:1;padding:16px;overflow-y:auto;background:#f9f9f9;display:flex;flex-direction:column;gap:10px;"><div style="background:#6366F1;color:white;padding:10px 14px;border-radius:12px;max-width:80%;font-size:13px;">Hi! How can I help you today? 😊</div></div><div style="display:flex;padding:12px;border-top:1px solid #eee;background:white;"><input id="botbuddy-input" type="text" placeholder="Type a message..." style="flex:1;padding:10px;border:1px solid #ddd;border-radius:8px;font-size:13px;outline:none;"/><button id="botbuddy-send" style="margin-left:8px;padding:10px 16px;background:#6366F1;color:white;border:none;border-radius:8px;cursor:pointer;font-size:13px;">Send</button></div>';
    document.body.appendChild(chatWindow);

    bubble.onclick = function() {{
        chatWindow.style.display = chatWindow.style.display === 'flex' ? 'none' : 'flex';
    }};

    function sendMessage() {{
        var input = document.getElementById('botbuddy-input');
        var message = input.value.trim();
        if (!message) return;
        var messages = document.getElementById('botbuddy-messages');
        var userMsg = document.createElement('div');
        userMsg.style.cssText = 'background:#E5E7EB;color:#111;padding:10px 14px;border-radius:12px;max-width:80%;font-size:13px;align-self:flex-end;margin-left:auto;';
        userMsg.innerText = message;
        messages.appendChild(userMsg);
        input.value = '';
        messages.scrollTop = messages.scrollHeight;
        fetch('https://web-production-e9d55.up.railway.app/chat', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{business_id: {id}, user_message: message}})
        }})
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            var botMsg = document.createElement('div');
            botMsg.style.cssText = 'background:#6366F1;color:white;padding:10px 14px;border-radius:12px;max-width:80%;font-size:13px;';
            botMsg.innerText = data.bot_reply;
            messages.appendChild(botMsg);
            messages.scrollTop = messages.scrollHeight;
        }});
    }}

    document.getElementById('botbuddy-send').onclick = sendMessage;
    document.getElementById('botbuddy-input').onkeypress = function(e) {{
        if (e.key === 'Enter') sendMessage();
    }};
}})();
"""
    return HTMLResponse(content=js_code, media_type="application/javascript")
    

          


    


