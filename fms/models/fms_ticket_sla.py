# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import timedelta


class FMSTicketSLA(models.Model):
    _inherit = 'fms.ticket'

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
        store=True
    )

    # --------------------------------------------------
    # SLA RULE: match by service category + priority
    # --------------------------------------------------
    @api.depends('service_category_id', 'priority')
    def _compute_sla_rule(self):
        for rec in self:
            rec.sla_rule_id = self.env['fms.sla.rule'].search([
                ('service_category_id', '=', rec.service_category_id.id),
                ('priority', '=', rec.priority),
                ('active', '=', True)
            ], limit=1)

    # --------------------------------------------------
    # SET SLA START on ticket creation
    # --------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        now = fields.Datetime.now()
        for rec in records:
            if rec.sla_rule_id and not rec.sla_start_datetime:
                rec.sla_start_datetime = now
        return records

    # --------------------------------------------------
    # Also start SLA if rule is assigned later
    # --------------------------------------------------
    def write(self, vals):
        result = super().write(vals)
        if 'service_category_id' in vals or 'priority' in vals:
            now = fields.Datetime.now()
            for rec in self:
                if rec.sla_rule_id and not rec.sla_start_datetime:
                    rec.sla_start_datetime = now
        return result

    # --------------------------------------------------
    # COMPUTE DEADLINES
    # --------------------------------------------------
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
            # Keep the legacy sla_deadline field in sync
            rec.sla_deadline = rec.sla_resolution_deadline

    # --------------------------------------------------
    # COMPUTE BREACH FLAG
    # --------------------------------------------------
    @api.depends('sla_resolution_deadline')
    def _compute_sla_breached(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.sla_breached = bool(
                rec.sla_resolution_deadline
                and now > rec.sla_resolution_deadline
            )