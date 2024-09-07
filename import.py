import argparse
from Bx24Client import Bitrix24
from datetime import datetime
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
from utils import extrair_dados, alfanum
from logger import write_log


def ler_dados_csv(caminho_arquivo):
    with open(caminho_arquivo, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        dados = [row for row in reader]
    return dados


class Bitrix24APIHandler:
    mapped_deal_fields = {
        'DATA_R1': 'UF_CRM_1725044538254',
        'DATA_R2': 'UF_CRM_1725044550153',
        'DATA_R3': 'UF_CRM_1725044560605',
        'DATA_R4': 'UF_CRM_1725044571725',
        'c1': 'UF_CRM_1725680565',
        'c2': 'UF_CRM_1725680575',
        'c3': 'UF_CRM_1725680584',
        'c4': 'UF_CRM_1725680597',
        'c5': 'UF_CRM_1725680607',
        'Informações da Fonte': 'SOURCE_DESCRIPTION',
        'Fonte': 'SOURCE_ID',
        'Telefone_2': 'UF_CRM_1725379010352', # ESTE É DE CONTATO, OS DEMAIS DE DEAL
    }
    skip_contact_prefetch = False

    def __init__(self, bitrix24_instance, csv_data):
        self.bitrix24 = bitrix24_instance

        if csv_data:
            self.data = [extrair_dados(line) for _, line in enumerate(csv_data)]
        else:
            self.data = None

    @staticmethod
    def lowerSPAField(field: str) -> str:
        if isinstance(field, str) and 'crm' in field.lower() and 'uf' in field.lower() and field.count("_") >= 2:
            parts = field.split("_", maxsplit=2)
            if len(parts) == 3:
                return f"{parts[0].lower()}{parts[1].capitalize()}{parts[2]}"
        return field

    @staticmethod
    def phone_exists(search, d):
        for k, v in d.items():
            if k in search:
                return v
        return None

    @staticmethod
    def convert_date(date: any) -> str:
        return datetime.strptime(value.strip(), kwargs.get("format", "%d/%m/%Y %H:%M:%S"))

    def criar_contato_e_negocio(self, start_from: int):
        save_path = os.path.join(os.getcwd(), "save.txt")
        source_ids_path = os.path.join(os.getcwd(), "source_id.json")

        ID_USUARIO_ESPERA = "17"

        """ SOURCE IDS """

        with open(source_ids_path, 'r') as file:
            source_id_map = json.load(file)

        if not self.skip_contact_prefetch:
            print("PREFETCH ALL CONTACTS")

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

            print(f"{len(contacts_id)} CONTACTS FOUND IN BITRIX... Getting its numbers")

            contacts_id_divided = []
            while contacts_id:
                contacts_id_divided.append(contacts_id[:50])
                contacts_id = contacts_id[50:]

            contact_id_mapping = {}

            for contact_id_list in contacts_id_divided:
                crm_contact_get_batch_result = self.bitrix24.call(
                    "batch",
                    {
                        "halt": 0,
                        "cmd": {
                            f"add_contact_{c_id}": ["crm.contact.get", {"id": c_id, "SELECT": ['PHONE', "ID"]}]
                            for c_id in contact_id_list
                        }
                    }
                )

                result = crm_contact_get_batch_result.get('result').get("result")

                if isinstance(result, dict):
                    for contact in result.values():
                        if 'PHONE' in contact:
                            for phone_number in contact.get("PHONE"):
                                contact_id_mapping[alfanum(phone_number.get('VALUE'))] = contact.get('ID')
            
            print(f"ALL CONTACTS GOT")
        
        print(f"REGISTERING CONTACT AND DEALS...\n")

        csv_index = start_from
        for i, negocio_contato in enumerate(self.data):
            loop_result = {
                'line': f"{csv_index}+1",
                'contact': 'not processed',
                'deal': 'not processed',
                'error': None
            }

            try:
                nome = negocio_contato['nome']
                nome_unico = negocio_contato['primeiro_nome']
                telefone_principal = negocio_contato['telefone_trabalho'] if negocio_contato['telefone_trabalho'] else ""
                telefone_secundario = negocio_contato['telefone_2'] if negocio_contato['telefone_2'] else ""

                fonte = None
                for source in source_id_map:
                    if source['NAME'] == negocio_contato['origem_do_lead']:
                        fonte = source['STATUS_ID']

                phones = []
                if telefone_principal:
                    phones.append({"VALUE": telefone_principal, "VALUE_TYPE": "WORK"})

                """ CONTATO """
                contact_id_to_link = None
                
                telefone_principal_contact_id = self.phone_exists(telefone_principal, contact_id_mapping)
                telefone_secundario_contact_id = self.phone_exists(telefone_secundario, contact_id_mapping)

                if telefone_principal_contact_id:
                    contact_id_to_link = telefone_principal_contact_id

                if telefone_secundario_contact_id:
                    contact_id_to_link = telefone_secundario_contact_id

                if contact_id_to_link:
                    crm_contact_update_result = self.bitrix24.call(
                        "crm.contact.update",
                        {
                            "id": contact_id_to_link,
                            "fields": {
                                "NAME": nome_unico,
                            }
                        }
                    )

                    if crm_contact_update_result.get('result'):
                        loop_result['contact'] = f"updated[ID:{contact_id_to_link}]"
                else:
                    crm_contact_add_result = self.bitrix24.call(
                        "crm.contact.add",
                        {
                            "fields": {
                                "NAME": nome_unico,
                                "PHONE": phones,
                                "EMAIL": [
                                    {"VALUE": negocio_contato['email'], "VALUE_TYPE": "WORK"}
                                ],
                                "SOURCE_ID": fonte,
                                "SOURCE_DESCRIPTION": negocio_contato['campanha'],
                                self.lowerSPAField(self.mapped_deal_fields['Telefone_2']): telefone_secundario,
                                "ASSIGNED_BY_ID": ID_USUARIO_ESPERA
                            }
                        }
                    )

                    if crm_contact_add_result.get('result'):
                        contact_id_to_link = crm_contact_add_result.get('result')
                        loop_result['contact'] = f"created[ID:{contact_id_to_link}]"
                    else:
                        loop_result['contact'] = "creation-error"

                """ NEGOCIO """

                deal_add_obj = {
                    "fields": {
                        "TITLE": negocio_contato['nome'],
                        "CONTACT_ID": contact_id_to_link,
                        "CATEGORY_ID": "1",
                        "ASSIGNED_BY_ID": ID_USUARIO_ESPERA,
                        "COMMENTS": f"Planilha de Rebatida",
                        self.mapped_deal_fields['DATA_R1']: negocio_contato['data_r1'],
                        self.mapped_deal_fields['DATA_R2']: negocio_contato['data_r2'],
                        self.mapped_deal_fields['DATA_R3']: negocio_contato['data_r3'],
                        self.mapped_deal_fields['DATA_R4']: negocio_contato['data_r4'],
                        self.mapped_deal_fields['c1']: negocio_contato['primeiro'],
                        self.mapped_deal_fields['c2']: negocio_contato['segundo'],
                        self.mapped_deal_fields['c3']: negocio_contato['terceiro'],
                        self.mapped_deal_fields['c4']: negocio_contato['quarto'],
                        self.mapped_deal_fields['c5']: negocio_contato['quinto'],
                        self.mapped_deal_fields['Informações da Fonte']: negocio_contato['campanha'],
                        self.mapped_deal_fields['Fonte']: fonte,
                        self.mapped_deal_fields['Telefone_2']: negocio_contato['telefone_2'],
                    }
                }
                
                crm_deal_add_result = self.bitrix24.call("crm.deal.add", deal_add_obj)

                if crm_deal_add_result.get('result'):
                    loop_result['deal'] = f"created[ID:{crm_deal_add_result.get('result')}]"
            except Exception as e:
                loop_result['error'] = str(e)
                write_log("exceptions", str(e))
            
            try:
                """ SAVE LAST LINE """
                
                csv_index += 1
                with open(save_path, 'w') as file:
                    file.write(str(csv_index))
                
                loop_msg = " | ".join([f"{k}: {v}" for k, v in loop_result.items()])
                
                write_log("REBATIDA", loop_msg)

                print(loop_msg)

            except Exception as e:
                write_log("exceptions", str(e))
        

    def create_save(self):
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
    dados = ler_dados_csv('deals.csv')

    starts_from = 0

    save_path = os.path.join(os.getcwd(), "save.txt")
    if os.path.exists(save_path):
        with open(save_path, 'r') as file:
            result = file.read()
            if result.isdigit():
                starts_from = int(result)
    else:
        with open(save_path, 'w') as file:
            file.write(str("0"))

    Bitrix24APIHandler(bx24, dados).criar_contato_e_negocio(starts_from)


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
    bx24.log_mode = "log" # 'verbose' | 'minimal' | 'log'

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
