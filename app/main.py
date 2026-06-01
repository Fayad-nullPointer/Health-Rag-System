from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.api.chat import router as chat_router
from app.api.auth import router as auth_router

from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MindCare AI")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")
templates.env.cache = {}


app.include_router(chat_router)
app.include_router(auth_router, prefix="/auth")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})

@app.get("/chat")
def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html", {})