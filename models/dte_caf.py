from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class DTECAF(models.Model):
    _inherit = "dte.caf"

    def _join_inspeccionar(self):
        if self.sii_document_class in [50, 52]:
            return ' LEFT JOIN stock_picking sp on s = sp.sii_document_number and sp.document_class_id = %s' % self.sequence_id.sii_document_class_id.id
        return super(DTECAF, self)._join_inspeccionar()


    def _where_inspeccionar(self):
        if self.sii_document_class in [50, 52]:
            return ' sp.sii_document_number is null'
        return super(DTECAF, self)._where_inspeccionar()
