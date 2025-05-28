# src/models/entities.py
import datetime
import os
import time

# --- Módulos de Log ---
import logging
# A ideia é que estes logs também apareçam no console do Streamlit,
# mas o `streamlit_log_callback` levará para a UI.
logger = logging.getLogger(__name__)

# Assumindo que Transacao está em src/models/transaction.py
from src.models.transaction import Transacao
# Assumindo que Chargeback está em src/models/chargeback.py
from src.models.chargeback import Chargeback

class Estabelecimento:
    def __init__(self, id_estab, nome, cnae):
        self.id = id_estab
        self.nome = nome
        self.cnae = cnae
        logger.debug(f"Estabelecimento: {self.nome} ({self.id}) criado.")

class Portador:
    def __init__(self, id_portador, nome, cpf, tipo_cartao):
        self.id = id_portador
        self.nome = nome
        self.cpf = cpf
        self.tipo_cartao = tipo_cartao # 'CREDITO' ou 'DEBITO'
        logger.debug(f"Portador: {self.nome} ({self.id}) criado.")

class Bandeira:
    def __init__(self, nome, log_callback=None): # Mantenha essa ordem padrão ou use argumentos nomeados na chamada
        self.nome = nome
        self.log_callback = log_callback
        self.transacoes_pendentes_emissor = {}
        self.arquivos_captura_recebidos = []
        self.chargebacks_ativos = {} # Para rastrear CBs
        logger.debug(f"Bandeira: {self.nome} criada.")

    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(f"[{self.nome}]: {message}", color_tag)
        else:
            print(f"[{self.nome}]: {message}") # Fallback para console
        logger.debug(f"Bandeira {self.nome} Log: {message}")

    def rotear_para_emissor(self, transacao):
        self._log(f"Roteando ISO 8583 (Autorização): TXN {transacao.id}", "yellow")
        self.transacoes_pendentes_emissor[transacao.id] = transacao
        return transacao

    def rotear_resposta_do_emissor(self, transacao):
        self._log(f"Roteando ISO 8583 (Resposta Autorização): TXN {transacao.id} Status: {transacao.status}", "yellow")
        return transacao

    def receber_arquivo_captura(self, filename, data):
        self._log(f"Recebido Arquivo de Captura: {os.path.basename(filename)}", "lightmagenta")
        self.arquivos_captura_recebidos.append((filename, data)) # Guardando para referência

    # NOVOS MÉTODOS PARA CHARGEBACK
    def receber_chargeback_emissor(self, chargeback):
        self._log(f"Recebido solicitação de Chargeback do Emissor: CB ID {chargeback.id}", "yellow")
        self.chargebacks_ativos[chargeback.id] = chargeback
        # Em um sistema real, aqui a bandeira debitaria a adquirente
        logger.debug(f"Bandeira: CB {chargeback.id} registrado como ativo.")

    def receber_reapresentacao_adquirente(self, chargeback):
        self._log(f"Recebida Reapresentação (Documentos de Defesa) da Adquirente para CB: {chargeback.id}", "yellow")
        chargeback.update_status(Chargeback.STATUS_REAPRESENTADO)
        logger.debug(f"Bandeira: CB {chargeback.id} atualizado para STATUS_REAPRESENTADO.")

class Adquirente:
    def __init__(self, nome, log_callback=None): # Mantenha essa ordem padrão ou use argumentos nomeados na chamada
        self.nome = nome
        self.log_callback = log_callback
        self.transacoes_recebidas = [] # Todas as transações passadas
        self.transacoes_capturadas = [] # As que foram capturadas com sucesso
        self.estabelecimentos = {}
        self.transacoes_a_liquidar = [] # Transações prontas para pagamento ao lojista
        self.chargebacks_ativos = {} # Para rastrear CBs recebidos
        logger.debug(f"Adquirente: {self.nome} criada.")


    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(f"[{self.nome}]: {message}", color_tag)
        else:
            print(f"[{self.nome}]: {message}") # Fallback para console
        logger.debug(f"Adquirente {self.nome} Log: {message}")

    def cadastrar_estabelecimento(self, estabelecimento):
        self.estabelecimentos[estabelecimento.id] = estabelecimento
        self._log(f"Estabelecimento {estabelecimento.nome} ({estabelecimento.id}) cadastrado.", "green")

    def receber_transacao(self, transacao):
        self._log(f"Recebida transação: TXN {transacao.id} - Valor: R${transacao.valor:.2f}", "blue")
        self.transacoes_recebidas.append(transacao)
        # Em um sistema real, aqui haveria validações antes de enviar para a bandeira
        logger.debug(f"Adquirente: TXN {transacao.id} recebida e armazenada.")
        return transacao

    def enviar_para_bandeira(self, transacao, bandeira):
        self._log(f"Enviando para Bandeira: TXN {transacao.id}", "blue")
        return bandeira.rotear_para_emissor(transacao)

    def receber_resposta_bandeira(self, transacao):
        self._log(f"Recebida resposta da Bandeira: TXN {transacao.id} - Status: {transacao.status}", "blue")
        if transacao.status == "APROVADA_EMISSOR":
            transacao.status = "APROVADA_CAPTURA" # Adquirente marca como capturada
            self.transacoes_capturadas.append(transacao)
            self._log(f"TXN {transacao.id} APROVADA e marcada para captura.", "green")
        else:
            transacao.status = "NEGADA_CAPTURA" # Adquirente marca como negada
            self._log(f"TXN {transacao.id} NEGADA. Motivo: {transacao.motivo_negacao}", "red")
        logger.debug(f"Adquirente: TXN {transacao.id} resposta processada.")
        return transacao
    
    # NOVO MÉTODO PARA CHARGEBACK
    def receber_chargeback_bandeira(self, chargeback):
        self._log(f"Recebida Notificação de Chargeback da Bandeira: CB ID {chargeback.id} (TXN {chargeback.transacao_original_id})", "blue")
        self.chargebacks_ativos[chargeback.id] = chargeback
        # Lógica para notificar estabelecimento, solicitar documentos, etc.
        logger.debug(f"Adquirente: CB {chargeback.id} recebido e registrado.")


class Emissor:
    def __init__(self, nome, log_callback=None): # Mantenha essa ordem padrão ou use argumentos nomeados na chamada
        self.nome = nome
        self.log_callback = log_callback
        self.portadores = {}
        self.transacoes_aprovadas = []
        self.transacoes_negadas = []
        self.transacoes_para_faturar = [] # Transações liquidadas prontas para faturamento
        self.chargebacks_iniciados = {} # Para rastrear CBs iniciados
        logger.debug(f"Emissor: {self.nome} criada.")

    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(f"[{self.nome}]: {message}", color_tag)
        else:
            print(f"[{self.nome}]: {message}") # Fallback para console
        logger.debug(f"Emissor {self.nome} Log: {message}")

    def cadastrar_portador(self, portador):
        self.portadores[portador.id] = portador
        self._log(f"Portador {portador.nome} ({portador.id}) cadastrado.", "green")

    def receber_solicitacao_autorizacao(self, transacao):
        self._log(f"Recebida solicitação de Autorização: TXN {transacao.id} - Valor: R${transacao.valor:.2f}", "red")
        
        # Simulação de lógica de aprovação/negação
        if transacao.valor > 1000.00:
            transacao.status = "NEGADA_EMISSOR"
            transacao.motivo_negacao = "SALDO_INSUFICIENTE"
            self.transacoes_negadas.append(transacao)
            self._log(f"TXN {transacao.id} NEGADA (Saldo Insuficiente).", "red")
        else:
            transacao.status = "APROVADA_EMISSOR"
            self.transacoes_aprovadas.append(transacao)
            self._log(f"TXN {transacao.id} APROVADA.", "green")
        logger.debug(f"Emissor: TXN {transacao.id} autorização processada.")
        return transacao

    # NOVO MÉTODO PARA CHARGEBACK
    def receber_solicitacao_chargeback(self, chargeback):
        self._log(f"Recebida solicitação de Chargeback do Portador para TXN {chargeback.transacao_original_id}", "red")
        self.chargebacks_iniciados[chargeback.id] = chargeback
        # Aqui o emissor pode fazer um estorno provisório ao portador
        logger.debug(f"Emissor: CB {chargeback.id} iniciado e registrado.")

    def receber_reapresentacao_bandeira(self, chargeback):
        self._log(f"Recebida Avaliação da Reapresentação da Bandeira para CB: {chargeback.id} - Status: {chargeback.status}", "red")
        # Baseado na decisão da bandeira, re-cobrar o portador ou confirmar o estorno.
        if chargeback.status == Chargeback.STATUS_RESOLVIDO_FAVOR_ESTABELECIMENTO:
            self._log(f"Chargeback {chargeback.id} resolvido a favor do Estabelecimento. Pode ser necessário re-cobrar o portador.", "green")
            # Lógica para re-cobrar o portador se um estorno provisório foi feito
        elif chargeback.status == Chargeback.STATUS_RESOLVIDO_FAVOR_PORTADOR:
            self._log(f"Chargeback {chargeback.id} resolvido a favor do Portador. Estorno confirmado.", "red")
            # Lógica para confirmar o estorno
        logger.debug(f"Emissor: CB {chargeback.id} reapresentação processada.")
