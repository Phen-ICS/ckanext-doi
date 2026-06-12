import pytest
from ckan.model import meta

from ckanext.doi.model.doi import doi_table


@pytest.fixture
def with_doi_table(reset_db):
    """
    Simple fixture which resets the database and creates the doi table.
    """
    reset_db()
    doi_table.create(bind=meta.engine, checkfirst=True)
