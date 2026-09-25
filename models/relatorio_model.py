from datetime import date, timedelta
from database.database import Database


class RelatorioModel(Database):
    """Consultas de leitura; erros não são confundidos com ausência de dados."""

    DATA_SQL = """CASE WHEN length(t.Data) = 10 AND substr(t.Data, 3, 1) = '/'
        AND substr(t.Data, 6, 1) = '/'
        THEN date(substr(t.Data, 7, 4) || '-' || substr(t.Data, 4, 2) || '-' || substr(t.Data, 1, 2))
        ELSE date(t.Data) END"""
    MOVIMENTOS = "COALESCE(t.Tipo, '') <> 'Transferência'"

    def get_anos_disponiveis(self, id_usuario):
        rows = self.fetch_all(f"""SELECT DISTINCT strftime('%Y', {self.DATA_SQL}) AS Ano
            FROM transacoes t WHERE t.ID_Usuario = ? ORDER BY Ano DESC""", (id_usuario,))
        return [int(row['Ano']) for row in rows if row['Ano']]

    def get_relatorio_diario(self, dias, id_usuario):
        params = [id_usuario]
        periodo = ''
        if dias is not None:
            hoje = date.today()
            periodo = f'AND {self.DATA_SQL} BETWEEN ? AND ?'
            params.extend(((hoje - timedelta(days=dias - 1)).isoformat(), hoje.isoformat()))
        return self.fetch_all(f"""
            SELECT {self.DATA_SQL} AS Data, COALESCE(c.Nome, 'Sem categoria') AS Categoria,
                SUM(CASE WHEN t.Valor > 0 THEN t.Valor ELSE 0 END) AS Receita,
                SUM(CASE WHEN t.Valor < 0 THEN ABS(t.Valor) ELSE 0 END) AS Despesa,
                SUM(t.Valor) AS Economia
            FROM transacoes t LEFT JOIN categorias c ON c.ID_Categoria = t.ID_Categoria
                AND c.ID_Usuario = t.ID_Usuario
            WHERE t.ID_Usuario = ? AND {self.MOVIMENTOS} {periodo}
            GROUP BY {self.DATA_SQL}, c.Nome ORDER BY Data
        """, params)

    def get_relatorio_anual(self, ano, id_usuario):
        return self.fetch_all(f"""
            SELECT strftime('%m', {self.DATA_SQL}) AS Mes,
                COALESCE(c.Nome, 'Sem categoria') AS Categoria,
                SUM(CASE WHEN t.Valor > 0 THEN t.Valor ELSE 0 END) AS Receita,
                SUM(CASE WHEN t.Valor < 0 THEN ABS(t.Valor) ELSE 0 END) AS Despesa,
                SUM(t.Valor) AS Economia
            FROM transacoes t LEFT JOIN categorias c ON c.ID_Categoria = t.ID_Categoria
                AND c.ID_Usuario = t.ID_Usuario
            WHERE strftime('%Y', {self.DATA_SQL}) = ? AND t.ID_Usuario = ? AND {self.MOVIMENTOS}
            GROUP BY Mes, c.Nome ORDER BY Mes, Categoria
        """, (str(ano), id_usuario))

    def get_transacoes_ano(self, ano, id_usuario):
        return self.fetch_all(f"""SELECT t.* FROM transacoes t
            WHERE strftime('%Y', {self.DATA_SQL}) = ? AND t.ID_Usuario = ?
            ORDER BY {self.DATA_SQL}, t.ID_Transacao""", (str(ano), id_usuario))

    def _informe(self, ano, id_usuario, receitas):
        operador = '>' if receitas else '<'
        return self.fetch_all(f"""
            SELECT COALESCE(f.Nome, 'Não informado') AS Fonte,
                pj.CNPJ AS CNPJ, COALESCE(pj.CNPJ, pf.CPF, '') AS Documento,
                f.Tipo AS Tipo_Favorecido, SUM(ABS(t.Valor)) AS Valor
            FROM transacoes t
            LEFT JOIN favorecido f ON t.ID_Favorecido = f.ID_Favorecido
                AND f.ID_Usuario = t.ID_Usuario
            LEFT JOIN pessoa_juridica pj ON pj.ID_Favorecido = f.ID_Favorecido
            LEFT JOIN pessoa_fisica pf ON pf.ID_Favorecido = f.ID_Favorecido
            WHERE strftime('%Y', {self.DATA_SQL}) = ? AND t.Valor {operador} 0
                AND t.ID_Usuario = ? AND {self.MOVIMENTOS}
            GROUP BY f.ID_Favorecido, f.Nome, pj.CNPJ, pf.CPF, f.Tipo ORDER BY Fonte
        """, (str(ano), id_usuario))

    def get_informe_rendimentos(self, ano, id_usuario):
        return self._informe(ano, id_usuario, True)

    def get_informe_gastos(self, ano, id_usuario):
        return self._informe(ano, id_usuario, False)

    def get_informes_fiscais(self, ano, id_usuario):
        return self.fetch_all("""
            SELECT * FROM informes_fiscais
            WHERE Ano_Calendario = ? AND ID_Usuario = ?
            ORDER BY Fonte_Nome, ID_Informe
        """, (int(ano), id_usuario))

    def salvar_informe_fiscal(self, dados, id_usuario):
        campos = (
            'Ano_Calendario', 'Fonte_Nome', 'Fonte_Documento',
            'Natureza_Rendimento', 'Rendimentos_Tributaveis',
            'Previdencia_Oficial', 'Previdencia_Complementar',
            'Pensao_Alimenticia', 'IRRF', 'Parcela_Isenta_65',
            'Diarias_Ajudas_Custo', 'Pensao_Molestia_Grave',
            'Lucros_Dividendos', 'Valores_Empresario', 'Indenizacoes',
            'Isentos_Outros', 'Decimo_Terceiro',
            'IRRF_Decimo_Terceiro', 'Exclusivos_Outros',
            'RRA_Meses', 'RRA_Tributacao', 'RRA_Rendimentos', 'RRA_Previdencia_Oficial',
            'RRA_Pensao_Alimenticia', 'RRA_IRRF', 'RRA_Despesas_Judiciais',
            'Informacoes_Complementares',
        )
        valores = [dados[campo] for campo in campos]
        self.execute_query(f"""
            INSERT INTO informes_fiscais (ID_Usuario, {', '.join(campos)})
            VALUES (?, {', '.join('?' for _ in campos)})
            ON CONFLICT(ID_Usuario, Ano_Calendario, Fonte_Documento)
            DO UPDATE SET
                Fonte_Nome=excluded.Fonte_Nome,
                Natureza_Rendimento=excluded.Natureza_Rendimento,
                Rendimentos_Tributaveis=excluded.Rendimentos_Tributaveis,
                Previdencia_Oficial=excluded.Previdencia_Oficial,
                Previdencia_Complementar=excluded.Previdencia_Complementar,
                Pensao_Alimenticia=excluded.Pensao_Alimenticia,
                IRRF=excluded.IRRF,
                Parcela_Isenta_65=excluded.Parcela_Isenta_65,
                Diarias_Ajudas_Custo=excluded.Diarias_Ajudas_Custo,
                Pensao_Molestia_Grave=excluded.Pensao_Molestia_Grave,
                Lucros_Dividendos=excluded.Lucros_Dividendos,
                Valores_Empresario=excluded.Valores_Empresario,
                Indenizacoes=excluded.Indenizacoes,
                Isentos_Outros=excluded.Isentos_Outros,
                Decimo_Terceiro=excluded.Decimo_Terceiro,
                IRRF_Decimo_Terceiro=excluded.IRRF_Decimo_Terceiro,
                Exclusivos_Outros=excluded.Exclusivos_Outros,
                RRA_Meses=excluded.RRA_Meses,
                RRA_Tributacao=excluded.RRA_Tributacao,
                RRA_Rendimentos=excluded.RRA_Rendimentos,
                RRA_Previdencia_Oficial=excluded.RRA_Previdencia_Oficial,
                RRA_Pensao_Alimenticia=excluded.RRA_Pensao_Alimenticia,
                RRA_IRRF=excluded.RRA_IRRF,
                RRA_Despesas_Judiciais=excluded.RRA_Despesas_Judiciais,
                Informacoes_Complementares=excluded.Informacoes_Complementares,
                Atualizado_Em=CURRENT_TIMESTAMP
        """, [id_usuario, *valores])
        return self.fetch_one("""
            SELECT * FROM informes_fiscais
            WHERE ID_Usuario=? AND Ano_Calendario=? AND Fonte_Documento=?
        """, (id_usuario, dados['Ano_Calendario'], dados['Fonte_Documento']))
