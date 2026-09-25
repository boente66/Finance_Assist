class NameFormat:

    @staticmethod
    def somente_numeros(valor):
        if not valor:
            return ""
        return "".join(filter(str.isdigit, str(valor)))

    @staticmethod
    def formatCPF(cpf):
        cpf = NameFormat.somente_numeros(cpf)
        if len(cpf) != 11:
            return cpf
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    @staticmethod
    def formatCNPJ(cnpj):
        cnpj = NameFormat.somente_numeros(cnpj)
        if len(cnpj) != 14:
            return cnpj
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

    @staticmethod
    def formatTelefone(telefone):
        telefone = NameFormat.somente_numeros(telefone)

        if len(telefone) == 11:
            return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
        elif len(telefone) == 10:
            return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
        elif len(telefone) == 9:
            return f"{telefone[:5]}-{telefone[5:]}"
        elif len(telefone) == 8:
            return f"{telefone[:4]}-{telefone[4:]}"
        return telefone

    @staticmethod
    def format_documento(valor):
        valor = NameFormat.somente_numeros(valor)

        if len(valor) == 11:
            return NameFormat.formatCPF(valor)
        elif len(valor) == 14:
            return NameFormat.formatCNPJ(valor)

        return valor

    @staticmethod
    def documento_valido(valor):
        numero = NameFormat.somente_numeros(valor)
        if len(numero) not in (11, 14) or numero == numero[0] * len(numero):
            return False

        def digito(base, pesos):
            resto = sum(int(n) * peso for n, peso in zip(base, pesos)) % 11
            return '0' if resto < 2 else str(11 - resto)

        if len(numero) == 11:
            primeiro = digito(numero[:9], range(10, 1, -1))
            segundo = digito(numero[:9] + primeiro, range(11, 1, -1))
            return numero[-2:] == primeiro + segundo

        primeiro = digito(numero[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
        segundo = digito(
            numero[:12] + primeiro,
            (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
        )
        return numero[-2:] == primeiro + segundo
