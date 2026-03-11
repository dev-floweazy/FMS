# -*- encoding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_fms_vendor = fields.Boolean(string='Is FMS Vendor')
    vendor_service_category_ids = fields.Many2many(
        'fms.service.category',
        string='Service Categories'
    )
    vendor_rating = fields.Selection([
        ('1', '⭐'),
        ('2', '⭐⭐'),
        ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'),
        ('5', '⭐⭐⭐⭐⭐'),
    ])
    vendor_job_ids = fields.One2many('fms.job', 'vendor_id', string='Jobs')

    service_id = fields.Many2one(
        'product.template',
        string='Primary Service Category',
        domain=[('website_published', '=', True), ('sale_ok', '=', True)],
        ondelete='set null',
    )

    # KYC fields
    fms_aadhaar_number = fields.Char('Aadhaar Number', size=12)
    fms_pan_number = fields.Char('PAN Number', size=10)
    fms_aadhaar_doc = fields.Many2one(
        'ir.attachment', string='Aadhaar Document', ondelete='set null')
    fms_pan_doc = fields.Many2one(
        'ir.attachment', string='PAN Document', ondelete='set null')
    fms_kyc_verified = fields.Boolean('KYC Verified', default=False)

    # Computed helpers
    fms_doc_count = fields.Integer(
        string='KYC Documents',
        compute='_compute_fms_doc_count',
    )
    fms_vendor_attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Vendor Documents',
        compute='_compute_vendor_attachments',
    )

    @api.depends('fms_aadhaar_doc', 'fms_pan_doc')
    def _compute_fms_doc_count(self):
        for rec in self:
            rec.fms_doc_count = bool(rec.fms_aadhaar_doc) + bool(rec.fms_pan_doc)

    @api.depends('fms_aadhaar_doc', 'fms_pan_doc')
    def _compute_vendor_attachments(self):
        Attachment = self.env['ir.attachment'].sudo()
        for rec in self:
            rec.fms_vendor_attachment_ids = Attachment.search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', rec.id),
            ])

    def action_view_vendor_documents(self):
        self.ensure_one()
        return {
            'name': f'KYC Documents — {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'res.partner'), ('res_id', '=', self.id)],
        }

    def action_download_aadhaar_doc(self):
        self.ensure_one()
        if not self.fms_aadhaar_doc:
            return False
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.fms_aadhaar_doc.id}?download=true',
            'target': 'new',
        }

    def action_download_pan_doc(self):
        self.ensure_one()
        if not self.fms_pan_doc:
            return False
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.fms_pan_doc.id}?download=true',
            'target': 'new',
        }