import datetime
import time
import logging

logger = logging.getLogger(__name__)

class ChargebackProcessor:
    def __init__(self, log_callback=None, output_dir="data/output/"):
        self.log_callback = log_callback
        self.output_dir = output_dir
        logger.debug("ChargebackProcessor inicializado.")

    def _log(self, message, color_tag="black", animation_data=None):
        if self.log_callback:
            self.log_callback(f"[ChargebackProcessor]: {message}", color_tag, animation_data)

    def processar_chargeback(self, portador, emissor, bandeira, adquirente, estabelecimento, transacao_disputada):
        self._log(
            "----- FLUXO DE CHARGEBACK INICIADO PARA TXN " + transacao_disputada.id + " -----",
            "magenta",
            {"description": "Iniciando processo de Chargeback", "active_entities": ["client", "issuer"], "flow_path": None}
        )
        time.sleep(0.5)

        # 1. Portador inicia Chargeback
        portador.iniciar_chargeback(emissor, transacao_disputada.id, "Mercadoria Não Recebida")

        # 2. Emissor recebe solicitação e a encaminha para a Bandeira
        cb_id = emissor.encaminhar_chargeback_para_bandeira(transacao_disputada.id, bandeira)

        # 3. Bandeira registra e notifica a Adquirente
        bandeira.registrar_chargeback(cb_id, transacao_disputada.id)
        adquirente.receber_notificacao_chargeback(cb_id, transacao_disputada.id)
        
        # 4. Adquirente notifica o Estabelecimento
        estabelecimento.receber_notificacao_chargeback(cb_id, transacao_disputada.id)
        
        self._log("--- 6.1. FASE DE DEFESA DO CHARGEBACK ---", "magenta",
                  {"description": "Fase de Defesa do Chargeback", "active_entities": ["store"], "flow_path": None})
        time.sleep(0.5)
        self._log(
            "----- FLUXO DE CHARGEBACK - FASE DE DEFESA PARA CB " + cb_id + " -----",
            "magenta",
            {"description": "Fase de Defesa - Estabelecimento", "active_entities": ["store"], "flow_path": None}
        )
        time.sleep(0.1)

        # 5. Estabelecimento prepara e envia defesa para Adquirente
        if estabelecimento.preparar_defesa_chargeback(cb_id):
            adquirente.enviar_reapresentacao(cb_id, transacao_disputada.id, bandeira)
        
        # 6. Adquirente envia reapresentação para a Bandeira
        bandeira.receber_reapresentacao(cb_id, transacao_disputada.id, "Docs: Ok")
        
        self._log(
            "----- FLUXO DE CHARGEBACK - FASE DE DEFESA CONCLUÍDA PARA CB " + cb_id + " -----",
            "magenta",
            {"description": "Defesa Concluída", "active_entities": ["store", "acquirer", "flag", "issuer"], "flow_path": None}
        )
        time.sleep(0.5)

        self._log("--- 6.2. FINALIZAÇÃO DO CHARGEBACK ---", "magenta",
                  {"description": "Finalização do Chargeback", "active_entities": ["flag"], "flow_path": None})
        time.sleep(0.5)
        self._log(
            "----- FLUXO DE CHARGEBACK - FINALIZAÇÃO PARA CB " + cb_id + " -----",
            "magenta",
            {"description": "Finalização do Chargeback", "active_entities": ["flag", "issuer", "client", "store"], "flow_path": None}
        )
        time.sleep(0.1)
        
        # 7. Bandeira decide e informa Emissor
        resolucao = bandeira.receber_reapresentacao(cb_id, transacao_disputada.id, "Docs: Ok") # Simula a decisão
        bandeira.finalizar_chargeback(cb_id, resolucao, emissor)

        # 8. Emissor notifica Portador da decisão
        emissor.notificar_portador_decisao_chargeback(cb_id, resolucao)

        self._log(
            f"Chargeback {cb_id} RESOLVIDO a favor do {'ESTABELECIMENTO' if 'Estabelecimento' in resolucao else 'PORTADOR'}.",
            "green" if 'Estabelecimento' in resolucao else "red",
            {"description": f"Chargeback Resolvido ({'Estabelecimento' if 'Estabelecimento' in resolucao else 'Portador'})", "active_entities": ["client", "issuer", "store", "acquirer"], "flow_path": None}
        )
        time.sleep(0.1)
        self._log(
            f"----- FLUXO DE CHARGEBACK FINALIZADO PARA CB {cb_id} -----",
            "magenta",
            {"description": "Chargeback Concluído!", "active_entities": [], "flow_path": None}
        )
        time.sleep(0.5)
