# -*- encoding: utf-8 -*-
from odoo import api, fields, models
from odoo.fields import Domain


class FMSVendorRateCard(models.Model):
    _name = 'fms.vendor.rate.card'
    _description = 'FMS Vendor Rate Card'
    _order = 'valid_from desc, id desc'
    _rec_name = 'display_name'

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain=[('is_fms_vendor', '=', True)]
    )

    product_id = fields.Many2one(
        'product.product',
        string='Service',
        required=True,
        domain=[('is_fms_service', '=', True)]
    )

    unit_cost = fields.Monetary(
        string='Unit Cost',
        required=True,
        help='Cost per unit for this vendor'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    valid_from = fields.Date(
        string='Valid From',
        help='Rate card effective from this date'
    )

    valid_to = fields.Date(
        string='Valid To',
        help='Rate card valid until this date (blank = no end date)'
    )

    notes = fields.Text(
        string='Notes',
        help='Internal notes or terms'
    )

    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
        string='Display Name'
    )

    active = fields.Boolean(
        default=True,
        help='Uncheck to archive this rate card'
    )

    @api.depends('vendor_id', 'product_id', 'valid_from', 'valid_to')
    def _compute_display_name(self):
        """Generate display name from vendor, product, and dates"""
        for rec in self:
            name = []
            if rec.vendor_id:
                name.append(rec.vendor_id.name)
            if rec.product_id:
                name.append(rec.product_id.display_name)
            if rec.valid_from or rec.valid_to:
                from_date = rec.valid_from or ''
                to_date = rec.valid_to or '∞'
                name.append(f"{from_date} → {to_date}")
            rec.display_name = " | ".join(name) if name else "Vendor Rate Card"

    @api.model
    def get_rate_for_vendor(self, vendor_id, product_id, rate_date=False):
        """
        Get the applicable rate card for a vendor and product on a specific date.

        Args:
            vendor_id: ID of the vendor (res.partner)
            product_id: ID of the product (product.product)
            rate_date: Date to check validity (defaults to today)

        Returns:
            fms.vendor.rate.card record or False if not found
        """
        if not vendor_id or not product_id:
            return False

        if not rate_date:
            rate_date = fields.Date.context_today(self)

        # Build domain for vendor and product
        domain = [
            ('vendor_id', '=', vendor_id),
            ('product_id', '=', product_id),
            ('active', '=', True)
        ]

        # Add date range filters
        # valid_from check: either no date or date <= rate_date
        date_from_domain = Domain([('valid_from', '=', False)]) | Domain([('valid_from', '<=', rate_date)])
        domain = Domain(domain) & date_from_domain

        # valid_to check: either no date or date >= rate_date
        date_to_domain = Domain([('valid_to', '=', False)]) | Domain([('valid_to', '>=', rate_date)])
        domain = domain & date_to_domain

        # Search and return most recent
        return self.search(domain, limit=1)