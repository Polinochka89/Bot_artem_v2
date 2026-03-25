import pytest

from src.domain.value_objects import DataCategory

pytestmark = pytest.mark.unit


def test_data_category_contains_all_expected_values() -> None:
    assert {member.value for member in DataCategory} == {
        "crypto",
        "currency",
        "goods",
        "stocks",
        "indices",
    }


def test_data_category_behaves_like_string() -> None:
    assert str(DataCategory.CRYPTO) == "crypto"
    assert DataCategory.CRYPTO == "crypto"
