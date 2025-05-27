# src/services/simulation.py
import datetime
import time
import os

from src.models.chargeback import Chargeback # Novo import
from src.services.chargeback_processor import ChargebackProcessor # Novo import
from src.services.regulatory_reporter import RegulatoryReporter # Novo import

class PaymentSimulator:
    def __init__(self, output_dir="data/output/", log_callback=None):
        self.adquirente = Adquirente("AdquirenteXPTO", log_callback)
        self.emissor = Emissor("BancoAlpha", log_callback)
        self.bandeira = Bandeira("BandeiraPrincipal", log_callback)
        self.cb_processor = ChargebackProcessor(log_callback, output_dir) # Novo
        self.regulatory_reporter = RegulatoryReporter(log_callback, output_dir) # Novo
        self.output_dir = output_dir
        self.log_callback = log_callback

        # Setup inicial das entidades (MANTÉM)
        self.estab_1 = Estabelecimento("ESTAB001", "Loja do Zé", "4751-2/01")
        self.adquirente.cadastrar_estabelecimento(self.estab_1)
        self.portador_1 = Portador("PORT001", "Maria Silva", "123.456.789-00", "CREDITO")
        self.emissor.cadastrar_portador(self.portador_1)
        self.portador_2 = Portador("PORT002", "João Pereira", "987.654.321-00", "DEBITO")
        self.emissor.cadastrar_portador(self.portador_2)

        # Listas para coletar todas as transações para relatórios
        self.all_processed_transactions = [] # Para CADOC 6334

    def _log_step(self, title, color_tag="magenta"):
        if self.log_callback:
            self.log_callback(f"\n--- {title} ---", color_tag)
        else:
            print_step(title)
        time.sleep(1)

    def _log_message(self, sender, receiver, msg_type, content, color_tag="white"):
        if self.log_callback:
            self.log_callback(f"[{sender} -> {receiver}] {msg_type}: {content}", color_tag)
        else:
            print_message(sender, receiver, msg_type, content)
        time.sleep(0.5)

    def _log_file_action(self, entity, action, filename, color_tag="green"):
        if self.log_callback:
            self.log_callback(f"[{entity}] {action} Arquivo: {os.path.basename(filename)}", color_tag)
        else:
            print_file_action(entity, action, filename)
        time.sleep(0.7)

    def run_full_simulation(self):
        self._log_step("1. FLUXO DE AUTORIZAÇÃO EM TEMPO REAL (ISO 8583)")

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
        self.all_processed_transactions.append(t1_adq_response) # Coleta para relatórios

        # Transação 2: Negada
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
        self.all_processed_transactions.append(t2_adq_response) # Coleta para relatórios
        self._log_step("FIM DA AUTORIZAÇÃO")

        self._log_step("2. PROCESSO DE CAPTURA (Lotes - Adquirente -> Bandeira)")
        arquivo_captura_adquirente = generate_capture_file(self.adquirente.transacoes_recebidas, self.output_dir)
        if arquivo_captura_adquirente:
            self._log_file_action(self.adquirente.nome, "Gerado", arquivo_captura_adquirente, "green")
            self._log_message(self.adquirente.nome, self.bandeira.nome, "Envio SFTP", f"Arquivo de Captura: {os.path.basename(arquivo_captura_adquirente)}", "lightblue")
        self._log_step("FIM DA CAPTURA")

        self._log_step("3. PROCESSO DE LIQUIDAÇÃO (Lotes - Bandeira -> Adquirente e Emissor)")
        arquivo_liquidacao_adquirente = generate_liquidation_file_adq(self.adquirente.transacoes_capturadas, self.output_dir)
        if arquivo_liquidacao_adquirente:
            self._log_file_action(self.bandeira.nome, "Gerado (p/ Adquirente)", arquivo_liquidacao_adquirente, "green")
            self._log_message(self.bandeira.nome, self.adquirente.nome, "Envio SFTP", f"Arquivo de Liquidação Adquirente: {os.path.basename(arquivo_liquidacao_adquirente)}", "lightblue")
            # Adquirente processa o arquivo para marcar transações como liquidadas
            # Lógica de processamento no services/file_generator.py
            # Forçar um "processamento" de status aqui para fins de simulação
            for t in self.adquirente.transacoes_capturadas:
                if t.status == "APROVADA_CAPTURA": # Se foi capturada e está no arquivo de liquidação
                    t.status = "LIQUIDADA_ADQUIRENTE"
                    self.adquirente.transacoes_a_liquidar.append(t)
                    self._log_message(self.adquirente.nome, "Interno", "Status Atualizado", f"TXN {t.id} - LIQUIDADA_ADQUIRENTE", "blue")


        arquivo_liquidacao_emissor = generate_liquidation_file_emissor(self.emissor.transacoes_aprovadas, self.output_dir)
        if arquivo_liquidacao_emissor:
            self._log_file_action(self.bandeira.nome, "Gerado (p/ Emissor)", arquivo_liquidacao_emissor, "green")
            self._log_message(self.bandeira.nome, self.emissor.nome, "Envio SFTP", f"Arquivo de Liquidação Emissor: {os.path.basename(arquivo_liquidacao_emissor)}", "lightblue")
            # Emissor processa o arquivo
            for t in self.emissor.transacoes_aprovadas:
                if t.status == "APROVADA_EMISSOR": # Se foi aprovada pelo emissor e está no arquivo de liquidação
                    t.status = "LIQUIDADA_EMISSOR"
                    self.emissor.transacoes_para_faturar.append(t)
                    self._log_message(self.emissor.nome, "Interno", "Status Atualizado", f"TXN {t.id} - LIQUIDADA_EMISSOR", "red")
        self._log_step("FIM DA LIQUIDAÇÃO")

        self._log_step("4. PROCESSO DE PAGAMENTO (Lotes - Adquirente -> Bancos dos Estabelecimentos - CNAB)")
        arquivo_pagamento_estab = generate_payment_cnab_file(self.adquirente.transacoes_a_liquidar, self.output_dir)
        if arquivo_pagamento_estab:
            self._log_file_action(self.adquirente.nome, "Gerado (CNAB para Banco)", arquivo_pagamento_estab, "green")
            self._log_message(self.adquirente.nome, "Bancos Parceiros", "Envio SFTP (CNAB)", f"Arquivo CNAB: {os.path.basename(arquivo_pagamento_estab)}", "lightblue")
        self._log_step("FIM DO PAGAMENTO")

        self._log_step("5. PROCESSO DE FATURAMENTO (Lotes - Emissor -> Sistemas Internos/Regulatórios)")
        arquivo_faturamento_emissor = generate_faturamento_3040_file(self.emissor.transacoes_para_faturar, self.output_dir)
        if arquivo_faturamento_emissor:
             self._log_file_action(self.emissor.nome, "Gerado (XML para Faturamento/3040 Simulado)", arquivo_faturamento_emissor, "green")
        self._log_step("FIM DO FATURAMENTO")

        # --- NOVO: FLUXO DE CHARGEBACK ---
        self._log_step("6. FLUXO DE CHARGEBACK (DISPUTA DE COMPRA)")
        # Simular um chargeback para a transacao_1 (APROVADA)
        cb_tx1 = self.cb_processor.iniciar_chargeback(self.emissor, self.adquirente, self.bandeira, transacao_1, "Mercadoria Não Recebida")
        time.sleep(2)
        if cb_tx1:
            self._log_step("6.1. FASE DE DEFESA DO CHARGEBACK")
            self.cb_processor.processar_defesa_chargeback(self.adquirente, self.bandeira, cb_tx1)
            time.sleep(2)
            self._log_step("6.2. FINALIZAÇÃO DO CHARGEBACK")
            self.cb_processor.finalizar_chargeback(self.emissor, self.bandeira, cb_tx1)
        self._log_step("FIM DO CHARGEBACK")

        # --- NOVO: ARQUIVOS REGULATÓRIOS DETALHADOS ---
        self._log_step("7. ARQUIVOS REGULATÓRIOS (Adquirente/Emissor -> Banco Central)")
        current_month_year = datetime.datetime.now().strftime("%Y%m")

        # Dados para o CADOC 3040 (SCR) - Emissor
        # Coletar transações aprovadas e chargebacks para o relatório de crédito
        emissor_report_data = {
            self.emissor.nome: self.emissor.transacoes_aprovadas + list(self.cb_processor.chargebacks_ativos.values())
        }
        self.regulatory_reporter.generate_cadoc_3040_scr(emissor_report_data, current_month_year)
        time.sleep(1)

        # Dados para o CADOC 5817 (Credenciadoras) - Adquirente
        adquirente_report_data = {
            "transacoes_capturadas": self.adquirente.transacoes_capturadas,
            "transacoes_negadas": self.adquirente.transacoes_recebidas, # Negadas estão aqui tb
            "estabelecimentos": self.adquirente.estabelecimentos,
            "chargebacks_ativos": self.adquirente.chargebacks_ativos # Adquirente também rastreia
        }
        self.regulatory_reporter.generate_cadoc_5817_credenciadoras(adquirente_report_data, current_month_year)
        time.sleep(1)

        # Dados para o CADOC 6334 (Estatístico) - Geral
        self.regulatory_reporter.generate_cadoc_6334_estatistico(self.all_processed_transactions, current_month_year)
        
        self._log_step("FIM DOS REGULATÓRIOS")

        self.log_callback("SIMULAÇÃO COMPLETA CONCLUÍDA!", "green")

