# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class FMSSite(models.Model):
    _name = 'fms.site'
    _description = 'Customer Site/Location'

    name = fields.Char(required=True)
    code = fields.Char()
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)

    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one('res.country.state')
    zip = fields.Char()
    country_id = fields.Many2one('res.country')

    contact_person = fields.Char()
    contact_phone = fields.Char()
    contact_email = fields.Char()

    active = fields.Boolean(default=True)
    notes = fields.Text()
    ticket_count = fields.Integer('Tickets count')
    job_count = fields.Integer('Jobs count')

    def action_view_tickets(self):
        pass

    def action_view_jobs(self):
        pass