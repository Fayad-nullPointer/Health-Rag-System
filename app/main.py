from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router

app = FastAPI(title="MindCare AI")

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

templates = Jinja2Templates(
    directory="app/templates"
)

app.include_router(chat_router)


@app.get("/")
def home(request: Request):

    return templates.TemplateResponse(
        request,
        "chat.html",
        {}
    )