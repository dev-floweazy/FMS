# -*- encoding: utf-8 -*-
import base64
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FMSConsolidatedInvoice(models.Model):
    _name = 'fms.consolidated.invoice'
    _description = 'FMS Consolidated Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, partner_id'

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True)
    date_from = fields.Date(string='Period From', required=True, tracking=True)
    date_to = fields.Date(string='Period To', required=True, tracking=True)

    billing_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('on_demand', 'On-Demand'),
    ], string='Billing Frequency', default='monthly', required=True)

    site_id = fields.Many2one('fms.site', string='Site Filter')
    contract_ref = fields.Char(string='Contract Reference')

    job_ids = fields.Many2many(
        'fms.job',
        'fms_consolidated_invoice_job_rel',
        'consolidated_id',
        'job_id',
        string='Jobs',
    )

    line_ids = fields.One2many(
        'fms.consolidated.invoice.line',
        'consolidated_id',
        string='Summary Lines',
    )

    invoice_id = fields.Many2one(
        'account.move', string='Invoice', readonly=True, tracking=True)
    invoice_state = fields.Selection(
        related='invoice_id.state', string='Invoice Status', store=True)
    attachment_id = fields.Many2one(
        'ir.attachment', string='Ticket Detail Attachment', readonly=True)

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total',
        store=True,
        currency_field='currency_id',
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status', tracking=True)

    notes = fields.Text(string='Internal Notes')

    # ----------------------------------------------------------------
    # Computes
    # ----------------------------------------------------------------
    @api.depends('partner_id', 'date_from', 'date_to', 'billing_frequency')
    def _compute_name(self):
        for rec in self:
            if rec.partner_id and rec.date_from and rec.date_to:
                freq = (rec.billing_frequency or 'on_demand')[:3].upper()
                rec.name = (
                    f"CINV/{rec.partner_id.name[:10].upper()}/"
                    f"{rec.date_from.strftime('%Y%m%d')}-"
                    f"{rec.date_to.strftime('%Y%m%d')}/{freq}"
                )
            else:
                rec.name = _('New')

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_('Period From must be before Period To.'))

    # ----------------------------------------------------------------
    # Collect eligible jobs
    # ----------------------------------------------------------------
    def action_collect_jobs(self):
        self.ensure_one()
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['completed']),
        ]
        if self.date_from:
            domain.append(('scheduled_date', '>=',
                            fields.Datetime.from_string(str(self.date_from))))
        if self.date_to:
            domain.append(('scheduled_date', '<=',
                            fields.Datetime.from_string(str(self.date_to) + ' 23:59:59')))
        if self.site_id:
            domain.append(('site_id', '=', self.site_id.id))

        jobs = self.env['fms.job'].search(domain)
        if not jobs:
            raise UserError(_(
                'No eligible completed jobs found for %s between %s and %s.'
            ) % (self.partner_id.name, self.date_from, self.date_to))

        self.job_ids = [(6, 0, jobs.ids)]
        self._build_summary_lines()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Jobs Collected'),
                'message': _('%d job(s) collected.') % len(jobs),
                'type': 'success',
            }
        }

    # ----------------------------------------------------------------
    # Build grouped summary lines
    # ----------------------------------------------------------------
    def _build_summary_lines(self):
        self.ensure_one()
        self.line_ids.unlink()

        grouped = defaultdict(lambda: {'qty': 0.0, 'amount': 0.0, 'count': 0})
        for job in self.job_ids:
            for line in job.job_line_ids.filtered(
                lambda l: l.scope_state not in ('rejected', 'pending')
            ):
                key = (line.product_id.id, line.product_id.name)
                grouped[key]['qty'] += line.quantity
                grouped[key]['amount'] += line.subtotal_price
                grouped[key]['count'] += 1

        new_lines = []
        for (product_id, product_name), data in grouped.items():
            new_lines.append((0, 0, {
                'product_id': product_id,
                'name': product_name,
                'quantity': data['qty'],
                'subtotal': data['amount'],
                'ticket_count': data['count'],
            }))
        self.line_ids = new_lines

    # ----------------------------------------------------------------
    # Workflow actions
    # ----------------------------------------------------------------
    def action_confirm(self):
        self.ensure_one()
        if not self.job_ids:
            raise UserError(_('Please collect jobs before confirming.'))
        self.state = 'confirmed'

    def action_generate_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(
                _('Invoice already generated: %s') % self.invoice_id.name)
        if not self.job_ids:
            raise UserError(_('No jobs linked to this consolidated invoice.'))
        if not self.line_ids:
            self._build_summary_lines()

        invoice_lines = []
        for line in self.line_ids:
            product = line.product_id
            account = (
                product.property_account_income_id
                or product.categ_id.property_account_income_categ_id
            )
            if not account:
                raise UserError(_(
                    'No income account configured for product: %s.\n'
                    'Please set it in the product or its category.'
                ) % product.name)

            avg_price = (line.subtotal / line.quantity) if line.quantity else 0.0
            invoice_lines.append((0, 0, {
                'product_id': product.id,
                'name': line.name,
                'quantity': line.quantity,
                'price_unit': avg_price,
                'account_id': account.id,
            }))

        narration = (
            f"Consolidated Invoice\n"
            f"Period: {self.date_from} to {self.date_to}\n"
            f"Billing Frequency: {self.billing_frequency}"
        )
        if self.contract_ref:
            narration += f"\nContract: {self.contract_ref}"
        if self.site_id:
            narration += f"\nSite: {self.site_id.name}"

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'narration': narration,
            'ref': self.name,
        })

        self.invoice_id = invoice.id
        self.state = 'invoiced'
        self.job_ids.filtered(
            lambda j: j.state == 'completed'
        ).write({'state': 'invoiced'})

        invoice.action_post()
        self._generate_ticket_attachment()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _generate_ticket_attachment(self):
        self.ensure_one()
        rows = ['Job,Ticket,Site,Scheduled Date,Product,Description,Qty,Unit Price,Subtotal']
        for job in self.job_ids.sorted('name'):
            ticket_name = job.ticket_id.name if job.ticket_id else ''
            site_name = job.site_id.name if job.site_id else ''
            sched = (job.scheduled_date.strftime('%Y-%m-%d')
                     if job.scheduled_date else '')
            for line in job.job_line_ids.filtered(
                lambda l: l.scope_state not in ('rejected', 'pending')
            ):
                desc = (line.description or '').replace('\n', ' ')
                rows.append(
                    f'"{job.name}","{ticket_name}","{site_name}","{sched}",'
                    f'"{line.product_id.name}","{desc}",'
                    f'{line.quantity},{line.unit_price},{line.subtotal_price}'
                )

        csv_bytes = base64.b64encode('\n'.join(rows).encode('utf-8'))
        filename = f'ticket_detail_{self.name.replace("/", "_")}.csv'

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': csv_bytes,
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'mimetype': 'text/csv',
        })
        self.attachment_id = attachment.id
        self.invoice_id.message_post(
            body=_(
                'Ticket-wise detail attached for period %s – %s.'
            ) % (self.date_from, self.date_to),
            attachment_ids=[attachment.id],
        )

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No invoice generated yet.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'invoiced' and self.invoice_id.state == 'posted':
            raise UserError(_(
                'Cannot cancel: invoice %s is already posted. '
                'Please reset or cancel the invoice first.'
            ) % self.invoice_id.name)
        self.state = 'cancelled'

    def action_reset_draft(self):
        self.ensure_one()
        if self.state == 'invoiced':
            raise UserError(_('Cannot reset to draft once invoiced.'))
        self.state = 'draft'


class FMSConsolidatedInvoiceLine(models.Model):
    _name = 'fms.consolidated.invoice.line'
    _description = 'FMS Consolidated Invoice Summary Line'

    consolidated_id = fields.Many2one(
        'fms.consolidated.invoice', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Product', required=True)
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(
        string='Total Qty', digits='Product Unit of Measure')
    subtotal = fields.Monetary(
        string='Subtotal', currency_field='currency_id')
    currency_id = fields.Many2one(
        related='consolidated_id.currency_id', store=True)
    ticket_count = fields.Integer(string='# Job Lines')