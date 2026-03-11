from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo import http, _
from odoo.http import request
import werkzeug
from odoo.addons.web.models.res_users import SKIP_CAPTCHA_LOGIN
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.exceptions import UserError
from werkzeug.urls import url_encode
import logging
from markupsafe import Markup
from odoo.tools.translate import LazyTranslate
import base64

SIGN_UP_REQUEST_PARAMS = {
    'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
    'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
    'password', 'confirm_password', 'city', 'country_id', 'lang',
    'signup_email', 'role',
    # FMS custom fields
    'fms_company', 'fms_phone',
    'fms_facility_type', 'fms_services_needed', 'fms_num_sites',
    'fms_service_category', 'fms_coverage_region', 'service_id',
    'fms_registration_no', 'fms_certifications', 'fms_company_profile',
    'fms_aadhaar_number', 'fms_pan_number',
}

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)

def _save_document(partner, file_storage, doc_type):
    if not file_storage or not file_storage.filename:
        return False
    file_data = file_storage.read()
    if not file_data:
        return False
    label = 'Aadhaar' if doc_type == 'aadhaar' else 'PAN'
    attachment = request.env['ir.attachment'].sudo().create({
        'name':      f'{label}_{partner.name}_{file_storage.filename}',
        'res_model': 'res.partner',
        'res_id':    partner.id,
        'datas':     base64.b64encode(file_data).decode(),
        'mimetype':  file_storage.mimetype or 'application/octet-stream',
    })
    return attachment.id

def _enrich_partner(partner, role, qcontext):
    """Write FMS data onto the partner record after successful signup."""
    env = request.env

    if role == 'customer':
        partner.sudo().write({
            'is_fms_customer':     True,
            'customer_rank':       1,
            'fms_facility_type':   qcontext.get('fms_facility_type') or False,
            'fms_services_needed': qcontext.get('fms_services_needed') or False,
            'fms_num_sites':       qcontext.get('fms_num_sites') or False,
            'fms_approval_state':  'approved',
            'phone':               qcontext.get('fms_phone') or False,
            'company_name':        qcontext.get('fms_company') or False,
        })
        tag = env.ref('registration_process.partner_tag_fms_customer', raise_if_not_found=False)
        if tag:
            partner.sudo().write({'category_id': [(4, tag.id)]})

    elif role == 'vendor':
        # Save uploaded docs BEFORE write so IDs go into vals
        aadhaar_file = request.httprequest.files.get('fms_aadhaar_doc')
        pan_file = request.httprequest.files.get('fms_pan_doc')
        aadhaar_att_id = _save_document(partner, aadhaar_file, 'aadhaar')
        pan_att_id = _save_document(partner, pan_file, 'pan')
        vals = {
            'is_fms_vendor':        True,
            'supplier_rank':        1,
            'is_company':           True,
            # 'fms_service_category': qcontext.get('fms_service_category') or False,
            'fms_coverage_region':  qcontext.get('fms_coverage_region') or False,
            'fms_registration_no':  qcontext.get('fms_registration_no') or False,
            'fms_certifications':   qcontext.get('fms_certifications') or False,
            'fms_company_profile':  qcontext.get('fms_company_profile') or False,
            'fms_approval_state':   'pending',
            'city': qcontext.get('city') or False,
            'phone':                qcontext.get('fms_phone') or False,
            'fms_aadhaar_number': qcontext.get('fms_aadhaar_number') or False,
            'fms_pan_number': (qcontext.get('fms_pan_number') or '').upper() or False,
            'fms_aadhaar_doc': aadhaar_att_id or False,
            'fms_pan_doc': pan_att_id or False,
        }
        # For vendors the company name becomes the partner name
        if qcontext.get('fms_company'):
            vals['name'] = qcontext['fms_company']

        partner.sudo().write(vals)
        tag = env.ref('registration_process.partner_tag_fms_vendor', raise_if_not_found=False)
        if tag:
            partner.sudo().write({'category_id': [(4, tag.id)]})
        if qcontext.get('service_id'):
            try:
                product_id = int(qcontext['service_id'])
                # Store the product name as the category label
                product = request.env['product.template'].sudo().browse(product_id)
                if product.exists():
                    vals['service_id'] = product  # store name in Char field
            except (ValueError, TypeError):
                vals['service_id'] = qcontext.get('service_id')
        partner.sudo().write(vals)

    _logger.info('FMS signup: partner %s (id=%s) created as %s', partner.name, partner.id, role)


class AuthSignUp(AuthSignupHome):

    # ------------------------------------------------------------------
    # YOUR ORIGINAL /web/signup — unchanged except the render decision
    # at the bottom now redirects to dedicated routes instead of
    # rendering auth_signup.signup (which is plain Odoo form).
    # ------------------------------------------------------------------
    @http.route('/web/signup', type='http', auth='public', website=True,
                sitemap=False, captcha='signup',
                list_as_website_content=_lt("Sign Up"))
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                if request.session.uid is None:
                    public_user = request.env.ref('base.public_user')
                    request.update_env(user=public_user)
                User = request.env['res.users']
                user_sudo = User.sudo().search(
                    User._get_login_domain(qcontext.get('login')),
                    order=User._get_login_order(), limit=1
                )
                template = request.env.ref(
                    'auth_signup.mail_template_user_signup_account_created',
                    raise_if_not_found=False
                )
                if user_sudo and template:
                    template.sudo().send_mail(user_sudo.id, force_send=True)
                request.update_context(skip_captcha_login=SKIP_CAPTCHA_LOGIN)
                return self.web_login(*args, **kw)
            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                User = request.env['res.users']
                if User.sudo().with_context(active_test=False).search_count(
                    User._get_login_domain(qcontext.get('login')), limit=1
                ):
                    qcontext['error'] = _('Another user is already registered using this email address.')
                else:
                    _logger.warning('%s', e)
                    qcontext['error'] = _('Could not create a new account.') + Markup('<br/>') + str(e)

        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search(
                [('email', '=', qcontext.get('signup_email')), ('state', '!=', 'new')], limit=1)
            if user:
                return request.redirect(
                    '/web/login?%s' % url_encode({'login': user.login, 'redirect': '/web'})
                )

        # ── RENDER DECISION ──────────────────────────────────────────────
        # GET with no role → show your beautiful landing page (unchanged)
        # GET with role    → redirect to the dedicated FMS form route
        # POST errors land back on the same dedicated route (handled there)
        role = request.params.get('role', '').strip()

        if not role and request.httprequest.method == 'GET':
            response = request.render('registration_process.fms_signup_landing', qcontext)
        elif role == 'customer':
            return request.redirect('/fms/signup/customer', code=302)
        elif role == 'vendor':
            return request.redirect('/fms/signup/vendor', code=302)
        else:
            response = request.render('auth_signup.signup', qcontext)

        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    # ------------------------------------------------------------------
    # DEDICATED CUSTOMER SIGNUP — /fms/signup/customer
    # Own route = no parent conflict, full control over form + backend
    # ------------------------------------------------------------------
    @http.route('/fms/signup/customer', type='http', auth='public',
                website=True, sitemap=False)
    def fms_customer_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        # Inject FMS params into qcontext
        for key in SIGN_UP_REQUEST_PARAMS:
            if key not in qcontext and request.params.get(key) is not None:
                qcontext[key] = request.params[key]
        qcontext['role'] = 'customer'

        if request.httprequest.method == 'POST' and 'error' not in qcontext:
            try:
                self.do_signup(qcontext)
                if request.session.uid is None:
                    request.update_env(user=request.env.ref('base.public_user'))

                User = request.env['res.users']
                user_sudo = User.sudo().search(
                    User._get_login_domain(qcontext.get('login')),
                    order=User._get_login_order(), limit=1
                )
                if user_sudo:
                    _enrich_partner(user_sudo.partner_id, 'customer', qcontext)
                    template = request.env.ref(
                        'auth_signup.mail_template_user_signup_account_created',
                        raise_if_not_found=False
                    )
                    if template:
                        template.sudo().send_mail(user_sudo.id, force_send=True)

                request.update_context(skip_captcha_login=SKIP_CAPTCHA_LOGIN)
                return self.web_login(*args, **kw)

            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                User = request.env['res.users']
                if User.sudo().with_context(active_test=False).search_count(
                    User._get_login_domain(qcontext.get('login')), limit=1
                ):
                    qcontext['error'] = _('Another user is already registered using this email address.')
                else:
                    _logger.warning('%s', e)
                    qcontext['error'] = _('Could not create a new account.') + Markup('<br/>') + str(e)

        response = request.render('registration_process.fms_signup_customer', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    # ------------------------------------------------------------------
    # DEDICATED VENDOR SIGNUP — /fms/signup/vendor
    # ------------------------------------------------------------------
    @http.route('/fms/signup/vendor', type='http', auth='public',
                website=True, sitemap=False)
    def fms_vendor_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        for key in SIGN_UP_REQUEST_PARAMS:
            if key not in qcontext and request.params.get(key) is not None:
                qcontext[key] = request.params[key]
        qcontext['role'] = 'vendor'

        if request.httprequest.method == 'POST' and 'error' not in qcontext:
            try:
                self.do_signup(qcontext)
                if request.session.uid is None:
                    request.update_env(user=request.env.ref('base.public_user'))

                User = request.env['res.users']
                user_sudo = User.sudo().search(
                    User._get_login_domain(qcontext.get('login')),
                    order=User._get_login_order(), limit=1
                )
                if user_sudo:
                    _enrich_partner(user_sudo.partner_id, 'vendor', qcontext)
                    template = request.env.ref(
                        'auth_signup.mail_template_user_signup_account_created',
                        raise_if_not_found=False
                    )
                    if template:
                        template.sudo().send_mail(user_sudo.id, force_send=True)

                request.update_context(skip_captcha_login=SKIP_CAPTCHA_LOGIN)
                return self.web_login(*args, **kw)

            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                User = request.env['res.users']
                if User.sudo().with_context(active_test=False).search_count(
                    User._get_login_domain(qcontext.get('login')), limit=1
                ):
                    qcontext['error'] = _('Another user is already registered using this email address.')
                else:
                    _logger.warning('%s', e)
                    qcontext['error'] = _('Could not create a new account.') + Markup('<br/>') + str(e)

        qcontext['fms_services'] = self._get_fms_services()
        response = request.render('registration_process.fms_signup_vendor', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    def _get_fms_services(self):
        """Fetch published products/services from website shop."""
        Product = request.env['product.template'].sudo()
        products = Product.search([
            ('website_published', '=', True),
            ('sale_ok', '=', True),
        ], order='name asc')
        return products


