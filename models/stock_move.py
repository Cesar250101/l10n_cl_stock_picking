# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def name_get(self):
        if self._context.get('cdg_item'):
            result = []
            for move in self:
                name = move.description_picking or (move.product_id.display_name if move.product_id else move.name or str(move.id))
                if name == move.product_id.name:
                    name = move.product_id.display_name
                result.append((move.id, name))
            return result
        return super().name_get()

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = super(StockMove, self)._prepare_merge_moves_distinct_fields()
        fields += [
            'precio_unitario',
            'discount',
            'move_line_tax_ids',
            'currency_id',
        ]
        return fields

    def _set_price_from(self):
        return
        if self.picking_id.reference:
            for ref in self.picking_id.reference:
                if ref.sii_referencia_TpoDocRef.sii_code in [33]:
                    il = self.env['account.move'].search(
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

    @api.onchange('name', 'description_picking', 'product_id', 'move_line_tax_ids', 'product_uom_qty', 'precio_unitario', 'quantity_done')
    @api.depends('name', 'description_picking', 'product_id', 'move_line_tax_ids', 'product_uom_qty', 'precio_unitario', 'quantity_done')
    def _compute_amount(self):
        for rec in self:
            qty = rec.quantity_done
            if qty <= 0:
                qty = rec.product_uom_qty
            taxes = rec.move_line_tax_ids.compute_all(rec.precio_unitario, rec.currency_id, qty, product=rec.product_id, partner=rec.picking_id.partner_id, discount=rec.discount, uom_id=rec.product_uom)
            rec.price_untaxed = taxes['total_excluded']
            rec.subtotal = taxes['total_included']

    subtotal = fields.Monetary(
            compute='_compute_amount',
            string='Subtotal',
            store=True,
        )
    precio_unitario = fields.Float(
            string='Precio Unitario',
            digits='Product Price',
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
    discount = fields.Float(
            digits='Discount',
            string='Discount (%)',
        )
    currency_id = fields.Many2one(
            'res.currency',
            string='Currency',
            states={'draft': [('readonly', False)]},
            default=lambda self: self.env.user.company_id.currency_id.id
        )
    cdg_item_ids = fields.One2many(
            'stock.move.cdg.item',
            'move_id',
            string='Códigos Adicionales',
        )
    use_codigos_adicionales = fields.Boolean(
            related='picking_id.use_codigos_adicionales',
            string='Definir Códigos Adicionales',
            store=False,
        )


class StockMoveCdgItem(models.Model):
    _name = 'stock.move.cdg.item'
    _description = 'Código adicional de ítem en línea de guía'

    move_id = fields.Many2one(
        'stock.move',
        string='Línea',
        ondelete='cascade',
        index=True,
        required=True,
    )
    picking_id = fields.Many2one(
        related='move_id.picking_id',
        string='Guía',
        store=True,
        index=True,
    )
    product_id = fields.Many2one(
        related='move_id.product_id',
        string='Producto',
        store=True,
    )
    tpo_codigo = fields.Selection(
        [
            ('INT1', 'INT1 - Código interno'),
            ('QBLI', 'QBLI - Código de barras'),
            ('EAN13', 'EAN13'),
            ('DUN14', 'DUN14'),
            ('EAN8', 'EAN8'),
            ('STKPICKING', 'STKPICKING - Picking'),
        ],
        string='Tipo Código',
        required=True,
        default='QBLI',
    )
    vlr_codigo = fields.Char(string='Valor Código', required=True)
