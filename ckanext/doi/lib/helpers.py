# !/usr/bin/env python
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK

from datetime import datetime

from ckan.plugins import toolkit
from ckantools.config import get_debug, get_setting
from dateutil import parser


def package_get_year(pkg_dict):
    """
    Helper function to return the package year published.

    :param pkg_dict: return:
    """
    if not isinstance(pkg_dict['metadata_created'], datetime):
        pkg_dict['metadata_created'] = parser.parse(pkg_dict['metadata_created'])

    return pkg_dict['metadata_created'].year


def get_site_title():
    """
    Helper function to return the config site title, if it exists.

    :returns: str site title
    """
    return toolkit.config.get('ckanext.doi.site_title')


def get_site_url():
    """
    Get the site URL.

    Try and use ckanext.doi.site_url but if that's not set use ckan.site_url.
    """
    site_url = toolkit.config.get(
        'ckanext.doi.site_url', toolkit.config.get('ckan.site_url', '')
    )
    return site_url.rstrip('/')


def date_or_none(date_object_or_string):
    """
    Try and convert the given object into a datetime; if not possible, return None.

    :param date_object_or_string: a datetime or date string
    :returns: datetime or None
    """
    if isinstance(date_object_or_string, datetime):
        return date_object_or_string
    elif isinstance(date_object_or_string, str):
        return parser.parse(date_object_or_string)
    else:
        return None


def doi_test_mode():
    """
    Determines whether we're running in test mode.

    :returns: bool
    """
    return toolkit.asbool(get_setting('ckanext.doi.test_mode', default=get_debug()))


def doi_resolver_url(doi):
    """Link for a DOI: https://doi.org/<doi> in production, DataCite's
    test resolver in test mode - test DOIs (e.g. prefix 10.83249) only
    exist on DataCite's test system, doi.org 404s on them, while
    handle.test.datacite.org resolves them to their landing page just
    like doi.org does in production.

    :param doi: the DOI string
    :returns: the URL
    """
    if doi_test_mode():
        return f'https://handle.test.datacite.org/{doi}'
    return f'https://doi.org/{doi}'
