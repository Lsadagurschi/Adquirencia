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
            {"description": "Iniciando Simulação...", "active_entities": [], "flow_path": None}
        )
        time.sleep(0.5)

        # --- 1. FLUXO DE AUTORIZAÇÃO EM TEMPO REAL (ISO 8583) ---
        self.log_callback("--- 1. FLUXO DE AUTORIZAÇÃO EM TEMPO REAL (ISO 8583) ---", "white")
        time.sleep(0.5)

        # Transação Aprovada
        self.log_callback(
            f"[Portador → Estabelecimento] Passagem de Cartão: Cartão {self.portador_1.numero_cartao} - R150.00",
            "black",
            {"description": "Cliente passa cartão", "active_entities": ["client", "store"], "flow_path": "client_to_store"}
        )
        aprovada = self.estab_1.iniciar_transacao(self.portador_1, 150.00, self.adquirente, self.bandeira, self.emissor)
        
        self.log_callback(
            "[AdquirenteXPTO]: Recebida transação: TXN TXN001 - Valor: R150.00",
            "blue",
            {"description": "Adquirente recebe transação", "active_entities": ["acquirer", "store"], "flow_path": "store_to_acquirer"}
        )
        # Continue adicionando animation_data para cada etapa relevante
        self.log_callback(
            "[AdquirenteXPTO]: Enviando para Bandeira: TXN TXN001",
            "blue",
            {"description": "Adquirente envia para Bandeira", "active_entities": ["acquirer", "flag"], "flow_path": "acquirer_to_flag"}
        )
        self.log_callback(
            "[BandeiraPrincipal]: Roteando ISO 8583 (Autorização): TXN TXN001",
            "yellow",
            {"description": "Bandeira roteia para Emissor", "active_entities": ["flag", "issuer"], "flow_path": "flag_to_issuer"}
        )
        self.log_callback(
            "[BancoAlpha]: Recebida solicitação de Autorização: TXN TXN001 - Valor: R150.00",
            "red",
            {"description": "Emissor recebe autorização", "active_entities": ["issuer", "flag"], "flow_path": "issuer_from_flag"} # ou from_flag_to_issuer
        )
        # ... e assim por diante para todas as etapas importantes
        # Lembre-se de passar o "animation_data" em cada chamada relevante da callback!

        # ... (restante do método run_full_simulation, adicionando animation_data onde fizer sentido) ...

        self.log_callback(
            "[Simulador → Interno] Fim: Simulação completa concluída!",
            "green",
            {"description": "Simulação Concluída!", "active_entities": [], "flow_path": None}
        )
