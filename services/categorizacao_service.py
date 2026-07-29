# -*- coding: utf-8 -*-
import logging
import re
import unicodedata

from services.category_service import CategoryService
from models.categoria_map_model import CategoriaMapModel

logger = logging.getLogger(__name__)


class CategorizacaoService:
    """
    Serviço de categorização automática.

    Prioridade:
    1. Categorias já cadastradas pelo usuário via IA semântica.
    2. CategoriaMapModel por palavras-chave.
    3. Sem categoria.

    Observação:
    - A categoria sugerida ainda passa pela tela temporária.
    - O usuário pode alterar antes de confirmar a importação.
    """

    SCORE_MINIMO = 0.45

    def __init__(self):
        # IMPORTANTE:
        # Não instanciar CategoryService aqui.
        # Ele usa SQLite e precisa ser criado na mesma thread onde será usado.
        self.model = None

        self._modelo_indisponivel = False
        self._categorias_cache = {}
        self._embeddings_cache = {}

    # ======================================================
    # SERVICES THREAD-SAFE
    # ======================================================
    def _get_category_service(self):
        """
        Cria CategoryService sob demanda.

        Isso evita erro:
        SQLite objects created in a thread can only be used in that same thread.
        """
        return CategoryService()

    # ======================================================
    # MODELO IA
    # ======================================================
    def _get_model(self):
        if self._modelo_indisponivel:
            return None

        if self.model is not None:
            return self.model

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(
                "all-MiniLM-L6-v2",
                device="cpu"
            )

            return self.model

        except Exception:
            logger.exception("Modelo de categorização indisponível.")
            self._modelo_indisponivel = True
            return None

    # ======================================================
    # MÉTODO PRINCIPAL
    # ======================================================
    def categorizar(self, descricao: str, valor: float, id_usuario: int):
        if not descricao:
            return None, 0.0

        descricao_limpa = self._normalizar_texto(descricao)

        id_categoria, confianca = self._categorizar_por_usuario(
            descricao=descricao_limpa,
            valor=valor,
            id_usuario=id_usuario
        )

        if id_categoria:
            return id_categoria, confianca

        id_categoria, confianca = self._categorizar_por_mapa(
            descricao=descricao_limpa,
            valor=valor,
            id_usuario=id_usuario
        )

        if id_categoria:
            return id_categoria, confianca

        return None, 0.0

    # ======================================================
    # CATEGORIZAÇÃO PELO USUÁRIO
    # ======================================================
    def _categorizar_por_usuario(
        self,
        descricao: str,
        valor: float,
        id_usuario: int
    ):
        try:
            categorias = self._obter_categorias_usuario(id_usuario)

            if not categorias:
                return None, 0.0

            model = self._get_model()

            if model is None:
                return None, 0.0

            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            emb_desc = model.encode([descricao])
            emb_cats = self._embeddings_cache.get(id_usuario)

            if emb_cats is None:
                return None, 0.0

            similaridades = cosine_similarity(emb_desc, emb_cats)[0]

            indice = int(np.argmax(similaridades))
            score = float(similaridades[indice])

            if score < self.SCORE_MINIMO:
                return None, round(score, 2)

            categoria = categorias[indice]

            category_service = self._get_category_service()

            id_categoria = category_service.resolver_categoria_importacao(
                categoria_pai_nome=categoria["CategoriaPai"],
                subcategoria_nome=categoria["Subcategoria"],
                valor=valor,
                id_usuario=id_usuario
            )

            return id_categoria, round(score, 2)

        except Exception:
            logger.exception("Erro ao categorizar usando categorias do usuário.")
            return None, 0.0

    # ======================================================
    # CATEGORIZAÇÃO PELO MAPA PADRÃO
    # ======================================================
    def _categorizar_por_mapa(
        self,
        descricao: str,
        valor: float,
        id_usuario: int
    ):
        try:
            category_service = self._get_category_service()

            for item in CategoriaMapModel.get_all():
                palavras = item.get("Palavras", [])

                for palavra in palavras:
                    palavra_norm = self._normalizar_texto(palavra)

                    if palavra_norm and palavra_norm in descricao:
                        id_categoria = (
                            category_service
                            .resolver_categoria_importacao(
                                categoria_pai_nome=item.get("CategoriaPai"),
                                subcategoria_nome=item.get("Subcategoria"),
                                valor=valor,
                                id_usuario=id_usuario
                            )
                        )

                        return id_categoria, 0.85

            return None, 0.0

        except Exception:
            logger.exception("Erro ao categorizar usando CategoriaMapModel.")
            return None, 0.0

    # ======================================================
    # CARREGAR CATEGORIAS DO USUÁRIO
    # ======================================================
    def _obter_categorias_usuario(self, id_usuario):
        if id_usuario in self._categorias_cache:
            return self._categorias_cache[id_usuario]

        model = self._get_model()

        if model is None:
            return None

        category_service = self._get_category_service()
        categorias_db = category_service.get_all_categories(id_usuario)

        categorias_formatadas = []

        for cat in categorias_db:
            if cat.get("ID_Categoria_Pai") is None:
                continue

            nome_pai = self._obter_nome_pai(
                categorias_db,
                cat.get("ID_Categoria_Pai")
            )

            nome_sub = cat.get("Nome")

            if not nome_pai or not nome_sub:
                continue

            categorias_formatadas.append({
                "CategoriaPai": nome_pai,
                "Subcategoria": nome_sub,
                "Texto": f"{nome_pai} {nome_sub}".strip()
            })

        if not categorias_formatadas:
            return None

        textos = [c["Texto"] for c in categorias_formatadas]

        self._categorias_cache[id_usuario] = categorias_formatadas
        self._embeddings_cache[id_usuario] = model.encode(textos)

        return categorias_formatadas

    # ======================================================
    # CACHE
    # ======================================================
    def limpar_cache(self, id_usuario=None):
        if id_usuario is None:
            self._categorias_cache.clear()
            self._embeddings_cache.clear()
            return

        self._categorias_cache.pop(id_usuario, None)
        self._embeddings_cache.pop(id_usuario, None)

    # ======================================================
    # AUXILIARES
    # ======================================================
    def _obter_nome_pai(self, categorias, id_pai):
        for cat in categorias:
            if cat.get("ID_Categoria") == id_pai:
                return cat.get("Nome")

        return None

    def _normalizar_texto(self, texto: str) -> str:
        texto = str(texto or "").strip().lower()

        texto = unicodedata.normalize("NFKD", texto)
        texto = texto.encode("ASCII", "ignore").decode("ASCII")

        texto = re.sub(r"[^a-z0-9\s]", " ", texto)
        texto = re.sub(r"\s+", " ", texto)

        return texto.strip()
