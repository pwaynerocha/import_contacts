import os
from datetime import datetime

# Função que cria/acrescenta um log com base na data e hora atual
def write_log(log_file: str, content: str):
    # Obter data e hora atual
    current_time = datetime.now()
    
    # Formatar a data e hora para o nome do arquivo
    log_filename = log_file+".log"
    log_time = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    
    # Definir o caminho da pasta de logs
    logs_folder = os.path.join(os.getcwd(), "logs")
    
    # Garantir que a pasta logs exista
    if not os.path.exists(logs_folder):
        os.makedirs(logs_folder)
    
    # Definir o caminho completo do arquivo de log
    log_file_path = os.path.join(logs_folder, log_filename)
    
    # Escrever no arquivo (acrescentar no final, se o arquivo já existir)
    with open(log_file_path, 'a') as log_file:
        log_file.write(f"\n[{log_time}]" + content)
    
    print(f"[{log_file}] "+content)
