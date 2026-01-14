# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class FMSConsolidatedInvoice(models.Model):
    _name = 'fms.consolidated.invoice'
    _description = 'Monthly Consolidated Invoice'

    name = fields.Char(compute='_compute_name')
    partner_id = fields.Many2one('res.partner', required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    job_ids = fields.Many2many('fms.job', string='Jobs')
    invoice_id = fields.Many2one('account.move', string='Invoice')

    total_amount = fields.Monetary(compute='_compute_total')
    currency_id = fields.Many2one('res.currency')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced')
    ], default='draft')

    def action_generate_invoice(self):
        invoice_lines = []
        for job in self.job_ids:
            for line in job.job_line_ids:
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': f'{job.name} - {line.description or line.product_id.name}',
                    'quantity': line.quantity,
                    'price_unit': line.unit_price,
                    'account_id': line.product_id.property_account_income_id.id
                }))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines
        })

        self.invoice_id = invoice.id
        self.state = 'invoiced'
        self.job_ids.write({'state': 'invoiced'})