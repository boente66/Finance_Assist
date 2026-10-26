from models.favorecido_model import FavorecidoModel
from services.document_validator import DocumentValidator


class FavorecidoService:
    def __init__(self):
        self.model = FavorecidoModel()

    # ---------------------------------------------------------
    # UTIL
    # ---------------------------------------------------------
    def _somente_numeros(self, valor):
        return DocumentValidator.somente_numeros(valor)

    def _validar_documento(self, tipo, valor):
        if tipo == "PF":
            return DocumentValidator.validar_cpf(valor)
        if tipo == "PJ":
            return DocumentValidator.validar_cnpj(valor)
        raise ValueError("Tipo inválido. Informe CPF ou CNPJ corretamente.")

    # ---------------------------------------------------------
    # LISTAR
    # ---------------------------------------------------------
    def listar(self, id_usuario):
        return self.model.get_all_favorecidos(id_usuario)

    # ---------------------------------------------------------
    # OBTER
    # ---------------------------------------------------------
    def obter(self, id_favorecido, id_usuario):
        fav = self.model.get_favorecido_by_id(id_favorecido, id_usuario)
        if not fav:
            raise ValueError("Favorecido não encontrado.")
        return fav

    # ---------------------------------------------------------
    # CRIAR
    # ---------------------------------------------------------
    def criar(self, dados, id_usuario):
        nome = (dados.get("Nome") or "").strip()

        cpf = self._somente_numeros(dados.get("CPF"))
        cnpj = self._somente_numeros(dados.get("CNPJ"))

        if cpf and cnpj:
            raise ValueError('Informe apenas CPF ou CNPJ, conforme o tipo.')

        # 🔥 inferência automática (mais robusto)
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

        # 🔐 validação + duplicidade
        if tipo == "PF":
            if not cpf:
                raise ValueError("CPF é obrigatório para Pessoa Física.")
            cpf = self._validar_documento(tipo, cpf)

            existente = self.model.get_favorecido_by_cpf(cpf, id_usuario)
            if existente:
                return existente["ID_Favorecido"]

        else:
            if not cnpj:
                raise ValueError("CNPJ é obrigatório para Pessoa Jurídica.")
            cnpj = self._validar_documento(tipo, cnpj)

            existente = self.model.get_favorecido_by_cnpj(cnpj, id_usuario)
            if existente:
                return existente["ID_Favorecido"]

        payload = {
            "Nome": nome,
            "Tipo": tipo,
            "Telefone": dados.get("Telefone")
        }

        if tipo == "PF":
            payload["CPF"] = cpf
        else:
            payload["CNPJ"] = cnpj
            payload["Razao_Social"] = dados.get("Razao_Social") or nome

        # 🔥 ponto crítico: garantir retorno direto
        return self.model.add_favorecido(payload, id_usuario)

    # ---------------------------------------------------------
    # ATUALIZAR
    # ---------------------------------------------------------
    def atualizar(self, id_favorecido, dados, id_usuario):
        fav = self.model.get_favorecido_by_id(id_favorecido, id_usuario)
        if not fav:
            raise ValueError("Favorecido não encontrado.")

        tipo = fav["Tipo"]

        cpf = self._somente_numeros(dados.get("CPF"))
        cnpj = self._somente_numeros(dados.get("CNPJ"))

        documento_informado = "CPF" in dados if tipo == "PF" else "CNPJ" in dados
        documento_atual = fav.get("CPF" if tipo == "PF" else "CNPJ")
        documento_novo = cpf if tipo == "PF" else cnpj

        # Documento legado inválido é preservado quando o usuário edita
        # somente nome, telefone ou razão social.
        if documento_informado and documento_novo != documento_atual:
            documento_novo = self._validar_documento(tipo, documento_novo)
            if tipo == "PF":
                cpf = documento_novo
            else:
                cnpj = documento_novo

        if tipo == "PF" and cpf:
            existente = self.model.get_favorecido_by_cpf(cpf, id_usuario)
            if existente and existente["ID_Favorecido"] != id_favorecido:
                raise ValueError("CPF já cadastrado.")

            dados["CPF"] = cpf  # 🔥 normaliza antes de enviar

        if tipo == "PJ" and cnpj:
            existente = self.model.get_favorecido_by_cnpj(cnpj, id_usuario)
            if existente and existente["ID_Favorecido"] != id_favorecido:
                raise ValueError("CNPJ já cadastrado.")

            dados["CNPJ"] = cnpj  # 🔥 normaliza antes de enviar

        return self.model.update_favorecido(
            id_favorecido,
            dados,
            id_usuario
        )

    # ---------------------------------------------------------
    # DELETAR
    # ---------------------------------------------------------
    def deletar(self, id_favorecido, id_usuario):
        fav = self.model.get_favorecido_by_id(id_favorecido, id_usuario)
        if not fav:
            raise ValueError("Favorecido não encontrado.")

        return self.model.delete_favorecido(id_favorecido, id_usuario)

    # ---------------------------------------------------------
    # RESOLVER
    # ---------------------------------------------------------
    def resolver_favorecido(self, dados, id_usuario):
        nome = (dados.get("Nome") or "").strip()
        cpf = self._somente_numeros(dados.get("CPF"))
        cnpj = self._somente_numeros(dados.get("CNPJ"))

        if cpf and cnpj:
            raise ValueError("Informe apenas CPF ou CNPJ, conforme o tipo.")
        if cpf:
            cpf = self._validar_documento("PF", cpf)
        if cnpj:
            cnpj = self._validar_documento("PJ", cnpj)

        if cpf:
            fav = self.model.get_favorecido_by_cpf(cpf, id_usuario)
            if fav:
                return fav["ID_Favorecido"]

        if cnpj:
            fav = self.model.get_favorecido_by_cnpj(cnpj, id_usuario)
            if fav:
                return fav["ID_Favorecido"]

        if nome:
            fav = self.model.get_favorecido_by_name(nome, id_usuario)
            if fav:
                return fav["ID_Favorecido"]

        if not cpf and not cnpj:
            return None

        tipo = "PF" if cpf else "PJ"
        payload = {
            "Nome": nome,
            "Tipo": tipo,
            "Telefone": dados.get("Telefone")
        }

        if tipo == "PF":
            payload["CPF"] = cpf
        else:
            payload["CNPJ"] = cnpj
            payload["Razao_Social"] = dados.get("Razao_Social") or nome

        return self.model.add_favorecido(payload, id_usuario)
