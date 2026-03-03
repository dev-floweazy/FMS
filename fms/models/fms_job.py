# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import timedelta


class FMSJob(models.Model):
    _name = 'fms.job'
    _description = 'FMS Job/Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Job Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('fms.job') or 'JOB'
    )
    ticket_id = fields.Many2one('fms.ticket', string='Ticket', required=True)
    partner_id = fields.Many2one(related='ticket_id.partner_id', store=True)
    site_id = fields.Many2one(related='ticket_id.site_id', store=True)
    service_category_id = fields.Many2one(
        related='ticket_id.service_category_id', store=True)

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain=[('is_fms_vendor', '=', True)]
    )
    assigned_user_id = fields.Many2one('res.users', string='Assigned To')

    scheduled_date = fields.Datetime(string='Scheduled Date')
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    job_line_ids = fields.One2many(
        'fms.job.line', 'job_id', string='Job Lines'
    )

    # Pricing fields
    total_cost = fields.Monetary(compute='_compute_totals', store=True)
    total_price = fields.Monetary(compute='_compute_totals', store=True)
    margin = fields.Monetary(compute='_compute_totals', store=True)
    margin_percent = fields.Float(compute='_compute_totals', store=True)

    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # Invoicing
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    purchase_order_id = fields.Many2one('purchase.order', string='Vendor PO')
    invoice_id = fields.Many2one('account.move', string='Customer Invoice')
    vendor_bill_id = fields.Many2one('account.move', string='Vendor Bill')

    description = fields.Text(string='Description')
    quantity = fields.Float(default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    unit_cost = fields.Monetary(string='Unit Cost')
    subtotal_cost = fields.Monetary(string='Subtotal Cost')
    unit_price = fields.Monetary(string='Unit Price')
    subtotal_price = fields.Monetary('Subtotal Price')

    work_summary = fields.Char('Work Summary')

    completion_photos = fields.Many2many(
        'ir.attachment',
        string="Completion Photos",
        help="Photos taken after the job is completed."
    )

    customer_signature = fields.Image(
        string="Signature",
        copy=False, attachment=True, max_width=1024, max_height=1024
    )

    customer_feedback = fields.Text('Customer Feedback')
    notes = fields.Html('Notes')

    # ---------------------------------------------------------
    # SLA
    # ---------------------------------------------------------

    sla_rule_id = fields.Many2one(
        'fms.sla.rule',
        compute='_compute_sla_rule',
        store=True
    )

    sla_start_datetime = fields.Datetime(
        readonly=True,
        copy=False
    )

    sla_response_deadline = fields.Datetime(
        compute='_compute_sla_deadlines',
        store=True
    )

    sla_resolution_deadline = fields.Datetime(
        compute='_compute_sla_deadlines',
        store=True
    )

    sla_breached = fields.Boolean(
        compute='_compute_sla_breached',
        store=False
    )

    # ---------------------------------------------------------
    # COMPUTE TOTALS
    # ---------------------------------------------------------

    @api.depends('job_line_ids.subtotal_cost', 'job_line_ids.subtotal_price')
    def _compute_totals(self):
        for job in self:
            job.total_cost = sum(job.job_line_ids.mapped('subtotal_cost'))
            job.total_price = sum(job.job_line_ids.mapped('subtotal_price'))
            job.margin = job.total_price - job.total_cost
            job.margin_percent = (
                job.margin / job.total_price
            ) if job.total_price else 0

    # ---------------------------------------------------------
    # SLA rule selection
    # ---------------------------------------------------------

    @api.depends('service_category_id', 'ticket_id.priority')
    def _compute_sla_rule(self):
        for job in self:
            priority = job.ticket_id.priority if job.ticket_id else False

            job.sla_rule_id = self.env['fms.sla.rule'].search([
                ('service_category_id', '=', job.service_category_id.id),
                ('priority', '=', priority),
                ('active', '=', True)
            ], limit=1)

    # ---------------------------------------------------------
    # SLA start at job creation
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        now = fields.Datetime.now()
        for job in records:
            if job.sla_rule_id:
                job.sla_start_datetime = now

        return records

    # ---------------------------------------------------------
    # SLA deadlines
    # ---------------------------------------------------------

    @api.depends('sla_start_datetime', 'sla_rule_id')
    def _compute_sla_deadlines(self):

        for job in self:

            job.sla_response_deadline = False
            job.sla_resolution_deadline = False

            if not job.sla_start_datetime or not job.sla_rule_id:
                continue

            job.sla_response_deadline = job.sla_start_datetime + timedelta(
                hours=job.sla_rule_id.response_time
            )

            job.sla_resolution_deadline = job.sla_start_datetime + timedelta(
                hours=job.sla_rule_id.resolution_time
            )

    # ---------------------------------------------------------
    # SLA breach
    # ---------------------------------------------------------

    def _compute_sla_breached(self):

        now = fields.Datetime.now()

        for job in self:
            job.sla_breached = False

            if job.sla_resolution_deadline and now > job.sla_resolution_deadline:
                job.sla_breached = True

    # ---------------------------------------------------------
    # PLACEHOLDER METHODS (kept as you asked)
    # ---------------------------------------------------------

    def action_create_sale_order(self):
        # Create SO from job lines
        pass

    def action_create_purchase_order(self):
        # Create PO for vendor
        pass

    def action_assign_vendor(self):
        pass

    def action_schedule(self):
        pass

    def action_start(self):
        pass

    def action_complete(self):
        pass

    def action_create_invoice(self):
        pass

    def action_cancel(self):
        pass

    # Smart button : Create / Open Sales Order

    def action_view_sale_order(self):
        self.ensure_one()

        if not self.sale_order_id:

            if not self.partner_id:
                raise UserError("Please set customer before creating Sales Order.")

            if not self.job_line_ids:
                raise UserError("Please add job lines before creating Sales Order.")

            so_lines = []

            for line in self.job_line_ids:

                if not line.product_id:
                    raise UserError("Please select product in all job lines.")

                # Job line unit_price → SO line price_unit

                so_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.name,
                    'product_uom_qty': line.quantity,
                    'product_uom_id': line.uom_id.id or line.product_id.uom_id.id,

                    # >>> REQUIRED
                    'price_unit': line.unit_price,
                }))

            so = self.env['sale.order'].with_context(
                default_product_uom=False,
                default_product_uom_qty=False,
            ).create({
                'partner_id': self.partner_id.id,
                'origin': self.name,
                'order_line': so_lines,
            })

            self.sale_order_id = so.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    # Smart button : Create / Open Purchase Order

    def action_view_purchase_order(self):
        self.ensure_one()

        if not self.vendor_id:
            raise UserError("Please select a vendor before creating Vendor PO.")

        if not self.job_line_ids:
            raise UserError("Please add job lines before creating Purchase Order.")

        if not self.purchase_order_id:

            po_lines = []

            for line in self.job_line_ids:

                if not line.product_id:
                    raise UserError("Please select product in all job lines.")

                # --------------------------------------------------
                # LOGIC ADDED:
                # Job line unit_cost → PO line price_unit
                # --------------------------------------------------
                po_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.name,
                    'product_qty': line.quantity,
                    'product_uom_id': line.uom_id.id or line.product_id.uom_id.id,

                    # >>> REQUIRED
                    'price_unit': line.unit_cost,

                    'date_planned': fields.Datetime.now(),
                }))

            po = self.env['purchase.order'].create({
                'partner_id': self.vendor_id.id,
                'origin': self.name,
                'order_line': po_lines,
            })

            self.purchase_order_id = po.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
            'target': 'current',
        }

    # Smart button : Open Customer Invoice

    def action_view_invoice(self):
        self.ensure_one()

        invoice = self.invoice_id

        if not invoice and self.sale_order_id:
            invoices = self.sale_order_id.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice'
            )

            if invoices:
                invoice = invoices[0]
                self.invoice_id = invoice.id

        if not invoice:
            raise UserError(
                "No invoice created for this job. Please create the invoice first."
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }

    def compute_margin(self):
        pass


# ---------------------------------------------------------
# Job Lines model
# ---------------------------------------------------------


class FMSJobLine(models.Model):
    _name = 'fms.job.line'
    _description = 'FMS Job Line'

    job_id = fields.Many2one(
        'fms.job',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        # domain=[('is_fms_service', '=', True)],
        required=True
    )

    description = fields.Text()
    quantity = fields.Float(default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')

    # Pricing
    unit_cost = fields.Monetary(string='Unit Cost (Vendor)')
    unit_price = fields.Monetary(string='Unit Price (Customer)')

    subtotal_cost = fields.Monetary(
        compute='_compute_subtotals',
        store=True
    )
    subtotal_price = fields.Monetary(
        compute='_compute_subtotals',
        store=True
    )
    margin = fields.Monetary(
        compute='_compute_subtotals',
        store=True
    )

    currency_id = fields.Many2one(
        related='job_id.currency_id',
        store=True
    )

    # COMPUTE LINE TOTALS

    @api.depends('quantity', 'unit_cost', 'unit_price')
    def _compute_subtotals(self):
        for line in self:
            line.subtotal_cost = line.quantity * line.unit_cost
            line.subtotal_price = line.quantity * line.unit_price
            line.margin = line.subtotal_price - line.subtotal_cost

    # ONCHANGE PRODUCT

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id

            # ---------------------------------------------------------
            # EXISTING LOGIC (kept as is)
            # ---------------------------------------------------------
            rate_card = self.env['fms.rate.card'].search([
                ('partner_id', '=', self.job_id.partner_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)

            if rate_card:
                self.unit_price = rate_card.unit_price

            # ---------------------------------------------------------
            # NEW LOGIC ADDED (as you asked)
            # Using get_rate_for_customer()
            # ---------------------------------------------------------
            partner_id = self.job_id.partner_id.id
            product_id = self.product_id.id

            # job date used for validity check
            job_date = (
                self.job_id.scheduled_date.date()
                if self.job_id.scheduled_date
                else fields.Date.context_today(self)
            )

            rate = self.env['fms.rate.card'].get_rate_for_customer(
                partner_id,
                product_id,
                job_date
            )

            if rate:
                self.unit_price = rate.unit_price