from unittest.mock import MagicMock, patch

import pytest
from ckan import model
from ckan.tests import factories
from ckan.tests.helpers import call_action
from datacite.errors import DataCiteNotFoundError

from ckanext.doi.plugin import DOIPlugin


@pytest.mark.filterwarnings('ignore::sqlalchemy.exc.SADeprecationWarning')
@pytest.mark.ckan_config('ckan.plugins', 'doi')
@pytest.mark.ckan_config('ckanext.doi.prefix', '10.12345')
@pytest.mark.usefixtures('with_doi_table', 'with_plugins')
def test_bulk_update_carries_on_past_a_failing_dataset(monkeypatch):
    # One dataset whose after_dataset_update raises (as this plugin does
    # for incomplete DOI metadata) must not stop the rest of the batch,
    # and must itself stay unchanged.
    user = factories.Sysadmin()
    org = factories.Organization()
    # Creating a dataset reserves a DOI, which checks DataCite for a
    # clash - mocked the same way test_plugin.py does.
    with patch('ckanext.doi.lib.api.DataCiteMDSClient') as client_class:
        client_class.return_value = MagicMock(
            metadata_get=MagicMock(side_effect=DataCiteNotFoundError())
        )
        datasets = [
            factories.Dataset(owner_org=org['id'], private=False) for _ in range(3)
        ]
    failing_id = datasets[1]['id']

    def after_dataset_update(self, context, pkg_dict):
        if pkg_dict['id'] == failing_id:
            raise ValueError('Creator name must be supplied')
        return pkg_dict

    monkeypatch.setattr(DOIPlugin, 'after_dataset_update', after_dataset_update)

    call_action(
        'bulk_update_private',
        {'user': user['name']},
        datasets=[d['id'] for d in datasets],
        org_id=org['id'],
    )

    model.Session.expire_all()
    private = {d['id']: model.Package.get(d['id']).private for d in datasets}
    assert private == {
        datasets[0]['id']: True,
        failing_id: False,
        datasets[2]['id']: True,
    }


@pytest.mark.parametrize(
    ('test_mode', 'expected'),
    [
        ('True', 'https://handle.test.datacite.org/10.83249/abc'),
        ('False', 'https://doi.org/10.83249/abc'),
    ],
)
def test_doi_resolver_url(test_mode, expected):
    from ckan.tests.helpers import changed_config

    from ckanext.doi.lib.helpers import doi_resolver_url

    with changed_config('ckanext.doi.test_mode', test_mode):
        assert doi_resolver_url('10.83249/abc') == expected
