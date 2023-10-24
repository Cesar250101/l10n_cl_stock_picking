# -*- coding: utf-8 -*-
from odoo import osv, models, fields, api, _
from odoo.exceptions import except_orm, UserError
import odoo.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        if 'picking_id' in vals:
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking and picking.company_id:
                vals['company_id'] = picking.company_id.id
        return super(StockMove, self).create(vals)

    def _set_price_from(self):
        if self.picking_id.reference:
            for ref in self.picking_id.reference:
                if ref.sii_referencia_TpoDocRef.sii_code in [33]:
                    il = self.env['account.invoice'].search(
                            [
                                    ('sii_document_number', '=', ref.origen),
                                    ('document_class_id.sii_code', '=', ref.sii_referencia_TpoDocRef.sii_code),
                                    ('product_id', '=', self.product_id.id),
                            ]
                        )
                    if il:
                        self.precio_unitario = il.price_unit
                        self.subtotal = il.subtotal
                        self.discount = il.discount
                        self.move_line_tax_ids = il.invoice_line_tax_ids

    @api.onchange('name')
    def _sale_prices(self):
        for rec in self:
            if rec.precio_unitario <= 0:
                rec._set_price_from()
            if rec.precio_unitario <= 0:
                rec.precio_unitario = rec.product_id.lst_price
                rec.move_line_tax_ids = rec.product_id.taxes_id # @TODO mejorar asignación
            if not rec.name:
                rec.name = rec.product_id.name

    @api.onchange('name', 'product_id', 'move_line_tax_ids', 'product_uom_qty', 'precio_unitario', 'quantity_done')
    @api.depends('name', 'product_id', 'move_line_tax_ids', 'product_uom_qty', 'precio_unitario', 'quantity_done')
    def _compute_amount(self):
        for rec in self:
            qty = rec.quantity_done
            if qty <= 0:
                qty = rec.product_uom_qty
            taxes = rec.move_line_tax_ids.compute_all(rec.precio_unitario, rec.currency_id, qty, product=rec.product_id, partner=rec.picking_id.partner_id, discount=rec.discount, uom_id=rec.product_uom)
            rec.price_untaxed = taxes['total_excluded']
            rec.subtotal = taxes['total_included']

    name = fields.Char(
            string="Nombre",
        )
    subtotal = fields.Monetary(
            compute='_compute_amount',
            string='Subtotal',
            store=True,
        )
    precio_unitario = fields.Float(
            string='Precio Unitario',
            digits=dp.get_precision('Product Price'),
        )
    price_untaxed = fields.Monetary(
            string='Price Untaxed',
            compute='_compute_amount',
        )
    move_line_tax_ids = fields.Many2many(
            'account.tax',
            'move_line_tax_ids',
            'move_line_id',
            'tax_id',
            string='Taxes',
            domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False), ('active', '=', True)],
        )
    discount = fields.Monetary(
            digits=dp.get_precision('Discount'),
            string='Discount (%)',
        )
    currency_id = fields.Many2one(
            'res.currency',
            string='Currency',
            required=True,
            states={'draft': [('readonly', False)]},
            default=lambda self: self.env.user.company_id.currency_id.id,
            track_visibility='always',
        )
