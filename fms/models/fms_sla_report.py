# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class FMSSLAReport(models.Model):
    _name = 'fms.sla.report'
    _description = 'FMS SLA Report'
    _auto = False
    _rec_name = 'ticket_name'

    ticket_id = fields.Many2one('fms.ticket', readonly=True)
    ticket_name = fields.Char(string='Ticket', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    site_id = fields.Many2one('fms.site', string='Site', readonly=True)
    service_category_id = fields.Many2one(
        'fms.service.category', string='Service Category', readonly=True)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent')
    ], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'), ('pending', 'Pending'),
        ('resolved', 'Resolved'), ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], readonly=True)
    sla_rule_id = fields.Many2one('fms.sla.rule', string='SLA Rule', readonly=True)
    sla_start_datetime = fields.Datetime(string='SLA Start', readonly=True)
    sla_response_deadline = fields.Datetime(string='Response Deadline', readonly=True)
    sla_resolution_deadline = fields.Datetime(string='Resolution Deadline', readonly=True)
    sla_breached = fields.Boolean(string='Breached', readonly=True)
    requested_date = fields.Datetime(string='Requested Date', readonly=True)
    assigned_to_id = fields.Many2one('res.users', string='Assigned To', readonly=True)
    response_time_hours = fields.Float(string='Response Time (hrs)', readonly=True)
    resolution_time_hours = fields.Float(string='Resolution Time (hrs)', readonly=True)

    # Margin / Financial fields
    currency_id = fields.Many2one('res.currency', readonly=True)
    total_cost = fields.Monetary(
        string='Total Cost', currency_field='currency_id', readonly=True)
    total_price = fields.Monetary(
        string='Total Price', currency_field='currency_id', readonly=True)
    fms_margin = fields.Monetary(
        string='Margin', currency_field='currency_id', readonly=True)
    margin_percent = fields.Float(string='Margin (%)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    t.id                            AS id,
                    t.id                            AS ticket_id,
                    t.name                          AS ticket_name,
                    t.partner_id                    AS partner_id,
                    t.site_id                       AS site_id,
                    t.service_category_id           AS service_category_id,
                    t.priority                      AS priority,
                    t.state                         AS state,
                    t.assigned_to_id                AS assigned_to_id,
                    t.requested_date                AS requested_date,
                    t.sla_rule_id                   AS sla_rule_id,
                    t.sla_start_datetime            AS sla_start_datetime,
                    t.sla_response_deadline         AS sla_response_deadline,
                    t.sla_resolution_deadline       AS sla_resolution_deadline,
                    CASE
                        WHEN t.sla_resolution_deadline IS NOT NULL
                         AND NOW() > t.sla_resolution_deadline
                        THEN TRUE ELSE FALSE
                    END                             AS sla_breached,
                    CASE
                        WHEN t.sla_start_datetime IS NOT NULL
                         AND t.sla_response_deadline IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (
                            t.sla_response_deadline - t.sla_start_datetime
                        )) / 3600.0
                        ELSE 0
                    END                             AS response_time_hours,
                    CASE
                        WHEN t.sla_start_datetime IS NOT NULL
                         AND t.sla_resolution_deadline IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (
                            t.sla_resolution_deadline - t.sla_start_datetime
                        )) / 3600.0
                        ELSE 0
                    END                             AS resolution_time_hours,
                    COALESCE(SUM(j.total_cost), 0)  AS total_cost,
                    COALESCE(SUM(j.total_price), 0) AS total_price,
                    COALESCE(SUM(j.margin), 0)      AS fms_margin,
                    CASE
                        WHEN COALESCE(SUM(j.total_price), 0) > 0
                        THEN COALESCE(SUM(j.margin), 0) / SUM(j.total_price) * 100
                        ELSE 0
                    END                             AS margin_percent,
                    COALESCE(
                        (SELECT currency_id FROM fms_job
                         WHERE ticket_id = t.id LIMIT 1),
                        (SELECT id FROM res_currency WHERE name = 'USD' LIMIT 1)
                    )                               AS currency_id
                FROM fms_ticket t
                LEFT JOIN fms_job j ON j.ticket_id = t.id
                WHERE t.sla_rule_id IS NOT NULL
                GROUP BY
                    t.id, t.name, t.partner_id, t.site_id,
                    t.service_category_id, t.priority, t.state,
                    t.assigned_to_id, t.requested_date, t.sla_rule_id,
                    t.sla_start_datetime, t.sla_response_deadline,
                    t.sla_resolution_deadline
            )
        """ % self._table)