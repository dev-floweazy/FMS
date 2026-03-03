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

    ticket_count = fields.Integer(
        string='Tickets count',
        compute='_compute_ticket_job_count',
        store=False
    )

    job_count = fields.Integer(
        string='Jobs count',
        compute='_compute_ticket_job_count',
        store=False
    )

    # ---------------------------------------------------------
    # Counts
    # ---------------------------------------------------------

    def _compute_ticket_job_count(self):
        Ticket = self.env['fms.ticket']
        Job = self.env['fms.job']

        for rec in self:
            rec.ticket_count = Ticket.search_count([
                ('site_id', '=', rec.id)
            ])
            rec.job_count = Job.search_count([
                ('site_id', '=', rec.id)
            ])

    # ---------------------------------------------------------
    # Smart buttons
    # ---------------------------------------------------------

    def action_view_tickets(self):
        self.ensure_one()

        return {
            'name': 'Tickets',
            'type': 'ir.actions.act_window',
            'res_model': 'fms.ticket',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', '=', self.id)
            ],
            'context': {
                'default_site_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }

    def action_view_jobs(self):
        self.ensure_one()

        return {
            'name': 'Jobs',
            'type': 'ir.actions.act_window',
            'res_model': 'fms.job',
            'view_mode': 'list,form',
            'domain': [
                ('site_id', '=', self.id)
            ],
            'context': {
                'default_site_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }