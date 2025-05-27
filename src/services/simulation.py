# src/services/simulation.py
import datetime
import time
import os

from src.models.transaction import Transacao
from src.models.entities import Adquirente, Emissor, Bandeira, Estabelecimento, Portador
from src.services.file_generator import (
    generate_capture_file, generate_liquidation_file_adq,
    generate_liquidation_file_emissor, generate_payment_cnab_file,
    generate_faturamento_3040_file, generate_regulatory_file
)
from src.services.utils import print_message, print_file_action, print_step, print_separator # Ou adaptar para logs da GUI

class PaymentSimulator:
    def __init__(self, output_dir="data/output/", log_callback=None):
        self.adquirente = Adquirente("AdquirenteXPTO", log_callback)
        self.emissor = Emissor("BancoAlpha", log_callback)
        self.bandeira = Bandeira("BandeiraPrincipal", log_callback)
        self.output_dir = output_dir
        self.log_callback = log_callback

        # Setup inicial das entidades
        self.estab_1 = Estabelecimento("ESTAB001", "Loja do Zé", "4751-2/01")
        self.adquirente.cadastrar_estabelecimento(self.estab_1)
        self.portador_1 = Portador("PORT001", "Maria Silva", "123.456.789-00", "CREDITO")
        self.emissor.cadastrar_portador(self.portador_1)
        self.portador_2 = Portador("PORT002", "João Pereira", "987.654.321-00", "DEBITO")
        self.emissor.cadastrar_portador(self.portador_2)

    def _log_step(self, title):
        if self.log_callback:
            self.log_callback(f"\n--- {title} ---", "magenta") # Cor para títulos
        else:
            print_step(title)
        time.sleep(1) # Simula delay

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
        time.sleep(1)

        transacao_processada_adquirente = self.adquirente.receber_transacao(transacao_1)
        time.sleep(1)
        transacao_roteada_bandeira = self.adquirente.enviar_para_bandeira(transacao_processada_adquirente, self.bandeira)
        time.sleep(1)
        transacao_autorizada_emissor = self.emissor.receber_solicitacao_autorizacao(transacao_roteada_bandeira)
        time.sleep(1)
        transacao_resposta_adquirente = self.bandeira.rotear_resposta_do_emissor(transacao_autorizada_emissor)
        time.sleep(1)
        self.adquirente.receber_resposta_bandeira(transacao_resposta_adquirente)

        # Transação 2: Negada
        transacao_2 = Transacao(
            id_transacao="TXN002", valor=1200.00, tipo_cartao="CREDITO",
            numero_cartao_bin="987654", data_hora=datetime.datetime.now(),
            id_estabelecimento=self.estab_1.id, id_portador=self.portador_2.id
        )
        self._log_message("Portador", "Estabelecimento", "Passagem de Cartão", f"Cartão {transacao_2.numero_cartao_bin} - R${transacao_2.valor:.2f}", "white")
        time.sleep(1)
        transacao_processada_adquirente_2 = self.adquirente.receber_transacao(transacao_2)
        time.sleep(1)
        transacao_roteada_bandeira_2 = self.adquirente.enviar_para_bandeira(transacao_processada_adquirente_2, self.bandeira)
        time.sleep(1)
        transacao_autorizada_emissor_2 = self.emissor.receber_solicitacao_autorizacao(transacao_roteada_bandeira_2)
        time.sleep(1)
        transacao_resposta_adquirente_2 = self.bandeira.rotear_resposta_do_emissor(transacao_autorizada_emissor_2)
        time.sleep(1)
        self.adquirente.receber_resposta_bandeira(transacao_resposta_adquirente_2)
        self._log_step("FIM DA AUTORIZAÇÃO")

        self._log_step("2. PROCESSO DE CAPTURA (Lotes - Adquirente -> Bandeira)")
        arquivo_captura_adquirente = generate_capture_file(self.adquirente.transacoes_recebidas, self.output_dir)
        if arquivo_captura_adquirente:
            self._log_file_action(self.adquirente.nome, "Gerado", arquivo_captura_adquirente, "green")
            self._log_message(self.adquirente.nome, self.bandeira.nome, "Envio SFTP", f"Arquivo de Captura: {os.path.basename(arquivo_captura_adquirente)}", "lightblue")
            # Simular a Bandeira processando (em um cenário real, ela leria este arquivo)
        self._log_step("FIM DA CAPTURA")

        self._log_step("3. PROCESSO DE LIQUIDAÇÃO (Lotes - Bandeira -> Adquirente e Emissor)")
        arquivo_liquidacao_adquirente = generate_liquidation_file_adq(self.adquirente.transacoes_capturadas, self.output_dir)
        time.sleep(1)
        if arquivo_liquidacao_adquirente:
            self._log_file_action(self.bandeira.nome, "Gerado (p/ Adquirente)", arquivo_liquidacao_adquirente, "green")
            self._log_message(self.bandeira.nome, self.adquirente.nome, "Envio SFTP", f"Arquivo de Liquidação Adquirente: {os.path.basename(arquivo_liquidacao_adquirente)}", "lightblue")
            # A Adquirente processaria este arquivo aqui
        time.sleep(1)

        arquivo_liquidacao_emissor = generate_liquidation_file_emissor(self.emissor.transacoes_aprovadas, self.output_dir)
        time.sleep(1)
        if arquivo_liquidacao_emissor:
            self._log_file_action(self.bandeira.nome, "Gerado (p/ Emissor)", arquivo_liquidacao_emissor, "green")
            self._log_message(self.bandeira.nome, self.emissor.nome, "Envio SFTP", f"Arquivo de Liquidação Emissor: {os.path.basename(arquivo_liquidacao_emissor)}", "lightblue")
            # O Emissor processaria este arquivo aqui
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

        self._log_step("6. ARQUIVOS REGULATÓRIOS (Adquirente/Emissor -> Banco Central)")
        generate_regulatory_file(self.adquirente.nome, self.adquirente.transacoes_capturadas, "Adquirente", "CADOC_5817_SIMULADO", self.output_dir)
        time.sleep(1)
        generate_regulatory_file(self.emissor.nome, self.emissor.transacoes_aprovadas, "Emissor", "CADOC_3040_DADOS_SIMULADO", self.output_dir)
        self._log_step("FIM DOS REGULATÓRIOS")

        self.log_callback("SIMULAÇÃO COMPLETA CONCLUÍDA!", "green")
