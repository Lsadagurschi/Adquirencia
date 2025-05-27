# src/services/chargeback_processor.py
import datetime
import random
import time
import os

from src.models.chargeback import Chargeback
from src.services.utils import print_message, print_file_action, print_step

class ChargebackProcessor:
    def __init__(self, log_callback=None, output_dir="data/output/"):
        self.log_callback = log_callback
        self.output_dir = output_dir
        self.chargebacks_ativos = {} # Dicionário de chargebacks em andamento

    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(message, color_tag)
        else:
            print(message)

    def iniciar_chargeback(self, emissor_obj, adquirente_obj, bandeira_obj, transacao_original, motivo):
        self._log(f"\n----- FLUXO DE CHARGEBACK INICIADO -----", "magenta")
        chargeback_id = f"CB{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"
        chargeback = Chargeback(chargeback_id, transacao_original.id, motivo, transacao_original.valor, datetime.datetime.now())
        self.chargebacks_ativos[chargeback.id] = chargeback

        self._log_cb_action("Portador", "Emissor", "Iniciando Chargeback", f"Motivo: {motivo}", "red")
        emissor_obj.receber_solicitacao_chargeback(chargeback)
        chargeback.update_status(Chargeback.STATUS_INICIADO)
        
        self._log_cb_action("Emissor", "Bandeira", "Disputa de Compra", f"ID CB: {chargeback.id}, TXN: {transacao_original.id}", "red")
        bandeira_obj.receber_chargeback_emissor(chargeback)

        self._log_cb_action("Bandeira", "Adquirente", "Notificação de Chargeback", f"ID CB: {chargeback.id}, TXN: {transacao_original.id}", "yellow")
        adquirente_obj.receber_chargeback_bandeira(chargeback)
        
        self._log_cb_action("Adquirente", "Estabelecimento", "Notificação de Chargeback", f"ID CB: {chargeback.id}, TXN: {transacao_original.id}", "blue")
        # Estabelecimento é notificado e pode reagir (ex: enviar documentos)
        self._log(f"[Estabelecimento]: Recebeu notificação de chargeback para TXN {transacao_original.id}. Preparando defesa...", "blue")
        
        return chargeback

    def _log_cb_action(self, sender, receiver, msg_type, content, color_tag="black"):
        self._log(f"[{sender} -> {receiver}] Chargeback: {msg_type} - {content}", color_tag)
        time.sleep(1) # Simula atraso

    def processar_defesa_chargeback(self, adquirente_obj, bandeira_obj, chargeback):
        self._log_cb_action("Estabelecimento", "Adquirente", "Documentos de Defesa", f"CB: {chargeback.id}", "blue")
        # Simula o estabelecimento enviando documentos para a adquirente
        
        # Adquirente processa e envia para a Bandeira (Representation/Reapresentação)
        chargeback.update_status(Chargeback.STATUS_DOCUMENTACAO_ENVIADA)
        self._log_cb_action("Adquirente", "Bandeira", "Reapresentação (Representment)", f"CB: {chargeback.id}, Docs: Ok", "green")
        bandeira_obj.receber_reapresentacao_adquirente(chargeback)
        
        # Bandeira avalia e envia para o Emissor
        selfback_obj.update_status(Chargeback.STATUS_REAPRESENTADO)
        self._log_cb_action("Bandeira", "Emissor", "Reapresentação Avaliada", f"CB: {chargeback.id}, Resultado: Favorable ao Estab.", "yellow")
        emissor_obj = next((e for e in self.chargebacks_ativos.values() if e.id == chargeback.id), None) # Apenas para o log, emissor real precisaria ser passado
        if emissor_obj: # Apenas para o log, emissor real precisaria ser passado
            emissor_obj.receber_reapresentacao_bandeira(chargeback)
        
        self._log(f"\n----- FLUXO DE CHARGEBACK - FASE DE DEFESA CONCLUÍDA -----", "magenta")

    def finalizar_chargeback(self, emissor_obj, bandeira_obj, chargeback):
        self._log_cb_action("Emissor", "Portador", "Decisão de Chargeback", f"CB: {chargeback.id}, Resolução: Favorable ao Estab.", "red")
        chargeback.update_status(Chargeback.STATUS_RESOLVIDO_FAVOR_ESTABELECIMENTO)
        self._log(f"Chargeback {chargeback.id} RESOLVIDO a favor do ESTABELECIMENTO. Portador será cobrado novamente ou não receberá estorno inicial.", "green")
        
        # Ou, se for a favor do portador:
        # chargeback.update_status(Chargeback.STATUS_RESOLVIDO_FAVOR_PORTADOR)
        # self._log(f"Chargeback {chargeback.id} RESOLVIDO a favor do PORTADOR. Estabelecimento terá o valor estornado.", "red")
        
        self._log(f"\n----- FLUXO DE CHARGEBACK FINALIZADO -----", "magenta")
        # O chargeback é removido dos ativos ou arquivado
