import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    _logger.warning("Post Migrating l10n_cl_stock_picking from version %s to 14.0.0.24.1" % installed_version)

    cr.execute("ALTER TABLE stock_picking DROP COLUMN sii_document_number")
    cr.execute("ALTER TABLE stock_picking RENAME COLUMN dcn_temp TO sii_document_number")
