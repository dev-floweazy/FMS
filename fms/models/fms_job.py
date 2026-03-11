# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _
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

    # Pricing
    total_cost = fields.Monetary(compute='_compute_totals', store=True)
    total_price = fields.Monetary(compute='_compute_totals', store=True)
    margin = fields.Monetary(compute='_compute_totals', store=True)
    margin_percent = fields.Float(compute='_compute_totals', store=True)
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # Invoicing links
    sale_order_id = fields.Many2one('sale.order', string='Latest Sales Order')
    purchase_order_id = fields.Many2one('purchase.order', string='Latest Vendor PO')
    invoice_id = fields.Many2one('account.move', string='Customer Invoice')
    vendor_bill_id = fields.Many2one('account.move', string='Vendor Bill')

    # Smart button counts
    sale_order_count = fields.Integer(
        compute='_compute_sale_order_count', store=False, string='Sales Orders'
    )
    purchase_order_count = fields.Integer(
        compute='_compute_purchase_order_count', store=False, string='Vendor POs'
    )
    scope_approval_count = fields.Integer(
        compute='_compute_scope_approval_count', store=False, string='Approvals'
    )

    description = fields.Text(string='Description')
    work_summary = fields.Char('Work Summary')
    completion_photos = fields.Many2many(
        'ir.attachment', string="Completion Photos")
    customer_signature = fields.Image(
        string="Signature", copy=False, attachment=True,
        max_width=1024, max_height=1024)
    customer_feedback = fields.Text('Customer Feedback')
    notes = fields.Html('Notes')

    auto_so_po_created = fields.Boolean(default=False, copy=False)

    # ---------------------------------------------------------
    # SLA
    # ---------------------------------------------------------
    sla_rule_id = fields.Many2one(
        'fms.sla.rule', compute='_compute_sla_rule', store=True)
    sla_start_datetime = fields.Datetime(readonly=True, copy=False)
    sla_response_deadline = fields.Datetime(
        compute='_compute_sla_deadlines', store=True)
    sla_resolution_deadline = fields.Datetime(
        compute='_compute_sla_deadlines', store=True)
    sla_breached = fields.Boolean(
        compute='_compute_sla_breached', store=False)

    vendor_task_id = fields.Many2one('project.task', string='Vendor Task', copy=False)
    task_count = fields.Integer(
        string="Tasks",
        compute="_compute_task_count"
    )

    def _create_or_update_project_task(self, state):
        """Create/update project.task for vendor and customer when job is assigned or scheduled."""
        ProjectTask = self.env['project.task'].sudo()

        for job in self:
            # ── Determine deadline ──────────────────────────────────────
            deadline = False
            if state == 'scheduled' and job.scheduled_date:
                deadline = job.scheduled_date.date()

            task_name = f'[{job.name}] {job.ticket_id.name if job.ticket_id else "Job"}'
            description = f"""
                <p><b>Job:</b> {job.name}</p>
                <p><b>Site:</b> {job.site_id.name if job.site_id else '-'}</p>
                <p><b>Service:</b> {job.service_category_id.name if job.service_category_id else '-'}</p>
                <p><b>Scheduled:</b> {job.scheduled_date or '-'}</p>
                <p><b>Description:</b> {job.description or '-'}</p>
            """

            # ── VENDOR TASK ─────────────────────────────────────────────
            if job.vendor_id:
                # # Find or create vendor project
                # vendor_project = self.env['project.project'].sudo().search([
                #     ('name', '=', f'FMS Vendor: {job.vendor_id.name}'),
                # ], limit=1)
                # if not vendor_project:

                vendor_project = self.env['project.project'].sudo().create({
                    'name': f'FMS Vendor: {job.vendor_id.name}',
                    'partner_id': job.vendor_id.id,
                    'privacy_visibility': 'employees',
                })

                # Check if task already exists for this job
                # vendor_task = ProjectTask.search([
                #     ('project_id', '=', vendor_project.id),
                #     ('fms_job_id', '=', job.id),
                # ], limit=1)

                task_vals = {
                    'name': task_name,
                    'project_id': vendor_project.id,
                    'partner_id': job.vendor_id.id,
                    'description': description,
                    'fms_job_id': job.id,
                    'date_deadline': deadline,
                }
                if job.assigned_user_id:
                    task_vals['user_ids'] = [(4, job.assigned_user_id.id)]

                # if vendor_task:
                # vendor_task.write(task_vals)
                # else:
                vendor_task = ProjectTask.create(task_vals)

                job.vendor_task_id = vendor_task.id
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
                job.margin / job.total_price) if job.total_price else 0

    # ---------------------------------------------------------
    # SMART BUTTON COUNTS
    # ---------------------------------------------------------
    def _compute_sale_order_count(self):
        for job in self:
            job.sale_order_count = (
                self.env['sale.order'].search_count(
                    [('origin', 'like', job.name)])
                if job.name and job.name != 'JOB' else 0
            )

    def _compute_purchase_order_count(self):
        for job in self:
            job.purchase_order_count = (
                self.env['purchase.order'].search_count(
                    [('origin', '=', job.name)])
                if job.name and job.name != 'JOB' else 0
            )

    def _compute_scope_approval_count(self):
        for job in self:
            job.scope_approval_count = self.env['fms.scope.approval'].search_count(
                [('job_id', '=', job.id)])

    # ---------------------------------------------------------
    # SLA
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

    @api.depends('sla_start_datetime', 'sla_rule_id')
    def _compute_sla_deadlines(self):
        for job in self:
            job.sla_response_deadline = False
            job.sla_resolution_deadline = False
            if not job.sla_start_datetime or not job.sla_rule_id:
                continue
            job.sla_response_deadline = job.sla_start_datetime + timedelta(
                hours=job.sla_rule_id.response_time)
            job.sla_resolution_deadline = job.sla_start_datetime + timedelta(
                hours=job.sla_rule_id.resolution_time)

    @api.depends('sla_resolution_deadline')
    def _compute_sla_breached(self):
        now = fields.Datetime.now()
        for job in self:
            job.sla_breached = bool(
                job.sla_resolution_deadline
                and now > job.sla_resolution_deadline)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        now = fields.Datetime.now()
        for job in records:
            if job.sla_rule_id and not job.sla_start_datetime:
                job.sla_start_datetime = now
        return records

    # ---------------------------------------------------------
    # AUTO SO/PO — only original scope lines
    # ---------------------------------------------------------
    def _auto_create_so_po(self):
        for job in self:
            eligible = job.job_line_ids.filtered(
                lambda l: l.line_type == 'original'
                and l.scope_state == 'na'
            )
            if not eligible:
                continue

            lines_ready = all(
                l.product_id and l.quantity > 0
                and l.uom_id and l.unit_cost >= 0 and l.unit_price >= 0
                for l in eligible
            )
            if not lines_ready:
                continue

            so_created = False
            po_created = False

            existing_so_keys = set()
            if job.sale_order_id:
                for sol in job.sale_order_id.order_line:
                    existing_so_keys.add(
                        (sol.product_id.id, sol.product_uom_qty, sol.price_unit))

            new_so_lines = [
                l for l in eligible
                if (l.product_id.id, l.quantity, l.unit_price)
                not in existing_so_keys
            ]

            if job.partner_id and new_so_lines:
                so_vals = [(0, 0, {
                    'product_id': l.product_id.id,
                    'name': l.description or l.product_id.name,
                    'product_uom_qty': l.quantity,
                    'product_uom_id': l.uom_id.id or l.product_id.uom_id.id,
                    'price_unit': l.unit_price,
                }) for l in new_so_lines]
                so = self.env['sale.order'].create({
                    'partner_id': job.partner_id.id,
                    'origin': job.name,
                    'order_line': so_vals,
                })
                job.sale_order_id = so.id
                so_created = True

            existing_po_keys = set()
            if job.purchase_order_id:
                for pol in job.purchase_order_id.order_line:
                    existing_po_keys.add(
                        (pol.product_id.id, pol.product_qty, pol.price_unit))

            new_po_lines = [
                l for l in eligible
                if (l.product_id.id, l.quantity, l.unit_cost)
                not in existing_po_keys
            ]

            if job.vendor_id and new_po_lines:
                po_vals = [(0, 0, {
                    'product_id': l.product_id.id,
                    'name': l.description or l.product_id.name,
                    'product_qty': l.quantity,
                    'product_uom_id': l.uom_id.id or l.product_id.uom_id.id,
                    'price_unit': l.unit_cost,
                    'date_planned': fields.Datetime.now(),
                }) for l in new_po_lines]
                po = self.env['purchase.order'].create({
                    'partner_id': job.vendor_id.id,
                    'origin': job.name,
                    'order_line': po_vals,
                })
                job.purchase_order_id = po.id
                po_created = True

            if so_created or po_created:
                job.auto_so_po_created = True
                msg_parts = []
                if so_created:
                    msg_parts.append(
                        f'✅ Sales Order <a href="#" data-oe-model="sale.order" '
                        f'data-oe-id="{job.sale_order_id.id}">'
                        f'{job.sale_order_id.name}</a> created automatically.')
                if po_created:
                    msg_parts.append(
                        f'✅ Purchase Order <a href="#" data-oe-model="purchase.order" '
                        f'data-oe-id="{job.purchase_order_id.id}">'
                        f'{job.purchase_order_id.name}</a> created automatically.')
                job.message_post(body=' '.join(msg_parts))

    # ---------------------------------------------------------
    # SCOPE APPROVAL TRIGGER
    # ---------------------------------------------------------
    def _check_and_trigger_scope_approval(self, additional_lines):
        for job in self:
            if not additional_lines:
                continue

            rule = self.env['fms.approval.rule'].search(
                [('active', '=', True)],
                order='amount_threshold desc',
                limit=1
            )

            if not rule:
                for line in additional_lines:
                    line.scope_state = 'approved'
                job.message_post(
                    body='ℹ️ No approval rule configured. '
                         'Additional scope lines auto-approved.'
                )
                continue

            additional_total = sum(
                l.quantity * l.unit_price for l in additional_lines
            )

            if additional_total <= rule.amount_threshold:
                for line in additional_lines:
                    line.scope_state = 'approved'
                job.message_post(
                    body=f'ℹ️ Additional scope total '
                         f'({additional_total:.2f}) is within the '
                         f'threshold ({rule.amount_threshold:.2f}). '
                         f'Auto-approved.'
                )
                self._create_so_po_for_approved_additional(additional_lines)
                continue

            for line in additional_lines:
                line.scope_state = 'pending'

            approval_line_vals = [(0, 0, {
                'job_line_id': line.id,
                'product_id': line.product_id.id,
                'description': line.description,
                'quantity': line.quantity,
                'uom_id': line.uom_id.id,
                'unit_price': line.unit_price,
            }) for line in additional_lines]

            existing = self.env['fms.scope.approval'].search([
                ('job_id', '=', job.id),
                ('state', '=', 'pending'),
            ], limit=1)

            if existing:
                existing.write({'approval_line_ids': approval_line_vals})
                existing.message_post(
                    body=f'➕ {len(additional_lines)} new additional scope '
                         f'line(s) added to this request.'
                )
                job.message_post(
                    body=f'🔔 {len(additional_lines)} new additional scope line(s) '
                         f'added to pending approval '
                         f'<a href="#" data-oe-model="fms.scope.approval" '
                         f'data-oe-id="{existing.id}">{existing.name}</a>.'
                )
            else:
                approver = rule.approver_id
                approval = self.env['fms.scope.approval'].create({
                    'job_id': job.id,
                    'approval_rule_id': rule.id,
                    'approver_id': approver.id,
                    'approver_group_id': rule.approver_group_id.id
                    if rule.approver_group_id else False,
                    'approval_line_ids': approval_line_vals,
                })
                job.message_post(
                    body=f'🔔 Additional scope requires approval. Request '
                         f'<a href="#" data-oe-model="fms.scope.approval" '
                         f'data-oe-id="{approval.id}">{approval.name}</a> '
                         f'sent to <b>{approver.name}</b> for review. '
                         f'Total: {additional_total:.2f} exceeds '
                         f'threshold of {rule.amount_threshold:.2f}.'
                )

    # ---------------------------------------------------------
    # CREATE SO/PO FOR AUTO-APPROVED ADDITIONAL LINES
    # ---------------------------------------------------------
    def _create_so_po_for_approved_additional(self, lines):
        for job in self:
            if job.partner_id and lines:
                so_vals = [(0, 0, {
                    'product_id': l.product_id.id,
                    'name': l.description or l.product_id.name,
                    'product_uom_qty': l.quantity,
                    'product_uom_id': l.uom_id.id or l.product_id.uom_id.id,
                    'price_unit': l.unit_price,
                }) for l in lines]
                so = self.env['sale.order'].create({
                    'partner_id': job.partner_id.id,
                    'origin': job.name,
                    'order_line': so_vals,
                })
                job.sale_order_id = so.id
                job.message_post(
                    body=f'✅ Sales Order <a href="#" data-oe-model="sale.order" '
                         f'data-oe-id="{so.id}">{so.name}</a> created for '
                         f'auto-approved additional scope.'
                )

            if job.vendor_id and lines:
                po_vals = [(0, 0, {
                    'product_id': l.product_id.id,
                    'name': l.description or l.product_id.name,
                    'product_qty': l.quantity,
                    'product_uom_id': l.uom_id.id or l.product_id.uom_id.id,
                    'price_unit': l.unit_cost,
                    'date_planned': fields.Datetime.now(),
                }) for l in lines]
                po = self.env['purchase.order'].create({
                    'partner_id': job.vendor_id.id,
                    'origin': job.name,
                    'order_line': po_vals,
                })
                job.purchase_order_id = po.id
                job.message_post(
                    body=f'✅ Purchase Order <a href="#" data-oe-model="purchase.order" '
                         f'data-oe-id="{po.id}">{po.name}</a> created for '
                         f'auto-approved additional scope.'
                )

    # ---------------------------------------------------------
    # SMART BUTTONS
    # ---------------------------------------------------------

    def _compute_task_count(self):
        for job in self:
            job.task_count = self.env['project.task'].search_count([
                ('fms_job_id', '=', job.id)
            ])

    def action_view_tasks(self):
        self.ensure_one()

        tasks = self.env['project.task'].search([
            ('fms_job_id', '=', self.id)
        ])

        if len(tasks) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Task',
                'res_model': 'project.task',
                'view_mode': 'form',
                'res_id': tasks.id,
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Tasks',
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('fms_job_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_sale_orders(self):
        self.ensure_one()
        sale_orders = self.env['sale.order'].search(
            [('origin', 'like', self.name)])
        if not sale_orders:
            if not self.partner_id:
                raise UserError(
                    "Please set a customer before creating a Sales Order.")
            if not self.job_line_ids:
                raise UserError(
                    "Please add job lines before creating a Sales Order.")
            so_lines = []
            for line in self.job_line_ids:
                if not line.product_id:
                    raise UserError(
                        "Please select a product in all job lines.")
                so_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.name,
                    'product_uom_qty': line.quantity,
                    'product_uom_id': line.uom_id.id or line.product_id.uom_id.id,
                    'price_unit': line.unit_price,
                }))
            so = self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'origin': self.name,
                'order_line': so_lines,
            })
            self.sale_order_id = so.id
            sale_orders = so
        if len(sale_orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales Order',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': sale_orders.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Orders',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('origin', 'like', self.name)],
            'target': 'current',
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        purchase_orders = self.env['purchase.order'].search(
            [('origin', '=', self.name)])
        if not purchase_orders:
            if not self.vendor_id:
                raise UserError(
                    "Please select a vendor before creating a Purchase Order.")
            if not self.job_line_ids:
                raise UserError(
                    "Please add job lines before creating a Purchase Order.")
            po_lines = []
            for line in self.job_line_ids:
                if not line.product_id:
                    raise UserError(
                        "Please select a product in all job lines.")
                po_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.name,
                    'product_qty': line.quantity,
                    'product_uom_id': line.uom_id.id or line.product_id.uom_id.id,
                    'price_unit': line.unit_cost,
                    'date_planned': fields.Datetime.now(),
                }))
            po = self.env['purchase.order'].create({
                'partner_id': self.vendor_id.id,
                'origin': self.name,
                'order_line': po_lines,
            })
            self.purchase_order_id = po.id
            purchase_orders = po
        if len(purchase_orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Purchase Order',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': purchase_orders.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)],
            'target': 'current',
        }

    def action_view_invoice(self):
        self.ensure_one()
        invoice = self.invoice_id
        if not invoice and self.sale_order_id:
            invoices = self.sale_order_id.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice')
            if invoices:
                invoice = invoices[0]
                self.invoice_id = invoice.id
        if not invoice:
            raise UserError(
                "No invoice found. Please create the invoice from the Sales Order first.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }

    def action_view_scope_approvals(self):
        self.ensure_one()
        approvals = self.env['fms.scope.approval'].search(
            [('job_id', '=', self.id)])
        if len(approvals) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Scope Approval',
                'res_model': 'fms.scope.approval',
                'view_mode': 'form',
                'res_id': approvals.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Scope Approvals',
            'res_model': 'fms.scope.approval',
            'view_mode': 'list,form',
            'domain': [('job_id', '=', self.id)],
            'target': 'current',
        }

    # ---------------------------------------------------------
    # STATE ACTION METHODS
    # ---------------------------------------------------------
    def action_create_sale_order(self): pass
    def action_create_purchase_order(self): pass
    def action_assign_vendor(self): pass
    def compute_margin(self): pass

    def action_assign(self):
        for job in self:
            if job.state != 'draft':
                raise UserError(_('Only draft jobs can be assigned.'))
            job.state = 'assigned'
            job.message_post(body='📋 Job assigned.')
            job._create_or_update_project_task('assigned')

    def action_schedule(self):
        for job in self:
            if job.state not in ('draft', 'assigned'):
                raise UserError(_('Only draft or assigned jobs can be scheduled.'))
            if not job.scheduled_date:
                raise UserError(_('Please set a Scheduled Date before scheduling.'))
            job.state = 'scheduled'
            job._create_or_update_project_task('scheduled')
            job.message_post(body='📅 Job scheduled.')

    def action_start(self):
        for job in self:
            if job.state in ('completed', 'invoiced', 'cancelled'):
                raise UserError(_('Cannot start a completed, invoiced or cancelled job.'))
            job.state = 'in_progress'
            job.start_date = fields.Datetime.now()
            job.message_post(body='▶️ Job started.')

    def action_complete(self):
        for job in self:
            if job.state in ('invoiced', 'cancelled'):
                raise UserError(_('Cannot complete an invoiced or cancelled job.'))
            if not job.job_line_ids:
                raise UserError(_('Please add at least one job line before completing.'))
            job.state = 'completed'
            job.end_date = fields.Datetime.now()
            job.message_post(body='✅ Job marked as completed.')

    def action_create_invoice(self):
        for job in self:
            if job.state != 'completed':
                raise UserError(_('Only completed jobs can be invoiced.'))
            job.state = 'invoiced'
            job.message_post(body='🧾 Job marked as invoiced.')

    def action_cancel(self):
        for job in self:
            if job.state == 'invoiced':
                raise UserError(_('Cannot cancel an invoiced job.'))
            job.state = 'cancelled'
            job.message_post(body='❌ Job cancelled.')

    def action_reset_draft(self):
        for job in self:
            if job.state not in ('cancelled', 'assigned', 'scheduled'):
                raise UserError(
                    _('Only cancelled, assigned or scheduled jobs can be reset to draft.'))
            job.state = 'draft'
            job.message_post(body='🔄 Job reset to draft.')


# ---------------------------------------------------------------------------
# Job Lines
# ---------------------------------------------------------------------------
class FMSJobLine(models.Model):
    _name = 'fms.job.line'
    _description = 'FMS Job Line'

    job_id = fields.Many2one('fms.job', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Service', required=True)
    description = fields.Text()
    quantity = fields.Float(default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM')

    unit_cost = fields.Monetary(string='Unit Cost (Vendor)')
    unit_price = fields.Monetary(string='Unit Price (Customer)')
    subtotal_cost = fields.Monetary(compute='_compute_subtotals', store=True)
    subtotal_price = fields.Monetary(compute='_compute_subtotals', store=True)
    margin = fields.Monetary(compute='_compute_subtotals', store=True)
    currency_id = fields.Many2one(related='job_id.currency_id', store=True)

    # ---------------------------------------------------------
    # SCOPE FIELDS
    # ---------------------------------------------------------
    line_type = fields.Selection([
        ('original', 'Original Scope'),
        ('additional', 'Additional Scope'),
    ], default='original', string='Line Type', readonly=True)

    scope_state = fields.Selection([
        ('na', 'N/A'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='na', string='Approval Status', readonly=True,
        help="Rejected lines remain on the job but cannot be billed.")

    @api.depends('quantity', 'unit_cost', 'unit_price')
    def _compute_subtotals(self):
        for line in self:
            line.subtotal_cost = line.quantity * line.unit_cost
            line.subtotal_price = line.quantity * line.unit_price
            line.margin = line.subtotal_price - line.subtotal_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            rate_card = self.env['fms.rate.card'].search([
                ('partner_id', '=', self.job_id.partner_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            if rate_card:
                self.unit_price = rate_card.unit_price
            job_date = (
                self.job_id.scheduled_date.date()
                if self.job_id.scheduled_date
                else fields.Date.context_today(self)
            )
            rate = self.env['fms.rate.card'].get_rate_for_customer(
                self.job_id.partner_id.id, self.product_id.id, job_date)
            if rate:
                self.unit_price = rate.unit_price

    # ---------------------------------------------------------
    # TRIGGER AFTER LINE SAVED
    # ---------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for line in records:
            if line.job_id.auto_so_po_created and line.line_type == 'original':
                line.line_type = 'additional'

        original_jobs = records.filtered(
            lambda l: l.line_type == 'original'
        ).mapped('job_id')

        additional_by_job = {}
        for line in records.filtered(lambda l: l.line_type == 'additional'):
            additional_by_job.setdefault(
                line.job_id, self.env['fms.job.line'])
            additional_by_job[line.job_id] |= line

        if original_jobs:
            original_jobs._auto_create_so_po()

        for job, add_lines in additional_by_job.items():
            job._check_and_trigger_scope_approval(add_lines)

        return records

    def write(self, vals):
        result = super().write(vals)
        trigger_fields = {'product_id', 'quantity', 'uom_id', 'unit_cost', 'unit_price'}
        if trigger_fields.intersection(vals.keys()):
            original_jobs = self.filtered(
                lambda l: l.line_type == 'original'
            ).mapped('job_id')
            if original_jobs:
                original_jobs._auto_create_so_po()
        return result