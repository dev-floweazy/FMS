# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'
    _order = 'is_special_rate desc, valid_from desc, id desc'

    # ----------------------------------------------------------
    # ADDED
    # ----------------------------------------------------------
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        domain=[('is_fms_service', '=', True)],
        required=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    # ----------------------------------------------------------
    # ADDED (for proper display instead of fms.rate.card,1)
    # ----------------------------------------------------------
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]

    # ----------------------------------------------------------
    # ADDED METHOD (display name)
    # ----------------------------------------------------------
    @api.depends('partner_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        for rec in self:
            name = []

            if rec.partner_id:
                name.append(rec.partner_id.name)

            if rec.product_id:
                name.append(rec.product_id.display_name)

            if rec.valid_from or rec.valid_to:
                date_part = "%s → %s" % (
                    rec.valid_from or '',
                    rec.valid_to or ''
                )
                name.append(date_part)

            rec.display_name = " | ".join(name) if name else "Rate Card"

    # ----------------------------------------------------------
    # YOUR EXISTING METHOD (unchanged)
    # ----------------------------------------------------------
    @api.model
    def get_rate_for_customer(self, partner_id, product_id, rate_date=False):
        """
        Returns the correct rate card line for the given
        customer + service + date.

        Special rates are preferred.
        """

        if not partner_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        domain = [
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id),
        ]

        date_domain = expression.OR([
            [('valid_from', '=', False)],
            [('valid_from', '<=', rate_date)]
        ])

        domain = expression.AND([domain, date_domain])

        date_to_domain = expression.OR([
            [('valid_to', '=', False)],
            [('valid_to', '>=', rate_date)]
        ])

        domain = expression.AND([domain, date_to_domain])

        rate = self.search(domain, limit=1)

        return rate# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'
    _order = 'is_special_rate desc, valid_from desc, id desc'

    # ----------------------------------------------------------
    # ADDED
    # ----------------------------------------------------------
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        domain=[('is_fms_service', '=', True)],
        required=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    # ----------------------------------------------------------
    # ADDED (for proper display instead of fms.rate.card,1)
    # ----------------------------------------------------------
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]

    # ----------------------------------------------------------
    # ADDED METHOD (display name)
    # ----------------------------------------------------------
    @api.depends('partner_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        for rec in self:
            name = []

            if rec.partner_id:
                name.append(rec.partner_id.name)

            if rec.product_id:
                name.append(rec.product_id.display_name)

            if rec.valid_from or rec.valid_to:
                date_part = "%s → %s" % (
                    rec.valid_from or '',
                    rec.valid_to or ''
                )
                name.append(date_part)

            rec.display_name = " | ".join(name) if name else "Rate Card"

    # ----------------------------------------------------------
    # YOUR EXISTING METHOD (unchanged)
    # ----------------------------------------------------------
    @api.model
    def get_rate_for_customer(self, partner_id, product_id, rate_date=False):
        """
        Returns the correct rate card line for the given
        customer + service + date.

        Special rates are preferred.
        """

        if not partner_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        domain = [
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id),
        ]

        date_domain = expression.OR([
            [('valid_from', '=', False)],
            [('valid_from', '<=', rate_date)]
        ])

        domain = expression.AND([domain, date_domain])

        date_to_domain = expression.OR([
            [('valid_to', '=', False)],
            [('valid_to', '>=', rate_date)]
        ])

        domain = expression.AND([domain, date_to_domain])

        rate = self.search(domain, limit=1)

        return rate# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'
    _order = 'is_special_rate desc, valid_from desc, id desc'

    # ----------------------------------------------------------
    # ADDED
    # ----------------------------------------------------------
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        domain=[('is_fms_service', '=', True)],
        required=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    # ----------------------------------------------------------
    # ADDED (for proper display instead of fms.rate.card,1)
    # ----------------------------------------------------------
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]

    # ----------------------------------------------------------
    # ADDED METHOD (display name)
    # ----------------------------------------------------------
    @api.depends('partner_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        for rec in self:
            name = []

            if rec.partner_id:
                name.append(rec.partner_id.name)

            if rec.product_id:
                name.append(rec.product_id.display_name)

            if rec.valid_from or rec.valid_to:
                date_part = "%s → %s" % (
                    rec.valid_from or '',
                    rec.valid_to or ''
                )
                name.append(date_part)

            rec.display_name = " | ".join(name) if name else "Rate Card"

    # ----------------------------------------------------------
    # YOUR EXISTING METHOD (unchanged)
    # ----------------------------------------------------------
    @api.model
    def get_rate_for_customer(self, partner_id, product_id, rate_date=False):
        """
        Returns the correct rate card line for the given
        customer + service + date.

        Special rates are preferred.
        """

        if not partner_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        domain = [
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id),
        ]

        date_domain = expression.OR([
            [('valid_from', '=', False)],
            [('valid_from', '<=', rate_date)]
        ])

        domain = expression.AND([domain, date_domain])

        date_to_domain = expression.OR([
            [('valid_to', '=', False)],
            [('valid_to', '>=', rate_date)]
        ])

        domain = expression.AND([domain, date_to_domain])

        rate = self.search(domain, limit=1)

        return rate# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'
    _order = 'is_special_rate desc, valid_from desc, id desc'

    # ----------------------------------------------------------
    # ADDED
    # ----------------------------------------------------------
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        domain=[('is_fms_service', '=', True)],
        required=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    # ----------------------------------------------------------
    # ADDED (for proper display instead of fms.rate.card,1)
    # ----------------------------------------------------------
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]

    # ----------------------------------------------------------
    # ADDED METHOD (display name)
    # ----------------------------------------------------------
    @api.depends('partner_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        for rec in self:
            name = []

            if rec.partner_id:
                name.append(rec.partner_id.name)

            if rec.product_id:
                name.append(rec.product_id.display_name)

            if rec.valid_from or rec.valid_to:
                date_part = "%s → %s" % (
                    rec.valid_from or '',
                    rec.valid_to or ''
                )
                name.append(date_part)

            rec.display_name = " | ".join(name) if name else "Rate Card"

    # ----------------------------------------------------------
    # YOUR EXISTING METHOD (unchanged)
    # ----------------------------------------------------------
    @api.model
    def get_rate_for_customer(self, partner_id, product_id, rate_date=False):
        """
        Returns the correct rate card line for the given
        customer + service + date.

        Special rates are preferred.
        """

        if not partner_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        domain = [
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id),
        ]

        date_domain = expression.OR([
            [('valid_from', '=', False)],
            [('valid_from', '<=', rate_date)]
        ])

        domain = expression.AND([domain, date_domain])

        date_to_domain = expression.OR([
            [('valid_to', '=', False)],
            [('valid_to', '>=', rate_date)]
        ])

        domain = expression.AND([domain, date_to_domain])

        rate = self.search(domain, limit=1)

        return rate# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'
    _order = 'is_special_rate desc, valid_from desc, id desc'

    # ----------------------------------------------------------
    # ADDED
    # ----------------------------------------------------------
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        domain=[('is_fms_service', '=', True)],
        required=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    # ----------------------------------------------------------
    # ADDED (for proper display instead of fms.rate.card,1)
    # ----------------------------------------------------------
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]

    # ----------------------------------------------------------
    # ADDED METHOD (display name)
    # ----------------------------------------------------------
    @api.depends('partner_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        for rec in self:
            name = []

            if rec.partner_id:
                name.append(rec.partner_id.name)

            if rec.product_id:
                name.append(rec.product_id.display_name)

            if rec.valid_from or rec.valid_to:
                date_part = "%s → %s" % (
                    rec.valid_from or '',
                    rec.valid_to or ''
                )
                name.append(date_part)

            rec.display_name = " | ".join(name) if name else "Rate Card"

    # ----------------------------------------------------------
    # YOUR EXISTING METHOD (unchanged)
    # ----------------------------------------------------------
    @api.model
    def get_rate_for_customer(self, partner_id, product_id, rate_date=False):
        """
        Returns the correct rate card line for the given
        customer + service + date.

        Special rates are preferred.
        """

        if not partner_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        domain = [
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id),
        ]

        date_domain = expression.OR([
            [('valid_from', '=', False)],
            [('valid_from', '<=', rate_date)]
        ])

        domain = expression.AND([domain, date_domain])

        date_to_domain = expression.OR([
            [('valid_to', '=', False)],
            [('valid_to', '>=', rate_date)]
        ])

        domain = expression.AND([domain, date_to_domain])

        rate = self.search(domain, limit=1)

        return rate# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'
    _order = 'is_special_rate desc, valid_from desc, id desc'

    # ----------------------------------------------------------
    # ADDED
    # ----------------------------------------------------------
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        domain=[('is_fms_service', '=', True)],
        required=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    # ----------------------------------------------------------
    # ADDED (for proper display instead of fms.rate.card,1)
    # ----------------------------------------------------------
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]

    # ----------------------------------------------------------
    # ADDED METHOD (display name)
    # ----------------------------------------------------------
    @api.depends('partner_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        for rec in self:
            name = []

            if rec.partner_id:
                name.append(rec.partner_id.name)

            if rec.product_id:
                name.append(rec.product_id.display_name)

            if rec.valid_from or rec.valid_to:
                date_part = "%s → %s" % (
                    rec.valid_from or '',
                    rec.valid_to or ''
                )
                name.append(date_part)

            rec.display_name = " | ".join(name) if name else "Rate Card"

    # ----------------------------------------------------------
    # YOUR EXISTING METHOD (unchanged)
    # ----------------------------------------------------------
    @api.model
    def get_rate_for_customer(self, partner_id, product_id, rate_date=False):
        """
        Returns the correct rate card line for the given
        customer + service + date.

        Special rates are preferred.
        """

        if not partner_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        domain = [
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id),
        ]

        date_domain = expression.OR([
            [('valid_from', '=', False)],
            [('valid_from', '<=', rate_date)]
        ])

        domain = expression.AND([domain, date_domain])

        date_to_domain = expression.OR([
            [('valid_to', '=', False)],
            [('valid_to', '>=', rate_date)]
        ])

        domain = expression.AND([domain, date_to_domain])

        rate = self.search(domain, limit=1)

        return rate# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'
    _order = 'is_special_rate desc, valid_from desc, id desc'

    # ----------------------------------------------------------
    # ADDED
    # ----------------------------------------------------------
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        domain=[('is_fms_service', '=', True)],
        required=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    # ----------------------------------------------------------
    # ADDED (for proper display instead of fms.rate.card,1)
    # ----------------------------------------------------------
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]

    # ----------------------------------------------------------
    # ADDED METHOD (display name)
    # ----------------------------------------------------------
    @api.depends('partner_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        for rec in self:
            name = []

            if rec.partner_id:
                name.append(rec.partner_id.name)

            if rec.product_id:
                name.append(rec.product_id.display_name)

            if rec.valid_from or rec.valid_to:
                date_part = "%s → %s" % (
                    rec.valid_from or '',
                    rec.valid_to or ''
                )
                name.append(date_part)

            rec.display_name = " | ".join(name) if name else "Rate Card"

    # ----------------------------------------------------------
    # YOUR EXISTING METHOD (unchanged)
    # ----------------------------------------------------------
    @api.model
    def get_rate_for_customer(self, partner_id, product_id, rate_date=False):
        """
        Returns the correct rate card line for the given
        customer + service + date.

        Special rates are preferred.
        """

        if not partner_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        domain = [
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id),
        ]

        date_domain = expression.OR([
            [('valid_from', '=', False)],
            [('valid_from', '<=', rate_date)]
        ])

        domain = expression.AND([domain, date_domain])

        date_to_domain = expression.OR([
            [('valid_to', '=', False)],
            [('valid_to', '>=', rate_date)]
        ])

        domain = expression.AND([domain, date_to_domain])

        rate = self.search(domain, limit=1)

        return rate# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class FMSRateCard(models.Model):
    _name = 'fms.rate.card'
    _description = 'FMS Rate Card'
    _order = 'is_special_rate desc, valid_from desc, id desc'

    # ----------------------------------------------------------
    # ADDED
    # ----------------------------------------------------------
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        domain=[('is_fms_service', '=', True)],
        required=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date()
    valid_to = fields.Date()

    is_special_rate = fields.Boolean(string='Special Rate')
    notes = fields.Text()

    # ----------------------------------------------------------
    # ADDED (for proper display instead of fms.rate.card,1)
    # ----------------------------------------------------------
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('unique_rate_card',
         'UNIQUE(partner_id, product_id, valid_from)',
         'Rate card must be unique per customer, service, and date!')
    ]

    # ----------------------------------------------------------
    # ADDED METHOD (display name)
    # ----------------------------------------------------------
    @api.depends('partner_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        for rec in self:
            name = []

            if rec.partner_id:
                name.append(rec.partner_id.name)

            if rec.product_id:
                name.append(rec.product_id.display_name)

            if rec.valid_from or rec.valid_to:
                date_part = "%s → %s" % (
                    rec.valid_from or '',
                    rec.valid_to or ''
                )
                name.append(date_part)

            rec.display_name = " | ".join(name) if name else "Rate Card"

    # ----------------------------------------------------------
    # YOUR EXISTING METHOD (unchanged)
    # ----------------------------------------------------------
    @api.model
    def get_rate_for_customer(self, partner_id, product_id, rate_date=False):
        """
        Returns the correct rate card line for the given
        customer + service + date.

        Special rates are preferred.
        """

        if not partner_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        domain = [
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id),
        ]

        date_domain = expression.OR([
            [('valid_from', '=', False)],
            [('valid_from', '<=', rate_date)]
        ])

        domain = expression.AND([domain, date_domain])

        date_to_domain = expression.OR([
            [('valid_to', '=', False)],
            [('valid_to', '>=', rate_date)]
        ])

        domain = expression.AND([domain, date_to_domain])

        rate = self.search(domain, limit=1)

        return rate