# -*- encoding: utf-8 -*-
from odoo import api, fields, models

class HREmployee(models.Model):
    _inherit = 'hr.employee'
    
    timesheet_cost = fields.Float(
        string='Hourly Rate',
        help='Hourly cost rate for timesheet entries and job cost calculation'
    )
