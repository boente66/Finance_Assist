from database.database import Database, DatabaseError


class FavorecidoModel(Database):

    # =========================================================
    # UTIL
    # =========================================================
    def _somente_numeros(self, valor):
        if not valor:
            return None
        return "".join(filter(str.isdigit, str(valor)))

    # =========================================================
    # LISTAR
    # =========================================================
    def get_all_favorecidos(self, id_usuario):
        return self.fetch_all("""
            SELECT 
                f.ID_Favorecido,
                f.Nome,
                f.Tipo,

                COALESCE(pf.Telefone, pj.Telefone) AS Telefone,

                pf.CPF,
                pj.CNPJ,
                pj.Razao_Social,

                COALESCE(pf.CPF, pj.CNPJ) AS Documento

            FROM favorecido f

            LEFT JOIN pessoa_fisica pf 
                ON pf.ID_Favorecido = f.ID_Favorecido

            LEFT JOIN pessoa_juridica pj 
                ON pj.ID_Favorecido = f.ID_Favorecido

            WHERE f.ID_Usuario = ?
            ORDER BY f.Nome ASC
        """, (id_usuario,))

    # =========================================================
    # OBTER POR ID
    # =========================================================
    def get_favorecido_by_id(self, id_favorecido, id_usuario):
        return self.fetch_one("""
            SELECT 
                f.ID_Favorecido,
                f.Nome,
                f.Tipo,

                COALESCE(pf.Telefone, pj.Telefone) AS Telefone,

                pf.CPF,
                pj.CNPJ,
                pj.Razao_Social,

                COALESCE(pf.CPF, pj.CNPJ) AS Documento

            FROM favorecido f

            LEFT JOIN pessoa_fisica pf 
                ON pf.ID_Favorecido = f.ID_Favorecido

            LEFT JOIN pessoa_juridica pj 
                ON pj.ID_Favorecido = f.ID_Favorecido

            WHERE f.ID_Favorecido = ? 
              AND f.ID_Usuario = ?
        """, (id_favorecido, id_usuario))

    # =========================================================
    # BUSCAR POR NOME
    # =========================================================
    def get_favorecido_by_name(self, nome, id_usuario):
        return self.fetch_one("""
            SELECT ID_Favorecido, Nome
            FROM favorecido
            WHERE Nome = ? AND ID_Usuario = ?
        """, (nome, id_usuario))

    # =========================================================
    # BUSCAR POR CPF
    # =========================================================
    def get_favorecido_by_cpf(self, cpf, id_usuario):
        cpf = self._somente_numeros(cpf)
        return self.fetch_one("""
            SELECT f.ID_Favorecido, f.Nome
            FROM favorecido f
            INNER JOIN pessoa_fisica pf 
                ON pf.ID_Favorecido = f.ID_Favorecido
            WHERE pf.CPF = ? AND f.ID_Usuario = ?
        """, (cpf, id_usuario))

    # =========================================================
    # BUSCAR POR CNPJ
    # =========================================================
    def get_favorecido_by_cnpj(self, cnpj, id_usuario):
        cnpj = self._somente_numeros(cnpj)
        return self.fetch_one("""
            SELECT f.ID_Favorecido, f.Nome
            FROM favorecido f
            INNER JOIN pessoa_juridica pj 
                ON pj.ID_Favorecido = f.ID_Favorecido
            WHERE pj.CNPJ = ? AND f.ID_Usuario = ?
        """, (cnpj, id_usuario))

    # =========================================================
    # OBTER TIPO
    # =========================================================
    def get_tipo(self, id_favorecido, id_usuario):
        row = self.fetch_one("""
            SELECT Tipo
            FROM favorecido
            WHERE ID_Favorecido = ? AND ID_Usuario = ?
        """, (id_favorecido, id_usuario))

        return row["Tipo"] if row else None

    # =========================================================
    # INSERIR
    # =========================================================
    def add_favorecido(self, dados, id_usuario):
        nome = (dados.get("Nome") or "").strip()
        cpf = self._somente_numeros(dados.get("CPF"))
        cnpj = self._somente_numeros(dados.get("CNPJ"))
        telefone = self._somente_numeros(dados.get("Telefone"))  # 🔥 CORRIGIDO

        if cpf and not cnpj:
            tipo = "PF"
        elif cnpj and not cpf:
            tipo = "PJ"
        else:
            tipo = (dados.get("Tipo") or "").strip().upper()

        if not nome:
            raise ValueError("Nome é obrigatório.")

        if tipo not in ("PF", "PJ"):
            raise ValueError("Tipo inválido. Informe CPF ou CNPJ corretamente.")

        if tipo == "PF" and not cpf:
            raise ValueError("CPF é obrigatório para Pessoa Física.")

        if tipo == "PJ" and not cnpj:
            raise ValueError("CNPJ é obrigatório para Pessoa Jurídica.")
        if cpf and cnpj:
            raise ValueError('Informe apenas CPF ou CNPJ, conforme o tipo.')
        if tipo == 'PF' and len(cpf) != 11:
            raise ValueError('CPF deve conter 11 dígitos.')
        if tipo == 'PJ' and len(cnpj) != 14:
            raise ValueError('CNPJ deve conter 14 dígitos.')

        try:
            self.begin(immediate=True)
            existente = (self.get_favorecido_by_cpf(cpf, id_usuario) if tipo == 'PF'
                         else self.get_favorecido_by_cnpj(cnpj, id_usuario))
            if existente:
                self.commit()
                return existente['ID_Favorecido']

            self.execute_query("""
                INSERT INTO favorecido (Nome, Tipo, ID_Usuario)
                VALUES (?, ?, ?)
            """, (
                nome,
                tipo,
                id_usuario
            ))

            row = self.fetch_one("SELECT last_insert_rowid() AS id")
            id_favorecido = row["id"]

            if tipo == "PF":
                self.execute_query("""
                    INSERT INTO pessoa_fisica (ID_Favorecido, CPF, Telefone)
                    VALUES (?, ?, ?)
                """, (
                    id_favorecido,
                    cpf,
                    telefone
                ))
            else:
                self.execute_query("""
                    INSERT INTO pessoa_juridica (ID_Favorecido, CNPJ, Razao_Social, Telefone)
                    VALUES (?, ?, ?, ?)
                """, (
                    id_favorecido,
                    cnpj,
                    dados.get("Razao_Social"),
                    telefone
                ))

            self.commit()
            return id_favorecido

        except Exception as e:
            self.rollback()
            raise DatabaseError(str(e))

    # =========================================================
    # ATUALIZAR
    # =========================================================
    def update_favorecido(self, id_favorecido, dados, id_usuario):
        tipo = self.get_tipo(id_favorecido, id_usuario)
        if not tipo:
            raise ValueError("Favorecido não encontrado.")

        cpf = self._somente_numeros(dados.get("CPF"))
        cnpj = self._somente_numeros(dados.get("CNPJ"))
        telefone = self._somente_numeros(dados.get("Telefone"))
        if dados.get('Tipo', tipo) != tipo or (tipo == 'PF' and cnpj) or (tipo == 'PJ' and cpf):
            raise ValueError('O documento deve corresponder ao tipo do favorecido.')
        if 'CPF' in dados and tipo == 'PF' and len(cpf or '') != 11:
            raise ValueError('CPF deve conter 11 dígitos.')
        if 'CNPJ' in dados and tipo == 'PJ' and len(cnpj or '') != 14:
            raise ValueError('CNPJ deve conter 14 dígitos.')
        if 'Nome' in dados and not (dados['Nome'] or '').strip():
            raise ValueError('Nome é obrigatório.')

        try:
            self.begin()

            self.execute_query("""
                UPDATE favorecido
                SET Nome = COALESCE(?, Nome)
                WHERE ID_Favorecido = ? AND ID_Usuario = ?
            """, (
                dados.get("Nome"),
                id_favorecido,
                id_usuario
            ))

            if tipo == "PF":
                self.execute_query("""
                    UPDATE pessoa_fisica
                    SET 
                        CPF = COALESCE(?, CPF),
                        Telefone = COALESCE(?, Telefone)
                    WHERE ID_Favorecido = ?
                """, (
                    cpf,
                    telefone,
                    id_favorecido
                ))

            elif tipo == "PJ":
                self.execute_query("""
                    UPDATE pessoa_juridica
                    SET 
                        CNPJ = COALESCE(?, CNPJ),
                        Razao_Social = COALESCE(?, Razao_Social),
                        Telefone = COALESCE(?, Telefone)
                    WHERE ID_Favorecido = ?
                """, (
                    cnpj,
                    dados.get("Razao_Social"),
                    telefone,
                    id_favorecido
                ))

            self.commit()
            return True, "Favorecido atualizado."

        except Exception as e:
            self.rollback()
            raise DatabaseError(str(e))

    # =========================================================
    # DELETE
    # =========================================================
    def delete_favorecido(self, id_favorecido, id_usuario):
        try:
            self.begin()

            self.execute_query("""
                DELETE FROM pessoa_fisica
                WHERE ID_Favorecido = ?
            """, (id_favorecido,))

            self.execute_query("""
                DELETE FROM pessoa_juridica
                WHERE ID_Favorecido = ?
            """, (id_favorecido,))

            self.execute_query("""
                DELETE FROM favorecido
                WHERE ID_Favorecido = ? AND ID_Usuario = ?
            """, (id_favorecido, id_usuario))

            self.commit()
            return True

        except Exception as e:
            self.rollback()
            raise DatabaseError(str(e))
