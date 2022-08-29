import logging

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    _logger.warning("Pre Migrating l10n_cl_stock_picking from version %s to 14.0.0.24.1" % installed_version)

    cr.execute("ALTER TABLE stock_picking ADD COLUMN dcn_temp BIGINT")
    cr.execute("UPDATE stock_picking set dcn_temp=CAST(sii_document_number as BIGINT) where sii_document_number!=''")
