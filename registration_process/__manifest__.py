{
    'name': 'FMS Registration Process',
    'version': '19.0.1.0.0',
    'summary': 'Custom signup for Facility Management — Customer & Vendor',
    'author': 'FacilityPro',
    'category': 'Facility Management',
    'depends': ['base', 'auth_signup', 'portal', 'mail', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/partner_tags.xml',
        'views/signup_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
