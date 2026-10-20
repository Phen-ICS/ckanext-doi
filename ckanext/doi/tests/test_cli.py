from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from ckanext.doi import cli


def test_update_doi_skips_private_datasets_and_carries_on_past_a_failure():
    records = [
        MagicMock(identifier=f'10.1/{i}', package_id=i, published=True) for i in 'abc'
    ]
    packages = {
        'a': {'title': 'Private one', 'private': True},
        'c': {'title': 'Public one'},
    }

    def package_show(context, data_dict):
        # a CLI run has no user: without ignore_auth, private datasets raise
        assert context == {'ignore_auth': True}
        if data_dict['id'] == 'b':
            raise RuntimeError('boom')
        return packages[data_dict['id']]

    with (
        patch('ckanext.doi.cli.Session') as session,
        patch('ckanext.doi.cli.toolkit') as toolkit,
        patch('ckanext.doi.cli.DataciteClient') as client_class,
        patch('ckanext.doi.cli.build_metadata_dict'),
        patch('ckanext.doi.cli.build_xml_dict'),
    ):
        session.query.return_value.all.return_value = records
        toolkit.get_action.return_value = package_show
        client = client_class.return_value
        client.check_for_update.return_value = False

        result = CliRunner().invoke(cli.update_doi)

    assert result.exit_code == 0
    assert '"Private one" is inactive or private' in result.output
    assert 'Error while updating "b" (DOI 10.1/b): boom' in result.output
    client.set_metadata.assert_called_once()
    assert client.set_metadata.call_args.args[0] == '10.1/c'
