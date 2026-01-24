# -*- encoding: utf-8 -*-

{
    'name': 'Facility Management System',
    'version': '19.0.0.0',
    'category': 'Services/FMS',
    'summary': 'Complete Facility Management System for B2B Services',
    'description': """
Facility Management System (FMS) - Complete Solution
=====================================================

A comprehensive facility management system designed for B2B service companies.

Key Features:
-------------
* **Ticket Management**: Customer service requests with SLA tracking
* **Job/Work Order Management**: Complete job lifecycle from assignment to invoicing
* **Vendor Management**: Vendor assignment, performance tracking, and ratings
* **Site Management**: Multi-site support with location-specific details
* **Rate Card Management**: Customer-specific pricing for services
* **Service Categories**: Hierarchical service organization with SLA rules
* **Margin Tracking**: Real-time margin visibility at job, site, and customer level
* **Consolidated Billing**: Monthly consolidated invoicing for enterprise clients
* **SLA Compliance**: Automated SLA calculation and tracking
* **Performance Analytics**: Vendor performance and job profitability reports

Workflow:
---------
1. Customer creates ticket (or ticket created via portal/email)
2. Ticket assigned to operations team
3. Job created from ticket and assigned to vendor
4. Vendor completes work and updates job
5. Customer approves work completion
6. Monthly consolidated billing or immediate invoicing
7. Vendor payment processing

Perfect for:
-----------
* Facility Management Companies
* Property Maintenance Services
* Multi-Site Service Providers
* B2B Service Companies
* Enterprise Maintenance Contractors

Multi-Tenant Ready:
------------------
* Database-per-tenant architecture
* Complete data isolation
* Scalable SaaS deployment
    """,

    'author': 'A.P',
    'website': 'https://www.com',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'mail',
        'product',
        'sale_management',
        'account',
        'purchase',
        'project',
        'hr',
        'portal',
        'web',
        'web_tour',
    ],

    'data': [
        # 'security/fms_security.xml',
        'security/ir.model.access.csv',
        'data/fms_sequence.xml',
        'views/fms_service_category_views.xml',
        'views/fms_site_views.xml',
        'views/fms_rate_card_views.xml',
        'views/fms_ticket_views.xml',
        'views/fms_job_views.xml',
        'views/res_partner_views.xml',
        'views/fms_menu.xml',

    ],




    # Module configuration
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 10,

    # Pricing (if publishing on Odoo Apps)
    'price': 499.00,
    'currency': 'USD',

    'support': 'support@yourcompany.com',
}