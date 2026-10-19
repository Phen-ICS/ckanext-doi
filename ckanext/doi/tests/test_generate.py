#!/usr/bin/env python3
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

import pytest

try:
    from datacite import schema45 as schema42
except ImportError:
    from datacite import schema42

from ckanext.doi.lib.metadata import build_metadata_dict, build_xml_dict, format_size

from .helpers import constants


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Example Publisher')
def test_extracts_metadata():
    metadata_dict = build_metadata_dict(constants.PKG_DICT)
    assert isinstance(metadata_dict, dict)
    for k in ['creators', 'titles', 'publisher', 'publicationYear', 'resourceType']:
        assert k in metadata_dict
    assert 1 == len(metadata_dict['creators'])
    assert 1 == len(metadata_dict['titles'])
    assert constants.PKG_DICT['title'] == metadata_dict['titles'][0]['title']
    assert metadata_dict['publisher'] == 'Example Publisher'
    assert isinstance(metadata_dict['publicationYear'], int)
    assert constants.PKG_DICT['type'] == metadata_dict['resourceType']


@pytest.mark.parametrize(
    'num_bytes, expected',
    [
        (32, '32 B'),
        (1024, '1 KB'),
        (1500, '1.5 KB'),
        (1468006, '1.4 MB'),
        (5 * 1024**3, '5 GB'),
    ],
)
def test_format_size(num_bytes, expected):
    assert format_size(num_bytes) == expected


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Example Publisher')
@pytest.mark.parametrize(
    'sizes, expected',
    [
        ([32, None], ['32 B']),
        ([1024, 2048], ['3 KB']),
        ([None, None], []),
    ],
)
def test_sizes_sum_resource_sizes(sizes, expected):
    pkg_dict = {
        **constants.PKG_DICT,
        'resources': [{'size': size} for size in sizes],
    }
    assert build_metadata_dict(pkg_dict)['sizes'] == expected


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Example Publisher')
def test_handles_bad_data():
    bad_pkg_dict = {k: v for k, v in constants.PKG_DICT.items()}
    bad_pkg_dict['resources'] = None
    bad_pkg_dict['author'] = {'given_name': 'Test', 'family_name': 'Author'}
    bad_pkg_dict['license_id'] = None
    build_metadata_dict(bad_pkg_dict)

    del bad_pkg_dict['author']
    del bad_pkg_dict['resources']
    del bad_pkg_dict['license_id']
    build_metadata_dict(bad_pkg_dict)


@pytest.mark.ckan_config('ckanext.doi.publisher', 'Example Publisher')
def test_generate_xml():
    xml_dict = build_xml_dict(constants.METADATA_DICT)
    # build_xml_dict does not add a DOI
    xml_dict['doi'] = '10.0000/this-would-be-a-doi'
    assert schema42.validate(xml_dict)


def test_generate_xml_includes_publisher_and_affiliation_identifiers():
    metadata_dict = {
        **constants.METADATA_DICT,
        'publisherIdentifier': 'https://ror.org/03cjqqq10',
        'publisherIdentifierScheme': 'ROR',
        'schemeURI': 'https://ror.org/',
        'creators': [
            {
                'full_name': 'Bouri, Laurent',
                'given_name': 'Laurent',
                'family_name': 'Bouri',
                'identifiers': [
                    {
                        'identifier': 'https://orcid.org/0000-0002-2297-1559',
                        'scheme': 'ORCID',
                        'scheme_uri': 'https://orcid.org/',
                    }
                ],
                'affiliation_objects': [
                    {
                        'affiliation': 'Institut Clinique de la Souris',
                        'affiliationIdentifier': 'https://ror.org/03cjqqq10',
                        'affiliationIdentifierScheme': 'ROR',
                        'schemeURI': 'https://ror.org/',
                    }
                ],
            }
        ],
    }

    xml_dict = build_xml_dict(metadata_dict)
    xml_dict['doi'] = '10.0000/this-would-be-a-doi'

    assert schema42.validate(xml_dict)

    xml_doc = schema42.tostring(xml_dict)
    if isinstance(xml_doc, bytes):
        xml_doc = xml_doc.decode('utf-8')

    assert 'publisherIdentifier="https://ror.org/03cjqqq10"' in xml_doc
    assert 'publisherIdentifierScheme="ROR"' in xml_doc
    assert 'schemeURI="https://ror.org/"' in xml_doc
    assert 'affiliationIdentifier="https://ror.org/03cjqqq10"' in xml_doc
    assert 'affiliationIdentifierScheme="ROR"' in xml_doc
