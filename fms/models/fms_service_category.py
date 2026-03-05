# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class FMSServiceCategory(models.Model):
    _name = 'fms.service.category'
    _description = 'FMS Service Category'

    name = fields.Char(required=True)
    code = fields.Char()
    parent_id = fields.Many2one('fms.service.category', string='Parent Category')
    child_ids = fields.One2many('fms.service.category', 'parent_id')
    default_sla_hours = fields.Float(string='Default SLA (Hours)')
    active = fields.Boolean(default=True)
    product_ids = fields.Many2many('product.product')
    default_code = fields.Char('Internal Reference', index=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    product_id = fields.Many2one('product.product', string='Product')
    standard_price = fields.Float(related='product_id.standard_price', string='Standard Price')
    list_price = fields.Float('Price', digits='Product Price', required=True, default=0.0)
    response_time = fields.Float(
        string='Response Time (Hours)',
        required=True)
    resolution_time = fields.Float(
        string='Resolution Time (Hours)',
        required=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], default='1', tracking=True)