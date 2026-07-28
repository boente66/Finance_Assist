# backup/backup_model.py

import os
import json
import uuid
from datetime import datetime

from database.database import Database
from utilitarios.crypto_util import encrypt_bytes, decrypt_bytes


class BackupModel:
    """
    Backup lógico (.kp)
    - NÃO copia o .db
    - extrai dados das tabelas
    - criptografa
    - restaura via INSERT
    """

    BACKUP_TABLES = (
        "usuarios",
        "categorias",
        "contas",
        "credito",
        "favorecido",
        "pessoa_fisica",
        "pessoa_juridica",
        "metas",
        "agendamentos",
        "transacoes",
        "lancamentos",
        "pagamentos_fatura",
    )

    RESTORE_ORDER = (
        "usuarios",
        "recuperacao_senha",
        "categorias",
        "contas",
        "credito",
        "favorecido",
        "pessoa_fisica",
        "pessoa_juridica",
        "metas",
        "agendamentos",
        "transacoes",
        "lancamentos",
        "pagamentos_fatura",
    )

    DELETE_ORDER = tuple(reversed(RESTORE_ORDER))

    def __init__(self, database_path: str):
        self.database_path = database_path
        self.db = Database(database_path)

    # =====================================================
    # EXTRAÇÃO DE DADOS
    # =====================================================
    def _extrair_dados(self):

        dados = {}

        for tabela in self.BACKUP_TABLES:
            dados[tabela] = self.db.fetch_all(f"SELECT * FROM {tabela}")

        return dados

    # =====================================================
    # BACKUP (.kp)
    # =====================================================
    def criar_backup(
        self,
        destino: str,
        senha: str,
        prefixo: str = "backup"
    ) -> str:

        if not os.path.isdir(destino):
            raise FileNotFoundError("Pasta de destino inválida.")

        if not senha:
            raise ValueError("Senha obrigatória.")

        # 1️⃣ extrair dados
        dados = self._extrair_dados()

        # 2️⃣ converter para JSON
        json_bytes = json.dumps(dados, ensure_ascii=False).encode("utf-8")

        # 3️⃣ criptografar
        criptografado = encrypt_bytes(json_bytes, senha)

        # 4️⃣ montar estrutura final
        estrutura = {
            "meta": {
                "version": 1,
                "tipo": "kp_logico",
                "data": datetime.now().isoformat()
            },
            "payload": criptografado
        }

        # 5️⃣ salvar arquivo
        instante = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        sufixo = uuid.uuid4().hex[:12]
        nome = f"{prefixo}_{instante}_{sufixo}.kp"
        caminho = os.path.join(destino, nome)

        with open(caminho, "x", encoding="utf-8") as f:
            json.dump(estrutura, f)

        return caminho

    # =====================================================
    # RESTAURAÇÃO (.kp)
    # =====================================================
    def restaurar_backup(self, arquivo: str, senha: str):

        if not os.path.isfile(arquivo):
            raise FileNotFoundError("Backup não encontrado.")

        with open(arquivo, "r", encoding="utf-8") as f:
            estrutura = json.load(f)

        # valida estrutura
        if "payload" not in estrutura:
            raise ValueError("Backup inválido.")

        try:
            # 1️⃣ descriptografar
            json_bytes = decrypt_bytes(estrutura["payload"], senha)

        except Exception:
            raise Exception("Senha inválida ou backup corrompido.")

        # 2️⃣ carregar dados
        dados = json.loads(json_bytes.decode("utf-8"))

        if not isinstance(dados, dict):
            raise ValueError("Conteúdo do backup inválido.")

        desconhecidas = set(dados) - set(self.RESTORE_ORDER)
        if desconhecidas:
            raise ValueError(
                "Backup contém tabelas não reconhecidas: "
                f"{sorted(desconhecidas)}"
            )

        # A ordem explícita respeita as dependências. FKs permanecem ativas;
        # o adiamento cobre referências próprias e permite validação integral
        # antes do único commit.
        conn = self.db.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("PRAGMA defer_foreign_keys = ON")
            cursor = conn.cursor()

            for tabela in self.DELETE_ORDER:
                cursor.execute(f"DELETE FROM {tabela}")

            for tabela in self.RESTORE_ORDER:
                registros = dados.get(tabela, [])
                for row in registros:
                    if not isinstance(row, dict) or not row:
                        raise ValueError(
                            f"Registro inválido na tabela {tabela}."
                        )
                    colunas = ", ".join(row.keys())
                    placeholders = ", ".join(["?"] * len(row))

                    cursor.execute(
                        f"INSERT INTO {tabela} ({colunas}) VALUES ({placeholders})",
                        tuple(row.values())
                    )

            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise ValueError(
                    "Backup produziria violações de integridade: "
                    f"{[tuple(row) for row in violations]}"
                )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

        return True

    # =====================================================
    # VALIDAR
    # =====================================================
    def validar_backup(self, arquivo: str, senha: str) -> bool:

        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                estrutura = json.load(f)

            decrypt_bytes(estrutura.get("payload"), senha)
            return True

        except Exception:
            return False

    # =====================================================
    # LISTAR
    # =====================================================
    def listar_backups(self, diretorio: str):

        if not os.path.isdir(diretorio):
            return []

        backups = []

        for f in os.listdir(diretorio):
            if f.endswith(".kp"):
                caminho = os.path.join(diretorio, f)

                backups.append({
                    "nome": f,
                    "caminho": caminho,
                    "tamanho": os.path.getsize(caminho),
                    "data": datetime.fromtimestamp(
                        os.path.getmtime(caminho)
                    ).strftime("%d/%m/%Y %H:%M")
                })

        return backups

    # =====================================================
    # EXCLUIR
    # =====================================================
    def excluir_backup(self, arquivo: str):

        if not os.path.exists(arquivo):
            raise FileNotFoundError("Arquivo não encontrado.")

        os.remove(arquivo)
