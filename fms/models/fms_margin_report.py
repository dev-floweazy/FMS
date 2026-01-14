# -*- encoding: utf-8 -*-

from odoo import api, fields, models, tools

class FMSMarginReport(models.Model):
    _name = 'fms.margin.report'
    _description = 'FMS Margin Analysis'
    _auto = False

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        readonly=True,
    )
    job_id = fields.Many2one('fms.job', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    site_id = fields.Many2one('fms.site', readonly=True)
    service_category_id = fields.Many2one('fms.service.category', readonly=True)
    total_cost = fields.Monetary(currency_field="currency_id",readonly=True)
    total_price = fields.Monetary(currency_field="currency_id",readonly=True)
    margin = fields.Monetary(currency_field="currency_id",readonly=True)
    margin_percent = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    j.id AS id,
                    j.id AS job_id,
                    j.partner_id,
                    j.site_id,
                    t.service_category_id,
                    j.total_cost,
                    j.total_price,
                    j.margin,
                    j.margin_percent,
                    j.currency_id
                FROM fms_job j
                LEFT JOIN fms_ticket t ON j.ticket_id = t.id
                WHERE j.state = 'completed'
            )
        """ % self._table)