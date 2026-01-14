# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_fms_service = fields.Boolean(string='FMS Service')
    fms_service_category_id = fields.Many2one('fms.service.category')
    is_additional_service = fields.Boolean(string='Additional Service')
    is_visit_charge = fields.Boolean(string='Visit Charge')
    standard_duration = fields.Float(string='Standard Duration (Hours)')