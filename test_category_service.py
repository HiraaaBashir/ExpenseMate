import pytest
from exceptions import ValidationError


def test_add_category_success(services):
    category = services['category_service'].add_category("Rent")
    assert category.category_name == "Rent"


def test_add_category_empty_name_raises_error(services):
    with pytest.raises(ValidationError):
        services['category_service'].add_category("")


def test_add_category_whitespace_only_raises_error(services):
    with pytest.raises(ValidationError):
        services['category_service'].add_category("   ")