from models.relatorio_model import RelatorioModel
from utilitarios.name_format import NameFormat
from utilitarios.currency_formatter import CurrencyFormatter
from services.user_services import UserService


class RelatorioService:
    CAMPOS_FISCAIS = (
        'Rendimentos_Tributaveis', 'Previdencia_Oficial',
        'Previdencia_Complementar', 'Pensao_Alimenticia', 'IRRF',
        'Parcela_Isenta_65', 'Diarias_Ajudas_Custo',
        'Pensao_Molestia_Grave', 'Lucros_Dividendos',
        'Valores_Empresario', 'Indenizacoes', 'Isentos_Outros',
        'Decimo_Terceiro', 'IRRF_Decimo_Terceiro', 'Exclusivos_Outros',
        'RRA_Rendimentos', 'RRA_Previdencia_Oficial',
        'RRA_Pensao_Alimenticia', 'RRA_IRRF', 'RRA_Despesas_Judiciais',
    )
    def __init__(self):
        self.model = RelatorioModel()
        self.usuario = UserService()

    # ============================================================
    # RELATÓRIO DIÁRIO
    # ============================================================
    def relatorio_diario(self, dias, id_usuario):
        if dias is not None and (not isinstance(dias, int) or dias <= 0):
            raise ValueError("O período deve ser maior que zero.")
        return self.model.get_relatorio_diario(dias, id_usuario)

    def resumo_relatorio_diario(self, dias, id_usuario):
        """Entrega dados e totais prontos; a View apenas apresenta o resultado."""
        dados = self.relatorio_diario(dias, id_usuario)
        receitas = sum(float(item.get("Receita", 0) or 0) for item in dados)
        despesas = sum(float(item.get("Despesa", 0) or 0) for item in dados)
        return {
            "dados": dados,
            "receitas": receitas,
            "despesas": despesas,
            "saldo": receitas - despesas,
        }

    def anos_disponiveis(self, id_usuario):
        return self.model.get_anos_disponiveis(id_usuario)

    # ============================================================
    # RELATÓRIO ANUAL
    # ============================================================
    def relatorio_anual(self, ano, id_usuario):
        if not str(ano).isdigit():
            raise ValueError("Ano inválido.")
        return self.model.get_relatorio_anual(ano, id_usuario)

    # ============================================================
    # INFORME DE RENDIMENTOS (RF)
    # ============================================================
    def informe_rendimentos(self, ano, id_usuario):
        receitas = self.model.get_informe_rendimentos(ano, id_usuario)
        gastos = self.model.get_informe_gastos(ano, id_usuario)

        return {
            "ano": ano,
            "receitas": receitas if receitas else [],
            "gastos": gastos if gastos else []
        }

    def informes_fiscais(self, ano, id_usuario):
        if not str(ano).isdigit():
            raise ValueError("Ano-calendário inválido.")
        return self.model.get_informes_fiscais(int(ano), id_usuario)

    def salvar_informe_fiscal(self, dados, id_usuario):
        dados = dict(dados or {})
        documento = NameFormat.somente_numeros(dados.get('Fonte_Documento'))
        if not NameFormat.documento_valido(documento):
            raise ValueError("Informe um CPF ou CNPJ válido da fonte pagadora.")
        for campo in ('Fonte_Nome', 'Natureza_Rendimento'):
            dados[campo] = str(dados.get(campo) or '').strip()
            if not dados[campo]:
                raise ValueError("Nome da fonte e natureza do rendimento são obrigatórios.")
        ano = int(dados.get('Ano_Calendario', 0))
        if not 1900 <= ano <= 9999:
            raise ValueError("Ano-calendário inválido.")
        dados['Ano_Calendario'] = ano
        dados['Fonte_Documento'] = documento
        dados['RRA_Meses'] = int(dados.get('RRA_Meses', 0) or 0)
        if dados['RRA_Meses'] < 0:
            raise ValueError("A quantidade de meses de RRA não pode ser negativa.")
        dados['RRA_Tributacao'] = str(
            dados.get('RRA_Tributacao') or 'EXCLUSIVA'
        ).upper()
        if dados['RRA_Tributacao'] not in ('EXCLUSIVA', 'AJUSTE_ANUAL'):
            raise ValueError("Forma de tributação de RRA inválida.")
        for campo in self.CAMPOS_FISCAIS:
            valor = round(float(dados.get(campo, 0) or 0), 2)
            if valor < 0:
                raise ValueError("Valores fiscais não podem ser negativos.")
            dados[campo] = valor
        dados['Informacoes_Complementares'] = str(
            dados.get('Informacoes_Complementares') or ''
        ).strip()
        return self.model.salvar_informe_fiscal(dados, id_usuario)

    def gerar_comprovante_fiscal(self, id_usuario, ano, id_informe=None):
        usuario = self.usuario.get_user_by_id(id_usuario)
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        if not NameFormat.documento_valido(usuario.get('CPF')) or len(
            NameFormat.somente_numeros(usuario.get('CPF'))
        ) != 11:
            raise ValueError("Cadastre um CPF válido no perfil do beneficiário.")
        registros = self.informes_fiscais(ano, id_usuario)
        if id_informe is not None:
            registros = [r for r in registros if r['ID_Informe'] == id_informe]
        if len(registros) != 1:
            raise ValueError("Selecione uma fonte pagadora com dados fiscais cadastrados.")
        d = registros[0]
        moeda = lambda campo: CurrencyFormatter.format(d.get(campo, 0))
        return f"""COMPROVANTE DE RENDIMENTOS PAGOS E DE IMPOSTO SOBRE A RENDA RETIDO NA FONTE
Ano-calendário de {ano}                                      Exercício de {int(ano) + 1}

1. FONTE PAGADORA PESSOA JURÍDICA OU PESSOA FÍSICA
CNPJ/CPF: {NameFormat.format_documento(d['Fonte_Documento'])}
Nome empresarial/Nome completo: {d['Fonte_Nome']}

2. PESSOA FÍSICA BENEFICIÁRIA DOS RENDIMENTOS
CPF: {NameFormat.formatCPF(usuario.get('CPF', ''))}
Nome completo: {usuario.get('Nome', '')}
Natureza do rendimento: {d['Natureza_Rendimento']}

3. RENDIMENTOS TRIBUTÁVEIS, DEDUÇÕES E IRRF — VALORES EM REAIS
1. Total dos rendimentos (inclusive férias): {moeda('Rendimentos_Tributaveis')}
2. Contribuição previdenciária oficial: {moeda('Previdencia_Oficial')}
3. Contribuição a entidades de previdência complementar: {moeda('Previdencia_Complementar')}
4. Pensão alimentícia: {moeda('Pensao_Alimenticia')}
5. Imposto sobre a renda retido na fonte: {moeda('IRRF')}

4. RENDIMENTOS ISENTOS E NÃO TRIBUTÁVEIS
1. Parcela isenta de aposentadoria/pensão (65 anos ou mais): {moeda('Parcela_Isenta_65')}
2. Diárias e ajudas de custo: {moeda('Diarias_Ajudas_Custo')}
3. Pensão e proventos por moléstia grave: {moeda('Pensao_Molestia_Grave')}
4. Lucros e dividendos: {moeda('Lucros_Dividendos')}
5. Valores pagos ao titular/sócio de ME ou EPP, exceto pró-labore: {moeda('Valores_Empresario')}
6. Indenizações por rescisão, inclusive PDV, e acidente de trabalho: {moeda('Indenizacoes')}
7. Outros: {moeda('Isentos_Outros')}

5. RENDIMENTOS SUJEITOS À TRIBUTAÇÃO EXCLUSIVA
1. Décimo terceiro salário: {moeda('Decimo_Terceiro')}
2. IRRF sobre décimo terceiro salário: {moeda('IRRF_Decimo_Terceiro')}
3. Outros: {moeda('Exclusivos_Outros')}

6. RENDIMENTOS RECEBIDOS ACUMULADAMENTE — ART. 12-A DA LEI Nº 7.713/1988
1. Número de meses: {d.get('RRA_Meses', 0)}
2. Forma de tributação: {'Exclusiva na fonte' if d.get('RRA_Tributacao') == 'EXCLUSIVA' else 'Ajuste anual'}
3. Rendimentos tributáveis: {moeda('RRA_Rendimentos')}
4. Contribuição previdenciária oficial: {moeda('RRA_Previdencia_Oficial')}
5. Pensão alimentícia: {moeda('RRA_Pensao_Alimenticia')}
6. Imposto sobre a renda retido na fonte: {moeda('RRA_IRRF')}
7. Despesas com ação judicial: {moeda('RRA_Despesas_Judiciais')}

7. INFORMAÇÕES COMPLEMENTARES
{d.get('Informacoes_Complementares') or 'Sem informações complementares.'}

Dados transcritos pelo usuário a partir do comprovante da fonte pagadora.
Confira os valores com o documento original antes de declarar."""

    # ============================================================
    # GERA TEXTO FORMATADO PARA PDF
    # ============================================================
    def gerar_texto_informe(self, id_usuario, ano):
        # ---------------------------
        #  Resolve ID do usuário
        # ---------------------------

        usuarios = self.usuario.get_user_by_id(id_usuario)

        if not usuarios:
            raise ValueError("Usuário não encontrado.")

        nome = usuarios.get("Nome", "")
        cpf = usuarios.get("CPF", "")

        dados = self.informe_rendimentos(ano, id_usuario)

        # ---------------------------
        #  Cabeçalho
        # ---------------------------
        texto = f"""
INFORME DE RENDIMENTOS - ANO BASE {ano}

IDENTIFICAÇÃO DO CONTRIBUINTE:
Nome: {nome}
CPF: {NameFormat.formatCPF(cpf)}

Relatório auxiliar das transações de contas registradas no sistema.
Não substitui informes oficiais. Não classifica tributação ou dedutibilidade.
Transferências internas e faturas/agendamentos ainda não pagos não são somados.

RECEITAS REGISTRADAS:
"""

        # ---------------------------
        #  Receitas
        # ---------------------------
        for item in dados["receitas"]:
            fonte = item.get("Fonte", "N/D")
            cnpj = NameFormat.format_documento(item.get("Documento") or "") or "Não informado"
            valor = CurrencyFormatter.format(item.get("Valor", 0))

            texto += f"""
Fonte Pagadora: {fonte}
Documento: {cnpj}
Valor Total Recebido: {valor}
"""

        # ---------------------------
        #  Gastos
        # ---------------------------
        texto += """
DESPESAS REGISTRADAS:
"""

        for item in dados["gastos"]:
            fav = item.get("Fonte", "N/D")
            doc_formatado = NameFormat.format_documento(item.get("Documento") or "") or "Não informado"
            valor = CurrencyFormatter.format(item.get("Valor", 0),)

            texto += f"""
Favorecido: {fav}
Documento: {doc_formatado}
Total Pago: {valor}
"""

        receita = sum(float(item['Valor'] or 0) for item in dados['receitas'])
        despesa = sum(float(item['Valor'] or 0) for item in dados['gastos'])
        if not dados['receitas'] and not dados['gastos']:
            texto += '\nNenhuma transação encontrada para o ano selecionado.\n'
        texto += f'\nTotal de receitas: {CurrencyFormatter.format(receita)}'
        texto += f'\nTotal de despesas: {CurrencyFormatter.format(despesa)}'
        texto += f'\nResultado: {CurrencyFormatter.format(receita - despesa)}'
        return texto.strip()
