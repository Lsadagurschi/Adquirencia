# src/models/entities.py
import datetime
import random
import os
import json
import csv
from src.models.transaction import Transacao
from src.models.chargeback import Chargeback # Novo import

# ... classes Estabelecimento, Portador ...

class Bandeira:
    def __init__(self, nome, log_callback=None):
        self.nome = nome
        self.log_callback = log_callback
        self.transacoes_pendentes_emissor = {}
        self.arquivos_captura_recebidos = []
        self.chargebacks_ativos = {} # Para rastrear CBs

    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(f"[{self.nome}]: {message}", color_tag)
        else:
            print(message)

    def rotear_para_emissor(self, transacao):
        self._log(f"Roteando ISO 8583 (Autorização): TXN {transacao.id}", "yellow")
        self.transacoes_pendentes_emissor[transacao.id] = transacao
        return transacao # Em um sistema real, não retornaria a transação completa

    def rotear_resposta_do_emissor(self, transacao):
        self._log(f"Roteando ISO 8583 (Resposta Autorização): TXN {transacao.id} Status: {transacao.status}", "yellow")
        return transacao

    def receber_arquivo_captura(self, filename, data): # Adapte para receber o nome do arquivo gerado
        self._log(f"Recebido Arquivo de Captura: {os.path.basename(filename)}", "lightmagenta")

    # NOVOS MÉTODOS PARA CHARGEBACK
    def receber_chargeback_emissor(self, chargeback):
        self._log(f"Recebido solicitação de Chargeback do Emissor: CB ID {chargeback.id}", "yellow")
        self.chargebacks_ativos[chargeback.id] = chargeback
        # A Bandeira, em um sistema real, debitaria o adquirente e iniciaria a notificação

    def receber_reapresentacao_adquirente(self, chargeback):
        self._log(f"Recebida Reapresentação (Documentos de Defesa) da Adquirente para CB: {chargeback.id}", "yellow")
        chargeback.update_status(Chargeback.STATUS_REAPRESENTADO)
        # Bandeira avalia a defesa e envia a decisão ao Emissor

# ... Adquirente e Emissor com métodos semelhantes para chargeback ...
class Adquirente:
    def __init__(self, nome, log_callback=None):
        self.nome = nome
        self.log_callback = log_callback
        self.transacoes_recebidas = []
        self.transacoes_capturadas = []
        self.estabelecimentos = {}
        self.transacoes_a_liquidar = []
        self.chargebacks_ativos = {} # Para rastrear CBs recebidos

    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(f"[{self.nome}]: {message}", color_tag)
        else:
            print(message)

    # ... métodos existentes ...

    # NOVO MÉTODO PARA CHARGEBACK
    def receber_chargeback_bandeira(self, chargeback):
        self._log(f"Recebida Notificação de Chargeback da Bandeira: CB ID {chargeback.id} (TXN {chargeback.transacao_original_id})", "blue")
        self.chargebacks_ativos[chargeback.id] = chargeback
        # Notificar estabelecimento, solicitar documentos de defesa, etc.

class Emissor:
    def __init__(self, nome, log_callback=None):
        self.nome = nome
        self.log_callback = log_callback
        self.portadores = {}
        self.transacoes_aprovadas = []
        self.transacoes_negadas = []
        self.transacoes_para_faturar = []
        self.chargebacks_iniciados = {} # Para rastrear CBs iniciados

    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(f"[{self.nome}]: {message}", color_tag)
        else:
            print(message)

    # ... métodos existentes ...

    # NOVO MÉTODO PARA CHARGEBACK
    def receber_solicitacao_chargeback(self, chargeback):
        self._log(f"Recebida solicitação de Chargeback do Portador para TXN {chargeback.transacao_original_id}", "red")
        self.chargebacks_iniciados[chargeback.id] = chargeback
        # Iniciar o processo de disputa, potencialmente estornar o portador (provisoriamente)

    def receber_reapresentacao_bandeira(self, chargeback):
        self._log(f"Recebida Avaliação da Reapresentação da Bandeira para CB: {chargeback.id}", "red")
        # Baseado na decisão da bandeira, re-cobrar o portador ou confirmar o estorno.
        if chargeback.status == Chargeback.STATUS_RESOLVIDO_FAVOR_ESTABELECIMENTO:
            self._log(f"Chargeback {chargeback.id} resolvido a favor do Estabelecimento. Pode ser necessário re-cobrar o portador.", "green")
        elif chargeback.status == Chargeback.STATUS_RESOLVIDO_FAVOR_PORTADOR:
            self._log(f"Chargeback {chargeback.id} resolvido a favor do Portador. Estorno confirmado.", "red")
