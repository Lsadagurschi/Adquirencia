# src/services/simulation.py
import datetime
import time
import os
import logging
logger = logging.getLogger(__name__)

from src.models.transaction import Transacao
from src.models.entities import Adquirente, Emissor, Bandeira, Estabelecimento, Portador
from src.models.chargeback import Chargeback # Importando a classe Chargeback
from src.services.file_generator import (
    generate_capture_file, generate_liquidation_file_adq, 
    generate_liquidation_file_emissor, generate_payment_cnab_file, 
    generate_faturamento_3040_file
)
from src.services.chargeback_processor import ChargebackProcessor
from src.services.regulatory_reporter import RegulatoryReporter
# from src.services.utils import print_message, print_file_action, print_step # Não usados diretamente aqui se houver log_callback

class PaymentSimulator:
    def __init__(self, output_dir="data/output/", log_callback=None):
        self.output_dir = output_dir
        self.log_callback = log_callback # Este é agora uma lambda que inclui a fila

        logger.info("PaymentSimulator: Inicializando simulador.")

        # Corrigir a ordem dos argumentos para os construtores abaixo
        self.adquirente = Adquirente("AdquirenteXPTO", log_callback=self.log_callback) # Passa como argumento nomeado
        self.emissor = Emissor("BancoAlpha", log_callback=self.log_callback) # Passa como argumento nomeado
        self.bandeira = Bandeira("BandeiraPrincipal", log_callback=self.log_callback) # Passa como argumento nomeado
        
        # Aqui, a ordem dos argumentos está correta na definição dos __init__
        self.cb_processor = ChargebackProcessor(log_callback=self.log_callback, output_dir=self.output_dir)
        self.regulatory_reporter = RegulatoryReporter(output_dir=self.output_dir, log_callback=self.log_callback) # <--- ORDEM CORRIGIDA!
        
        # Setup inicial das entidades (MANTÉM)
        self.estab_1 = Estabelecimento("ESTAB001", "Loja do Zé", "4751-2/01")
        self.adquirente.cadastrar_estabelecimento(self.estab_1)
        self.portador_1 = Portador("PORT001", "Maria Silva", "123.456.789-00", "CREDITO")
        self.emissor.cadastrar_portador(self.portador_1)
        self.portador_2 = Portador("PORT002", "João Pereira", "987.654.321-00", "DEBITO")
        self.emissor.cadastrar_portador(self.portador_2)

        self.all_processed_transactions = [] # Para CADOC 6334
        logger.info("PaymentSimulator: Simulador inicializado com entidades.")

    def _log_step(self, title, color_tag="magenta"):
        if self.log_callback:
            self.log_callback(f"\n--- {title} ---", color_tag)
        else:
            print(f"\n--- {title} ---")
        time.sleep(0.5) # Pequeno atraso para visualização
        logger.info(f"PaymentSimulator Step: {title}")

    def _log_message(self, sender, receiver, msg_type, content, color_tag="white"):
        if self.log_callback:
            self.log_callback(f"[{sender} -> {receiver}] {msg_type}: {content}", color_tag)
        else:
            print(f"[{sender} -> {receiver}] {msg_type}: {content}")
        time.sleep(0.05) # Reduzido para agilizar
        logger.debug(f"PaymentSimulator Message: {sender}->{receiver} {msg_type}")

    def _log_file_action(self, entity, action, filename, color_tag="green"):
        if self.log_callback:
            self.log_callback(f"[{entity}] {action} Arquivo: {os.path.basename(filename)}", color_tag)
        else:
            print(f"[{entity}] {action} Arquivo: {os.path.basename(filename)}")
        time.sleep(0.05) # Reduzido para agilizar
        logger.debug(f"PaymentSimulator File Action: {entity} {action} {os.path.basename(filename)}")

    def run_full_simulation(self):
        self._log_message("Simulador", "Interno", "Início", "Iniciando a simulação completa...", "black")
        logger.info("PaymentSimulator: Iniciando run_full_simulation.")

        self._log_step("1. FLUXO DE AUTORIZAÇÃO EM TEMPO REAL (ISO 8583)")
        logger.info("PaymentSimulator: Iniciando Fluxo de Autorização.")

        # Transação 1: Aprovada
        transacao_1 = Transacao(
            id_transacao="TXN001", valor=150.00, tipo_cartao="CREDITO",
            numero_cartao_bin="456789", data_hora=datetime.datetime.now(),
            id_estabelecimento=self.estab_1.id, id_portador=self.portador_1.id
        )
        self._log_message("Portador", "Estabelecimento", "Passagem de Cartão", f"Cartão {transacao_1.numero_cartao_bin} - R${transacao_1.valor:.2f}", "white")
        
        t1_adq_processed = self.adquirente.receber_transacao(transacao_1)
        t1_bandeira_routed = self.adquirente.enviar_para_bandeira(t1_adq_processed, self.bandeira)
        t1_emissor_auth = self.emissor.receber_solicitacao_autorizacao(t1_bandeira_routed)
        t1_adq_response = self.bandeira.rotear_resposta_do_emissor(t1_emissor_auth)
        self.adquirente.receber_resposta_bandeira(t1_adq_response)
        self.all_processed_transactions.append(t1_adq_response)
        logger.info("PaymentSimulator: Transação TXN001 processada.")

        # Transação 2: Negada (valor alto)
        transacao_2 = Transacao(
            id_transacao="TXN002", valor=1200.00, tipo_cartao="CREDITO",
            numero_cartao_bin="987654", data_hora=datetime.datetime.now(),
            id_estabelecimento=self.estab_1.id, id_portador=self.portador_2.id
        )
        self._log_message("Portador", "Estabelecimento", "Passagem de Cartão", f"Cartão {transacao_2.numero_cartao_bin} - R${transacao_2.valor:.2f}", "white")
        
        t2_adq_processed = self.adquirente.receber_transacao(transacao_2)
        t2_bandeira_routed = self.adquirente.enviar_para_bandeira(t2_adq_processed, self.bandeira)
        t2_emissor_auth = self.emissor.receber_solicitacao_autorizacao(t2_bandeira_routed)
        t2_adq_response = self.bandeira.rotear_resposta_do_emissor(t2_emissor_auth)
        self.adquirente.receber_resposta_bandeira(t2_adq_response)
        self.all_processed_transactions.append(t2_adq_response)
        logger.info("PaymentSimulator: Transação TXN002 processada.")
        self._log_step("FIM DA AUTORIZAÇÃO")

        self._log_step("2. PROCESSO DE CAPTURA (Lotes - Adquirente -> Bandeira)")
        logger.info("PaymentSimulator: Iniciando processo de Captura.")
        arquivo_captura_adquirente = generate_capture_file(self.adquirente.transacoes_recebidas, self.output_dir)
        if arquivo_captura_adquirente:
            self._log_file_action(self.adquirente.nome, "Gerado", arquivo_captura_adquirente, "green")
            self._log_message(self.adquirente.nome, self.bandeira.nome, "Envio SFTP", f"Arquivo de Captura: {os.path.basename(arquivo_captura_adquirente)}", "lightblue")
        logger.info("PaymentSimulator: Processo de Captura finalizado.")
        self._log_step("FIM DA CAPTURA")

        self._log_step("3. PROCESSO DE LIQUIDAÇÃO (Lotes - Bandeira -> Adquirente e Emissor)")
        logger.info("PaymentSimulator: Iniciando processo de Liquidação.")
        arquivo_liquidacao_adquirente = generate_liquidation_file_adq(self.adquirente.transacoes_capturadas, self.output_dir)
        if arquivo_liquidacao_adquirente:
            self._log_file_action(self.bandeira.nome, "Gerado (p/ Adquirente)", arquivo_liquidacao_adquirente, "green")
            self._log_message(self.bandeira.nome, self.adquirente.nome, "Envio SFTP", f"Arquivo de Liquidação Adquirente: {os.path.basename(arquivo_liquidacao_adquirente)}", "lightblue")
            for t in self.adquirente.transacoes_capturadas:
                if t.status == "APROVADA_CAPTURA":
                    t.status = "LIQUIDADA_ADQUIRENTE"
                    self.adquirente.transacoes_a_liquidar.append(t)
                    self._log_message(self.adquirente.nome, "Interno", "Status Atualizado", f"TXN {t.id} - LIQUIDADA_ADQUIRENTE", "blue")
        logger.info("PaymentSimulator: Arquivo de liquidação para Adquirente processado.")

        arquivo_liquidacao_emissor = generate_liquidation_file_emissor(self.emissor.transacoes_aprovadas, self.output_dir)
        if arquivo_liquidacao_emissor:
            self._log_file_action(self.bandeira.nome, "Gerado (p/ Emissor)", arquivo_liquidacao_emissor, "green")
            self._log_message(self.bandeira.nome, self.emissor.nome, "Envio SFTP", f"Arquivo de Liquidação Emissor: {os.path.basename(arquivo_liquidacao_emissor)}", "lightblue")
            for t in self.emissor.transacoes_aprovadas:
                if t.status == "APROVADA_EMISSOR":
                    t.status = "LIQUIDADA_EMISSOR"
                    self.emissor.transacoes_para_faturar.append(t)
                    self._log_message(self.emissor.nome, "Interno", "Status Atualizado", f"TXN {t.id} - LIQUIDADA_EMISSOR", "red")
        logger.info("PaymentSimulator: Processo de Liquidação finalizado.")
        self._log_step("FIM DA LIQUIDAÇÃO")

        self._log_step("4. PROCESSO DE PAGAMENTO (Lotes - Adquirente -> Bancos dos Estabelecimentos - CNAB)")
        logger.info("PaymentSimulator: Iniciando processo de Pagamento CNAB.")
        arquivo_pagamento_estab = generate_payment_cnab_file(self.adquirente.transacoes_a_liquidar, self.output_dir)
        if arquivo_pagamento_estab:
            self._log_file_action(self.adquirente.nome, "Gerado (CNAB para Banco)", arquivo_pagamento_estab, "green")
            self._log_message(self.adquirente.nome, "Bancos Parceiros", "Envio SFTP (CNAB)", f"Arquivo CNAB: {os.path.basename(arquivo_pagamento_estab)}", "lightblue")
        logger.info("PaymentSimulator: Processo de Pagamento CNAB finalizado.")
        self._log_step("FIM DO PAGAMENTO")

        self._log_step("5. PROCESSO DE FATURAMENTO (Lotes - Emissor -> Sistemas Internos/Regulatórios)")
        logger.info("PaymentSimulator: Iniciando processo de Faturamento.")
        arquivo_faturamento_emissor = generate_faturamento_3040_file(self.emissor.transacoes_para_faturar, self.output_dir)
        if arquivo_faturamento_emissor:
             self._log_file_action(self.emissor.nome, "Gerado (XML para Faturamento/3040 Simulado)", arquivo_faturamento_emissor, "green")
        logger.info("PaymentSimulator: Processo de Faturamento finalizado.")
        self._log_step("FIM DO FATURAMENTO")

        # --- FLUXO DE CHARGEBACK ---
        self._log_step("6. FLUXO DE CHARGEBACK (DISPUTA DE COMPRA)")
        logger.info("PaymentSimulator: Iniciando Fluxo de Chargeback.")
        cb_tx1 = self.cb_processor.iniciar_chargeback(self.emissor, self.adquirente, self.bandeira, transacao_1, "Mercadoria Não Recebida")
        time.sleep(1) # Pequeno atraso entre as fases do CB
        if cb_tx1:
            self._log_step("6.1. FASE DE DEFESA DO CHARGEBACK")
            # Passar o emissor_obj para a função processar_defesa_chargeback
            self.cb_processor.processar_defesa_chargeback(self.adquirente, self.bandeira, self.emissor, cb_tx1) 
            time.sleep(1)
            self._log_step("6.2. FINALIZAÇÃO DO CHARGEBACK")
            self.cb_processor.finalizar_chargeback(self.emissor, self.bandeira, cb_tx1)
        logger.info("PaymentSimulator: Fluxo de Chargeback finalizado.")
        self._log_step("FIM DO CHARGEBACK")

        # --- ARQUIVOS REGULATÓRIOS DETALHADOS ---
        self._log_step("7. ARQUIVOS REGULATÓRIOS (Adquirente/Emissor -> Banco Central)")
        logger.info("PaymentSimulator: Iniciando geração de Arquivos Regulatórios.")
        current_month_year = datetime.datetime.now().strftime("%Y%m")

        emissor_report_data = {
            self.emissor.nome: self.emissor.transacoes_aprovadas + list(self.cb_processor.chargebacks_ativos.values())
        }
        self.regulatory_reporter.generate_cadoc_3040_scr(emissor_report_data, current_month_year)
        time.sleep(0.5)

        adquirente_report_data = {
            "transacoes_capturadas": self.adquirente.transacoes_capturadas,
            "transacoes_recebidas": self.adquirente.transacoes_recebidas, # Inclui as negadas aqui
            "estabelecimentos": list(self.adquirente.estabelecimentos.values()), # Passar lista de objetos
            "chargebacks_ativos": self.adquirente.chargebacks_ativos
        }
        self.regulatory_reporter.generate_cadoc_5817_credenciadoras(adquirente_report_data, current_month_year)
        time.sleep(0.5)

        self.regulatory_reporter.generate_cadoc_6334_estatistico(self.all_processed_transactions, current_month_year)
        
        logger.info("PaymentSimulator: Geração de Arquivos Regulatórios finalizada.")
        self._log_step("FIM DOS REGULATÓRIOS")

        self._log_message("Simulador", "Interno", "Fim", "Simulação completa concluída!", "green")
        logger.info("PaymentSimulator: run_full_simulation concluída com sucesso.")
