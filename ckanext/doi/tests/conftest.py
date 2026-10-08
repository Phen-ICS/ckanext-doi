import configparser
import os
import re

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


def _resolve_ckan_ini(session):
    ckan_ini = getattr(session.config.option, 'ckan_ini', '') or ''
    if ckan_ini:
        return ckan_ini
    # pytest-ckan falls back to this env var when --ckan-ini is omitted -
    # mirror that so we inspect the config that will actually be used.
    return os.environ.get('CKAN_INI', '')


def _sqlalchemy_db_name(ini_path):
    """Best-effort extraction of the database name from an ini's
    sqlalchemy.url, without relying on CKAN's own config loader (which isn't
    initialised yet at pytest_sessionstart)."""
    if not ini_path or not os.path.isfile(ini_path):
        return None

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(ini_path)
    except configparser.Error:
        return None

    url = None
    for section in parser.sections():
        if parser.has_option(section, 'sqlalchemy.url'):
            url = parser.get(section, 'sqlalchemy.url')
            break
    if not url:
        return None

    # test.ini/test-core.ini use PasteDeploy-style %(VAR)s placeholders
    # resolved against the environment (not plain configparser
    # interpolation) - expand them the same way so a templated URL still
    # resolves to the real database name.
    url = re.sub(r'%\((\w+)\)s', lambda m: os.environ.get(m.group(1), ''), url)
    url = re.sub(r'\$\{(\w+)\}', lambda m: os.environ.get(m.group(1), ''), url)
    return url.rsplit('/', 1)[-1].split('?', 1)[0]


def pytest_sessionstart(session):
    """Fail fast if tests would run against anything but an isolated test
    database.

    This check is NOT affected by DOI_ALLOW_NON_TEST_INI (below), which
    only relaxes the *path* check - never this one. A sibling extension
    (ckanext-citations) hit exactly this gap: its equivalent bypass env var
    was set without --ckan-ini, so pytest-ckan silently fell back to the
    container's real CKAN_INI and a clean_db-using test dropped every table
    in the real local database.
    """
    ckan_ini = _resolve_ckan_ini(session)
    db_name = _sqlalchemy_db_name(ckan_ini)
    if db_name and not re.search('test', db_name, re.IGNORECASE):
        raise pytest.UsageError(
            f"Refusing to run: resolved database '{db_name}' (from "
            f'{ckan_ini or "CKAN_INI"}) does not look like a test database '
            "(expected a name containing 'test'). This check cannot be "
            'bypassed - point --ckan-ini (or CKAN_INI) at a test config.'
        )

    if os.environ.get('DOI_ALLOW_NON_TEST_INI') == '1':
        return

    normalized = ckan_ini.replace('\\', '/').strip()

    if normalized.endswith('/test.ini') or normalized == 'test.ini':
        return

    raise pytest.UsageError(
        'Unsafe CKAN test configuration detected. '
        'Run tests with --ckan-ini=/plugins/ckanext-doi/test.ini '
        '(or set DOI_ALLOW_NON_TEST_INI=1 to bypass intentionally).'
    )
