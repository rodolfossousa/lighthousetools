import pytest
from unittest.mock import MagicMock

from templates import find_category_id_by_name


class TestFindCategoryIdByName:
    """
    Testa find_category_id_by_name com mock do ws.get_categories().

    Cenário central do bug: a API faz busca por substring, então ao buscar
    "Sensors - Equipment Parts" pode retornar também "Sensors - Equipment Parts - T48".
    A função deve retornar o ID do match exato, não o do primeiro resultado.
    """

    def _make_ws(self, categories):
        """Cria um mock de workspace cujo get_categories retorna a lista fornecida."""
        ws = MagicMock()
        ws.get_categories.return_value = categories
        return ws

    def test_retorna_id_do_match_exato_quando_api_retorna_multiplos(self):
        """Bug original: API retorna superset como primeiro resultado."""
        ws = self._make_ws([
            {'id': 'id-errado', 'name': 'Sensors - Equipment Parts - T48'},
            {'id': 'id-correto', 'name': 'Sensors - Equipment Parts'},
        ])
        result = find_category_id_by_name(ws, 'Sensors - Equipment Parts')
        assert result == 'id-correto', (
            "Deve retornar o ID da categoria com nome exatamente igual, "
            "não o do primeiro resultado da busca."
        )

    def test_retorna_id_quando_ha_unico_resultado_exato(self):
        ws = self._make_ws([
            {'id': 'id-unico', 'name': 'Sensors - Equipment Parts'},
        ])
        result = find_category_id_by_name(ws, 'Sensors - Equipment Parts')
        assert result == 'id-unico'

    def test_retorna_none_quando_nenhum_resultado_e_exato(self):
        """API retorna resultados mas nenhum tem o nome exato buscado."""
        ws = self._make_ws([
            {'id': 'id-errado', 'name': 'Sensors - Equipment Parts - T48'},
        ])
        result = find_category_id_by_name(ws, 'Sensors - Equipment Parts')
        assert result is None

    def test_retorna_none_quando_lista_vazia(self):
        ws = self._make_ws([])
        result = find_category_id_by_name(ws, 'Qualquer Categoria')
        assert result is None

    def test_retorna_none_quando_api_retorna_none(self):
        ws = self._make_ws(None)
        result = find_category_id_by_name(ws, 'Qualquer Categoria')
        assert result is None

    def test_match_e_case_sensitive(self):
        """Nomes de categorias devem ser comparados exatamente (case sensitive)."""
        ws = self._make_ws([
            {'id': 'id-lower', 'name': 'sensors - equipment parts'},
        ])
        result = find_category_id_by_name(ws, 'Sensors - Equipment Parts')
        assert result is None
