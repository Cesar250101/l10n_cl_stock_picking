import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    _logger.warning("Post Migrating l10n_cl_stock_picking from version %s to 12.0.0.24.0" % installed_version)
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        "SELECT id, sequence_id, sii_document_class_id, sucursal_id, restore_mode FROM stock_location where sequence_id is not NULL")
    for row in cr.dictfetchall():
        warehouse = env['stock.warehouse'].search([('active', '=', True), '|', ('lot_stock_id', '=', row['id']), ('view_location_id', '=', row['id'])])
        if warehouse:
            warehouse.write({
                'sequence_id': row['sequence_id'],
                'document_class_id': row['sii_document_class_id'],
                'sucursal_id': row['sucursal_id'],
                'restore_mode': row['restore_mode']
            })
            warehouse.acteco_ids += warehouse.company_id.company_activities_ids[4:]
