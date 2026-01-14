# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class FMSSLARule(models.Model):
    _name = 'fms.sla.rule'
    _description = 'SLA Rule'

    name = fields.Char(required=True)
    service_category_id = fields.Many2one('fms.service.category')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ])

    response_time = fields.Float(string='Response Time (Hours)')
    resolution_time = fields.Float(string='Resolution Time (Hours)')

    apply_to_all = fields.Boolean()
    partner_ids = fields.Many2many('res.partner')