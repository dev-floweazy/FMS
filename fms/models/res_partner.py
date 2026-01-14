# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_fms_vendor = fields.Boolean(string='Is FMS Vendor')
    vendor_service_category_ids = fields.Many2many(
        'fms.service.category',
        string='Service Categories'
    )
    vendor_rating = fields.Selection([
        ('1', '⭐'),
        ('2', '⭐⭐'),
        ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'),
        ('5', '⭐⭐⭐⭐⭐')
    ])
    vendor_job_ids = fields.One2many('fms.job', 'vendor_id',
                                     string='Jobs')