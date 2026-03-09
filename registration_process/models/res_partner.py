from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_fms_customer = fields.Boolean('FMS Customer', default=False)
    is_fms_vendor   = fields.Boolean('FMS Vendor',   default=False)

    fms_facility_type = fields.Selection([
        ('commercial',  'Commercial Office'),
        ('retail',      'Retail & Shopping'),
        ('industrial',  'Industrial / Warehouse'),
        ('healthcare',  'Healthcare'),
        ('education',   'Education Campus'),
        ('hospitality', 'Hospitality & Hotel'),
        ('residential', 'Residential Complex'),
        ('government',  'Government / Public'),
        ('other',       'Other'),
    ], string='Facility Type')

    fms_services_needed  = fields.Char('Services Needed')
    fms_num_sites        = fields.Selection([
        ('1', '1 site'), ('2-5', '2–5 sites'),
        ('6-20', '6–20 sites'), ('20+', '20+ sites'),
    ], string='Number of Sites')

    fms_service_category = fields.Selection([
        ('hvac', 'HVAC & Mechanical'), ('electrical', 'Electrical Systems'),
        ('plumbing', 'Plumbing & Sanitation'), ('cleaning', 'Cleaning & Janitorial'),
        ('security', 'Security & Access Control'), ('landscaping', 'Landscaping & Grounds'),
        ('fire', 'Fire Safety & Suppression'), ('waste', 'Waste Management'),
        ('elevators', 'Elevators & Lifts'), ('civil', 'General Civil Works'),
        ('multi', 'Multiple / General FM'),
    ], string='Primary Service Category')

    fms_coverage_region = fields.Selection([
        ('north', 'North'), ('south', 'South'),
        ('east', 'East'), ('west', 'West'), ('national', 'Nationwide'),
    ], string='Coverage Region')

    fms_registration_no = fields.Char('Business Reg. No.')
    fms_certifications  = fields.Char('Certifications')
    fms_company_profile = fields.Text('Company Profile')
    fms_approval_state  = fields.Selection([
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='FMS Approval', default='pending')
