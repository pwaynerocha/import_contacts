import re

def extrair_dados(conteudo_csv) -> dict:
    return {
        'origem_do_lead': conteudo_csv.get('\ufeffFonte'),
        'data_r1': conteudo_csv.get('Data R1'),
        'data_r2': conteudo_csv.get('Data R2'),
        'data_r3': conteudo_csv.get('Data R3'),
        'data_r4': conteudo_csv.get('Data R4'),
        'email': conteudo_csv.get('Email'),
        'primeiro_nome': conteudo_csv.get('Primeiro Nome'),
        'nome': conteudo_csv.get('Nome'),
        'telefone_trabalho': conteudo_csv.get('Telefone de Trabalho'),
        'telefone_2': conteudo_csv.get('Telefone 2'),
        'url': conteudo_csv.get('URL'),
        'trabalho': conteudo_csv.get('Trabalho'),
        'mora': conteudo_csv.get('Mora'),
        'interesse': conteudo_csv.get('Interesse'),
        'feedback': conteudo_csv.get('Feedback'),
        'data_retorno': conteudo_csv.get('DATA RETORNO'),
        'renda': conteudo_csv.get('RENDA'),
        'fgts': conteudo_csv.get('FGTS'),
        'entrada': conteudo_csv.get('ENTRADA'),
        'campanha': conteudo_csv.get('Campanha'),
        'primeiro': conteudo_csv.get('Primeiro'),
        'segundo': conteudo_csv.get('Segundo'),
        'terceiro': conteudo_csv.get('Terceiro'),
        'quarto': conteudo_csv.get('Quarto'),
        'quinto': conteudo_csv.get('Quinto'),
        'sexto': conteudo_csv.get('SEXTO'),
        'setima': conteudo_csv.get('SETIMA'),
        'duplicate_1': conteudo_csv.get('Duplicate 1'),
        'duplicate_2': conteudo_csv.get('Duplicate 2'),
        'duplicate_3': conteudo_csv.get('Duplicate 3')
    }

def alfanum(value: any) -> str:
    return "".join([char for char in re.findall(r"[a-zA-Z0-9]+", str(value).strip())])
