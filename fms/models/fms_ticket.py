# -*- encoding: utf-8 -*-

from odoo import api, fields, models


class FMSTicket(models.Model):
    _name = 'fms.ticket'
    _description = 'FMS Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Quotation smart button
    so_count = fields.Integer(
        string='Quotations',
        compute='_compute_so_count',
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Quotation',
        compute='_compute_sale_order_id',
        store=False,
    )

    name = fields.Char(string='Ticket Number', required=True, copy=False,
                       default='New', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 required=True, tracking=True)
    site_id = fields.Many2one('fms.site', string='Site', required=True)
    service_category_id = fields.Many2one('fms.service.category',
                                          string='Service Category', required=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], default='1', tracking=True)

    description = fields.Html(string='Issue Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        # ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    requested_date = fields.Datetime(string='Requested Date',
                                     default=fields.Datetime.now)
    sla_deadline = fields.Datetime(string='SLA Deadline')
    # , compute = '_compute_sla'

    job_ids = fields.One2many('fms.job', 'ticket_id', string='Jobs')

    job_count = fields.Integer(
        'Jobs count',
        compute='_compute_job_count',
        store=True
    )

    assigned_to_id = fields.Many2one('res.users', string='Assigned To')
    contact_person = fields.Char('Contact Person')
    work_start_datetime = fields.Datetime(string="Work Start Time", tracking=True)
    work_stop_datetime = fields.Datetime(string="Work Stop Time", tracking=True)
    contact_phone = fields.Char('Contact Phone')
    vendor_id = fields.Many2one('res.partner', string='Vendor Id')
    scheduled_date = fields.Date('Scheduled Date')
    total_price = fields.Float('Total Price')
    total_cost = fields.Float('Total Cost')
    margin = fields.Float(
        "Margin",
        digits='Product Price',)
    # compute = '_compute_margin', store=True, groups="base.group_user", precompute=True
    margin_percent = fields.Float(
        "Margin (%)")
    # , compute = '_compute_margin', store = True, groups = "base.group_user", precompute = True
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Attachments"
    )
    internal_notes = fields.Html('Internal Notes')
    so_count = fields.Integer(
        string='Quotations',
        compute='_compute_so_count',
    )

    def _compute_so_count(self):
        for ticket in self:
            ticket.so_count = self.env['sale.order'].search_count([
                ('origin', 'in', ticket.job_ids.mapped('name'))
            ]) if ticket.job_ids else 0

    def action_view_quotation(self):
        self.ensure_one()
        sale_orders = self.env['sale.order'].search([
            ('origin', 'in', self.job_ids.mapped('name'))
        ])
        if len(sale_orders) == 1:
            so = sale_orders
            return {
                'type': 'ir.actions.act_url',
                'url': '/my/orders/%d?access_token=%s' % (so.id, so.access_token),
                'target': 'self',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotations',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('origin', 'in', self.job_ids.mapped('name'))],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fms.ticket') or 'New'
        return super().create(vals_list)

    def _compute_so_count(self):
        for ticket in self:
            ticket.so_count = self.env['sale.order'].search_count([
                ('origin', 'in', ticket.job_ids.mapped('name'))
            ]) if ticket.job_ids else 0

    def _compute_sale_order_id(self):
        for ticket in self:
            if ticket.job_ids:
                so = self.env['sale.order'].search([
                    ('origin', 'in', ticket.job_ids.mapped('name'))
                ], order='id desc', limit=1)
                ticket.sale_order_id = so
            else:
                ticket.sale_order_id = False

    def action_view_quotation(self):
        self.ensure_one()
        sale_orders = self.env['sale.order'].search([
            ('origin', 'in', self.job_ids.mapped('name'))
        ])
        if len(sale_orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Quotation',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': sale_orders.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotations',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('origin', 'in', self.job_ids.mapped('name'))],
            'target': 'current',
        }

    @api.depends('service_category_id', 'requested_date', 'priority')
    def _compute_sla(self):
        for ticket in self:
            # SLA calculation logic based on category and priority
            pass

    # ------------------------------------------------------------
    # COMPUTE JOB COUNT
    # ------------------------------------------------------------
    @api.depends('job_ids')
    def _compute_job_count(self):
        for rec in self:
            rec.job_count = len(rec.job_ids)

    def action_open(self):
        for rec in self:
            rec.write({'state': 'open'})

    def action_assign(self):
        for rec in self:
            rec.write({'state': 'assigned'})

    def action_start(self):
        for rec in self:
            rec.write({
                'state': 'in_progress',
                'work_start_datetime': fields.Datetime.now(),
                'work_stop_datetime': False,
            })

    def action_stop(self):
        for rec in self:
            rec.write({
                'state': 'pending',
                'work_stop_datetime': fields.Datetime.now(),
                'work_start_datetime': False,
            })

    def action_resolve(self):
        for rec in self:
            rec.write({'state': 'resolved'})

    def action_close(self):
        for rec in self:
            rec.write({'state': 'closed'})

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancelled'})

    # ------------------------------------------------------------
    # SMART BUTTON : JOBS
    # ------------------------------------------------------------
    def action_view_jobs(self):
        self.ensure_one()

        Job = self.env['fms.job']

        # ------------------------------------------------
        # If jobs already exist → just open them
        # ------------------------------------------------
        if self.job_ids:

            # If only one job → open form
            if len(self.job_ids) == 1:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Job',
                    'res_model': 'fms.job',
                    'view_mode': 'form',
                    'res_id': self.job_ids.id,
                    'target': 'current',
                }

            # If more than one job → open list
            return {
                'type': 'ir.actions.act_window',
                'name': 'Jobs',
                'res_model': 'fms.job',
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.job_ids.ids)],
                'target': 'current',
            }

        # ------------------------------------------------
        # No job exists yet → create first job
        # ------------------------------------------------

        job_vals = {
            'ticket_id': self.id,
            'vendor_id': self.vendor_id.id,
            'assigned_user_id': self.assigned_to_id.id,
            'scheduled_date': self.scheduled_date,
            'description': self.description,
        }

        job = Job.create(job_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Job',
            'res_model': 'fms.job',
            'view_mode': 'form',
            'res_id': job.id,
            'target': 'current',
        }