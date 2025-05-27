# src/models/transaction.py
import datetime

class Transacao:
    def __init__(self, id_transacao, valor, tipo_cartao, numero_cartao_bin, data_hora, status="PENDENTE_AUTORIZACAO", nsu=None, codigo_autorizacao=None, id_estabelecimento=None, id_portador=None):
        self.id = id_transacao
        self.valor = valor
        self.tipo_cartao = tipo_cartao
        self.numero_cartao_bin = numero_cartao_bin
        self.data_hora = data_hora
        self.status = status
        self.nsu = nsu
        self.codigo_autorizacao = codigo_autorizacao
        self.id_estabelecimento = id_estabelecimento
        self.id_portador = id_portador

    def __repr__(self):
        return (f"Transacao(ID: {self.id}, Valor: R${self.valor:.2f}, Status: {self.status}, "
                f"BIN: {self.numero_cartao_bin}, Est: {self.id_estabelecimento})")
