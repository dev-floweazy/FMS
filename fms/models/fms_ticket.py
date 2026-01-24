# -*- encoding: utf-8 -*-

from odoo import api, fields, models

class FMSTicket(models.Model):
    _name = 'fms.ticket'
    _description = 'FMS Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
        ('open', 'Open'),
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
    assigned_to_id = fields.Many2one('res.users', string='Assigned To')
    job_count = fields.Integer('Jobs count')
    contact_person = fields.Char('Contact Person')
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fms.ticket') or 'New'
        return super().create(vals_list)

    @api.depends('service_category_id', 'requested_date', 'priority')
    def _compute_sla(self):
        for ticket in self:
            # SLA calculation logic based on category and priority
            pass

    def action_open(self):
        for rec in self:
            rec.write({'state': 'open'})


    def action_assign(self):
        for rec in self:
            rec.write({'state': 'assigned'})

    def action_start(self):
        for rec in self:
            rec.write({'state': 'in_progress'})

    def action_resolve(self):
        for rec in self:
            rec.write({'state': 'resolved'})

    def action_close(self):
        for rec in self:
            rec.write({'state': 'closed'})

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancelled'})

    def action_view_jobs(self):
        for rec in self:
            # rec.write({'state': 'open'})
            pass

