# src/services/file_generator.py
import datetime
import os
import json
import csv
import random

# Assumindo que Transacao está em src/models/transaction.py
# Não precisamos dela aqui, pois as funções receberão listas de transações já prontas.

def generate_capture_file(transactions, output_dir):
    data_arquivo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(output_dir, f"ADQUIRENTE_CAPTURAS_BANDEIRA_{data_arquivo}.txt")

    capturas_data_linhas = []
    for transacao in transactions:
        if transacao.status == "APROVADA_ADQUIRENTE": # Apenas transações que passaram pela autorização
            # Adapte o layout para ser posicional (ex: TipoReg(2) | ID_Transacao(10) | ...)
            tipo_reg = "01"
            id_transacao_str = transacao.id.ljust(10)
            valor_str = str(int(transacao.valor * 100)).zfill(10)
            nsu_str = (transacao.nsu or "00000000").ljust(8)
            cod_auth_str = (transacao.codigo_autorizacao or "0000").ljust(4)
            bin_str = transacao.numero_cartao_bin.ljust(6)
            linha = f"{tipo_reg}{id_transacao_str}{valor_str}{nsu_str}{cod_auth_str}{bin_str}\n"
            capturas_data_linhas.append(linha)
            transacao.status = "APROVADA_CAPTURA" # Atualiza status para simulação

    if capturas_data_linhas:
        with open(filename, 'w') as f:
            f.writelines(capturas_data_linhas)
        return filename
    return None

def generate_liquidation_file_adq(transactions, output_dir):
    data_arquivo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(output_dir, f"BANDEIRA_LIQUIDACAO_ADQ_{data_arquivo}.txt")

    registros_liquidacao = []
    for transacao in transactions:
        if transacao.status == "APROVADA_CAPTURA": # Apenas transações já capturadas
            valor_str = str(int(transacao.valor * 100)).zfill(10)
            codigo_auth_str = (transacao.codigo_autorizacao or "0000").ljust(4)
            nsu_str = (transacao.nsu or "00000000").ljust(8)
            status_liq_str = "LIQOK".ljust(10)
            registro = f"{transacao.id.ljust(10)}{valor_str}{codigo_auth_str}{nsu_str}{status_liq_str}\n"
            registros_liquidacao.append(registro)
            transacao.status = "LIQUIDADA_ADQUIRENTE" # Atualiza status para simulação

    if registros_liquidacao:
        with open(filename, 'w') as f:
            f.writelines(registros_liquidacao)
        return filename
    return None

def generate_liquidation_file_emissor(transactions, output_dir):
    data_arquivo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(output_dir, f"BANDEIRA_LIQUIDACAO_EMISSOR_{data_arquivo}.txt")

    registros_liquidacao = []
    for transacao in transactions:
        if transacao.status == "APROVADA_EMISSOR": # Apenas transações aprovadas pelo emissor
            valor_str = str(int(transacao.valor * 100)).zfill(10)
            bin_str = transacao.numero_cartao_bin.ljust(6)
            codigo_auth_str = (transacao.codigo_autorizacao or "0000").ljust(4)
            data_hora_str = transacao.data_hora.strftime("%Y%m%d%H%M%S")
            status_fatura_str = "FATURAR".ljust(10)
            registro = f"{transacao.id.ljust(10)}{valor_str}{bin_str}{codigo_auth_str}{data_hora_str}{status_fatura_str}\n"
            registros_liquidacao.append(registro)
            transacao.status = "LIQUIDADA_EMISSOR" # Atualiza status para simulação

    if registros_liquidacao:
        with open(filename, 'w') as f:
            f.writelines(registros_liquidacao)
        return filename
    return None

def generate_payment_cnab_file(transactions, output_dir):
    data_arquivo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(output_dir, f"ADQUIRENTE_PAGAMENTO_CNAB_{data_arquivo}.txt")

    pagamentos_data_linhas = []
    for t in transactions:
        if t.status == "LIQUIDADA_ADQUIRENTE":
            valor_liquido = t.valor * 0.98 
            tipo_reg = "P" # Pagamento
            banco_estab = "001" # Ex: Banco do Brasil
            agencia_estab = "1234"
            conta_estab = "00000001"
            valor_liquido_str = str(int(valor_liquido * 100)).zfill(10)
            id_transacao_str = t.id.ljust(10)
            linha = f"{tipo_reg}{banco_estab}{agencia_estab}{conta_estab}{valor_liquido_str}{id_transacao_str}\n"
            pagamentos_data_linhas.append(linha)

    if pagamentos_data_linhas:
        with open(filename, 'w') as f:
            f.writelines(pagamentos_data_linhas)
        return filename
    return None

def generate_faturamento_3040_file(transactions, output_dir):
    data_arquivo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(output_dir, f"EMISSOR_FATURAMENTO_3040_SIMULADO_{data_arquivo}.xml")

    faturamento_xml_content = ['<FaturamentoReport>\n']
    for t in transactions:
        if t.status == "LIQUIDADA_EMISSOR":
            faturamento_xml_content.append(f'  <Transacao id="{t.id}">\n')
            faturamento_xml_content.append(f'    <PortadorID>{t.id_portador}</PortadorID>\n')
            faturamento_xml_content.append(f'    <NumeroCartaoBIN>{t.numero_cartao_bin}</NumeroCartaoBIN>\n')
            faturamento_xml_content.append(f'    <ValorCompra>{t.valor:.2f}</ValorCompra>\n')
            faturamento_xml_content.append(f'    <DataHoraCompra>{t.data_hora.isoformat()}</DataHoraCompra>\n')
            faturamento_xml_content.append(f'    <CodigoAutorizacao>{t.codigo_autorizacao}</CodigoAutorizacao>\n')
            faturamento_xml_content.append(f'    <NSUAdquirente>{t.nsu}</NSUAdquirente>\n')
            faturamento_xml_content.append(f'    <StatusFaturamento>FATURADO</StatusFaturamento>\n')
            faturamento_xml_content.append(f'  </Transacao>\n')
    faturamento_xml_content.append('</FaturamentoReport>\n')

    if len(faturamento_xml_content) > 2:
        with open(filename, 'w') as f:
            f.writelines(faturamento_xml_content)
        return filename
    return None

def generate_regulatory_file(entity_name, transactions, entity_type, cadoc_type, output_dir):
    data_arquivo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = os.path.join(output_dir, f"{entity_name}_{cadoc_type}_{data_arquivo}.csv")

    registros = []
    for t in transactions:
        registros.append({
            "id_transacao": t.id,
            "data_hora": t.data_hora.isoformat(),
            "valor": t.valor,
            "status_final": t.status,
            "tipo_cartao": t.tipo_cartao,
            "nsu_adquirente": t.nsu if hasattr(t, 'nsu') else '',
            "codigo_autorizacao": t.codigo_autorizacao if hasattr(t, 'codigo_autorizacao') else '',
            "entidade_responsavel": entity_type,
            "data_referencia_bcb": datetime.date.today().strftime("%Y-%m")
        })

    if registros:
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=registros[0].keys())
            writer.writeheader()
            writer.writerows(registros)
        return filename
    return None
