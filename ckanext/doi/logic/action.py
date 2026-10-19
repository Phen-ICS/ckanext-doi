"""Chained organization bulk actions (Make public / Make private /
Delete on the organization's bulk page) that carry on past a dataset
that fails, instead of aborting the rest of the batch.

CKAN's own _bulk_update_dataset calls package_patch per dataset with
no error handling: one dataset whose DOI metadata is incomplete (this
plugin's after_dataset_update raises - e.g. "Creator name must be
supplied") turned the whole request into a 500, with every dataset
after it in the batch silently left untouched.

Each failing dataset is rolled back on its own - its package_update
never reached its commit, so it stays exactly as it was (e.g. still
private, which is what should happen when its DOI can't be minted) -
and reported in one flash message; every other dataset goes through.
"""

from logging import getLogger

from ckan import model
from ckan.logic import fresh_context
from ckan.plugins import toolkit
from flask import has_request_context

log = getLogger(__name__)


def _bulk_update(context, data_dict, update_dict):
    dataset_ids = [
        row.id
        for row in model.Session.query(model.Package.id)
        .filter(model.Package.id.in_(data_dict.get('datasets', [])))
        .filter(model.Package.owner_org == data_dict.get('org_id'))
    ]

    failed = []
    for dataset_id in dataset_ids:
        try:
            toolkit.get_action('package_patch')(
                fresh_context(context), dict(update_dict, id=dataset_id)
            )
        except Exception:
            log.exception('Bulk update failed for dataset %s', dataset_id)
            # The failed package_update left its own pending changes in
            # the session - without this, every dataset after it would
            # fail too (InFailedSqlTransaction).
            model.Session.rollback()
            failed.append(dataset_id)

    if failed and has_request_context():
        names = [
            pkg.title or pkg.name
            for pkg in model.Session.query(model.Package).filter(
                model.Package.id.in_(failed)
            )
        ]
        toolkit.h.flash_error(
            toolkit._(
                'These datasets could not be updated and were left unchanged '
                '(check their metadata, e.g. creators for the DOI): {names}'
            ).format(names=', '.join(names))
        )
    return failed


@toolkit.chained_action
def bulk_update_public(original_action, context, data_dict):
    toolkit.check_access('bulk_update_public', context, data_dict)
    _bulk_update(context, data_dict, {'private': False})


@toolkit.chained_action
def bulk_update_private(original_action, context, data_dict):
    toolkit.check_access('bulk_update_private', context, data_dict)
    _bulk_update(context, data_dict, {'private': True})


@toolkit.chained_action
def bulk_update_delete(original_action, context, data_dict):
    toolkit.check_access('bulk_update_delete', context, data_dict)
    _bulk_update(context, data_dict, {'state': 'deleted'})
