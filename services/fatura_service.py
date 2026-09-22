import hashlib
import calendar
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from models.lancamento_model import LancamentoModel
from models.credito_model import CreditoModel
from models.transaction_model import TransactionModel
from models.category_model import CategoryModel
from models.account_model import AccountModel
from models.pagamento_fatura_model import PagamentoFaturaModel
from models.fatura_ciclo_model import FaturaCicloModel
from core.operation_result import operation_result
from database.database import DatabaseError
from services.reconciliacao_importacao_service import (
    ReconciliacaoImportacaoService,
)


logger = logging.getLogger(__name__)


class FaturaSaldoInsuficiente(ValueError):
    pass


class FaturaService:

    CENT = Decimal("0.01")

    @classmethod
    def _money(cls, value):
        return Decimal(str(value or 0)).quantize(
            cls.CENT, rounding=ROUND_HALF_UP
        )

    def __init__(self, db_name=None):
        self.lancamento_model = LancamentoModel(db_name)
        self.credito_model = CreditoModel(db_name)
        self.transaction_model = TransactionModel(db_name)
        self.category_model = CategoryModel(db_name)
        self.account_model = AccountModel(db_name)
        self.pagamento_model = PagamentoFaturaModel(db_name)
        self.ciclo_model = FaturaCicloModel(db_name)
        self.reconciliacao_service = ReconciliacaoImportacaoService()

        self._cache_fatura = {}

    # ============================================================
    # CACHE
    # ============================================================
    def _cache_key(self, id_cartao, mes, ano, id_usuario):
        return f"{id_cartao}_{mes}_{ano}_{id_usuario}"

    def _get_cache(self, key):
        # Models/controllers podem coexistir na mesma tela; consultar o banco
        # evita devolver uma fatura obsoleta após edição, colagem ou exclusão.
        return None

    def _set_cache(self, key, value):
        self._cache_fatura[key] = value

    def _clear_cache(self):
        self._cache_fatura.clear()

    # ============================================================
    # CARTÕES
    # ============================================================
    def criar_cartao(self, dados: dict, id_usuario: int):
        dados["ID_Usuario"] = id_usuario
        return self.credito_model.add_cartao(dados)

    def editar_cartao(self, id_cartao: int, dados: dict, id_usuario: int):
        cartao = self.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            raise ValueError("Cartão não encontrado.")
        return self.credito_model.update_cartao(id_cartao, dados, id_usuario)

    def excluir_cartao(self, id_cartao: int, id_usuario: int):
        cartao = self.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            raise ValueError("Cartão não encontrado.")
        return self.credito_model.delete_cartao(id_cartao, id_usuario)

    def listar_cartoes(self, id_usuario: int):
        return self.credito_model.get_all_cartoes(id_usuario)

    def buscar_cartao_por_id(self, id_cartao: int, id_usuario: int):
        return self.credito_model.get_cartao_by_id(id_cartao, id_usuario)

    # ============================================================
    # COMPETÊNCIA
    # ============================================================
    def aplicar_fatura(self, data_compra, dia_fechamento):

        if isinstance(data_compra, str):
            data_compra = datetime.fromisoformat(data_compra)

        if isinstance(data_compra, datetime):
            data_compra = data_compra.date()

        if data_compra.day > dia_fechamento:
            data_compra += relativedelta(months=1)

        return data_compra.month, data_compra.year

    @staticmethod
    def _data_fechamento(mes, ano, dia_fechamento):
        ultimo = calendar.monthrange(int(ano), int(mes))[1]
        return date(int(ano), int(mes), min(int(dia_fechamento), ultimo))

    @staticmethod
    def _data_vencimento(mes, ano, dia_fechamento, dia_vencimento):
        mes_venc, ano_venc = int(mes), int(ano)
        if int(dia_vencimento) <= int(dia_fechamento):
            referencia = date(ano_venc, mes_venc, 1) + relativedelta(months=1)
            mes_venc, ano_venc = referencia.month, referencia.year
        ultimo = calendar.monthrange(ano_venc, mes_venc)[1]
        return date(ano_venc, mes_venc, min(int(dia_vencimento), ultimo))

    def sincronizar_ciclo(
        self, id_cartao, mes, ano, id_usuario, referencia=None
    ):
        cartao = self.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            raise ValueError("Cartão inválido.")
        fechamento = self._data_fechamento(
            mes, ano, cartao["Dia_Fechamento"]
        )
        vencimento = self._data_vencimento(
            mes, ano, cartao["Dia_Fechamento"], cartao["Dia_Vencimento"]
        )
        ciclo = self.ciclo_model.garantir(
            id_cartao, mes, ano, id_usuario, fechamento.isoformat(),
            vencimento.isoformat(),
        )
        movimentos = self.lancamento_model.get_lancamentos_por_fatura(
            id_cartao, mes, ano, id_usuario
        )
        total_movimentos = sum(
            (self._money(item["Valor"]) for item in movimentos
             if item.get("Tipo_Movimento") != "PAGAMENTO"),
            Decimal("0.00"),
        )
        total_pago = self._money(
            self.pagamento_model.get_total_by_invoice(ciclo["ID_Fatura"])
        )
        if (ciclo["Status"] != "PAGA" and total_pago > 0
                and total_pago >= max(total_movimentos, Decimal("0.00"))):
            self.lancamento_model.marcar_fatura_como_quitada(
                id_cartao, mes, ano, id_usuario
            )
            return self.ciclo_model.definir_status(
                id_cartao, mes, ano, id_usuario, "PAGA",
                date.today().isoformat(),
            )
        hoje = referencia or date.today()
        if isinstance(hoje, str):
            hoje = datetime.fromisoformat(hoje).date()
        if isinstance(hoje, datetime):
            hoje = hoje.date()
        if ciclo["Status"] == "ABERTA" and hoje > fechamento:
            ciclo = self.ciclo_model.definir_status(
                id_cartao, mes, ano, id_usuario, "FECHADA",
                fechamento.isoformat(),
            )
            proxima = fechamento + relativedelta(months=1)
            proximo_fechamento = self._data_fechamento(
                proxima.month, proxima.year, cartao["Dia_Fechamento"]
            )
            proximo_vencimento = self._data_vencimento(
                proxima.month, proxima.year, cartao["Dia_Fechamento"],
                cartao["Dia_Vencimento"],
            )
            self.ciclo_model.garantir(
                id_cartao, proxima.month, proxima.year, id_usuario,
                proximo_fechamento.isoformat(),
                proximo_vencimento.isoformat(),
            )
        return ciclo

    def _garantir_competencia_aberta(
        self, id_cartao, mes, ano, id_usuario, referencia=None
    ):
        ciclo = self.sincronizar_ciclo(
            id_cartao, mes, ano, id_usuario, referencia
        )
        while ciclo["Status"] != "ABERTA":
            proxima = date(int(ano), int(mes), 1) + relativedelta(months=1)
            mes, ano = proxima.month, proxima.year
            ciclo = self.sincronizar_ciclo(
                id_cartao, mes, ano, id_usuario, referencia
            )
        return int(mes), int(ano)

    # ============================================================
    # 🔥 REGISTRAR DESPESA (COM PARCELAMENTO)
    # ============================================================
    def registrar_despesa_cartao(self, dados: dict):

        id_usuario = dados["ID_Usuario"]
        id_cartao = dados["ID_Cartao"]

        cartao = self.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            raise ValueError("Cartão inválido")

        dia_fechamento = cartao["Dia_Fechamento"]

        parcelas = int(dados.get("Num_Parcelas", 1))
        valor_total = self._money(dados["Valor"])
        if valor_total <= 0:
            raise ValueError("O valor da compra deve ser maior que zero.")
        if parcelas < 1:
            raise ValueError("Quantidade de parcelas inválida.")
        total_centavos = int(valor_total * 100)
        base_centavos, resto = divmod(total_centavos, parcelas)
        valores_parcelas = [
            Decimal(base_centavos + (1 if i >= parcelas - resto else 0)) / 100
            for i in range(parcelas)
        ]

        data_base = dados["Data"]

        if isinstance(data_base, str):
            data_base = datetime.fromisoformat(data_base).date()

        with self.lancamento_model.unit_of_work(
            self.credito_model,
            self.lancamento_model.credito,
            self.ciclo_model,
            immediate=True,
        ):
            for i in range(parcelas):

                data_parcela = data_base + relativedelta(months=i)

                mes, ano = self.aplicar_fatura(
                    data_parcela,
                    dia_fechamento
                )
                mes, ano = self._garantir_competencia_aberta(
                    id_cartao, mes, ano, id_usuario, data_parcela
                )
                ciclo = self.sincronizar_ciclo(
                    id_cartao, mes, ano, id_usuario, data_parcela
                )

                self.lancamento_model.add_lancamento({
                    "ID_Usuario": id_usuario,
                    "ID_Cartao": id_cartao,
                    "ID_Fatura": ciclo["ID_Fatura"],
                    "Descricao": dados["Descricao"],
                    "Valor": float(valores_parcelas[i]),
                    "Data": data_parcela.isoformat(),
                    "Competencia_Mes": mes,
                    "Competencia_Ano": ano,
                    "ID_Categoria": dados.get("ID_Categoria"),
                    "ID_Favorecido": dados.get("ID_Favorecido"),
                    "Num_Parcelas": parcelas,
                    "Parcela_Atual": i + 1,
                    "Notas": dados.get("Notas"),
                    "Previsto": int(dados.get("Previsto", 0)),
                    "Tipo_Movimento": "COMPRA",
                })

        self._clear_cache()
        return True

    def adicionar_credito_fatura(self, dados: dict):
        id_usuario = dados["ID_Usuario"]
        id_cartao = dados["ID_Cartao"]
        cartao = self.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            raise ValueError("Cartão inválido.")
        valor_informado = self._money(dados["Valor"])
        if valor_informado <= 0:
            raise ValueError("Informe um crédito maior que zero.")
        tipo_credito = str(dados.get("Tipo_Credito") or "Ajuste").strip()
        permitidos = {"Cashback", "Estorno", "Devolução", "Desconto", "Ajuste"}
        if tipo_credito not in permitidos:
            raise ValueError("Tipo de crédito inválido.")
        data_credito = dados.get("Data") or date.today().isoformat()
        if isinstance(data_credito, str):
            data_obj = datetime.fromisoformat(data_credito).date()
        elif isinstance(data_credito, datetime):
            data_obj = data_credito.date()
        else:
            data_obj = data_credito
        mes, ano = self.aplicar_fatura(
            data_obj, cartao["Dia_Fechamento"]
        )
        mes, ano = self._garantir_competencia_aberta(
            id_cartao, mes, ano, id_usuario, data_obj
        )
        ciclo = self.sincronizar_ciclo(
            id_cartao, mes, ano, id_usuario, data_obj
        )
        origem = dados.get("ID_Lancamento_Origem")
        if origem:
            compra = self.obter_lancamento(origem, id_usuario)
            if (
                not compra
                or compra.get("ID_Cartao") != id_cartao
                or compra.get("Tipo_Movimento", "COMPRA") != "COMPRA"
            ):
                raise ValueError("A compra original não pertence a este cartão.")
        descricao = str(dados.get("Descricao") or tipo_credito).strip()
        tipo_movimento = (
            "ESTORNO" if tipo_credito in {"Estorno", "Devolução"}
            else "AJUSTE" if tipo_credito == "Ajuste"
            else "CREDITO"
        )
        natureza_ajuste = str(dados.get("Natureza_Ajuste") or "Reduzir")
        valor_movimento = (
            valor_informado
            if tipo_movimento == "AJUSTE" and natureza_ajuste == "Aumentar"
            else -valor_informado
        )
        self.lancamento_model.add_lancamento({
            "ID_Usuario": id_usuario,
            "ID_Cartao": id_cartao,
            "ID_Fatura": ciclo["ID_Fatura"],
            "Descricao": descricao,
            "Valor": float(valor_movimento),
            "Data": data_obj.isoformat(),
            "Competencia_Mes": mes,
            "Competencia_Ano": ano,
            "ID_Categoria": dados.get("ID_Categoria"),
            "Num_Parcelas": 1,
            "Parcela_Atual": 1,
            "Notas": dados.get("Notas"),
            "Previsto": 0,
            "Paga": 0,
            "Tipo_Movimento": tipo_movimento,
            "ID_Lancamento_Origem": origem,
        })
        self._clear_cache()
        return True

    def salvar_lote_importado(self, lista_lancamentos, id_usuario):
        """Persiste apenas compras novas após revalidação atômica."""
        if not lista_lancamentos:
            return 0

        total = 0
        with self.lancamento_model.unit_of_work(
            self.credito_model,
            self.lancamento_model.credito,
            self.ciclo_model,
            immediate=True,
        ):
            por_cartao = {}
            for original in lista_lancamentos:
                id_cartao = original.get("ID_Cartao")
                if id_cartao:
                    por_cartao.setdefault(id_cartao, []).append(original)

            reconciliados = []
            for id_cartao, itens in por_cartao.items():
                if not self.credito_model.get_cartao_by_id(id_cartao, id_usuario):
                    raise PermissionError("Cartão não pertence ao usuário.")
                inicio, fim = self.reconciliacao_service.limites_periodo(itens)
                existentes = self.lancamento_model.get_import_candidates(
                    id_cartao, id_usuario, inicio, fim
                )
                normalizados = []
                for original in itens:
                    item = dict(original)
                    item["ID_Usuario"] = id_usuario
                    normalizados.append(item)
                reconciliados.extend(self.reconciliacao_service.reconciliar(
                    normalizados,
                    existentes,
                    ReconciliacaoImportacaoService.DOMINIO_CARTAO,
                ))

            for item in reconciliados:
                status = item.get("StatusImportacao")
                if status == ReconciliacaoImportacaoService.DUPLICADO:
                    continue
                if (
                    status == ReconciliacaoImportacaoService.POSSIVEL_DUPLICADO
                    and not item.get("_ConfirmadoPossivel")
                ):
                    continue
                descricao = str(item.get("Descricao") or "")
                tipo = item.get("Tipo_Movimento") or (
                    "CREDITO" if float(item.get("Valor", 0)) < 0 else "COMPRA"
                )
                if tipo == "PAGAMENTO" or "pagamento de fatura" in descricao.lower():
                    continue
                mes, ano = self._garantir_competencia_aberta(
                    item.get("ID_Cartao"),
                    item.get("Competencia_Mes"),
                    item.get("Competencia_Ano"),
                    id_usuario,
                    item.get("Data"),
                )
                ciclo = self.sincronizar_ciclo(
                    item.get("ID_Cartao"), mes, ano, id_usuario,
                    item.get("Data"),
                )
                self.lancamento_model.add_lancamento({
                    "ID_Usuario": id_usuario,
                    "ID_Cartao": item.get("ID_Cartao"),
                    "ID_Fatura": ciclo["ID_Fatura"],
                    "Descricao": item.get("Descricao"),
                    "Valor": float(item.get("Valor", 0)),
                    "Data": item.get("Data"),
                    "Competencia_Mes": mes,
                    "Competencia_Ano": ano,
                    "ID_Categoria": item.get("ID_Categoria"),
                    "ID_Favorecido": item.get("ID_Favorecido"),
                    "Num_Parcelas": item.get("Num_Parcelas", 1),
                    "Parcela_Atual": item.get("Parcela_Atual", 1),
                    "Notas": item.get("Notas"),
                    "Previsto": item.get("Previsto", 0),
                    "Tipo_Movimento": tipo,
                    "ID_Lancamento_Origem": item.get("ID_Lancamento_Origem"),
                })
                total += 1

        self._clear_cache()
        return total

    def obter_lancamento(self, id_lancamento, id_usuario):
        return self.lancamento_model.get_lancamento_by_id(id_lancamento, id_usuario)

    def listar_compras_cartao(self, id_cartao, id_usuario):
        if not self.buscar_cartao_por_id(id_cartao, id_usuario):
            raise ValueError("Cartão inválido.")
        return [
            item for item in self.lancamento_model.get_lancamentos_por_cartao(
                id_cartao, id_usuario
            )
            if item.get("Tipo_Movimento", "COMPRA") == "COMPRA"
        ]

    def atualizar_lancamento(self, id_lancamento, dados, id_usuario):
        atual = self.obter_lancamento(id_lancamento, id_usuario)
        if not atual:
            raise ValueError("Lançamento não encontrado.")
        ciclo = self.sincronizar_ciclo(
            atual["ID_Cartao"],
            atual["Competencia_Mes"],
            atual["Competencia_Ano"],
            id_usuario,
        )
        if ciclo["Status"] != "ABERTA":
            raise ValueError(
                "Somente lançamentos de uma fatura aberta podem ser editados."
            )
        if atual.get("Tipo_Movimento", "COMPRA") != "COMPRA":
            raise ValueError(
                "Créditos e pagamentos não podem ser editados como compra."
            )
        payload = dict(atual)
        payload.update(dados)
        payload["ID_Cartao"] = atual["ID_Cartao"]
        resultado = self.lancamento_model.update_lancamento(id_lancamento, payload, id_usuario)
        self._clear_cache()
        return resultado

    def excluir_lancamento(self, id_lancamento, id_usuario):
        atual = self.obter_lancamento(id_lancamento, id_usuario)
        if not atual:
            raise ValueError("Lançamento não encontrado.")
        ciclo = self.sincronizar_ciclo(
            atual["ID_Cartao"],
            atual["Competencia_Mes"],
            atual["Competencia_Ano"],
            id_usuario,
        )
        if ciclo["Status"] != "ABERTA":
            raise ValueError(
                "Somente lançamentos de uma fatura aberta podem ser excluídos."
            )
        if atual.get("Tipo_Movimento") == "PAGAMENTO":
            raise ValueError("O pagamento da fatura não pode ser excluído.")
        resultado = self.lancamento_model.excluir_lancamento(id_lancamento, id_usuario)
        self._clear_cache()
        return resultado

    # ============================================================
    # FATURA
    # ============================================================
    def obter_fatura(self, id_cartao, mes, ano, id_usuario):

        key = self._cache_key(id_cartao, mes, ano, id_usuario)

        cached = self._get_cache(key)
        if cached:
            return cached

        lancamentos = self.lancamento_model.get_lancamentos_por_fatura(
            id_cartao, mes, ano, id_usuario
        )

        for l in lancamentos:
            id_cat = l.get("ID_Categoria")

            if id_cat:
                l["Categoria"] = self.category_model.get_nome_categoria_by_id(
                    id_cat, id_usuario
                )
            else:
                l["Categoria"] = "Sem categoria"

        self._set_cache(key, lancamentos)
        return lancamentos

    def obter_fatura_paginada(self, id_cartao, mes, ano, id_usuario, limit=50, offset=0):

        fatura = self.obter_fatura(id_cartao, mes, ano, id_usuario)

        return {
            "dados": fatura[offset: offset + limit],
            "total": len(fatura)
        }

    # ============================================================
    # TOTAIS
    # ============================================================
    def calcular_total_fatura(self, id_cartao, mes, ano, id_usuario):

        fatura = self.obter_fatura(id_cartao, mes, ano, id_usuario)

        return sum(float(l["Valor"]) for l in fatura)

    def calcular_fatura_mes(self, id_cartao, mes, ano, id_usuario):
        return self.calcular_total_fatura(id_cartao, mes, ano, id_usuario)

    # ============================================================
    # LIMITE
    # ============================================================
    def get_resumo_cartao(self, id_cartao, id_usuario):

        cartao = self.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            return {}

        limite = float(cartao["Limite"])

        lancamentos = self.lancamento_model.get_lancamentos_para_limite(
            id_cartao, id_usuario
        )

        total_movimentos = sum(
            (self._money(l["Valor"]) for l in lancamentos
             if l.get("Tipo_Movimento") != "PAGAMENTO"),
            Decimal("0.00"),
        )
        total_pago = self._money(
            self.pagamento_model.get_total_by_card(id_cartao, id_usuario)
        )
        saldo_devedor = max(total_movimentos - total_pago, Decimal("0.00"))

        return {
            "limite": limite,
            "saldo_devedor": float(saldo_devedor),
            "disponivel": float(self._money(limite) - saldo_devedor)
        }

    def calcular_limite_disponivel(self, id_cartao, id_usuario):
        return self.get_resumo_cartao(id_cartao, id_usuario).get("disponivel", 0.0)

    def verificar_limite(self, id_cartao, id_usuario):

        resumo = self.get_resumo_cartao(id_cartao, id_usuario)

        if not resumo:
            return "OK"

        if resumo["disponivel"] < 0:
            return "ESTOUROU"

        if resumo["disponivel"] < resumo["limite"] * 0.2:
            return "ALERTA"

        return "OK"

    # ============================================================
    # PAGAMENTO
    # ============================================================
    def pagar_fatura(self, id_cartao, mes, ano, id_conta, id_usuario):
        try:
            if not id_usuario:
                raise PermissionError("Usuário não autenticado.")

            with self.transaction_model.unit_of_work(
                self.account_model,
                self.credito_model,
                self.category_model,
                self.lancamento_model,
                self.pagamento_model,
                self.ciclo_model,
                immediate=True
            ):
                cartao = self.credito_model.get_cartao_by_id(
                    id_cartao,
                    id_usuario
                )
                if not cartao:
                    raise PermissionError(
                        "Cartão não pertence ao usuário."
                    )

                conta = self.account_model.get_account_by_id(
                    id_conta,
                    id_usuario
                )
                if not conta:
                    raise PermissionError(
                        "Conta de pagamento não pertence ao usuário."
                    )

                fatura = self.lancamento_model.get_lancamentos_por_fatura(
                    id_cartao,
                    mes,
                    ano,
                    id_usuario
                )
                ciclo = self.sincronizar_ciclo(
                    id_cartao, mes, ano, id_usuario
                )
                if ciclo["Status"] == "ABERTA":
                    raise ValueError(
                        "A fatura precisa estar fechada antes do pagamento."
                    )
                movimentos = [
                    item for item in fatura
                    if item.get("Tipo_Movimento", "COMPRA") != "PAGAMENTO"
                ]
                total_pago = self._money(
                    self.pagamento_model.get_total_by_invoice(
                        ciclo["ID_Fatura"]
                    )
                )

                if ciclo["Status"] == "PAGA" or total_pago > 0:
                    pagamento = self.pagamento_model.get_last_by_invoice(
                        id_cartao,
                        mes,
                        ano,
                        id_usuario
                    )
                    if pagamento:
                        return operation_result(
                            False,
                            "JA_PROCESSADO",
                            "Esta fatura já foi paga.",
                            {"ID_Transacao": pagamento["ID_Transacao"]}
                        )
                    raise ValueError("Esta fatura já foi paga.")

                total_movimentos = sum(
                    (self._money(item["Valor"]) for item in movimentos),
                    Decimal("0.00"),
                )
                total = total_movimentos - total_pago
                if total <= 0:
                    raise ValueError(
                        "O valor da fatura deve ser maior que zero."
                    )

                if self._money(conta["Saldo_Atual"]) < total:
                    raise FaturaSaldoInsuficiente("Saldo insuficiente.")

                chave = self._chave_idempotencia_fatura(
                    id_cartao,
                    mes,
                    ano,
                    id_usuario,
                    movimentos,
                    float(total)
                )

                existente = self.pagamento_model.get_by_key(
                    chave,
                    id_usuario
                )
                if existente:
                    return operation_result(
                        False,
                        "JA_PROCESSADO",
                        "Este pagamento já foi processado.",
                        {"ID_Transacao": existente["ID_Transacao"]}
                    )

                categoria_id = self._get_categoria_pagamento_fatura(
                    id_usuario
                )

                transacao_id = self.transaction_model.add_transaction({
                    "Descricao": (
                        f"Pagamento Fatura {int(mes):02d}/{ano} - "
                        f"{cartao.get('Nome', '')}"
                    ),
                    "Valor": -float(total),
                    "Data": date.today().isoformat(),
                    "Tipo": "Despesa",
                    "ID_Conta": id_conta,
                    "ID_Usuario": id_usuario,
                    "ID_Categoria": categoria_id
                })

                self.account_model.update_saldo(
                    id_conta,
                    -float(total),
                    id_usuario
                )

                for lancamento in movimentos:
                    self.lancamento_model.marcar_como_pago(
                        lancamento["ID_Lancamento"],
                        transacao_id,
                        id_usuario
                    )

                self.pagamento_model.add_payment(
                    chave,
                    id_cartao,
                    ciclo["ID_Fatura"],
                    mes,
                    ano,
                    id_conta,
                    transacao_id,
                    id_usuario,
                    float(total)
                )
                self.ciclo_model.definir_status(
                    id_cartao, mes, ano, id_usuario, "PAGA",
                    date.today().isoformat(),
                )

            self._clear_cache()
            return operation_result(
                True,
                "OK",
                "Fatura paga com sucesso.",
                {
                    "ID_Transacao": transacao_id,
                    "Valor": float(total),
                    "Lancamentos_Pagos": len(movimentos),
                }
            )

        except FaturaSaldoInsuficiente as exc:
            logger.warning("Pagamento recusado por saldo: %s", exc)
            return operation_result(False, "SALDO_INSUFICIENTE", str(exc))

        except PermissionError as exc:
            logger.warning("Pagamento de fatura não autorizado: %s", exc)
            return operation_result(False, "NAO_AUTORIZADO", str(exc))

        except (TypeError, ValueError) as exc:
            logger.warning("Pagamento de fatura recusado: %s", exc)
            return operation_result(False, "DADOS_INVALIDOS", str(exc))

        except DatabaseError:
            logger.exception("Erro de banco no pagamento da fatura")
            return operation_result(
                False,
                "ERRO_BANCO",
                "Não foi possível concluir o pagamento da fatura."
            )

        except Exception:
            logger.exception("Erro no pagamento da fatura")
            return operation_result(
                False,
                "ERRO_INTERNO",
                "Não foi possível concluir o pagamento da fatura."
            )

    def _chave_idempotencia_fatura(
        self,
        id_cartao,
        mes,
        ano,
        id_usuario,
        lancamentos,
        total
    ):
        ids = ",".join(
            str(item["ID_Lancamento"])
            for item in sorted(
                lancamentos,
                key=lambda item: item["ID_Lancamento"]
            )
        )
        base = (
            f"{id_usuario}:{id_cartao}:{int(mes)}:{int(ano)}:"
            f"{ids}:{self._money(total):.2f}"
        )
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    # ============================================================
    # CICLOS
    # ============================================================
    def listar_ciclos(self, id_cartao, id_usuario, quantidade=12):
        cartao = self.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            return []

        hoje = date.today()
        ciclos = []
        for offset in range(quantidade):
            mes_ref = hoje + relativedelta(months=offset)
            ciclos.append({
                "Mes": mes_ref.month,
                "Ano": mes_ref.year,
                "Texto": f"{mes_ref.month:02d}/{mes_ref.year}"
            })

        return ciclos

    def get_painel_cartao(self, id_cartao, mes, ano, id_usuario, page=0, limit=50, status="Todos"):

        cartao = self.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            return {}

        lancamentos_todos = self.lancamento_model.get_lancamentos_por_cartao(
            id_cartao, id_usuario
        )

        fatura_atual = []
        futuras = {}

        for l in lancamentos_todos:
            valor = float(l["Valor"])
            comp_mes = int(l["Competencia_Mes"])
            comp_ano = int(l["Competencia_Ano"])

            if comp_mes == int(mes) and comp_ano == int(ano):
                if l.get("ID_Categoria"):
                    l["Categoria"] = self.category_model.get_nome_categoria_by_id(
                        l["ID_Categoria"],
                        id_usuario
                    )
                else:
                    l["Categoria"] = "Sem categoria"
                fatura_atual.append(l)
            elif (comp_ano, comp_mes) > (int(ano), int(mes)):
                chave = f"{comp_mes:02d}/{comp_ano}"
                futuras.setdefault(chave, 0)
                futuras[chave] += valor

        fatura_completa = list(fatura_atual)
        ciclo = self.sincronizar_ciclo(id_cartao, mes, ano, id_usuario)

        if status == "Abertos":
            if ciclo["Status"] == "PAGA":
                fatura_atual = []
        elif status == "Pagos":
            if ciclo["Status"] != "PAGA":
                fatura_atual = []

        for lancamento in fatura_atual:
            lancamento["Status_Fatura"] = ciclo["Status"]

        total_registros = len(fatura_atual)

        inicio = page * limit
        fim = inicio + limit
        fatura_paginada = fatura_atual[inicio:fim]

        movimentos_validos = [
            l for l in fatura_completa
            if l.get("Tipo_Movimento") != "PAGAMENTO"
        ]
        total_movimentos = sum(
            (self._money(l["Valor"]) for l in movimentos_validos),
            Decimal("0.00"),
        )
        compras = sum(
            (self._money(l["Valor"]) for l in movimentos_validos
             if l.get("Tipo_Movimento", "COMPRA") in {"COMPRA", "ENCARGO"}),
            Decimal("0.00"),
        )
        creditos = sum(
            (self._money(l["Valor"]) for l in movimentos_validos
             if l.get("Tipo_Movimento") == "CREDITO"),
            Decimal("0.00"),
        )
        estornos = sum(
            (self._money(l["Valor"]) for l in movimentos_validos
             if l.get("Tipo_Movimento") == "ESTORNO"),
            Decimal("0.00"),
        )
        ajustes = sum(
            (self._money(l["Valor"]) for l in movimentos_validos
             if l.get("Tipo_Movimento") == "AJUSTE"),
            Decimal("0.00"),
        )
        pagamentos = self._money(
            self.pagamento_model.get_total_by_invoice(ciclo["ID_Fatura"])
        )
        saldo = max(total_movimentos - pagamentos, Decimal("0.00"))
        resumo = self.get_resumo_cartao(id_cartao, id_usuario)

        return {
            "resumo": resumo,
            "fatura": {
                "total": float(total_movimentos),
                "total_fatura": float(total_movimentos),
                "compras": float(compras),
                "creditos": float(creditos),
                "estornos": float(estornos),
                "ajustes": float(ajustes),
                "pagamentos": float(pagamentos),
                "saldo_a_pagar": float(saldo),
                "status": ciclo["Status"],
                "data_fechamento": ciclo["Data_Fechamento"],
                "data_vencimento": ciclo["Data_Vencimento"],
            },
            "futuras": dict(sorted(
                futuras.items(),
                key=lambda item: (int(item[0][3:]), int(item[0][:2])),
            )),
            "lancamentos": fatura_paginada,
            "total_registros": total_registros
        }

    def exportar_fatura_pdf(self, cartao, lancamentos, caminho, mes, ano):
        if not caminho:
            raise ValueError("Caminho do PDF não informado.")

        from utilitarios.financial_pdf import FinancialPDF
        resumo = None
        if cartao and cartao.get("ID_Cartao") and cartao.get("ID_Usuario"):
            resumo = self.get_painel_cartao(
                cartao["ID_Cartao"], mes, ano, cartao["ID_Usuario"]
            ).get("fatura")
        return FinancialPDF.fatura(
            caminho, cartao or {}, lancamentos or [], mes, ano, resumo
        )

    # ============================================================
    # CATEGORIA
    # ============================================================
    def _get_categoria_pagamento_fatura(self, id_usuario):

        categoria = self.category_model.get_category_by_name(
            "Pagamento de Fatura",
            id_usuario
        )

        if categoria:
            return categoria["ID_Categoria"]

        return self.category_model.add_category(
            nome="Pagamento de Fatura",
            tipo="Despesa",
            id_usuario=id_usuario,
            id_categoria_pai=None
        )


    # ============================================
    # FATURAS VIRTUAIS PARA PROJEÇÃO
    # ============================================
    def listar_faturas_projetadas(
        self,
        id_usuario: int,
        quantidade_meses: int = 6,
        data_referencia=None,
    ):
        """Consulta faturas abertas sem criar registros em agendamentos.

        O valor continua vindo de ``calcular_fatura_mes``, a mesma fonte usada
        pelo painel da fatura. ``Decimal`` é mantido durante a normalização para
        não introduzir arredondamento binário nos novos totais de projeção.
        """
        referencia = data_referencia or date.today()
        quantidade_meses = max(1, min(int(quantidade_meses), 60))
        projecoes = []
        # Uma atualização explícita da projeção deve reler o banco, inclusive
        # quando a operação ocorreu em outra instância do painel de faturas.
        self._clear_cache()

        for cartao in self.listar_cartoes(id_usuario) or []:
            id_cartao = cartao["ID_Cartao"]
            nome_cartao = cartao.get("Nome") or "Cartão"
            dia_vencimento = int(cartao.get("Dia_Vencimento") or 1)
            competencias = {
                (
                    (referencia + relativedelta(months=offset)).year,
                    (referencia + relativedelta(months=offset)).month,
                )
                for offset in range(quantidade_meses)
            }
            limite_passado = referencia + relativedelta(months=-120)
            limite_futuro = referencia + relativedelta(months=quantidade_meses - 1)
            for lancamento in self.lancamento_model.get_lancamentos_nao_pagos(
                id_cartao, id_usuario
            ):
                try:
                    mes_lancamento = int(lancamento["Competencia_Mes"])
                    ano_lancamento = int(lancamento["Competencia_Ano"])
                    competencia = date(ano_lancamento, mes_lancamento, 1)
                except (KeyError, TypeError, ValueError):
                    logger.warning("Competência inválida no lançamento %s", lancamento)
                    continue
                if limite_passado.replace(day=1) <= competencia <= limite_futuro.replace(day=1):
                    competencias.add((ano_lancamento, mes_lancamento))

            for ano, mes in sorted(competencias):
                movimentos = self.lancamento_model.get_lancamentos_por_fatura(
                    id_cartao, mes, ano, id_usuario
                )
                total_movimentos = sum(
                    (self._money(item["Valor"]) for item in movimentos
                     if item.get("Tipo_Movimento") != "PAGAMENTO"),
                    Decimal("0.00"),
                )
                pagamento = self.pagamento_model.get_last_by_invoice(
                    id_cartao, mes, ano, id_usuario
                )
                total_pago = self._money(
                    pagamento["Valor"] if pagamento else 0
                )
                valor = max(
                    total_movimentos - total_pago, Decimal("0.00")
                )
                if valor <= Decimal("0.00"):
                    continue

                vencimento = self._data_vencimento(
                    mes, ano, cartao.get("Dia_Fechamento") or 1,
                    dia_vencimento,
                ).isoformat()
                projecoes.append({
                    "tipo_origem": "FATURA_CARTAO",
                    "id_origem": id_cartao,
                    "id_cartao": id_cartao,
                    "ID_Cartao": id_cartao,
                    "competencia_mes": mes,
                    "competencia_ano": ano,
                    "descricao": f"Fatura – {mes:02d}/{ano}",
                    "detalhe": "Fatura cartão de crédito",
                    "nome_cartao": nome_cartao,
                    "data_vencimento": vencimento,
                    "valor": valor,
                    "status": "A_PAGAR",
                })

        return sorted(
            projecoes,
            key=lambda item: (item["data_vencimento"], item["id_cartao"]),
        )

    # Compatibilidade com uma chamada introduzida em versões intermediárias.
    def lista_fatura_projetadas(self, *args, **kwargs):
        return self.listar_faturas_projetadas(*args, **kwargs)
