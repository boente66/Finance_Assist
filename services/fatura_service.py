import hashlib
import calendar
import logging
from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from models.lancamento_model import LancamentoModel
from models.credito_model import CreditoModel
from models.transaction_model import TransactionModel
from models.category_model import CategoryModel
from models.account_model import AccountModel
from models.pagamento_fatura_model import PagamentoFaturaModel
from core.operation_result import operation_result
from database.database import DatabaseError
from services.reconciliacao_importacao_service import (
    ReconciliacaoImportacaoService,
)


logger = logging.getLogger(__name__)


class FaturaSaldoInsuficiente(ValueError):
    pass


class FaturaService:

    def __init__(self, db_name=None):
        self.lancamento_model = LancamentoModel(db_name)
        self.credito_model = CreditoModel(db_name)
        self.transaction_model = TransactionModel(db_name)
        self.category_model = CategoryModel(db_name)
        self.account_model = AccountModel(db_name)
        self.pagamento_model = PagamentoFaturaModel(db_name)
        self.reconciliacao_service = ReconciliacaoImportacaoService()

        self._cache_fatura = {}

    # ============================================================
    # CACHE
    # ============================================================
    def _cache_key(self, id_cartao, mes, ano, id_usuario):
        return f"{id_cartao}_{mes}_{ano}_{id_usuario}"

    def _get_cache(self, key):
        return self._cache_fatura.get(key)

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
        valor_total = float(dados["Valor"])
        valor_parcela = round(valor_total / parcelas, 2)

        data_base = dados["Data"]

        if isinstance(data_base, str):
            data_base = datetime.fromisoformat(data_base).date()

        self.lancamento_model.begin()

        try:
            for i in range(parcelas):

                data_parcela = data_base + relativedelta(months=i)

                mes, ano = self.aplicar_fatura(
                    data_parcela,
                    dia_fechamento
                )

                self.lancamento_model.add_lancamento({
                    "ID_Usuario": id_usuario,
                    "ID_Cartao": id_cartao,
                    "Descricao": dados["Descricao"],
                    "Valor": valor_parcela,
                    "Data": data_parcela.isoformat(),
                    "Competencia_Mes": mes,
                    "Competencia_Ano": ano,
                    "ID_Categoria": dados.get("ID_Categoria"),
                    "ID_Favorecido": dados.get("ID_Favorecido"),
                    "Num_Parcelas": parcelas,
                    "Parcela_Atual": i + 1,
                    "Notas": dados.get("Notas"),
                    "Previsto": int(dados.get("Previsto", 0))
                })

            self.lancamento_model.commit()
            self._clear_cache()
            return True

        except Exception:
            self.lancamento_model.rollback()
            raise

    def salvar_lote_importado(self, lista_lancamentos, id_usuario):
        """Persiste apenas compras novas após revalidação atômica."""
        if not lista_lancamentos:
            return 0

        total = 0
        with self.lancamento_model.unit_of_work(
            self.credito_model,
            self.lancamento_model.credito,
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
                self.lancamento_model.add_lancamento({
                    "ID_Usuario": id_usuario,
                    "ID_Cartao": item.get("ID_Cartao"),
                    "Descricao": item.get("Descricao"),
                    "Valor": abs(float(item.get("Valor", 0))),
                    "Data": item.get("Data"),
                    "Competencia_Mes": item.get("Competencia_Mes"),
                    "Competencia_Ano": item.get("Competencia_Ano"),
                    "ID_Categoria": item.get("ID_Categoria"),
                    "ID_Favorecido": item.get("ID_Favorecido"),
                    "Num_Parcelas": item.get("Num_Parcelas", 1),
                    "Parcela_Atual": item.get("Parcela_Atual", 1),
                    "Notas": item.get("Notas"),
                    "Previsto": item.get("Previsto", 0),
                })
                total += 1

        self._clear_cache()
        return total

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

        return sum(float(l["Valor"]) for l in fatura if not l.get("Paga"))

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

        lancamentos = self.lancamento_model.get_lancamentos_nao_pagos(
            id_cartao, id_usuario
        )

        saldo_devedor = sum(float(l["Valor"]) for l in lancamentos)

        return {
            "limite": limite,
            "saldo_devedor": saldo_devedor,
            "disponivel": limite - saldo_devedor
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
                abertos = [item for item in fatura if not item.get("Paga")]

                if not abertos:
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
                    raise ValueError("Nenhum valor em aberto.")

                total = sum(float(item["Valor"]) for item in abertos)
                if total <= 0:
                    raise ValueError(
                        "O valor da fatura deve ser maior que zero."
                    )

                if float(conta["Saldo_Atual"]) < total:
                    raise FaturaSaldoInsuficiente("Saldo insuficiente.")

                chave = self._chave_idempotencia_fatura(
                    id_cartao,
                    mes,
                    ano,
                    id_usuario,
                    abertos,
                    total
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
                    "Valor": -abs(total),
                    "Data": date.today().isoformat(),
                    "Tipo": "Despesa",
                    "ID_Conta": id_conta,
                    "ID_Usuario": id_usuario,
                    "ID_Categoria": categoria_id
                })

                self.account_model.update_saldo(
                    id_conta,
                    -abs(total),
                    id_usuario
                )

                for lancamento in abertos:
                    self.lancamento_model.marcar_como_pago(
                        lancamento["ID_Lancamento"],
                        transacao_id,
                        id_usuario
                    )

                self.pagamento_model.add_payment(
                    chave,
                    id_cartao,
                    mes,
                    ano,
                    id_conta,
                    transacao_id,
                    id_usuario,
                    total
                )

            self._clear_cache()
            return operation_result(
                True,
                "OK",
                "Fatura paga com sucesso.",
                {
                    "ID_Transacao": transacao_id,
                    "Valor": total,
                    "Lancamentos_Pagos": len(abertos),
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
            f"{ids}:{total:.2f}"
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
            else:
                chave = f"{comp_mes:02d}/{comp_ano}"
                futuras.setdefault(chave, 0)
                futuras[chave] += valor

        if status == "Abertos":
            fatura_atual = [l for l in fatura_atual if not l.get("Paga")]
        elif status == "Pagos":
            fatura_atual = [l for l in fatura_atual if l.get("Paga")]

        total_registros = len(fatura_atual)

        inicio = page * limit
        fim = inicio + limit
        fatura_paginada = fatura_atual[inicio:fim]

        total = sum(float(l["Valor"]) for l in fatura_atual)
        abertos = sum(float(l["Valor"]) for l in fatura_atual if not l.get("Paga"))
        pagos = total - abertos

        resumo = self.get_resumo_cartao(id_cartao, id_usuario)

        return {
            "resumo": resumo,
            "fatura": {
                "total": total,
                "abertos": abertos,
                "pagos": pagos
            },
            "futuras": dict(sorted(futuras.items())),
            "lancamentos": fatura_paginada,
            "total_registros": total_registros
        }

    def exportar_fatura_pdf(self, cartao, lancamentos, caminho):
        if not caminho:
            raise ValueError("Caminho do PDF não informado.")

        from utilitarios.makepdf import MakePDF

        nome_cartao = (cartao or {}).get("Nome", "Cartão")
        linhas = [f"Cartão: {nome_cartao}", ""]

        total = 0.0
        for item in lancamentos or []:
            valor = float(item.get("Valor") or 0)
            total += valor
            data = item.get("Data", "")
            descricao = item.get("Descricao", "")
            categoria = item.get("Categoria", "Sem categoria")
            status = "Pago" if item.get("Paga") else "Aberto"

            linhas.append(
                f"{data} | {descricao} | {categoria} | R$ {valor:.2f} | {status}"
            )

        linhas.extend(["", f"Total: R$ {total:.2f}"])
        return MakePDF.gerar_pdf(
            caminho,
            f"Fatura - {nome_cartao}",
            "\n".join(linhas)
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
                valor = Decimal(str(self.calcular_fatura_mes(
                    id_cartao, mes, ano, id_usuario
                ))).quantize(Decimal("0.01"))
                if valor <= Decimal("0.00"):
                    continue

                ultimo_dia = calendar.monthrange(ano, mes)[1]
                vencimento = date(ano, mes, min(dia_vencimento, ultimo_dia))
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
                    "data_vencimento": vencimento.isoformat(),
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
