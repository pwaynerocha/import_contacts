from fastapi import FastAPI, HTTPException, Request
from Bx24Client import Bitrix24
from fastapi.templating import Jinja2Templates
import requests
import uvicorn
import json
from urllib.parse import unquote
from urllib.parse import parse_qs
from pydantic import BaseModel
from typing import Optional
from auth import create_or_update_auth

class AuthData(BaseModel):
    AUTH_ID: str
    AUTH_EXPIRES: str
    REFRESH_ID: str
    member_id: str
    status: str
    PLACEMENT: str
    PLACEMENT_OPTIONS: str

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.post("/install/")
async def install(request: Request):
    form_data = await request.form()
    post_data = {key: form_data[key] for key in form_data.keys()}

    create_or_update_auth(
        domain=request.query_params.get('DOMAIN'),
        auth_token=post_data.get('AUTH_ID'),
        refresh_token=post_data.get('REFRESH_ID')
    )

    return templates.TemplateResponse("install.html", {"request": request})


def main():
    # Inicie o servidor Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()