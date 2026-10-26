import logging
from datetime import date
from models.account_model import AccountModel
from database.database import DatabaseError
from models.transaction_model import TransactionModel

logger = logging.getLogger(__name__)


class AccountService:
    """
    Serviço responsável pela lógica de negócio de contas.
    """

    TIPOS_VALIDOS = ["Corrente", "Poupança", "Investimento"]

    def __init__(self, db_name=None):
        self.model = AccountModel(db_name)
        self.transaction_model = TransactionModel(db_name)

    def _registrar_ajuste(self, conta, novo_saldo, id_usuario):
        saldo_atual = self._parse_saldo(conta["Saldo_Atual"])
        diferenca = round(novo_saldo - saldo_atual, 2)
        if diferenca == 0:
            return False
        self.transaction_model.add_transaction({
            "ID_Conta": conta["ID_Conta"],
            "Tipo": "Receita" if diferenca > 0 else "Despesa",
            "Descricao": "Ajuste de saldo",
            "Valor": diferenca,
            "Data": date.today().isoformat(),
            "ID_Categoria": None,
            "ID_Favorecido": None,
            "Notas": (
                f"Saldo ajustado de {saldo_atual:.2f} para {novo_saldo:.2f}."
            ),
            "ID_Usuario": id_usuario,
            "ID_Agendamento": None,
        })
        return diferenca

    # --------------------------------------------------
    # UTIL
    # --------------------------------------------------
    def _parse_saldo(self, valor):
        try:
            return round(float(str(valor).replace(",", ".")), 2)
        except ValueError:
            raise ValueError("Saldo inválido")

    def _validar_tipo(self, tipo):
        tipo = str(tipo).strip().title()
        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError(f"Tipo inválido: {tipo}")
        return tipo

    # --------------------------------------------------
    # LISTAR
    # --------------------------------------------------
    def listar_contas(self, id_usuario):
        if not id_usuario:
            raise ValueError("Usuário inválido")

        try:
            return self.model.get_accounts_by_user(id_usuario)
        except DatabaseError as e:
            logger.exception("Erro ao listar contas")
            raise RuntimeError("Erro ao listar contas") from e

    # --------------------------------------------------
    # BUSCAR
    # --------------------------------------------------
    def buscar_por_id(self, id_conta, id_usuario):
        if not id_conta or not id_usuario:
            raise ValueError("Parâmetros inválidos")

        try:
            return self.model.get_account_by_id(id_conta, id_usuario)
        except DatabaseError as e:
            logger.exception("Erro ao buscar conta por ID")
            raise RuntimeError("Erro ao buscar conta") from e

    def buscar_por_nome(self, nome, id_usuario):
        if not nome or not id_usuario:
            raise ValueError("Parâmetros inválidos")

        try:
            return self.model.get_account_by_name(nome.strip(), id_usuario)
        except DatabaseError as e:
            logger.exception("Erro ao buscar conta por nome")
            raise RuntimeError("Erro ao buscar conta") from e

    # --------------------------------------------------
    # CRIAR
    # --------------------------------------------------
    def criar_conta(self, dados):

        obrigatorios = ["Nome_Conta", "Tipo", "Saldo_Atual", "ID_Usuario"]
        for campo in obrigatorios:
            if campo not in dados or dados[campo] in (None, ""):
                raise ValueError(f"Campo obrigatório ausente: {campo}")

        nome = str(dados["Nome_Conta"]).strip()
        instituicao = str(dados.get("Instituicao", "")).strip()
        tipo = self._validar_tipo(dados["Tipo"])
        id_usuario = int(dados["ID_Usuario"])

        saldo = self._parse_saldo(dados["Saldo_Atual"])

        if saldo < 0:
            raise ValueError("Saldo inicial não pode ser negativo")

        # evitar duplicidade
        if self.model.get_account_by_name(nome, id_usuario):
            raise ValueError("Já existe uma conta com esse nome")

        try:
            return self.model.add_account(
                nome=nome,
                instituicao=instituicao,
                tipo=tipo,
                saldo=saldo,
                id_usuario=id_usuario
            )
        except DatabaseError as e:
            logger.exception("Erro ao criar conta")
            raise RuntimeError("Erro ao salvar conta") from e

    # --------------------------------------------------
    # ATUALIZAR
    # --------------------------------------------------
    def atualizar_conta(self, id_conta, dados, id_usuario):

        conta = self.buscar_por_id(id_conta, id_usuario)
        if not conta:
            raise PermissionError("Conta não encontrada")

        nome = str(dados.get("Nome_Conta", conta["Nome_Conta"])).strip()
        instituicao = str(dados.get("Instituicao", conta["Instituicao"])).strip()
        tipo = self._validar_tipo(dados.get("Tipo", conta["Tipo"]))

        saldo = self._parse_saldo(
            dados.get("Saldo_Atual", conta["Saldo_Atual"])
        )

        if saldo < 0:
            raise ValueError("Saldo não pode ser negativo")

        # evitar duplicidade (CORREÇÃO IMPORTANTE)
        existente = self.model.get_account_by_name(nome, id_usuario)
        if existente and existente["ID_Conta"] != id_conta:
            raise ValueError("Já existe uma conta com esse nome")

        try:
            with self.model.unit_of_work(
                self.transaction_model, immediate=True
            ):
                self._registrar_ajuste(conta, saldo, id_usuario)
                self.model.update_account(
                    id_conta=id_conta,
                    nome=nome,
                    instituicao=instituicao,
                    tipo=tipo,
                    saldo=saldo,
                    id_usuario=id_usuario
                )
            return True

        except DatabaseError as e:
            logger.exception("Erro ao atualizar conta")
            raise RuntimeError("Erro ao atualizar conta") from e

    # --------------------------------------------------
    # AJUSTE DE SALDO
    # --------------------------------------------------
    def ajustar_saldo(self, id_conta, novo_saldo, id_usuario):

        if id_conta is None:
            raise ValueError("Conta inválida")

        saldo = self._parse_saldo(novo_saldo)

        if saldo < 0:
            raise ValueError("Saldo não pode ser negativo")

        conta = self.buscar_por_id(id_conta, id_usuario)
        if not conta:
            raise PermissionError("Conta não pertence ao usuário")

        try:
            with self.model.unit_of_work(
                self.transaction_model, immediate=True
            ):
                diferenca = self._registrar_ajuste(
                    conta, saldo, id_usuario
                )
                if diferenca:
                    self.model.update_saldo(
                        id_conta, diferenca, id_usuario
                    )
            return True

        except DatabaseError as e:
            logger.exception("Erro ao ajustar saldo")
            raise RuntimeError("Erro ao ajustar saldo") from e

    def atualizar_saldo(self, id_conta, novo_saldo, id_usuario):
        return self.ajustar_saldo(id_conta, novo_saldo, id_usuario)

    # --------------------------------------------------
    # EXCLUIR
    # --------------------------------------------------
    def deletar_conta(self, id_conta, id_usuario):

        conta = self.buscar_por_id(id_conta, id_usuario)
        if not conta:
            raise PermissionError("Conta não encontrada")

        try:
            self.model.delete_account(id_conta, id_usuario)
            return True

        except DatabaseError as e:
            logger.exception("Erro ao deletar conta")
            raise RuntimeError("Erro ao excluir conta") from e
        
    # =================================
    # ATUALIZAR SALDO
    # =================================
    
    def atualiza_saldo(self,id_conta,id_usuario):
        saldo = self.transaction_model.get_account_saldo(id_conta, id_usuario)

        valor = float(saldo.get("Saldo_Atual", 0))

        self.model.definir_saldo(
            id_conta=id_conta,
            valor=valor,
            id_usuario=id_usuario
        )
    
    # =================================
    # OBTER SALDO 
    # =================================

    def obter_saldo(self, id_conta, id_usuario):
        saldo = self.transaction_model.get_account_saldo(id_conta, id_usuario)
        return float(saldo.get("Saldo_Atual", 0))
