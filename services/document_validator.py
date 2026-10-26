class DocumentValidator:
    """Validação de domínio para documentos brasileiros."""

    @staticmethod
    def somente_numeros(valor):
        if valor in (None, ""):
            return None
        return "".join(filter(str.isdigit, str(valor)))

    @classmethod
    def validar_cpf(cls, valor):
        cpf = cls.somente_numeros(valor)
        if not cpf or len(cpf) != 11:
            raise ValueError("CPF deve conter 11 dígitos.")
        if cpf == cpf[0] * 11:
            raise ValueError("CPF inválido.")

        for tamanho in (9, 10):
            soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
            digito = (soma * 10 % 11) % 10
            if digito != int(cpf[tamanho]):
                raise ValueError("CPF inválido.")
        return cpf

    @classmethod
    def validar_cnpj(cls, valor):
        cnpj = cls.somente_numeros(valor)
        if not cnpj or len(cnpj) != 14:
            raise ValueError("CNPJ deve conter 14 dígitos.")
        if cnpj == cnpj[0] * 14:
            raise ValueError("CNPJ inválido.")

        pesos = (
            (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
            (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
        )
        for indice, fatores in enumerate(pesos, 12):
            resto = sum(int(n) * p for n, p in zip(cnpj[:indice], fatores)) % 11
            digito = 0 if resto < 2 else 11 - resto
            if digito != int(cnpj[indice]):
                raise ValueError("CNPJ inválido.")
        return cnpj

