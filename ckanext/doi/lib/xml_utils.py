#!/usr/bin/env python3
#
# This file is part of ckanext-doi
# Created by the Natural History Museum in London, UK


def create_contributor(
    full_name=None,
    family_name=None,
    given_name=None,
    is_org=False,
    contributor_type=None,
    affiliations=None,
    affiliation_objects=None,
    identifiers=None,
):
    """
    Create a dictionary representation of a contributing entity (either a person or an
    organisation) for use in an xml_dict.

    :param full_name: the full name of the creator, in the format "FamilyName,
        GivenName"; can be omitted if family_name and given_name are provided
    :param family_name: family name of the creator; will be ignored if given_name is
        None
    :param given_name: given name(s) or initials of the creator; will be ignored if
        family_name is None
    :param is_org: sets name type to Organizational if true
    :param contributor_type: the contributor type to set
    :param affiliations: affiliations of the contributor, either a string or list of
        strings
    :param affiliation_objects: optional list of affiliation dicts that may include
        DataCite affiliation identifiers
    :param identifiers: a list of dicts with "identifier", "scheme", and (optionally)
        "scheme_uri"
    :returns: a dict
    """
    if is_org and full_name is None:
        raise ValueError('Creator name must be supplied as full_name="Org Name"')
    if full_name is None and (family_name is None or given_name is None):
        raise ValueError(
            'Creator name must be supplied, either as full_name="FamilyName, '
            'GivenName" or separately as family_name and given_name'
        )
    if full_name is None:
        full_name = f'{family_name}, {given_name}'
    if (family_name is None or given_name is None) and not is_org:
        # try to extract the family and given names from the full name
        name_parts = full_name.split(',', 1)
        if len(name_parts) > 1:
            family_name, given_name = [x.strip() for x in name_parts]
        else:
            # assume it was formatted incorrectly and split by spaces instead
            # if that doesn't work then there isn't much we can do
            name_parts = full_name.split(' ')
            family_name = name_parts[-1].strip()
            given_name = ' '.join(name_parts[0:-1]).strip()
    contributor = {
        'name': full_name,
        'nameType': 'Organizational' if is_org else 'Personal',
    }
    if not is_org:
        if family_name is not None:
            family_name = str(family_name).strip()
            if family_name:
                contributor['familyName'] = family_name
        if given_name is not None:
            given_name = str(given_name).strip()
            if given_name:
                contributor['givenName'] = given_name
    if contributor_type is not None:
        contributor['contributorType'] = contributor_type

    def _normalize_affiliation(affiliation):
        if isinstance(affiliation, dict):
            name = str(
                affiliation.get('name') or affiliation.get('affiliation') or ''
            ).strip()
            if not name:
                return None
            normalized = {'name': name}
            if affiliation.get('affiliationIdentifier'):
                normalized['affiliationIdentifier'] = affiliation[
                    'affiliationIdentifier'
                ]
            if affiliation.get('affiliationIdentifierScheme'):
                normalized['affiliationIdentifierScheme'] = affiliation[
                    'affiliationIdentifierScheme'
                ]
            scheme_uri = affiliation.get('schemeUri') or affiliation.get('schemeURI')
            if scheme_uri:
                normalized['schemeUri'] = scheme_uri
            return normalized

        name = str(affiliation).strip()
        if not name:
            return None
        return {'name': name}

    source_affiliations = affiliation_objects
    if source_affiliations is None:
        source_affiliations = affiliations

    if source_affiliations is not None:
        contributor['affiliation'] = []
        if isinstance(source_affiliations, (str, dict)):
            source_affiliations = [source_affiliations]
        for affiliation in source_affiliations:
            normalized_affiliation = _normalize_affiliation(affiliation)
            if normalized_affiliation:
                contributor['affiliation'].append(normalized_affiliation)
        if not contributor['affiliation']:
            del contributor['affiliation']

    if identifiers:
        contributor['nameIdentifiers'] = []
        for _id in identifiers:
            if 'identifier' not in _id or 'scheme' not in _id:
                continue
            id_dict = {
                'nameIdentifier': _id['identifier'],
                'nameIdentifierScheme': _id['scheme'],
            }
            scheme_uri = (
                _id.get('scheme_uri') or _id.get('schemeURI') or _id.get('schemeUri')
            )
            if scheme_uri:
                id_dict['schemeUri'] = scheme_uri
            contributor['nameIdentifiers'].append(id_dict)
    return contributor
