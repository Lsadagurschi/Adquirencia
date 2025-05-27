# src/models/entities.py
import datetime
import random
import os
import json
import csv
from colorama import Fore, Style # Importar se for usar cores nos logs

# Assumindo que Transacao está em src/models/transaction.py
from src.models.transaction import Transacao

# As classes Bandeira, Adquirente, Emissor, Estabelecimento, Portador vêm aqui.
# Adapte os print_message e print_file_action para usar logging ou retornar mensagens para o Streamlit
# em vez de imprimir diretamente no console.
# Ex: Em vez de print(), você pode ter um método na classe que retorna a string do log.

# Exemplo de como a classe Adquirente poderia ser (com adaptações para logs):
class Estabelecimento:
    def __init__(self, id_estabelecimento, nome, cnae):
        self.id = id_estabelecimento
        self.nome = nome
        self.cnae = cnae

class Portador:
    def __init__(self, id_portador, nome, cpf, tipo_cartao):
        self.id = id_portador
        self.nome = nome
        self.cpf = cpf
        self.tipo_cartao = tipo_cartao

# Exemplo de adaptação:
class Adquirente:
    def __init__(self, nome, log_callback=None):
        self.nome = nome
        self.transacoes_recebidas = []
        self.transacoes_capturadas = []
        self.estabelecimentos = {}
        self.transacoes_a_liquidar = []
        self.log_callback = log_callback # Callback para enviar logs para a GUI

    def _log(self, message, color=None):
        if self.log_callback:
            self.log_callback(f"[{self.nome}]: {message}", color)
        else:
            print(message) # Fallback para console

    def cadastrar_estabelecimento(self, estabelecimento):
        self.estabelecimentos[estabelecimento.id] = estabelecimento
        self._log(f"Estabelecimento {estabelecimento.nome} ({estabelecimento.id}) cadastrado.")

    # ... resto da classe Adquirente, Bandeira, Emissor ...
    # Lembre-se de adaptar os métodos para usar self._log() em vez de print() direto
    # e para que as funções de geração de arquivos chamem as funções de src/services/file_generator.py
