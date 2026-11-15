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

    def adicionar_credito_fatura(self, dados: dict) -> bool:
        payload = dict(dados)
        payload["ID_Usuario"] = self.get_id_usuario()
        return self.service.adicionar_credito_fatura(payload)

    def listar_compras_cartao(self, id_cartao):
        return self.service.listar_compras_cartao(
            id_cartao, self.get_id_usuario()
        )

    def importar_arquivo_fatura(
        self,
        caminho_arquivo,
        id_cartao,
        progress_callback=None,
        senha_pdf=None,
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
            senha_pdf=senha_pdf,
        )

    def salvar_lancamentos_importados(self, lista_lancamentos):
        return self.service.salvar_lote_importado(
            lista_lancamentos, self.get_id_usuario()
        )

    # ==================================================
    # PAGAMENTO
    # ==================================================
    def pagar_fatura(
        self, id_cartao, id_conta, mes, ano, valor=None
    ) -> dict:
        id_usuario = self.get_id_usuario()
        return self.service.pagar_fatura(
            id_cartao, mes, ano, id_conta, id_usuario, valor
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
    def listar_cartoes(self, incluir_inativos=False):
        return self.service.listar_cartoes(
            self.get_id_usuario(), incluir_inativos
        )

    def listar_bandeiras(self):
        return self.service.listar_bandeiras()

    def criar_cartao(self, dados: dict):
        """
        Cria um novo cartão de crédito.
        """
        dados_formatados = { 
            "Nome": dados.get("nome"),
            "Bandeira": dados.get("bandeira"),
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
        # Omissão preserva o valor atual; None explícito remove a bandeira.
        campos = {
            "nome": "Nome", "bandeira": "Bandeira", "limite": "Limite",
            "dia_fechamento": "Dia_Fechamento", "dia_vencimento": "Dia_Vencimento",
            "ativo": "Ativo",
        }
        dados_formatados = {destino: dados[origem] for origem, destino in campos.items()
                            if origem in dados}

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

    def reativar_cartao(self, id_cartao):
        return self.service.reativar_cartao(id_cartao, self.get_id_usuario())

    def dependencias_cartao(self, id_cartao):
        return self.service.dependencias_cartao(id_cartao, self.get_id_usuario())

    def excluir_cartao_definitivamente(self, id_cartao):
        return self.service.excluir_cartao_definitivamente(id_cartao, self.get_id_usuario())

    def get_all_cartoes(self):
        return self.listar_cartoes()

    # ==================================================
    # EXPORTAÇÃO
    # ==================================================
    def exportar_fatura_pdf(self, cartao, lancamentos, caminho, mes, ano):
        return self.service.exportar_fatura_pdf(
            cartao, lancamentos, caminho, mes, ano
        )

    def obter_lancamento(self, id_lancamento):
        return self.service.obter_lancamento(id_lancamento, self.get_id_usuario())

    def atualizar_lancamento(self, id_lancamento, dados):
        return self.service.atualizar_lancamento(
            id_lancamento, dados, self.get_id_usuario()
        )

    def excluir_lancamento(self, id_lancamento):
        return self.service.excluir_lancamento(id_lancamento, self.get_id_usuario())

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

    def obter_resumo_fatura(self, id_cartao, mes, ano):
        painel = self.service.get_painel_cartao(
            id_cartao=id_cartao,
            mes=mes,
            ano=ano,
            id_usuario=self.get_id_usuario(),
            page=0,
            limit=1,
            status="Todos",
        )
        return (painel or {}).get("fatura", {})


    def listar_faturas_projetadas(self, quantidade_meses=6):
        return self.service.listar_faturas_projetadas(
            self.get_id_usuario(),
            quantidade_meses
        )

   
