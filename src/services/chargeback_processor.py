# src/services/chargeback_processor.py
import datetime
import random
import time
import os
import logging
logger = logging.getLogger(__name__)

from src.models.chargeback import Chargeback
from src.services.utils import print_message, print_file_action, print_step # Pode ser que essas não sejam usadas se o callback for o único método

class ChargebackProcessor:
    def __init__(self, log_callback=None, output_dir="data/output/"): # Mantenha essa ordem padrão ou use argumentos nomeados na chamada
        self.log_callback = log_callback
        self.output_dir = output_dir
        self.chargebacks_ativos = {}
        logger.debug("ChargebackProcessor inicializado.")

    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(message, color_tag)
        else:
            print(message) # Fallback para console
        logger.debug(f"ChargebackProcessor Log: {message}")

    def _log_cb_action(self, sender, receiver, msg_type, content, color_tag="black"):
        self._log(f"[{sender} -> {receiver}] Chargeback: {msg_type} - {content}", color_tag)
        time.sleep(0.5) # Ajustado para 0.5s para agilizar um pouco a depuração
        logger.debug(f"ChargebackProcessor Action Log: {sender} -> {receiver} {msg_type}")

    def iniciar_chargeback(self, emissor_obj, adquirente_obj, bandeira_obj, transacao_original, motivo):
        self._log(f"\n----- FLUXO DE CHARGEBACK INICIADO PARA TXN {transacao_original.id} -----", "magenta")
        logger.info(f"ChargebackProcessor: Iniciando CB para TXN {transacao_original.id}.")

        chargeback_id = f"CB{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"
        chargeback = Chargeback(chargeback_id, transacao_original.id, motivo, transacao_original.valor, datetime.datetime.now())
        self.chargebacks_ativos[chargeback.id] = chargeback
        logger.debug(f"ChargebackProcessor: CB {chargeback.id} criado e adicionado a ativos.")

        self._log_cb_action("Portador", "Emissor", "Iniciando Chargeback", f"Motivo: {motivo}", "red")
        emissor_obj.receber_solicitacao_chargeback(chargeback)
        chargeback.update_status(Chargeback.STATUS_INICIADO)
        
        self._log_cb_action("Emissor", "Bandeira", "Disputa de Compra", f"ID CB: {chargeback.id}, TXN: {transacao_original.id}", "red")
        bandeira_obj.receber_chargeback_emissor(chargeback)

        self._log_cb_action("Bandeira", "Adquirente", "Notificação de Chargeback", f"ID CB: {chargeback.id}, TXN: {transacao_original.id}", "yellow")
        adquirente_obj.receber_chargeback_bandeira(chargeback)
        
        self._log_cb_action("Adquirente", "Estabelecimento", "Notificação de Chargeback", f"ID CB: {chargeback.id}, TXN: {transacao_original.id}", "blue")
        self._log(f"[Estabelecimento]: Recebeu notificação de chargeback para TXN {transacao_original.id}. Preparando defesa...", "blue")
        logger.info(f"ChargebackProcessor: CB {chargeback.id} iniciado em todas as partes.")
        
        return chargeback

    def processar_defesa_chargeback(self, adquirente_obj, bandeira_obj, emissor_obj, chargeback): # Adicionado emissor_obj aqui para a chamada final
        self._log(f"\n----- FLUXO DE CHARGEBACK - FASE DE DEFESA PARA CB {chargeback.id} -----", "magenta")
        logger.info(f"ChargebackProcessor: Processando defesa para CB {chargeback.id}.")

        self._log_cb_action("Estabelecimento", "Adquirente", "Documentos de Defesa", f"CB: {chargeback.id}", "blue")
        
        chargeback.update_status(Chargeback.STATUS_DOCUMENTACAO_ENVIADA)
        self._log_cb_action("Adquirente", "Bandeira", "Reapresentação (Representment)", f"CB: {chargeback.id}, Docs: Ok", "green")
        bandeira_obj.receber_reapresentacao_adquirente(chargeback)
        
        chargeback.update_status(Chargeback.STATUS_REAPRESENTADO) # Atualiza o status do CB
        self._log_cb_action("Bandeira", "Emissor", "Reapresentação Avaliada", f"CB: {chargeback.id}, Resultado: Aguardando Decisão", "yellow")
        
        # Emissor precisa avaliar o resultado da reapresentação
        emissor_obj.receber_reapresentacao_bandeira(chargeback) # O emissor precisa ser passado aqui
        
        self._log(f"\n----- FLUXO DE CHARGEBACK - FASE DE DEFESA CONCLUÍDA PARA CB {chargeback.id} -----", "magenta")
        logger.info(f"ChargebackProcessor: Defesa para CB {chargeback.id} processada.")

    def finalizar_chargeback(self, emissor_obj, bandeira_obj, chargeback):
        self._log(f"\n----- FLUXO DE CHARGEBACK - FINALIZAÇÃO PARA CB {chargeback.id} -----", "magenta")
        logger.info(f"ChargebackProcessor: Finalizando CB {chargeback.id}.")

        # Simula a decisão da Bandeira e comunicação ao Emissor
        # Para simulação, vamos definir que a decisão é sempre a favor do Estabelecimento
        # em 70% dos casos para simular a defesa, e a favor do Portador em 30%.
        if random.random() < 0.7:
            chargeback.update_status(Chargeback.STATUS_RESOLVIDO_FAVOR_ESTABELECIMENTO)
            self._log_cb_action("Bandeira", "Emissor", "Decisão de Chargeback", f"CB: {chargeback.id}, Resolução: Favorable ao Estabelecimento", "yellow")
            self._log_cb_action("Emissor", "Portador", "Decisão de Chargeback", f"CB: {chargeback.id}, Resolução: Favorable ao Estab.", "red")
            self._log(f"Chargeback {chargeback.id} RESOLVIDO a favor do ESTABELECIMENTO. Portador será cobrado novamente ou não receberá estorno inicial.", "green")
        else:
            chargeback.update_status(Chargeback.STATUS_RESOLVIDO_FAVOR_PORTADOR)
            self._log_cb_action("Bandeira", "Emissor", "Decisão de Chargeback", f"CB: {chargeback.id}, Resolução: Favorable ao Portador", "yellow")
            self._log_cb_action("Emissor", "Portador", "Decisão de Chargeback", f"CB: {chargeback.id}, Resolução: Favorable ao Portador.", "red")
            self._log(f"Chargeback {chargeback.id} RESOLVIDO a favor do PORTADOR. Estabelecimento terá o valor estornado.", "red")

        # O emissor recebe a decisão final da bandeira
        emissor_obj.receber_reapresentacao_bandeira(chargeback) # Reusando o método para a notificação final

        self.chargebacks_ativos.pop(chargeback.id, None) # Remove dos chargebacks ativos
        self._log(f"\n----- FLUXO DE CHARGEBACK FINALIZADO PARA CB {chargeback.id} -----", "magenta")
        logger.info(f"ChargebackProcessor: CB {chargeback.id} finalizado.")
