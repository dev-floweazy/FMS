from odoo import fields, models

class ProjectTask(models.Model):
    _inherit = 'project.task'

    fms_job_id = fields.Many2one(
        'fms.job',
        string='FMS Job',
        ondelete='set null',
        index=True,
    )