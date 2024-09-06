import argparse
from Bx24Client import Bitrix24
import requests
import uvicorn
import json
from urllib.parse import unquote
from urllib.parse import parse_qs
from pydantic import BaseModel
from typing import Optional
import json
import os
from auth import create_or_update_auth, read_auth, CLIENT_ID, CLIENT_SECRET

import csv
from utils import extrair_dados
from logger import write_log


def ler_dados_csv(caminho_arquivo):
    with open(caminho_arquivo, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        dados = [row for row in reader]
    return dados


class Bitrix24APIHandler:
    mapped_deal_fields = {
        'DATA R1': 'UF_CRM_1725044538254',
        'DATA R2': 'UF_CRM_1725044550153',
        'DATA R3': 'UF_CRM_1725044560605',
        'DATA R4': 'UF_CRM_1725044571725',
        'Primeiro Consultor': 'UF_CRM_1725046948904',
        'Segundo Consultor': 'UF_CRM_1725047534529',
        'Terceiro Consultor': 'UF_CRM_1725047748204',
        'Quarto Consultor': 'UF_CRM_1725048019176',
        'Quinto Consultor': 'UF_CRM_1725048162238',
        'Informações da Fonte': 'SOURCE_DESCRIPTION',
        'Fonte': 'SOURCE_ID',
        'Telefone 2': 'UF_CRM_1725379010352', # ESTE É DE CONTATO, OS DEMAIS DE DEAL

    }
    def __init__(self, bitrix24_instance, csv_data):
        self.bitrix24 = bitrix24_instance

        if csv_data:
            self.data = [extrair_dados(line) for _, line in enumerate(csv_data)]
        else:
            self.data = None

    def criar_contato_e_negocio(self):
        ID_USUARIO_ESPERA = "17"

        write_log("REBATIDA", f"")

        for i, negocio_contato in enumerate(self.data):
            nome = negocio_contato['primeiro_nome']
            telefone_principal = negocio_contato['telefone_trabalho']
            telefone_secundario = negocio_contato['telefone_2'] if negocio_contato['telefone_2'] else ""


            self.bitrix24.call(
                "crm.contact.add",
                {
                    "fields": {
                        "NAME": negocio_contato['primeiro_nome'],
                        "PHONE": [
                            {"VALUE": telefone_principal, "VALUE_TYPE": "WORK"},
                            {"VALUE": telefone_secundario, "VALUE_TYPE": "MOBILE"},
                        ],
                        "EMAIL": [
                            {"VALUE": negocio_contato['email'], "VALUE_TYPE": "WORK"}
                        ],
                        "ASSIGNED_BY_ID": ID_USUARIO_ESPERA
                    }
                }
            )

            """ batch_cmd[f"negocio_{i}"] = [
                "crm.deal.add", {
                    "fields": {
                        "TITLE": f"{negocio_contato['nome']}",
                        "CONTACT_ID": "$result[contato_{i}]",  # Vincula o negócio ao contato criado
                        "CATEGORY_ID": "1",
                        "ASSIGNED_BY_ID": ID_USUARIO_ESPERA,
                        "COMMENTS": f"Planilha de Rebatida",
                        self.mapped_deal_fields['DATA R1']: negocio_contato['data_r1'],
                        self.mapped_deal_fields['DATA R2']: negocio_contato['data_r2'],
                        self.mapped_deal_fields['DATA R3']: negocio_contato['data_r3'],
                        self.mapped_deal_fields['DATA R4']: negocio_contato['data_r4'],
                        self.mapped_deal_fields['Primeiro Consultor']: negocio_contato['primeiro'],
                        self.mapped_deal_fields['Segundo Consultor']: negocio_contato['segundo'],
                        self.mapped_deal_fields['Terceiro Consultor']: negocio_contato['terceiro'],
                        self.mapped_deal_fields['Quarto Consultor']: negocio_contato['quarto'],
                        self.mapped_deal_fields['Quinto Consultor']: negocio_contato['quinto'],
                        self.mapped_deal_fields['Informações da Fonte']: negocio_contato['campanha'],
                        self.mapped_deal_fields['Fonte']: negocio_contato['origem_do_lead'],
                        self.mapped_deal_fields['Telefone 2']: negocio_contato['telefone_2'],
                    }
                }
            ] """

            """ # Se atingir o limite de 50, fazer a chamada em lote
            if len(batch_cmd) >= 50:
                result = self.bitrix24.call("batch", {"halt": 0, "cmd": batch_cmd})
                batch_cmd = {}

        # Fazer a chamada final com os comandos restantes
        if batch_cmd:
            result = self.bitrix24.call("batch", {"halt": 0, "cmd": batch_cmd}) """

    def create_contacts(self):
        pass
        
    def clean_55_contacts(self):
        contacts_id = []

        next_ID = None
        finish_fetch_contacts = False

        while not finish_fetch_contacts:
            contacts = self.bitrix24.call("crm.contact.list", {"select": ["ID"], "filter": {">ID": next_ID if next_ID else 0}})

            if not contacts.get("next"):
                finish_fetch_contacts = True
            else:
                try:
                    next_ID = contacts.get("result")[-1]["ID"]
                except KeyError as e:
                    finish_fetch_contacts = True

            for contact in contacts.get("result"):
                contacts_id.append(contact['ID'])
            

        for _id in contacts_id:
            contact = self.bitrix24.call("crm.contact.get", {"id": _id, "select": ['PHONE']})
            if contact['result'].get('PHONE'):
                has_55 = False
                _55_indexes = []
                
                for phone_obj in contact['result']['PHONE']:
                    if phone_obj.get("VALUE") == "55":
                        _55_indexes.append(phone_obj.get("ID"))

                if _55_indexes:
                    update_response = self.bitrix24.call("crm.contact.update", {"ID": _id, "fields": {"PHONE": [{"ID": _55_index, "VALUE": ""} for _55_index in _55_indexes]}})
                    write_log("clean55", f"[clean-55-numbers] Contact ID {_id} updated. 55 removed. Bitrix Response: {update_response.get('result')}")


def main(bx24: Bitrix24):
    dados = ler_dados_csv('fonte.csv')

    amostra = dados[1:2]

    Bitrix24APIHandler(bx24, amostra).criar_contato_e_negocio()


def refresh_auth(access_token: str, refresh_token: str):
    auth = read_auth()

    create_or_update_auth(
        domain=auth['domain'],
        auth_token=access_token,
        refresh_token=refresh_token
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ação")
    parser.add_argument('action', type=str, help="Qual ação será executada: 'see-auth' | 'clean-55-numbers' | 'start' ")

    args = parser.parse_args()

    action = args.action
    
    auth = read_auth()

    # Instancia o Bitrix24 com os parâmetros extraídos
    bx24 = Bitrix24(
        domain=auth['domain'],
        auth_token=auth['auth_token'],
        refresh_token=auth['refresh_token'],
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_renew_callback=lambda auth, refresh, expires, expires_in: refresh_auth(auth, refresh)
    )
    bx24.log_mode = "minimal" # 'verbose' | 'minimal' | 'log'

    if action == 'see-auth':
        print("Auth data:\n", json.dumps(auth, indent=4))
    elif action == 'clean55':
        print("\nRemovendo números com apenas '55'...")
        Bitrix24APIHandler(bx24, None).clean_55_contacts()
        print("\npronto")
    elif action == 'start':
        main(bx24)
    else:
        print("Ação inválida.")
        exit(1)
