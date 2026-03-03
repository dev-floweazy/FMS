# -*- coding: utf-8 -*-

from odoo import fields, models


class FMSSLARule(models.Model):
    _name = 'fms.sla.rule'
    _description = 'SLA Rule'
    _rec_name = 'name'

    name = fields.Char(required=True)

    service_category_id = fields.Many2one(
        'fms.service.category',
        required=True
    )

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], required=True, default='1')

    response_time = fields.Float(
        string='Response Time (Hours)',
        required=True
    )

    resolution_time = fields.Float(
        string='Resolution Time (Hours)',
        required=True
    )

    active = fields.Boolean(default=True)
    resolution_time = fields.Float(string='Resolution Time (Hours)')

    apply_to_all = fields.Boolean()
    partner_ids = fields.Many2many('res.partner')