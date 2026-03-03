# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import timedelta


class FMSTicket(models.Model):
    _inherit = 'fms.ticket'

    # ---------------------------
    # SLA fields
    # ---------------------------

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

    # ------------------------------------
    # SLA RULE SELECTION
    # ------------------------------------

    @api.depends('service_category_id', 'priority')
    def _compute_sla_rule(self):
        for rec in self:
            rec.sla_rule_id = self.env['fms.sla.rule'].search([
                ('service_category_id', '=', rec.service_category_id.id),
                ('priority', '=', rec.priority),
                ('active', '=', True)
            ], limit=1)

    # ------------------------------------
    # SLA start at creation
    # ------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        now = fields.Datetime.now()
        for rec in records:
            if rec.sla_rule_id:
                rec.sla_start_datetime = now

        return records

    # ------------------------------------
    # SLA deadlines
    # ------------------------------------

    @api.depends('sla_start_datetime', 'sla_rule_id')
    def _compute_sla_deadlines(self):

        for rec in self:

            rec.sla_response_deadline = False
            rec.sla_resolution_deadline = False

            if not rec.sla_start_datetime or not rec.sla_rule_id:
                continue

            rec.sla_response_deadline = rec.sla_start_datetime + timedelta(
                hours=rec.sla_rule_id.response_time
            )

            rec.sla_resolution_deadline = rec.sla_start_datetime + timedelta(
                hours=rec.sla_rule_id.resolution_time
            )

    # ------------------------------------
    # SLA breach
    # ------------------------------------

    @api.depends('sla_resolution_deadline')
    def _compute_sla_breached(self):

        now = fields.Datetime.now()

        for rec in self:
            rec.sla_breached = False

            if rec.sla_resolution_deadline and now > rec.sla_resolution_deadline:
                rec.sla_breached = True