import time
from enum import Enum
import datetime
import logging

logger = logging.getLogger(__name__)

class StatusTransacao(Enum):
    APROVADA = "APROVADA"
    NEGADA = "NEGADA"
    APROVADA_EMISSOR = "APROVADA_EMISSOR"
    NEGADA_EMISSOR = "NEGADA_EMISSOR"
    PENDENTE = "PENDENTE"
    CAPTURED = "CAPTURED"
    LIQUIDATED = "LIQUIDATED"
    SETTLED = "SETTLED" # Liquidada para o estabelecimento
    REVERSED = "REVERSED" # Estornada/Chargeback


class EntidadeBase:
    """Classe base para entidades com funcionalidade de log."""
    def __init__(self, nome, log_callback=None):
        self.nome = nome
        self.log_callback = log_callback

    def _log(self, message, color_tag="black", animation_data=None):
        """
        Método interno para enviar logs usando o callback fornecido.
        Atenção: NÃO adicione tags HTML aqui. O app.py fará isso.
        """
        if self.log_callback:
            # Passa a mensagem, a cor e os dados da animação
            self.log_callback(f"[{self.nome}]: {message}", color_tag, animation_data)

class Transacao:
    def __init__(self, portador_id, estabelecimento_id, valor, tipo="credito"):
        self.id = f"TXN{datetime.datetime.now().strftime('%H%M%S%f')[:-3]}" # ID único
        self.portador_id = portador_id
        self.estabelecimento_id = estabelecimento_id
        self.valor = valor
        self.tipo = tipo
        self.status = StatusTransacao.PENDENTE
        self.timestamp = datetime.datetime.now()
        self.codigo_autorizacao = None
        logger.debug(f"Transação {self.id} criada.")

class Adquirente(EntidadeBase):
    def __init__(self, nome, log_callback=None):
        super().__init__(nome, log_callback)
        self.estabelecimentos = {}
        self.transacoes_aprovadas = [] # Transações aprovadas e prontas para captura

    def cadastrar_estabelecimento(self, estabelecimento):
        self.estabelecimentos[estabelecimento.id] = estabelecimento
        self._log(f"Estabelecimento {estabelecimento.nome} ({estabelecimento.id}) cadastrado.", "green",
                  {"description": f"{self.nome} cadastra Estabelecimento", "active_entities": ["acquirer", "store"], "flow_path": None})
        time.sleep(0.1)

    def receber_transacao(self, transacao, bandeira, emissor):
        self._log(
            f"Recebida transação: TXN {transacao.id} - Valor: R{transacao.valor:.2f}",
            "blue",
            {"description": f"{self.nome} recebe transação", "active_entities": ["acquirer", "store"], "flow_path": "store_to_acquirer"}
        )
        time.sleep(0.1)
        self._log(
            f"Enviando para Bandeira: TXN {transacao.id}",
            "blue",
            {"description": f"{self.nome} envia para Bandeira", "active_entities": ["acquirer", "flag"], "flow_path": "acquirer_to_flag"}
        )
        time.sleep(0.1)
        
        status_autorizacao = bandeira.solicitar_autorizacao(transacao, emissor)
        
        self._log(
            f"Recebida resposta da Bandeira: TXN {transacao.id} - Status: {status_autorizacao.name}",
            "blue",
            {"description": f"{self.nome} recebe resposta da Bandeira", "active_entities": ["acquirer", "flag"], "flow_path": "flag_to_acquirer"}
        )
        time.sleep(0.1)

        if status_autorizacao == StatusTransacao.APROVADA_EMISSOR:
            transacao.status = StatusTransacao.APROVADA
            transacao.codigo_autorizacao = f"AUTH{datetime.datetime.now().strftime('%f')[:-3]}"
            self.transacoes_aprovadas.append(transacao)
            self._log(
                f"TXN {transacao.id} APROVADA e marcada para captura.",
                "green",
                {"description": f"{self.nome} aprova e marca para captura", "active_entities": ["acquirer", "store"], "flow_path": "acquirer_to_store_receipt"}
            )
            return True
        else:
            transacao.status = StatusTransacao.NEGADA
            self._log(
                f"TXN {transacao.id} NEGADA. Motivo: SALDO_INSUFICIENTE", # Assumindo este motivo para simplificar
                "red",
                {"description": f"{self.nome} nega transação", "active_entities": ["acquirer", "store"], "flow_path": "acquirer_to_store_denial"}
            )
            return False

class Emissor(EntidadeBase):
    def __init__(self, nome, log_callback=None):
        super().__init__(nome, log_callback)
        self.portadores = {}
        self.saldos = {} # Saldo simplificado para demonstração
        self.transacoes_aprovadas = {} # Guarda as transações que aprovou para controle de chargeback/faturamento

    def cadastrar_portador(self, portador):
        self.portadores[portador.id] = portador
        self.saldos[portador.id] = 2000.00 # Saldo inicial
        self._log(f"Portador {portador.nome} ({portador.id}) cadastrado.", "blue",
                  {"description": f"{self.nome} cadastra Portador", "active_entities": ["issuer", "client"], "flow_path": None})
        time.sleep(0.1)

    def solicitar_autorizacao(self, transacao):
        self._log(
            f"Recebida solicitação de Autorização: TXN {transacao.id} - Valor: R{transacao.valor:.2f}",
            "red",
            {"description": f"{self.nome} recebe autorização", "active_entities": ["issuer", "flag"], "flow_path": "flag_to_issuer"}
        )
        time.sleep(0.1)
        
        # Lógica de autorização simples: verifica saldo
        saldo_atual = self.saldos.get(transacao.portador_id, 0)
        autorizado = saldo_atual >= transacao.valor

        if autorizado:
            self.saldos[transacao.portador_id] -= transacao.valor
            transacao.status = StatusTransacao.APROVADA_EMISSOR
            self.transacoes_aprovadas[transacao.id] = transacao # Armazena a transação aprovada
            self._log(
                f"TXN {transacao.id} APROVADA.",
                "green",
                {"description": f"{self.nome} aprova transação", "active_entities": ["issuer", "client"], "flow_path": "issuer_approves"}
            )
            return StatusTransacao.APROVADA_EMISSOR
        else:
            transacao.status = StatusTransacao.NEGADA_EMISSOR
            self._log(
                f"TXN {transacao.id} NEGADA (Saldo Insuficiente).",
                "red",
                {"description": f"{self.nome} nega transação (saldo insuficiente)", "active_entities": ["issuer", "client"], "flow_path": "issuer_denies"}
            )
            return StatusTransacao.NEGADA_EMISSOR

    def processar_liquidacao(self, arquivo_liquidacao_emissor):
        # Em um sistema real, aqui o emissor processaria o arquivo da bandeira
        # e ajustaria as contas dos portadores.
        self._log(f"Processando arquivo de liquidação: {arquivo_liquidacao_emissor.split('/')[-1]}", "blue",
                  {"description": f"{self.nome} processa liquidação", "active_entities": ["issuer", "flag"], "flow_path": "flag_to_issuer_settlement"})
        time.sleep(0.1)
        # Lógica simplificada: Apenas marca como processado
        # Emissores de verdade faturariam seus clientes aqui, compensariam valores, etc.
        self._log("Liquidação processada pelo Emissor. (Faturamento)", "green",
                  {"description": f"{self.nome} processa faturamento", "active_entities": ["issuer", "client"], "flow_path": "issuer_to_client_bill"})
        time.sleep(0.1)

    def iniciar_faturamento(self):
        self._log("Iniciando faturamento para portadores...", "magenta",
                  {"description": f"{self.nome} inicia faturamento", "active_entities": ["issuer", "client"], "flow_path": None})
        time.sleep(0.1)
        # Lógica de faturamento: gerar extratos, etc.
        self._log("Faturamento concluído.", "green",
                  {"description": f"{self.nome} conclui faturamento", "active_entities": ["issuer", "client"], "flow_path": "issuer_bill_generated"})
        time.sleep(0.1)
        return True # Retorna um status de sucesso

class Bandeira(EntidadeBase):
    def __init__(self, nome, log_callback=None):
        super().__init__(nome, log_callback)
        self.transacoes_pendentes = {}
        self.transacoes_capturadas = []
        self.chargebacks_pendentes = {} # Para gerenciar disputas

    def solicitar_autorizacao(self, transacao, emissor):
        self._log(
            f"Roteando ISO 8583 (Autorização): TXN {transacao.id}",
            "yellow",
            {"description": f"{self.nome} roteia autorização para Emissor", "active_entities": ["flag", "issuer"], "flow_path": "flag_to_issuer"}
        )
        time.sleep(0.1)
        
        status_emissor = emissor.solicitar_autorizacao(transacao)
        
        self._log(
            f"Roteando ISO 8583 (Resposta Autorização): TXN {transacao.id} Status: {status_emissor.name}",
            "yellow",
            {"description": f"{self.nome} roteia resposta para Adquirente", "active_entities": ["flag", "acquirer"], "flow_path": "flag_to_acquirer"}
        )
        time.sleep(0.1)
        return status_emissor

    def processar_captura(self, lote_captura):
        self._log(f"Recebido lote de captura da Adquirente. Processando {len(lote_captura)} transações.", "yellow",
                  {"description": f"{self.nome} recebe lote de captura", "active_entities": ["flag", "acquirer"], "flow_path": "acquirer_to_flag_capture"})
        time.sleep(0.1)
        for transacao in lote_captura:
            if transacao.status == StatusTransacao.APROVADA:
                transacao.status = StatusTransacao.CAPTURED
                self.transacoes_capturadas.append(transacao)
                self._log(f"TXN {transacao.id} marcada como CAPTURADA.", "yellow")
        self._log("Lote de captura processado.", "green",
                  {"description": f"{self.nome} processa captura", "active_entities": ["flag"], "flow_path": None})
        time.sleep(0.1)
        return True

    def iniciar_liquidacao(self, adquirente, emissor):
        self._log("Iniciando processo de liquidação da Bandeira...", "yellow",
                  {"description": f"{self.nome} inicia liquidação", "active_entities": ["flag"], "flow_path": None})
        time.sleep(0.1)

        # Simula a geração de arquivos de liquidação para Adquirente e Emissor
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        adq_file = f"BANDEIRA_LIQUIDACAO_ADQ_{timestamp}.txt"
        emissor_file = f"BANDEIRA_LIQUIDACAO_EMISSOR_{timestamp}.txt"

        self._log(f"Gerado (p/ Adquirente) Arquivo: {adq_file}", "yellow",
                  {"description": f"{self.nome} gera arquivo p/ Adquirente", "active_entities": ["flag", "acquirer"], "flow_path": "flag_to_acquirer_settlement_file"})
        time.sleep(0.1)
        self._log(f"Gerado (p/ Emissor) Arquivo: {emissor_file}", "yellow",
                  {"description": f"{self.nome} gera arquivo p/ Emissor", "active_entities": ["flag", "issuer"], "flow_path": "flag_to_issuer_settlement_file"})
        time.sleep(0.1)

        # Simula o envio dos arquivos
        self._log(f"Enviando para Adquirente: Arquivo de Liquidação: {adq_file}", "yellow",
                  {"description": f"{self.nome} envia arquivo p/ Adquirente", "active_entities": ["flag", "acquirer"], "flow_path": "flag_to_acquirer_sftp"})
        time.sleep(0.1)
        self._log(f"Enviando para Emissor: Arquivo de Liquidação: {emissor_file}", "yellow",
                  {"description": f"{self.nome} envia arquivo p/ Emissor", "active_entities": ["flag", "issuer"], "flow_path": "flag_to_issuer_sftp"})
        time.sleep(0.1)

        # Em um sistema real, esses arquivos seriam transferidos via SFTP/API
        # e as entidades iriam processá-los em seus sistemas.
        # Aqui, chamamos os métodos correspondentes diretamente.
        adquirente.processar_liquidacao(adq_file)
        emissor.processar_liquidacao(emissor_file)

        self._log("Processo de liquidação da Bandeira concluído.", "green",
                  {"description": f"{self.nome} conclui liquidação", "active_entities": ["flag"], "flow_path": None})
        time.sleep(0.1)


    def registrar_chargeback(self, cb_id, txn_id):
        self._log(f"Recebido solicitação de Chargeback do Emissor: CB ID {cb_id}", "red",
                  {"description": f"{self.nome} recebe Chargeback do Emissor", "active_entities": ["flag", "issuer"], "flow_path": "issuer_to_flag_chargeback"})
        self.chargebacks_pendentes[cb_id] = {"txn_id": txn_id, "status": "PENDENTE_DEFESA"}
        time.sleep(0.1)
        # Notifica a adquirente
        self._log(f"Notificação de Chargeback - ID CB: {cb_id}, TXN: {txn_id}", "red",
                  {"description": f"{self.nome} notifica Adquirente sobre CB", "active_entities": ["flag", "acquirer"], "flow_path": "flag_to_acquirer_chargeback"})
        time.sleep(0.1)


    def receber_reapresentacao(self, cb_id, txn_id, docs_status):
        self._log(f"Recebida Reapresentação (Documentos de Defesa) da Adquirente para CB: {cb_id}", "yellow",
                  {"description": f"{self.nome} recebe defesa da Adquirente", "active_entities": ["flag", "acquirer"], "flow_path": "acquirer_to_flag_representment"})
        self.chargebacks_pendentes[cb_id]["status"] = "REAPRESENTADO"
        time.sleep(0.1)
        self._log(f"Reapresentação Avaliada - CB: {cb_id}, Resultado: Aguardando Decisão", "yellow",
                  {"description": f"{self.nome} avalia reapresentação", "active_entities": ["flag", "issuer"], "flow_path": "flag_to_issuer_evaluation"})
        time.sleep(0.1)
        # Em uma simulação mais complexa, haveria lógica para avaliar os docs.
        # Por simplicidade, vamos simular que a defesa será bem-sucedida 50% das vezes.
        import random
        if random.random() < 0.5: # 50% de chance de ser favorável ao estabelecimento
            return "Favorable ao Estabelecimento"
        else:
            return "Favorable ao Portador"
    
    def finalizar_chargeback(self, cb_id, resolucao, emissor):
        self._log(f"Decisão de Chargeback - CB: {cb_id}, Resolução: {resolucao}", "yellow",
                  {"description": f"{self.nome} finaliza Chargeback", "active_entities": ["flag", "issuer"], "flow_path": "flag_to_issuer_cb_resolution"})
        self.chargebacks_pendentes[cb_id]["status"] = "RESOLVIDO"
        emissor.finalizar_chargeback(cb_id, resolucao) # Notifica o emissor da decisão
        time.sleep(0.1)


class Estabelecimento(EntidadeBase):
    def __init__(self, nome, id, log_callback=None):
        super().__init__(nome, log_callback)
        self.id = id
        self.transacoes = [] # Transações iniciadas por este estabelecimento

    def iniciar_transacao(self, portador, valor, adquirente, bandeira, emissor):
        transacao = Transacao(portador.id, self.id, valor)
        self.transacoes.append(transacao)

        self._log(
            f"Passagem de Cartão: Cartão {portador.numero_cartao} - R{valor:.2f}",
            "black",
            {"description": f"{self.nome} processa cartão do Cliente", "active_entities": ["store", "client"], "flow_path": "client_to_store"}
        )
        time.sleep(0.1)
        
        autorizada = adquirente.receber_transacao(transacao, bandeira, emissor)
        return autorizada

    def receber_notificacao_chargeback(self, cb_id, txn_id):
        self._log(f"Recebeu notificação de chargeback para TXN {txn_id}. Preparando defesa...", "orange",
                  {"description": f"{self.nome} recebe notificação de Chargeback", "active_entities": ["store", "acquirer"], "flow_path": "acquirer_to_store_chargeback"})
        time.sleep(0.1)
        return True # Indica que vai preparar a defesa

    def preparar_defesa_chargeback(self, cb_id):
        self._log(f"Documentos de Defesa - CB: {cb_id}", "orange",
                  {"description": f"{self.nome} prepara e envia defesa", "active_entities": ["store", "acquirer"], "flow_path": "store_to_acquirer_defense"})
        time.sleep(0.1)
        # Em uma simulação real, aqui haveria a lógica para reunir provas
        return True # Simula que a defesa foi preparada

class Portador(EntidadeBase):
    def __init__(self, nome, id, log_callback=None):
        super().__init__(nome, log_callback)
        self.id = id
        self.numero_cartao = f"456789" if id == "PORT001" else f"987654"
        self.transacoes_historico = [] # Historico de transações para chargeback

    # O portador inicia o chargeback, mas a ação é registrada no Emissor (seu banco)
    def iniciar_chargeback(self, emissor, txn_id, motivo):
        self._log(f"Chargeback: Iniciando Chargeback - Motivo: {motivo}", "magenta",
                  {"description": f"{self.nome} inicia disputa", "active_entities": ["client", "issuer"], "flow_path": "client_to_issuer_chargeback"})
        time.sleep(0.1)
        emissor.receber_solicitacao_chargeback(self.id, txn_id, motivo)
