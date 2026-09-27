from db import get_connection
from models import Category


class CategoryNotFoundError(Exception):
    """Raised when a requested category does not exist in the database."""
    pass


class CategoryRepo:
    """Handles database operations for Category records."""

    def add(self, category_name):
        """Insert a new category and return the created Category object.

        Parameters:
            category_name: Name of the category to create.

        Returns:
            The newly created Category, including its auto-generated ID.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO categories (category_name) VALUES (?)",
            (category_name,)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return Category(category_id=new_id, category_name=category_name)

    def get_all(self):
        """Fetch all categories.

        Returns:
            A list of Category objects, empty if none exist.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories")
        rows = cursor.fetchall()
        conn.close()
        return [Category(category_id=row['category_id'], category_name=row['category_name']) for row in rows]

    def get_by_id(self, category_id):
        """Fetch a single category by its ID.

        Parameters:
            category_id: ID of the category to fetch.

        Returns:
            The matching Category object.

        Raises:
            CategoryNotFoundError: If no category with that ID exists.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE category_id = ?", (category_id,))
        row = cursor.fetchone()
        conn.close()
        if row is None:
            raise CategoryNotFoundError(f"No category found with id {category_id}")
        return Category(category_id=row['category_id'], category_name=row['category_name'])

    def delete(self, category_id):
        """Delete a category by its ID.

        Parameters:
            category_id: ID of the category to delete.

        Raises:
            CategoryNotFoundError: If no category with that ID exists.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise CategoryNotFoundError(f"No category found with id {category_id}")
        conn.commit()
        conn.close()