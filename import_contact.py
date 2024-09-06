import csv
from utils import *

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
    def __init__(self, bitrix24_instance):
        self.bitrix24 = bitrix24_instance

    def criar_contato_e_negocio(self, dados_csv):
        batch_cmd = {}

        for i, linha in enumerate(dados_csv):
            dados = extrair_dados(linha)
            

            # Comando para criar o contato
            batch_cmd[f"contato_{i}"] = [
                "crm.contact.add", {
                    "fields": {
                        "NAME": dados['primeiro_nome'],
                        "PHONE": [
                            {"VALUE": dados['telefone_trabalho'], "VALUE_TYPE": "WORK"},
                            {"VALUE": dados['telefone_2'], "VALUE_TYPE": "MOBILE"}
                        ],
                        "EMAIL": [
                            {"VALUE": dados['email'], "VALUE_TYPE": "WORK"}
                        ],
                        "ASSIGNED_BY_ID": "17" # Usuário de espera

                    }
                }
            ]


            batch_cmd[f"negocio_{i}"] = [
                "crm.deal.add", {
                    "fields": {
                        "TITLE": f"{dados['nome']}",
                        "CONTACT_ID": "$result[contato_{i}]",  # Vincula o negócio ao contato criado
                        "CATEGORY_ID": "1",
                        "ASSIGNED_BY_ID": "17", # Usuário de espera
                        "COMMENTS": f"Planilha de Rebatida",
                        # Adicionar outros campos relevantes
                    }
                }
            ]

            # Se atingir o limite de 50, fazer a chamada em lote
            if len(batch_cmd) >= 50:
                self.bitrix24.call("batch", {"halt": 0, "cmd": batch_cmd})
                batch_cmd = {}
            
            print('Bitrix24 instance created successfully!')
            

        # Fazer a chamada final com os comandos restantes
        if batch_cmd:
            self.bitrix24.call("batch", {"halt": 0, "cmd": batch_cmd})
