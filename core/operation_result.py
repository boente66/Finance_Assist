def operation_result(
    sucesso: bool,
    codigo: str,
    mensagem: str,
    dados=None
) -> dict:
    """Contrato de retorno dos fluxos críticos corrigidos."""
    return {
        "sucesso": bool(sucesso),
        "codigo": codigo,
        "mensagem": mensagem,
        "dados": dados,
    }
