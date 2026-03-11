# -*- encoding: utf-8 -*-

import base64
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class FMSPortalTicket(http.Controller):

    def _check_access(self):
        user = request.env.user
        if user._is_public():
            return request.redirect('/web/login?redirect=/fms/ticket/new')
        partner = user.partner_id
        is_allowed = partner.is_fms_customer or user.has_group('base.group_user')
        if not is_allowed:
            return request.render('fms.fms_portal_403', {}, status=403)
        return None

    @http.route('/fms/ticket/new', type='http', auth='user', website=True)
    def new_ticket(self, **kw):
        redirect = self._check_access()
        if redirect:
            return redirect

        env = request.env
        partner = env.user.partner_id

        if env.user.has_group('base.group_user'):
            sites = env['fms.site'].sudo().search([('active', '=', True)])
        else:
            sites = env['fms.site'].sudo().search([
                ('partner_id', '=', partner.id),
                ('active', '=', True),
            ])

        categories = env['fms.service.category'].sudo().search([('active', '=', True)])

        return request.render('fms.fms_portal_new_ticket', {
            'sites': sites,
            'categories': categories,
            'partner': partner,
        })

    @http.route('/fms/ticket/submit', type='http', auth='user',
                website=True, methods=['POST'], csrf=True)
    def submit_ticket(self, **post):
        redirect = self._check_access()
        if redirect:
            return redirect

        env = request.env
        partner = env.user.partner_id

        site_id = int(post.get('site_id') or 0)
        category_id = int(post.get('service_category_id') or 0)
        description = (post.get('description') or '').strip()

        if not site_id or not category_id or not description:
            if env.user.has_group('base.group_user'):
                sites = env['fms.site'].sudo().search([('active', '=', True)])
            else:
                sites = env['fms.site'].sudo().search([
                    ('partner_id', '=', partner.id), ('active', '=', True)])
            categories = env['fms.service.category'].sudo().search([('active', '=', True)])
            return request.render('fms.fms_portal_new_ticket', {
                'sites': sites,
                'categories': categories,
                'error': _('Please fill in all required fields.'),
                'partner': partner,
                'values': post,
            })

        site = env['fms.site'].sudo().browse(site_id)
        ticket_partner = site.partner_id if env.user.has_group('base.group_user') else partner

        ticket = env['fms.ticket'].sudo().create({
            'partner_id': ticket_partner.id,
            'site_id': site_id,
            'service_category_id': category_id,
            'description': description,
            'state': 'draft',
        })

        files = request.httprequest.files.getlist('attachments')
        attachment_ids = []
        for f in files:
            if f and f.filename:
                data = f.read()
                if data:
                    att = env['ir.attachment'].sudo().create({
                        'name': f.filename,
                        'res_model': 'fms.ticket',
                        'res_id': ticket.id,
                        'datas': base64.b64encode(data).decode(),
                        'mimetype': f.mimetype or 'application/octet-stream',
                    })
                    attachment_ids.append(att.id)

        if attachment_ids:
            ticket.sudo().write({'attachment_ids': [(4, aid) for aid in attachment_ids]})

        return request.redirect('/fms/tickets?submitted=%s' % ticket.name)

    @http.route('/fms/tickets', type='http', auth='user', website=True)
    def ticket_list(self, **kw):
        redirect = self._check_access()
        if redirect:
            return redirect

        env = request.env
        partner = env.user.partner_id

        if env.user.has_group('base.group_user'):
            tickets = env['fms.ticket'].sudo().search([], order='requested_date desc')
        else:
            tickets = env['fms.ticket'].sudo().search(
                [('partner_id', '=', partner.id)], order='requested_date desc')

        return request.render('fms.fms_portal_ticket_list', {
            'tickets': tickets,
            'submitted': kw.get('submitted'),
        })

class FMSCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'ticket_count' in counters:
            partner = request.env.user.partner_id
            if request.env.user.has_group('base.group_user'):
                count = request.env['fms.ticket'].sudo().search_count([])
            else:
                count = request.env['fms.ticket'].sudo().search_count(
                    [('partner_id', '=', partner.id)])
            values['ticket_count'] = count
        return values