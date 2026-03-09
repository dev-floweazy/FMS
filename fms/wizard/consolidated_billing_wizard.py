# -*- encoding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ConsolidatedBillingWizard(models.TransientModel):
    _name = 'fms.consolidated.billing.wizard'
    _description = 'Consolidated Billing Run Wizard'

    billing_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('on_demand', 'On-Demand'),
    ], string='Billing Frequency', default='monthly', required=True)

    date_from = fields.Date(string='Period From', required=True)
    date_to = fields.Date(string='Period To', required=True)

    partner_ids = fields.Many2many(
        'res.partner',
        string='Customers',
        help='Leave empty to process ALL eligible customers.',
    )
    site_id = fields.Many2one('fms.site', string='Site Filter')

    auto_confirm = fields.Boolean(string='Auto-Confirm', default=False)
    auto_invoice = fields.Boolean(string='Auto-Generate Invoices', default=False)

    @api.onchange('billing_frequency')
    def _onchange_billing_frequency(self):
        today = fields.Date.today()
        if self.billing_frequency == 'monthly':
            self.date_from = today.replace(day=1) - relativedelta(months=1)
            self.date_to = today.replace(day=1) - relativedelta(days=1)
        elif self.billing_frequency == 'weekly':
            monday = today - relativedelta(days=today.weekday() + 7)
            self.date_from = monday
            self.date_to = monday + relativedelta(days=6)
        else:
            self.date_from = today.replace(day=1)
            self.date_to = today

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.today()
        res['date_from'] = today.replace(day=1) - relativedelta(months=1)
        res['date_to'] = today.replace(day=1) - relativedelta(days=1)
        return res

    def action_run_billing(self):
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(_('Period From must be before Period To.'))

        domain = [('state', 'in', ['completed'])]
        if self.date_from:
            domain.append(('scheduled_date', '>=',
                            fields.Datetime.from_string(str(self.date_from))))
        if self.date_to:
            domain.append(('scheduled_date', '<=',
                            fields.Datetime.from_string(str(self.date_to) + ' 23:59:59')))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.site_id:
            domain.append(('site_id', '=', self.site_id.id))

        jobs = self.env['fms.job'].search(domain)
        if not jobs:
            raise UserError(_(
                'No eligible completed jobs found for the selected period.'
            ))

        # Group by (partner_id, site_id)
        groups = {}
        for job in jobs:
            key = (job.partner_id.id, job.site_id.id if self.site_id else 0)
            groups.setdefault(key, self.env['fms.job'])
            groups[key] |= job

        created = self.env['fms.consolidated.invoice']

        for (partner_id, site_id), group_jobs in groups.items():
            # Skip duplicate runs for same period + customer
            existing = self.env['fms.consolidated.invoice'].search([
                ('partner_id', '=', partner_id),
                ('date_from', '=', self.date_from),
                ('date_to', '=', self.date_to),
                ('billing_frequency', '=', self.billing_frequency),
                ('state', 'not in', ['cancelled']),
            ], limit=1)

            if existing:
                existing.job_ids = [(4, j.id) for j in group_jobs]
                existing._build_summary_lines()
                created |= existing
                continue

            vals = {
                'partner_id': partner_id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'billing_frequency': self.billing_frequency,
                'job_ids': [(6, 0, group_jobs.ids)],
            }
            if site_id:
                vals['site_id'] = site_id

            rec = self.env['fms.consolidated.invoice'].create(vals)
            rec._build_summary_lines()
            created |= rec

        if self.auto_confirm or self.auto_invoice:
            for rec in created.filtered(lambda r: r.state == 'draft'):
                rec.action_confirm()

        if self.auto_invoice:
            for rec in created.filtered(lambda r: r.state == 'confirmed'):
                rec.action_generate_invoice()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Consolidated Invoices'),
            'res_model': 'fms.consolidated.invoice',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
        }