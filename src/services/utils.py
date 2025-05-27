# src/services/utils.py
# Funções utilitárias aqui (ex: formatação de strings, validações gerais)
# Se você usar colorama para logs no terminal, pode mantê-las aqui
import time
from colorama import Fore, Style, init

init(autoreset=True)

def print_separator():
    print(Fore.CYAN + "\n" + "="*80 + Style.RESET_ALL)

def print_step(title):
    print(Fore.MAGENTA + f"\n--- {title} ---" + Style.RESET_ALL)
    time.sleep(1)

def print_message(sender, receiver, msg_type, content, color=Fore.WHITE):
    print(color + f"[{sender} -> {receiver}] {msg_type}: {content}" + Style.RESET_ALL)
    time.sleep(0.5)

def print_file_action(entity, action, filename, color=Fore.GREEN):
    print(color + f"[{entity}] {action} Arquivo: {os.path.basename(filename)}" + Style.RESET_ALL)
    time.sleep(0.7)
