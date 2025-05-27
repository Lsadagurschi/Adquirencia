# src/services/regulatory_reporter.py
import datetime
import os
import csv
import json
import logging
logger = logging.getLogger(__name__)

# Assumindo que Transacao está em src/models/transaction.py
from src.models.transaction import Transacao
# Assumindo que Chargeback está em src/models/chargeback.py
from src.models.chargeback import Chargeback

class RegulatoryReporter:
    def __init__(self, output_dir="data/output/", log_callback=None):
        self.output_dir = output_dir
        self.log_callback = log_callback
        logger.debug("RegulatoryReporter inicializado.")

    def _log(self, message, color_tag="black"):
        if self.log_callback:
            self.log_callback(message, color_tag)
        else:
            print(message) # Fallback para console
        logger.debug(f"RegulatoryReporter Log: {message}")

    def generate_cadoc_3040_scr(self, entities_data, reference_month_year):
        self._log(f"Iniciando geração do CADOC 3040 (SCR) para {reference_month_year}...", "red")
        logger.info(f"RegulatoryReporter: Gerando CADOC 3040 para {reference_month_year}.")
        filename = os.path.join(self.output_dir, f"REG_EMISSOR_CADOC_3040_SCR_{reference_month_year}.xml")
        
        xml_content = ['<SCR_Report xmlns="http://www.bcb.gov.br/scr/3040">\n']
        xml_content.append(f'  <Header DataRef="{reference_month_year}-01" Geracao="{datetime.datetime.now().isoformat()}" />\n')
        xml_content.append('  <OperacoesDeCredito>\n')

        # Simulando dados de transações (cartão de crédito gera "obrigação a pagar")
        for entity_name, data_list in entities_data.items():
            for item in data_list:
                if isinstance(item, Transacao) and item.status in ["APROVADA_EMISSOR", "LIQUIDADA_EMISSOR"]:
                    xml_content.append(f'    <Operacao id="{item.id}">\n')
                    xml_content.append(f'      <TipoOperacao>CartaoCredito</TipoOperacao>\n')
                    xml_content.append(f'      <CpfCnpjPortador>{item.id_portador}</CpfCnpjPortador>\n') # Simplificado para ID
                    xml_content.append(f'      <ValorOriginal>{item.valor:.2f}</ValorOriginal>\n')
                    xml_content.append(f'      <SaldoDevedor>{item.valor:.2f}</SaldoDevedor>\n')
                    xml_content.append(f'      <DataContratacao>{item.data_hora.strftime("%Y-%m-%d")}</DataContratacao>\n')
                    xml_content.append(f'    </Operacao>\n')
                elif isinstance(item, Chargeback):
                    xml_content.append(f'    <Operacao id="CB_{item.id}">\n')
                    xml_content.append(f'      <TipoOperacao>AjusteChargeback</TipoOperacao>\n')
                    xml_content.append(f'      <CpfCnpjPortador>{item.transacao_original_id}</CpfCnpjPortador>\n') # Associar ao portador original
                    xml_content.append(f'      <ValorOriginal>{item.valor:.2f}</ValorOriginal>\n')
                    xml_content.append(f'      <StatusChargeback>{item.status}</StatusChargeback>\n')
                    xml_content.append(f'      <DataSolicitacao>{item.data_solicitacao.strftime("%Y-%m-%d")}</DataSolicitacao>\n')
                    xml_content.append(f'    </Operacao>\n')

        xml_content.append('  </OperacoesDeCredito>\n')
        xml_content.append('</SCR_Report>\n')

        with open(filename, 'w') as f:
            f.writelines(xml_content)
        self._log(f"[BCB]: Gerado CADOC 3040 (SCR) em {filename}", "red")
        logger.info(f"RegulatoryReporter: CADOC 3040 gerado em {filename}.")
        return filename

    def generate_cadoc_5817_credenciadoras(self, adquirente_data, reference_month_year):
        self._log(f"Iniciando geração do CADOC 5817 (Credenciadoras) para {reference_month_year}...", "red")
        logger.info(f"RegulatoryReporter: Gerando CADOC 5817 para {reference_month_year}.")
        filename = os.path.join(self.output_dir, f"REG_ADQUIRENTE_CADOC_5817_CREDENCIADORAS_{reference_month_year}.csv")
        
        headers = ["DataReferencia", "Entidade", "TipoTransacao", "VolumeTransacoes", "ValorTotal", "NumEstabelecimentos"]
        data_rows = []

        total_aprovadas = sum(1 for t in adquirente_data["transacoes_capturadas"] if t.status == "APROVADA_CAPTURA")
        valor_aprovadas = sum(t.valor for t in adquirente_data["transacoes_capturadas"] if t.status == "APROVADA_CAPTURA")
        
        total_negadas = sum(1 for t in adquirente_data["transacoes_recebidas"] if t.status.startswith("NEGADA")) # Inclui todas as negadas
        valor_negadas = sum(t.valor for t in adquirente_data["transacoes_recebidas"] if t.status.startswith("NEGADA"))

        num_estabelecimentos = len(adquirente_data["estabelecimentos"])

        data_rows.append([reference_month_year, "AdquirenteXPTO", "APROVADA", total_aprovadas, valor_aprovadas, num_estabelecimentos])
        data_rows.append([reference_month_year, "AdquirenteXPTO", "NEGADA", total_negadas, valor_negadas, num_estabelecimentos])
        
        total_chargebacks_adq = sum(1 for cb in adquirente_data["chargebacks_ativos"].values())
        valor_chargebacks_adq = sum(cb.valor for cb in adquirente_data["chargebacks_ativos"].values())
        data_rows.append([reference_month_year, "AdquirenteXPTO", "CHARGEBACK_INICIADO", total_chargebacks_adq, valor_chargebacks_adq, num_estabelecimentos])

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data_rows)
        
        self._log(f"[BCB]: Gerado CADOC 5817 (Credenciadoras) em {filename}", "red")
        logger.info(f"RegulatoryReporter: CADOC 5817 gerado em {filename}.")
        return filename

    def generate_cadoc_6334_estatistico(self, all_transactions, reference_month_year):
        self._log(f"Iniciando geração do CADOC 6334 (Estatístico) para {reference_month_year}...", "red")
        logger.info(f"RegulatoryReporter: Gerando CADOC 6334 para {reference_month_year}.")
        filename = os.path.join(self.output_dir, f"REG_GERAL_CADOC_6334_ESTATISTICO_{reference_month_year}.csv")
        
        headers = ["DataReferencia", "TipoOperacao", "Instituicao", "ModalidadeCartao", "VolumeTransacoes", "ValorTotal"]
        data_rows = []

        credito_aprovadas = sum(1 for t in all_transactions if t.tipo_cartao == "CREDITO" and t.status.startswith("APROVADA"))
        credito_valor = sum(t.valor for t in all_transactions if t.tipo_cartao == "CREDITO" and t.status.startswith("APROVADA"))
        
        debito_aprovadas = sum(1 for t in all_transactions if t.tipo_cartao == "DEBITO" and t.status.startswith("APROVADA"))
        debito_valor = sum(t.valor for t in all_transactions if t.tipo_cartao == "DEBITO" and t.status.startswith("APROVADA"))

        data_rows.append([reference_month_year, "Pagamento", "TODAS", "CREDITO", credito_aprovadas, credito_valor])
        data_rows.append([reference_month_year, "Pagamento", "TODAS", "DEBITO", debito_aprovadas, debito_valor])

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data_rows)
        
        self._log(f"[BCB]: Gerado CADOC 6334 (Estatístico) em {filename}", "red")
        logger.info(f"RegulatoryReporter: CADOC 6334 gerado em {filename}.")
        return filename
