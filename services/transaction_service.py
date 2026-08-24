# -*- coding: utf-8 -*-
import logging

from core.operation_result import operation_result
from database.database import DatabaseError
from models.transaction_model import TransactionModel
from models.account_model import AccountModel
from services.reconciliacao_importacao_service import (
    ReconciliacaoImportacaoService,
)

logger = logging.getLogger(__name__)


class InsufficientFundsError(ValueError):
    pass


class TransactionService:
    """
    Regras de negócio de transações financeiras.

    Garante:
    - validação de conta/usuário
    - atualização de saldo
    - operações atômicas entre transação e conta
    """

    def __init__(self, db_name=None):
        self.transaction_model = TransactionModel(db_name)
        self.account_model = AccountModel(db_name)
        self.reconciliacao_service = ReconciliacaoImportacaoService()
        self._legacy_account_state = None

    # ============================================================
    # CONEXÃO / TRANSAÇÃO
    # ============================================================
    def _share_connection(self):
        """
        Faz TransactionModel e AccountModel usarem a mesma conexão SQLite.
        Nunca chamar connect() aqui, senão cria outra conexão.
        """
        return self.account_model._bind_connection(
            self.transaction_model.connection
        )

    def _begin(self, immediate=False):
        if self._legacy_account_state is not None:
            raise RuntimeError("Já existe uma transação ativa no serviço.")
        self.transaction_model.begin(immediate=immediate)
        try:
            self._legacy_account_state = self._share_connection()
        except Exception:
            self.transaction_model.rollback()
            raise

    def _restore_legacy_connection(self):
        if self._legacy_account_state is not None:
            self.account_model._restore_connection_state(
                self._legacy_account_state
            )
            self._legacy_account_state = None

    def _commit(self):
        try:
            self.transaction_model.commit()
        finally:
            self._restore_legacy_connection()

    def _rollback(self):
        try:
            self.transaction_model.rollback()
        finally:
            self._restore_legacy_connection()

    # ============================================================
    # HELPERS
    # ============================================================
    def _validar_conta_usuario(self, id_conta, id_usuario):
        if not id_usuario or not id_conta:
            raise ValueError("ID_Usuario e ID_Conta são obrigatórios.")

        conta = self.account_model.get_account_by_id(id_conta, id_usuario)

        if not conta:
            raise PermissionError("Conta não pertence ao usuário.")

        return conta

    def _normalizar_tipo(self, tipo, valor):
        if tipo:
            return tipo

        return "Despesa" if float(valor) < 0 else "Receita"

    def _criar_transacao_base(self, dados: dict, validar_saldo: bool):
        id_usuario = dados.get("ID_Usuario")
        id_conta = dados.get("ID_Conta")

        conta = self._validar_conta_usuario(id_conta, id_usuario)

        valor = float(dados["Valor"])
        dados["Valor"] = valor
        dados["Tipo"] = self._normalizar_tipo(
            dados.get("Tipo"),
            valor
        )

        if validar_saldo and valor < 0:
            saldo_atual = float(conta.get("Saldo_Atual", 0))

            if saldo_atual < abs(valor):
                raise ValueError("Saldo insuficiente.")

        self.transaction_model.add_transaction(dados)

        self.account_model.update_saldo(
            id_conta,
            valor,
            id_usuario
        )

        return True

    # ============================================================
    # CRIAR TRANSAÇÃO MANUAL
    # ============================================================
    def criar_transacao(self, dados: dict):
        self._begin()

        try:
            resultado = self._criar_transacao_base(
                dados,
                validar_saldo=True
            )

            self._commit()
            return resultado

        except Exception:
            self._rollback()
            logger.exception("Erro ao criar transação")
            raise

    # ============================================================
    # CRIAR TRANSAÇÃO IMPORTADA
    # ============================================================
    def criar_transacao_importada(self, dados: dict):
        self._begin()

        try:
            resultado = self._criar_transacao_base(
                dados,
                validar_saldo=False
            )

            self._commit()
            return resultado

        except Exception:
            self._rollback()
            logger.exception("Erro ao criar transação importada")
            raise

    # ============================================================
    # IMPORTAÇÃO EM LOTE
    # ============================================================
    def salvar_lote_importado(self, lista_transacoes: list, id_usuario: int):
        if not lista_transacoes:
            return 0

        total_importadas = 0

        self._begin(immediate=True)

        try:
            reconciliados = []
            contas = {}
            for item in lista_transacoes:
                id_conta = item.get("ID_Conta")
                if id_conta:
                    contas.setdefault(id_conta, []).append(item)

            for id_conta, itens_conta in contas.items():
                self._validar_conta_usuario(id_conta, id_usuario)
                inicio, fim = self.reconciliacao_service.limites_periodo(
                    itens_conta
                )
                existentes = self.transaction_model.get_import_candidates(
                    id_conta, id_usuario, inicio, fim
                )
                normalizados = []
                for original in itens_conta:
                    item = dict(original)
                    item["ID_Usuario"] = id_usuario
                    normalizados.append(item)
                reconciliados.extend(self.reconciliacao_service.reconciliar(
                    normalizados,
                    existentes,
                    ReconciliacaoImportacaoService.DOMINIO_CONTA,
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
                valor = float(item.get("Valor", 0))

                tipo = item.get("Tipo")
                if not tipo:
                    tipo = "Despesa" if valor < 0 else "Receita"

                dados = {
                    "ID_Conta": item.get("ID_Conta"),
                    "Descricao": item.get("Descricao"),
                    "Valor": valor,
                    "Data": item.get("Data"),
                    "Tipo": tipo,
                    "ID_Usuario": id_usuario,
                    "ID_Categoria": item.get("ID_Categoria"),
                    "ID_Favorecido": item.get("ID_Favorecido"),
                }

                if not dados["ID_Conta"] or not dados["Data"]:
                    logger.warning(
                        "Transação importada ignorada por dados obrigatórios ausentes: %s",
                        item
                    )
                    continue

                self._criar_transacao_base(
                    dados,
                    validar_saldo=False
                )

                total_importadas += 1

            self._commit()
            return total_importadas

        except Exception:
            self._rollback()
            logger.exception("Erro ao salvar lote importado")
            raise

    # ============================================================
    # EXCLUIR TRANSAÇÃO
    # ============================================================
    def excluir_transacao(self, id_transacao, id_usuario):
        self._begin()

        try:
            trans = self.transaction_model.get_transaction_by_id(
                id_transacao,
                id_usuario
            )

            if not trans:
                raise ValueError("Transação não encontrada.")

            if trans["ID_Usuario"] != id_usuario:
                raise PermissionError("Transação não pertence ao usuário.")

            valor = float(trans["Valor"])
            id_conta = trans["ID_Conta"]

            self.account_model.update_saldo(
                id_conta,
                -valor,
                id_usuario
            )

            self.transaction_model.delete_transaction(
                id_transacao,
                id_usuario
            )

            self._commit()
            return True

        except Exception:
            self._rollback()
            logger.exception("Erro ao excluir transação")
            raise

    # ============================================================
    # ATUALIZAR TRANSAÇÃO
    # ============================================================
    def atualizar_transacao(self, dados: dict):
        self._begin()

        try:
            id_transacao = dados.get("ID_Transacao")
            id_usuario = dados.get("ID_Usuario")

            trans = self.transaction_model.get_transaction_by_id(
                id_transacao,
                id_usuario
            )

            if not trans:
                raise ValueError("Transação não encontrada.")

            if trans["ID_Usuario"] != id_usuario:
                raise PermissionError("Transação não pertence ao usuário.")

            conta_antiga = trans["ID_Conta"]
            conta_nova = dados.get("ID_Conta", conta_antiga)

            valor_antigo = float(trans["Valor"])
            valor_novo = float(dados["Valor"])

            if conta_nova != conta_antiga:
                self._validar_conta_usuario(conta_nova, id_usuario)

                self.account_model.update_saldo(
                    conta_antiga,
                    -valor_antigo,
                    id_usuario
                )

                self.account_model.update_saldo(
                    conta_nova,
                    valor_novo,
                    id_usuario
                )

            else:
                diferenca = valor_novo - valor_antigo

                if diferenca != 0:
                    self.account_model.update_saldo(
                        conta_antiga,
                        diferenca,
                        id_usuario
                    )

            dados["Tipo"] = self._normalizar_tipo(
                dados.get("Tipo"),
                valor_novo
            )

            self.transaction_model.update_transaction(
                id_transacao,
                dados,
                id_usuario
            )

            self._commit()
            return True

        except Exception:
            self._rollback()
            logger.exception("Erro ao atualizar transação")
            raise

    # ============================================================
    # TRANSFERÊNCIA
    # ============================================================
    def transferir(self, id_origem, id_destino, valor, data, id_usuario):
        try:
            if not id_usuario:
                raise PermissionError("Usuário não autenticado.")

            if id_origem == id_destino:
                raise ValueError("Contas devem ser diferentes.")

            valor = float(valor)
            if valor <= 0:
                raise ValueError("O valor deve ser maior que zero.")

            with self.transaction_model.unit_of_work(
                self.account_model,
                immediate=True
            ):
                origem = self.account_model.get_account_by_id(
                    id_origem,
                    id_usuario
                )

                destino = self.account_model.get_account_by_id(
                    id_destino,
                    id_usuario
                )

                if not origem or not destino:
                    raise PermissionError(
                        "Uma das contas não pertence ao usuário."
                    )

                if float(origem.get("Saldo_Atual", 0)) < valor:
                    raise InsufficientFundsError("Saldo insuficiente.")

                self._registrar_transferencia(
                    id_origem,
                    id_destino,
                    valor,
                    data,
                    id_usuario
                )

            return operation_result(
                True,
                "OK",
                "Transferência realizada com sucesso.",
                {
                    "ID_Conta_Origem": id_origem,
                    "ID_Conta_Destino": id_destino,
                    "Valor": valor,
                }
            )

        except InsufficientFundsError as exc:
            logger.warning(
                "Transferência recusada por saldo insuficiente: %s",
                exc
            )
            return operation_result(False, "SALDO_INSUFICIENTE", str(exc))

        except PermissionError as exc:
            logger.warning("Transferência não autorizada: %s", exc)
            return operation_result(False, "NAO_AUTORIZADO", str(exc))

        except (TypeError, ValueError) as exc:
            logger.warning("Dados inválidos para transferência: %s", exc)
            return operation_result(False, "DADOS_INVALIDOS", str(exc))

        except DatabaseError:
            logger.exception("Erro de banco ao realizar transferência")
            return operation_result(
                False,
                "ERRO_BANCO",
                "Não foi possível concluir a transferência."
            )

        except Exception:
            logger.exception("Erro ao realizar transferência")
            return operation_result(
                False,
                "ERRO_INTERNO",
                "Não foi possível concluir a transferência."
            )

    # ============================================================
    # CONVERTER EM TRANSFERÊNCIA
    # ============================================================
    def converter_em_transferencia(
        self,
        id_transacao,
        id_destino,
        id_usuario
    ):
        self._begin()

        try:
            transacao = self.transaction_model.get_transaction_by_id(
                id_transacao,
                id_usuario
            )

            if not transacao:
                raise ValueError("Transação não encontrada.")

            if transacao["ID_Usuario"] != id_usuario:
                raise PermissionError("Transação não pertence ao usuário.")

            id_origem = transacao["ID_Conta"]
            valor_original = float(transacao["Valor"])
            valor_transferencia = abs(valor_original)
            data = transacao["Data"]

            conta_origem = self.account_model.get_account_by_id(
                id_origem,
                id_usuario
            )

            conta_destino = self.account_model.get_account_by_id(
                id_destino,
                id_usuario
            )

            if not conta_origem or not conta_destino:
                raise ValueError("Conta inválida.")

            self.account_model.update_saldo(
                id_origem,
                -valor_original,
                id_usuario
            )

            self.transaction_model.delete_transaction(
                id_transacao,
                id_usuario
            )

            self._registrar_transferencia(
                id_origem,
                id_destino,
                valor_transferencia,
                data,
                id_usuario
            )

            self._commit()
            return True

        except Exception:
            self._rollback()
            logger.exception("Erro ao converter transação em transferência")
            raise

    def _registrar_transferencia(
        self,
        id_origem,
        id_destino,
        valor,
        data,
        id_usuario
    ):
        data_str = (
            data
            if isinstance(data, str)
            else data.strftime("%Y-%m-%d")
        )


        conta_origem = self.account_model.get_account_by_id(
            id_origem,
            id_usuario
        )

        conta_destino = self.account_model.get_account_by_id(
            id_destino,
            id_usuario
        )

        nome_origem = (
            conta_origem.get("Nome_Conta")
            if conta_origem
            else f"Conta {id_origem}"
        )

        nome_destino = (
            conta_destino.get("Nome_Conta")
            if conta_destino
            else f"Conta {id_destino}"
        )

        self._criar_transacao_base(
            {
                "ID_Conta": id_origem,
                "Descricao": f"Transferência para conta {nome_destino}",
                "Valor": -abs(float(valor)),
                "Data": data_str,
                "Tipo": "Transferência",
                "ID_Usuario": id_usuario,
            },
            validar_saldo=True
        )

        self._criar_transacao_base(
            {
                "ID_Conta": id_destino,
                "Descricao": f"Transferência recebida da conta {nome_origem}",
                "Valor": abs(float(valor)),
                "Data": data_str,
                "Tipo": "Transferência",
                "ID_Usuario": id_usuario,
            },
            validar_saldo=False
        )
    # ============================================================
    # CONSULTAS
    # ============================================================
    def get_transactions_by_account_periodo(
        self,
        id_usuario,
        id_conta,
        periodo
    ):
        conta = self.account_model.get_account_by_id(
            id_conta,
            id_usuario
        )

        if not conta:
            raise PermissionError("Conta inválida.")

        data_inicio, data_fim = periodo

        return self.transaction_model.get_transactions_by_account_periodo(
            id_conta,
            data_inicio,
            data_fim,
            id_usuario
        )

    def get_transaction_by_id(self, id_transacao, id_usuario):
        return self.transaction_model.get_transaction_by_id(
            id_transacao,
            id_usuario
        )

    def get_resumo_financeiro(self, user_id):
        return self.transaction_model.get_resumo_financeiro(user_id)

    def get_analise_mensal(self, user_id):
        return self.transaction_model.get_analise_mensal(user_id)

    def get_extrato_conta_periodo(self, id_usuario, id_conta, periodo):
        conta = self.account_model.get_account_by_id(
            id_conta,
            id_usuario
        )

        if not conta:
            raise PermissionError("Conta inválida.")

        data_inicio, data_fim = periodo

        saldo_inicial = self.transaction_model.get_saldo_antes_periodo(
            id_conta,
            data_inicio,
            id_usuario
        )

        transacoes = self.transaction_model.get_transactions_by_account_periodo(
            id_conta,
            data_inicio,
            data_fim,
            id_usuario
        )

        return {
            "saldo_inicial": saldo_inicial,
            "transacoes": transacoes
        }
