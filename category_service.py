from category_repo import CategoryRepo
from exceptions import ValidationError


class CategoryService:
    """Business logic for category management."""

    def __init__(self):
        self.repo = CategoryRepo()

    def add_category(self, category_name):
        """Validate and create a new category.

        Parameters:
            category_name: Name of the category to create.

        Returns:
            The newly created Category.

        Raises:
            ValidationError: If category_name is empty.
        """
        if not category_name or not category_name.strip():
            raise ValidationError("Category name cannot be empty.")
        return self.repo.add(category_name.strip())

    def get_all_categories(self):
        """Return all categories."""
        return self.repo.get_all()

    def delete_category(self, category_id):
        """Delete a category by ID."""
        self.repo.delete(category_id)