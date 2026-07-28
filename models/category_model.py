import logging
from database.database import Database, DatabaseError

logger = logging.getLogger(__name__)


class CategoryModel(Database):

    def __init__(self, db_name=None):
        super().__init__(db_name) if db_name else super().__init__()

    # ==================================================
    # CREATE
    # ==================================================

    def add_category(self, nome, tipo, id_usuario, id_categoria_pai=None):

        query = """
        INSERT INTO categorias
        (Nome, Tipo, ID_Usuario, ID_Categoria_Pai)
        VALUES (?, ?, ?, ?)
        """

        return self.execute_insert(
            query,
            (nome, tipo, id_usuario, id_categoria_pai)
        )

    # ==================================================
    # READ
    # ==================================================

    def get_all_categories(self, id_usuario):

        query = """
        SELECT *
        FROM categorias
        WHERE ID_Usuario = ?
        ORDER BY Nome
        """

        return self.fetch_all(query, (id_usuario,))

    def get_category_by_id(self, id_categoria, id_usuario):

        query = """
        SELECT ID_Categoria, Nome, Tipo, ID_Categoria_Pai
        FROM categorias
        WHERE ID_Categoria = ?
        AND ID_Usuario = ?
        """

        return self.fetch_one(query, (id_categoria, id_usuario))

    def get_category_by_name(self, nome, id_usuario):

        query = """
        SELECT ID_Categoria, Nome, Tipo
        FROM categorias
        WHERE Nome = ?
        AND ID_Usuario = ?
        """

        return self.fetch_one(query, (nome, id_usuario))

    # ==================================================
    # UPDATE
    # ==================================================

    def update_category(self, id_categoria, nome, tipo, id_usuario):

        query = """
        UPDATE categorias
        SET Nome = ?, Tipo = ?
        WHERE ID_Categoria = ?
        AND ID_Usuario = ?
        """

        self.execute_query(query, (nome, tipo, id_categoria, id_usuario))
        return True

    # ==================================================
    # SUBCATEGORIAS (CORRETO)
    # ==================================================

    def get_subcategories(self, id_categoria_pai, id_usuario):

        query = """
        SELECT *
        FROM categorias
        WHERE ID_Categoria_Pai = ?
        AND ID_Usuario = ?
        ORDER BY Nome
        """

        return self.fetch_all(query, (id_categoria_pai, id_usuario))

    def add_subcategory(self, nome, tipo, id_categoria_pai, id_usuario):
        """
        Subcategoria é apenas categoria com pai
        """

        return self.add_category(
            nome=nome,
            tipo=tipo,
            id_usuario=id_usuario,
            id_categoria_pai=id_categoria_pai
        )

    # ==================================================
    # DELETE
    # ==================================================

    def delete_category(self, id_categoria, id_usuario):

        # 🔹 Verificar filhos
        filhos = self.fetch_one("""
            SELECT COUNT(*) as total
            FROM categorias
            WHERE ID_Categoria_Pai = ?
            AND ID_Usuario = ?
        """, (id_categoria, id_usuario))

        if filhos and filhos["total"] > 0:
            return False, "Categoria possui subcategorias."

        # 🔹 Verificar uso em transações
        trans = self.fetch_one("""
            SELECT COUNT(*) as total
            FROM transacoes
            WHERE ID_Categoria = ?
            AND ID_Usuario = ?
        """, (id_categoria, id_usuario))

        if trans and trans["total"] > 0:
            return False, "Categoria em uso."

        # 🔹 Verificar uso em lançamentos de cartão
        lanc = self.fetch_one("""
            SELECT COUNT(*) as total
            FROM lancamentos
            WHERE ID_Categoria = ?
            AND ID_Usuario = ?
        """, (id_categoria, id_usuario))

        if lanc and lanc["total"] > 0:
            return False, "Categoria usada em lançamentos."

        # 🔹 Excluir
        self.execute_query("""
            DELETE FROM categorias
            WHERE ID_Categoria = ?
            AND ID_Usuario = ?
        """, (id_categoria, id_usuario))

        return True, None

    # ==================================================
    # UTIL
    # ==================================================

    def get_nome_categoria_by_id(self, id_categoria, id_usuario):
        """
        ⚠️ Fallback apenas (não usar em massa)
        """

        try:
            categoria = self.fetch_one("""
                SELECT Nome
                FROM categorias
                WHERE ID_Categoria = ?
                AND ID_Usuario = ?
            """, (id_categoria, id_usuario))

            return categoria["Nome"] if categoria else "Sem categoria"

        except DatabaseError as e:
            logger.error(f"Erro categoria: {e}")
            return "Sem categoria"

    # ==================================================
    # JOIN (🔥 SOLUÇÃO CERTA)
    # ==================================================

    def map_categorias(self, lancamentos, id_usuario):
        """
        Resolve categorias em lote (evita N+1)
        """

        ids = list({l.get("ID_Categoria") for l in lancamentos if l.get("ID_Categoria")})

        if not ids:
            return lancamentos

        placeholders = ",".join("?" for _ in ids)

        categorias = self.fetch_all(f"""
            SELECT ID_Categoria, Nome
            FROM categorias
            WHERE ID_Categoria IN ({placeholders})
            AND ID_Usuario = ?
        """, (*ids, id_usuario))

        mapa = {c["ID_Categoria"]: c["Nome"] for c in categorias}

        for l in lancamentos:
            l["Categoria"] = mapa.get(l.get("ID_Categoria"), "Sem categoria")

        return lancamentos
