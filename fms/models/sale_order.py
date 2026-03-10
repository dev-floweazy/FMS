# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fms_margin = fields.Monetary(
        string='FMS Margin',
        compute='_compute_fms_margin',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('origin', 'order_line')
    def _compute_fms_margin(self):
        for order in self:
            if order.origin:
                # fms.job links to sale.order via sale_order_id
                jobs = self.env['fms.job'].search([
                    ('sale_order_id', '=', order.id)
                ])
                # Also check by origin (job name) for older records
                if not jobs:
                    jobs = self.env['fms.job'].search([
                        ('name', '=', order.origin)
                    ])
                order.fms_margin = sum(jobs.mapped('margin'))
            else:
                order.fms_margin = 0.0