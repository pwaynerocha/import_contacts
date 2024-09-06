from fastapi import FastAPI, HTTPException, Request
from Bx24Client import Bitrix24
from fastapi.templating import Jinja2Templates
from import_contact import *
import requests
import uvicorn
import json
from urllib.parse import unquote
from urllib.parse import parse_qs
from pydantic import BaseModel
from typing import Optional

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
    return templates.TemplateResponse("install.html", {"request": request})

@app.post("/import-contacts/")
async def import_contacts(request: Request):
    try:
        form_data = await request.form()
        post_data = {key: form_data[key] for key in form_data.keys()}
        try:
            auth_data = AuthData(**post_data)
        except ValueError as e:
            return {"error": str(e)}

        data = {
            "auth_data": auth_data.dict(),
        }

        
        print(data)

        # Extrai os parâmetros relevantes para o Bitrix24
        domain = 'hinodeimoveis.bitrix24.com.br'
        auth_token = data.get("auth_data", {}).get('AUTH_ID')
        refresh_token = data.get("auth_data", {}).get('REFRESH_ID')
        client_id = 'local.66daf1c62a5d42.82270587'
        client_secret = '3Bs8oie5zt0680QaNnUnEAbyY5BP5ECaZzy2HGTg72OWXviqQC'

        # Verifica se os parâmetros necessários estão presentes
        if not domain or not auth_token:
            raise HTTPException(status_code=400, detail="Domain and auth_token are required")

        # Instancia o Bitrix24 com os parâmetros extraídos
        bitrix_instance = Bitrix24(
            domain=domain,
            auth_token=auth_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret
        )

        dados = ler_dados_csv('teste.csv')
        Bitrix24APIHandler(bitrix_instance).criar_contato_e_negocio(dados)


        # Você pode armazenar ou utilizar a instância conforme necessário
        
        return {"message": "Bitrix24 instances created successfully!"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def main():
    # Inicie o servidor Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()