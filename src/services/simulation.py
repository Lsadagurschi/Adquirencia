import time
import datetime
import logging
from src.models.entities import Adquirente, Emissor, Bandeira, Estabelecimento, Portador, Transacao, StatusTransacao
from src.services.chargeback_processor import ChargebackProcessor
from src.services.regulatory_reporter import RegulatoryReporter

logger = logging.getLogger(__name__)

class PaymentSimulator:
    def __init__(self, output_dir="data/output/", log_callback=None):
        self.output_dir = output_dir
        self.log_callback = log_callback

        logger.info("PaymentSimulator: Inicializando simulador.")

        # Passa o callback para todas as entidades/serviços
        self.adquirente = Adquirente("AdquirenteXPTO", log_callback=self.log_callback)
        self.emissor = Emissor("BancoAlpha", log_callback=self.log_callback)
        self.bandeira = Bandeira("BandeiraPrincipal", log_callback=self.log_callback)
        self.cb_processor = ChargebackProcessor(log_callback=self.log_callback, output_dir=self.output_dir)
        self.regulatory_reporter = RegulatoryReporter(output_dir=self.output_dir, log_callback=self.log_callback)

        self.estab_1 = Estabelecimento("Loja do Zé", "ESTAB001", log_callback=self.log_callback)
        self.portador_1 = Portador("Maria Silva", "PORT001", log_callback=self.log_callback)
        self.portador_2 = Portador("João Pereira", "PORT002", log_callback=self.log_callback)

        # Cadastro inicial dos dados
        self.adquirente.cadastrar_estabelecimento(self.estab_1)
        self.emissor.cadastrar_portador(self.portador_1)
        self.emissor.cadastrar_portador(self.portador_2)

    def run_full_simulation(self):
        self.log_callback(
            "[Simulador → Interno] Início: Iniciando a simulação completa...",
            "black",
            {"description": "Iniciando Simulação Completa...", "active_entities": [], "flow_path": None}
        )
        time.sleep(0.5)

        # --- 1. FLUXO DE AUTORIZAÇÃO EM TEMPO REAL (ISO 8583) ---
        self.log_callback("--- 1. FLUXO DE AUTORIZAÇÃO EM TEMPO REAL (ISO 8583) ---", "white",
                          {"description": "Fluxo de Autorização (ISO 8583)", "active_entities": [], "flow_path": None})
        time.sleep(0.5)

        # Transação Aprovada
        self.log_callback(
            f"[Portador → Estabelecimento] Passagem de Cartão: Cartão {self.portador_1.numero_cartao} - R150.00",
            "black",
            {"description": "Cliente passa cartão", "active_entities": ["client", "store"], "flow_path": "client_to_store_token"}
        )
        autorizada_1 = self.estab_1.iniciar_transacao(self.portador_1, 150.00, self.adquirente, self.bandeira, self.emissor)
        
        # Transação Negada (Saldo Insuficiente)
        self.log_callback(
            f"[Portador -> Estabelecimento] Passagem de Cartão: Cartão {self.portador_2.numero_cartao} - R1200.00",
            "black",
            {"description": "Cliente passa cartão", "active_entities": ["client", "store"], "flow_path": "client_to_store_token"}
        )
        autorizada_2 = self.estab_1.iniciar_transacao(self.portador_2, 1200.00, self.adquirente, self.bandeira, self.emissor)
        
        self.log_callback("--- FIM DA AUTORIZAÇÃO ---", "white",
                          {"description": "Autorização Concluída", "active_entities": [], "flow_path": None})
        time.sleep(0.5)

        # --- 2. PROCESSO DE CAPTURA (Lotes - Adquirente → Bandeira) ---
        self.log_callback("--- 2. PROCESSO DE CAPTURA (Lotes - Adquirente → Bandeira) ---", "white",
                          {"description": "Iniciando Captura de Lotes", "active_entities": ["acquirer"], "flow_path": None})
        time.sleep(0.5)
        # Adquirente envia lote de transações aprovadas para a Bandeira
        lote_captura = self.adquirente.transacoes_aprovadas
        if lote_captura:
            self.bandeira.processar_captura(lote_captura)
            self.adquirente.limpar_transacoes_aprovadas() # Limpa após enviar para captura
        else:
            self.log_callback("Nenhuma transação para capturar.", "black")
        self.log_callback("--- FIM DA CAPTURA ---", "white",
                          {"description": "Captura Concluída", "active_entities": ["acquirer", "flag"], "flow_path": None})
        time.sleep(0.5)

        # --- 3. PROCESSO DE LIQUIDAÇÃO (Lotes - Bandeira → Adquirente e Emissor) ---
        self.log_callback("--- 3. PROCESSO DE LIQUIDAÇÃO (Lotes - Bandeira → Adquirente e Emissor) ---", "white",
                          {"description": "Iniciando Liquidação", "active_entities": ["flag"], "flow_path": None})
        time.sleep(0.5)
        self.bandeira.iniciar_liquidacao(self.adquirente, self.emissor)
        self.log_callback("--- FIM DA LIQUIDAÇÃO ---", "white",
                          {"description": "Liquidação Concluída", "active_entities": ["flag", "acquirer", "issuer"], "flow_path": None})
        time.sleep(0.5)

        # --- 4. PROCESSO DE PAGAMENTO (Lotes - Adquirente → Bancos dos Estabelecimentos - CNAB) ---
        self.log_callback("--- 4. PROCESSO DE PAGAMENTO (Lotes - Adquirente → Bancos dos Estabelecimentos - CNAB) ---", "white",
                          {"description": "Iniciando Pagamento ao Lojista (CNAB)", "active_entities": ["acquirer"], "flow_path": None})
        time.sleep(0.5)
        self.adquirente.iniciar_pagamento_estabelecimentos()
        self.log_callback("--- FIM DO PAGAMENTO ---", "white",
                          {"description": "Pagamento Concluído", "active_entities": ["acquirer", "store"], "flow_path": None})
        time.sleep(0.5)

        # --- 5. PROCESSO DE FATURAMENTO (Lotes - Emissor → Sistemas Internos/Regulatórios) ---
        self.log_callback("--- 5. PROCESSO DE FATURAMENTO (Lotes - Emissor → Sistemas Internos/Regulatórios) ---", "white",
                          {"description": "Iniciando Faturamento do Emissor", "active_entities": ["issuer"], "flow_path": None})
        time.sleep(0.5)
        self.emissor.iniciar_faturamento()
        self.log_callback("--- FIM DO FATURAMENTO ---", "white",
                          {"description": "Faturamento Concluído", "active_entities": ["issuer", "client"], "flow_path": None})
        time.sleep(0.5)

        # --- 6. FLUXO DE CHARGEBACK (DISPUTA DE COMPRA) ---
        self.log_callback("--- 6. FLUXO DE CHARGEBACK (DISPUTA DE COMPRA) ---", "white",
                          {"description": "Iniciando Fluxo de Chargeback", "active_entities": ["client"], "flow_path": None})
        time.sleep(0.5)
        # Vamos simular um chargeback para a primeira transação (aprovada)
        transacao_para_chargeback = next((t for t in self.bandeira.transacoes_capturadas if t.portador_id == self.portador_1.id), None)
        if transacao_para_chargeback:
            self.cb_processor.processar_chargeback(
                self.portador_1, 
                self.emissor, 
                self.bandeira, 
                self.adquirente, 
                self.estab_1, 
                transacao_para_chargeback
            )
        else:
            self.log_callback("Nenhuma transação capturada para simular chargeback.", "orange",
                              {"description": "Chargeback Não Simulado", "active_entities": [], "flow_path": None})
        self.log_callback("--- FIM DO CHARGEBACK ---", "white",
                          {"description": "Fluxo de Chargeback Concluído", "active_entities": [], "flow_path": None})
        time.sleep(0.5)

        # --- 7. ARQUIVOS REGULATÓRIOS (Adquirente/Emissor → Banco Central) ---
        self.log_callback("--- 7. ARQUIVOS REGULATÓRIOS (Adquirente/Emissor → Banco Central) ---", "white",
                          {"description": "Iniciando Relatórios Regulatórios", "active_entities": ["bcb"], "flow_path": None})
        time.sleep(0.5)
        self.regulatory_reporter.generate_all_reports()
        self.log_callback("--- FIM DOS REGULATÓRIOS ---", "white",
                          {"description": "Relatórios Regulatórios Concluídos", "active_entities": ["bcb"], "flow_path": None})
        time.sleep(0.5)


        self.log_callback(
            "[Simulador → Interno] Fim: Simulação completa concluída!",
            "green",
            {"description": "Simulação Concluída!", "active_entities": [], "flow_path": None}
        )
