# -*- encoding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class FMSApprovalRule(models.Model):
    """
    Approval rules based on amount threshold.
    When additional scope total exceeds threshold, approval is required.
    """
    _name = 'fms.approval.rule'
    _description = 'FMS Scope Approval Rule'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(default=True)

    amount_threshold = fields.Monetary(
        string='Amount Threshold',
        required=True,
        help="Approval required when additional scope total exceeds this amount."
    )
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # Approver — specific user or group
    approver_id = fields.Many2one(
        'res.users',
        string='Approver (User)',
        help="Specific user who can approve."
    )
    approver_group_id = fields.Many2one(
        'res.groups',
        string='Approver (Group)',
        help="Any user in this group can approve."
    )

    notes = fields.Text(string='Notes')

    @api.constrains('approver_id', 'approver_group_id')
    def _check_approver(self):
        for rule in self:
            if not rule.approver_id and not rule.approver_group_id:
                raise UserError(
                    "Please set either an Approver User or an Approver Group."
                )


class FMSScopeApproval(models.Model):
    """
    Approval request created when additional scope total exceeds threshold.
    Rejected lines stay on the job but are blocked from billing.
    """
    _name = 'fms.scope.approval'
    _description = 'FMS Additional Scope Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Approval Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'fms.scope.approval') or 'SCOPE'
    )
    job_id = fields.Many2one(
        'fms.job', string='Job', required=True, ondelete='cascade'
    )
    partner_id = fields.Many2one(related='job_id.partner_id', store=True)
    vendor_id = fields.Many2one(related='job_id.vendor_id', store=True)

    approval_rule_id = fields.Many2one(
        'fms.approval.rule', string='Triggered Rule', readonly=True
    )
    approver_id = fields.Many2one(
        'res.users', string='Approver', required=True, readonly=True
    )
    approver_group_id = fields.Many2one(
        'res.groups', string='Approver Group', readonly=True
    )
    requested_by_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True
    )

    state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending', tracking=True, string='Status')

    approval_line_ids = fields.One2many(
        'fms.scope.approval.line', 'approval_id', string='Additional Scope Lines'
    )

    total_additional_amount = fields.Monetary(
        compute='_compute_total', store=True, string='Total Additional Amount'
    )
    currency_id = fields.Many2one(
        related='job_id.currency_id', store=True
    )

    approve_date = fields.Datetime(string='Approved/Rejected On', readonly=True)
    approver_notes = fields.Text(string='Approver Notes')
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True)

    # SO created after approval
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order', readonly=True
    )

    @api.depends('approval_line_ids.subtotal_price')
    def _compute_total(self):
        for rec in self:
            rec.total_additional_amount = sum(
                rec.approval_line_ids.mapped('subtotal_price')
            )

    # ---------------------------------------------------------
    # APPROVE
    # ---------------------------------------------------------
    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError("Only pending approvals can be approved.")

        # Validate current user is authorised
        self._check_approver_access()

        self.state = 'approved'
        self.approve_date = fields.Datetime.now()

        # Mark all lines as approved
        for line in self.approval_line_ids:
            if line.job_line_id:
                line.job_line_id.scope_state = 'approved'

        # Create SO for approved lines
        self._create_so_for_approved_lines()

        self.message_post(
            body=f'✅ Additional scope approved by {self.env.user.name}.'
        )

    # ---------------------------------------------------------
    # REJECT — opens wizard for reason
    # ---------------------------------------------------------
    def action_reject(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError("Only pending approvals can be rejected.")
        self._check_approver_access()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rejection Reason',
            'res_model': 'fms.scope.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_approval_id': self.id},
        }

    # ---------------------------------------------------------
    # ACCESS CHECK
    # ---------------------------------------------------------
    def _check_approver_access(self):
        user = self.env.user
        is_approver_user = (self.approver_id == user)
        is_in_group = (
            self.approver_group_id
            and user in self.approver_group_id.users
        )
        is_admin = user.has_group('base.group_system')
        if not is_approver_user and not is_in_group and not is_admin:
            raise UserError(
                f"Only {self.approver_id.name or 'the designated approver'} "
                f"can approve or reject this request."
            )

    # ---------------------------------------------------------
    # CREATE SO FOR APPROVED LINES ONLY
    # ---------------------------------------------------------
    def _create_so_for_approved_lines(self):
        self.ensure_one()
        job = self.job_id

        approved_lines = self.approval_line_ids.filtered(
            lambda l: l.job_line_id
            and l.job_line_id.scope_state == 'approved'
        )
        if not approved_lines or not job.partner_id:
            return

        so_lines = []
        for line in approved_lines:
            jl = line.job_line_id
            so_lines.append((0, 0, {
                'product_id': jl.product_id.id,
                'name': jl.description or jl.product_id.name,
                'product_uom_qty': jl.quantity,
                'product_uom_id': jl.uom_id.id or jl.product_id.uom_id.id,
                'price_unit': jl.unit_price,
            }))

        so = self.env['sale.order'].create({
            'partner_id': job.partner_id.id,
            'origin': f"{job.name} (Scope: {self.name})",
            'order_line': so_lines,
        })
        self.sale_order_id = so.id
        job.sale_order_id = so.id

        self.message_post(
            body=f'✅ Sales Order <a href="#" data-oe-model="sale.order" '
                 f'data-oe-id="{so.id}">{so.name}</a> created for approved scope.'
        )

    # ---------------------------------------------------------
    # VIEW SO BUTTON
    # ---------------------------------------------------------
    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("No Sales Order created yet.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }


class FMSScopeApprovalLine(models.Model):
    """Lines inside an approval request, linked to the actual job line."""
    _name = 'fms.scope.approval.line'
    _description = 'FMS Scope Approval Line'

    approval_id = fields.Many2one(
        'fms.scope.approval', required=True, ondelete='cascade'
    )
    job_line_id = fields.Many2one(
        'fms.job.line', string='Job Line', ondelete='set null', readonly=True
    )
    product_id = fields.Many2one(
        'product.product', string='Service', required=True, readonly=True
    )
    description = fields.Text(readonly=True)
    quantity = fields.Float(default=1.0, readonly=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)
    unit_price = fields.Monetary(string='Unit Price', readonly=True)
    subtotal_price = fields.Monetary(compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one(related='approval_id.currency_id', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal_price = line.quantity * line.unit_price


class FMSScopeRejectionWizard(models.TransientModel):
    """Wizard to capture rejection reason."""
    _name = 'fms.scope.rejection.wizard'
    _description = 'Scope Rejection Wizard'

    approval_id = fields.Many2one('fms.scope.approval', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        approval = self.approval_id
        approval.state = 'rejected'
        approval.approve_date = fields.Datetime.now()
        approval.rejection_reason = self.rejection_reason

        # Mark lines as rejected — they STAY on the job but cannot be billed
        for line in approval.approval_line_ids:
            if line.job_line_id:
                line.job_line_id.scope_state = 'rejected'

        approval.message_post(
            body=f'❌ Additional scope rejected by {self.env.user.name}. '
                 f'Reason: {self.rejection_reason}'
        )
        # Notify the job chatter too
        approval.job_id.message_post(
            body=f'❌ Scope approval <a href="#" data-oe-model="fms.scope.approval" '
                 f'data-oe-id="{approval.id}">{approval.name}</a> was rejected. '
                 f'Reason: {self.rejection_reason}. '
                 f'The lines remain on the job but will not be billed.'
        )
        return {'type': 'ir.actions.act_window_close'}