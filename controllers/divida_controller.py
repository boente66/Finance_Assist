"""Direcionamento da interface para as regras do módulo de dívidas."""

from core.session import Session
from services.divida_service import DividaService


class DividaController:
    def __init__(self, db_name=None):
        self.service = DividaService(db_name)

    @staticmethod
    def _usuario_id():
        usuario = Session.get_usuario()
        if not usuario:
            raise PermissionError("Usuário não autenticado.")
        return usuario["ID_Usuario"]

    def criar(self, dados):
        return self.service.criar(dados, self._usuario_id())

    def tipos_disponiveis(self):
        return sorted(self.service.TIPOS)

    def listar(self, status=None):
        return self.service.listar(self._usuario_id(), status)

    def obter(self, id_divida):
        return self.service.obter(id_divida, self._usuario_id())

    def registrar_pagamento(self, dados):
        return self.service.registrar_pagamento(dados, self._usuario_id())

    def agendar_pagamento_livre(self, dados):
        return self.service.agendar_pagamento_livre(dados, self._usuario_id())

    def encerrar(self, id_divida, status):
        return self.service.encerrar(id_divida, status, self._usuario_id())
