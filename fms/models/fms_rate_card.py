# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_id = fields.Many2one('product.product', string='Service',
                                 domain=[('is_fms_service', '=', True)],
                                 required=True)

    unit_price = fields.Monetary(string='Unit Price', required=True)
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id)

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]