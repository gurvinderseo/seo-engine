from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "SEO Engine Backend is running!"}

@app.get("/api/connect")
def connect_to_google():
    # create OAuth URL
    ...

@app.get("/api/connect/callback")
def oauth_callback(code: str):
    # handle token exchange
    ...
