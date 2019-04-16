# Copyright 2017  Alexandre Díaz
# Copyright 2017  Dario Lodeiros
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import models, fields, api, _
import json
from odoo.tools import float_is_zero, float_compare, pycompat
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def create(self, vals):
        if self.env.context.get('invoice_origin', False):
            vals.update({'origin': self.env.context.get['invoice_origin']})
        return super(AccountInvoice, self).create(vals)

    """WIP"""
    @api.multi
    def action_folio_payments(self):
        self.ensure_one()
        sales = self.mapped('invoice_line_ids.sale_line_ids.order_id')
        folios = self.env['hotel.folio'].search([('order_id.id','in',sales.ids)])
        payments_obj = self.env['account.payment']
        payments = payments_obj.search([('folio_id','in',folios.ids)])
        payment_ids = payments.mapped('id')
        return{
            'name': _('Payments'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', payment_ids)],
        }

    from_folio = fields.Boolean(compute='_computed_folio_origin')
    folio_ids = fields.Many2many(
            comodel_name='hotel.folio', compute='_computed_folio_origin')
    outstanding_folios_debits_widget = fields.Text(compute='_get_outstanding_folios_JSON')
    has_folios_outstanding = fields.Boolean(compute='_get_outstanding_folios_JSON')

    @api.multi
    def action_invoice_open(self):
        to_open_invoices_without_vat = self.filtered(lambda inv: inv.state != 'open' and inv.partner_id.vat == False)
        to_open_invoices_without_country = self.filtered(lambda inv: inv.state != 'open' and not inv.partner_id.country_id)
        if to_open_invoices_without_vat or to_open_invoices_without_country:
            vat_error = _("We need the VAT and Country of the following companies")
            for invoice in to_open_invoices_without_vat:
                vat_error += ", " + invoice.partner_id.name
            for invoice in to_open_invoices_without_country:
                vat_error += ", " + invoice.partner_id.name
            raise ValidationError(vat_error)
        return super(AccountInvoice, self).action_invoice_open()

    @api.multi
    def _computed_folio_origin(self):
        for inv in self:
            folios = inv.mapped('invoice_line_ids.reservation_ids.folio_id')
            folios |= inv.mapped('invoice_line_ids.service_ids.folio_id')
            if folios:
                inv.from_folio = True
                inv.folio_ids = [(6, 0, folios.ids)]

    @api.one
    def _get_outstanding_folios_JSON(self):
        self.outstanding_folios_debits_widget = json.dumps(False)
        if self.from_folio:
            payment_ids = self.folio_ids.mapped('payment_ids.id')
            if self.state == 'open':
                domain = [('account_id', '=', self.account_id.id),
                          ('partner_id', '!=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                          ('reconciled', '=', False),
                          ('payment_id', 'in', payment_ids),
                          '|',
                            '&', ('amount_residual_currency', '!=', 0.0), ('currency_id','!=', None),
                            '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id','=', None), ('amount_residual', '!=', 0.0)]
                if self.type in ('out_invoice', 'in_refund'):
                    domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                    type_payment = _('Outstanding credits in Folio')
                else:
                    domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                    type_payment = _('Outstanding debits')
                info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
                lines = self.env['account.move.line'].search(domain)
                currency_id = self.currency_id
                if len(lines) != 0:
                    for line in lines:
                        # get the outstanding residual value in invoice currency
                        if line.currency_id and line.currency_id == self.currency_id:
                            amount_to_show = abs(line.amount_residual_currency)
                        else:
                            amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(abs(line.amount_residual), self.currency_id)
                        if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                            continue
                        if line.ref :
                            title = '%s : %s' % (line.move_id.name, line.ref)
                        else:
                            title = line.move_id.name
                        info['content'].append({
                            'journal_name': line.ref or line.move_id.name,
                            'title': title,
                            'amount': amount_to_show,
                            'currency': currency_id.symbol,
                            'id': line.id,
                            'position': currency_id.position,
                            'digits': [69, self.currency_id.decimal_places],
                        })
                    info['title'] = type_payment
                    self.outstanding_folios_debits_widget = json.dumps(info)
                    self.has_folio_outstanding = True
