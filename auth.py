import json
import os
from logger import write_log

CLIENT_ID = 'local.66daf1c62a5d42.82270587'
CLIENT_SECRET = '3Bs8oie5zt0680QaNnUnEAbyY5BP5ECaZzy2HGTg72OWXviqQC'

# Caminho do arquivo auth.json na pasta atual
file_path = os.path.join(os.getcwd(), "auth.json")

# Função para criar ou sobrescrever o arquivo auth.json
def create_or_update_auth(domain: str, auth_token: str, refresh_token: str):
    with open(file_path, 'w') as file:
        json.dump({
            "domain": domain,
            "auth_token": auth_token,
            "refresh_token": refresh_token
        }, file, indent=4)
    
    write_log("auth", f"Auth updated")


# Função para ler o arquivo auth.json
def read_auth():
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    else:
        write_log("auth", f"ERROR: auth.json not found")
        raise Exception("O arquivo auth.json não existe. Reinstale o App")