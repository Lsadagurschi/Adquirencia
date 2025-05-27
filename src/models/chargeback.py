# src/models/chargeback.py
import datetime

class Chargeback:
    # Status comuns de um chargeback
    STATUS_INICIADO = "CB_INICIADO"
    STATUS_DOCUMENTACAO_SOLICITADA = "CB_DOC_SOLICITADA"
    STATUS_DOCUMENTACAO_ENVIADA = "CB_DOC_ENVIADA"
    STATUS_REAPRESENTADO = "CB_REAPRESENTADO" # Representment
    STATUS_ARBITRAGEM = "CB_ARBITRAGEM"
    STATUS_RESOLVIDO_FAVOR_PORTADOR = "CB_RESOLVIDO_PORTADOR"
    STATUS_RESOLVIDO_FAVOR_ESTABELECIMENTO = "CB_RESOLVIDO_ESTAB"
    STATUS_CANCELADO = "CB_CANCELADO"

    def __init__(self, id_chargeback, transacao_original_id, motivo, valor, data_solicitacao, status=STATUS_INICIADO):
        self.id = id_chargeback
        self.transacao_original_id = transacao_original_id
        self.motivo = motivo # Ex: "FRAUDE", "MERCADORIA_NAO_RECEBIDA", "SERVICO_NAO_PRESTADO"
        self.valor = valor
        self.data_solicitacao = data_solicitacao
        self.status = status
        self.historico_status = [(data_solicitacao, status)] # Rastreia mudanças de status
        self.documentos_enviados = False

    def update_status(self, new_status):
        self.status = new_status
        self.historico_status.append((datetime.datetime.now(), new_status))

    def __repr__(self):
        return (f"Chargeback(ID: {self.id}, TXN Original: {self.transacao_original_id}, "
                f"Motivo: {self.motivo}, Status: {self.status})")
