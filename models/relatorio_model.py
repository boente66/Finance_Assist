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
