import logging
from datetime import datetime

from core.session import Session
from services.fatura_service import FaturaService
from services.importacao_service import ImportacaoService

logger = logging.getLogger(__name__)


class FaturaController:

    def __init__(self):
        self.service = FaturaService()
        self.import_service = ImportacaoService()

    # ==================================================
    # USUÁRIO
    # ==================================================
    def get_id_usuario(self):
        usuario = Session.get_usuario()
        if not usuario:
            raise PermissionError("Usuário não autenticado.")
        return usuario["ID_Usuario"]

    # ==================================================
    # FATURA (LISTAGEM)
    # ==================================================
    def listar_lancamentos_fatura(self, id_cartao, mes, ano):
        id_usuario = self.get_id_usuario()
        return self.service.obter_fatura(
            id_cartao, mes, ano, id_usuario
        )

    def obter_fatura_paginada(self, id_cartao, mes, ano, limit=50, offset=0):
        id_usuario = self.get_id_usuario()
        return self.service.obter_fatura_paginada(
            id_cartao, mes, ano, id_usuario, limit, offset
        )

    # ==================================================
    # REGISTRAR DESPESA
    # ==================================================
    def registrar_despesa_cartao(self, dados: dict) -> bool:
        id_usuario = self.get_id_usuario()
        payload = dict(dados)
        payload["ID_Usuario"] = id_usuario
        return self.service.registrar_despesa_cartao(payload)

    def importar_arquivo_fatura(
        self,
        caminho_arquivo,
        id_cartao,
        progress_callback=None,
    ):
        id_usuario = self.get_id_usuario()
        cartao = self.service.buscar_cartao_por_id(id_cartao, id_usuario)
        if not cartao:
            raise PermissionError("Cartão não pertence ao usuário.")
        return self.import_service.importar_fatura(
            caminho_arquivo=caminho_arquivo,
            id_usuario=id_usuario,
            id_cartao=id_cartao,
            dia_fechamento=cartao["Dia_Fechamento"],
            resolver_competencia=self.service.aplicar_fatura,
            progress_callback=progress_callback,
        )

    def salvar_lancamentos_importados(self, lista_lancamentos):
        return self.service.salvar_lote_importado(
            lista_lancamentos, self.get_id_usuario()
        )

    # ==================================================
    # PAGAMENTO
    # ==================================================
    def pagar_fatura(self, id_cartao, id_conta, mes, ano) -> dict:
        id_usuario = self.get_id_usuario()
        return self.service.pagar_fatura(
            id_cartao, mes, ano, id_conta, id_usuario
        )

    # ==================================================
    # LIMITE
    # ==================================================
    def obter_limite_disponivel(self, id_cartao):
        id_usuario = self.get_id_usuario()
        return self.service.calcular_limite_disponivel(
            id_cartao, id_usuario
        )

    # ==================================================
    # CARTÕES
    # ==================================================
    def listar_cartoes(self):
        return self.service.listar_cartoes(
            self.get_id_usuario()
        )

    def criar_cartao(self, dados: dict):
        """
        Cria um novo cartão de crédito.
        """
        dados_formatados = { 
            "Nome": dados.get("nome"),
            "Limite": dados.get("limite"),
            "Dia_Fechamento": dados.get("dia_fechamento"),
            "Dia_Vencimento": dados.get("dia_vencimento"),
            "Ativo": dados.get("ativo", 1)
        }

        return self.service.criar_cartao(
            dados_formatados,
            self.get_id_usuario()
        )

    def editar_cartao(self, id_cartao, dados: dict):
        """
        Edita um cartão de crédito existente.
        """
        dados_formatados = {
            "Nome": dados.get("nome"),
            "Limite": dados.get("limite"),
            "Dia_Fechamento": dados.get("dia_fechamento"),
            "Dia_Vencimento": dados.get("dia_vencimento"),
            "Ativo": dados.get("ativo", 1)
        }

        return self.service.editar_cartao(
            id_cartao,
            dados_formatados,
            self.get_id_usuario()
        )

    def buscar_cartao_por_id(self, id_cartao):
        return self.service.buscar_cartao_por_id(
            id_cartao,
            self.get_id_usuario()
        )

    def excluir_cartao(self, id_cartao):
        return self.service.excluir_cartao(
            id_cartao,
            self.get_id_usuario()
        )

    def get_all_cartoes(self):
        return self.listar_cartoes()

    # ==================================================
    # EXPORTAÇÃO
    # ==================================================
    def exportar_fatura_pdf(self, cartao, lancamentos, caminho):
        return self.service.exportar_fatura_pdf(
            cartao,
            lancamentos,
            caminho
        )

    # ==================================================
    # VALORES
    # ==================================================
    def obter_valor_fatura_atual(self, id_cartao):
        id_usuario = self.get_id_usuario()

        hoje = datetime.today()

        return self.service.calcular_fatura_mes(
            id_cartao,
            hoje.month,
            hoje.year,
            id_usuario
        )

    def obter_fatura_mes(self, id_cartao, mes, ano):
        return self.listar_lancamentos_fatura(
            id_cartao,
            mes,
            ano
        )

    def listar_ciclos(self, id_cartao, quantidade=12):
        return self.service.listar_ciclos(
            id_cartao,
            self.get_id_usuario(),
            quantidade
        )


    def get_painel_cartao(self, id_cartao, mes, ano, page, limit, status):

        id_usuario = self.get_id_usuario()

        return self.service.get_painel_cartao(
            id_cartao=id_cartao,
            mes=mes,
            ano=ano,
            id_usuario=id_usuario,
            page=page,
            limit=limit,
            status=status
        )


    def listar_faturas_projetadas(self, quantidade_meses=6):
        return self.service.listar_faturas_projetadas(
            self.get_id_usuario(),
            quantidade_meses
        )

   
