# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import requests
from odoo import _, fields, models
from odoo.exceptions import ValidationError
from .garanti_connector import GarantiConnector
from odoo.addons.payment_garanti.const import TEST_URL, PROD_URL, \
    CURRENCY_CODES

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('garanti', "Garanti Sanal Pos")],
        ondelete={'garanti': 'set default'})

    garanti_merchant_id = fields.Char(
        string="Merchant ID",
        help="Merchant ID provided by Garanti Sanal Pos",
        required_if_provider='garanti',
        groups='base.group_user')

    garanti_terminal_id = fields.Char(
        string="Terminal ID",
        help="Terminal ID provided by Garanti Sanal Pos",
        required_if_provider='garanti',
        groups='base.group_user')

    garanti_prov_user = fields.Char(
        string="Provision User",
        help="Provision User provided by Garanti Sanal Pos",
        required_if_provider='garanti',
        groups='base.group_user')

    garanti_prov_password = fields.Char(
        string="Provision Password",
        help="Provision Password provided by Garanti Sanal Pos",
        required_if_provider='garanti',
        groups='base.group_user')

    garanti_store_key = fields.Char(
        string="Store Key",
        help="Store Key provided by Garanti Sanal Pos",
        required_if_provider='garanti',
        groups='base.group_user')

    def _garanti_get_api_url(self):
        """ Return the API URL according to the provider state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            return PROD_URL
        else:
            return TEST_URL

    def _garanti_get_mode(self):
        """
        This method is used to get the mode of the transaction
        :return: The mode of the transaction
        """
        self.ensure_one()
        if self.state == 'enabled':
            return 'PROD'
        else:
            return 'TEST'

    def _garanti_get_company_name(self):
        """
        This method is used to get the company name
        :return: The company name
        """
        self.ensure_one()
        return self.company_id.name

    def _garanti_get_currency_code(self, currency):
        """
        This method is used to get the currency code
        :param currency: The currency id
        :return: The currency code
        """
        currency_id = self.env['res.currency'].browse(currency)
        if currency_id and currency_id.name in CURRENCY_CODES:
            return CURRENCY_CODES[currency_id.name]
        else:
            return '949'

    def _garanti_format_card_number(self, card_number):
        """
        This method is used to format the card number
        :param card_number: The card number
        :return: The formatted card number
        """
        card_number = card_number.replace(' ', '')
        if len(card_number) == 16 and card_number.isdigit():
            return card_number
        else:
            raise ValidationError(_('Card number is not valid.'))

    def _garanti_get_return_url(self):
        """
        This method is used to get the return url for the Garanti API
        :return: The return url
        """
        self.ensure_one()
        return self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url') + '/payment/garanti/return'

    def _garanti_make_payment_request(self, tx, amount, currency, card_args,
                                      client_ip):
        """
        This method is used to make a payment request to the Garanti Endpoint
        :param tx: The transaction
        :param amount: The amount of the transaction
        :param currency: The currency of the transaction
        """
        self.ensure_one()
        connector = GarantiConnector(self, tx, amount, currency, card_args,
                                     client_ip)
        method, resp = connector._garanti_make_payment_request()

        return {
            'status': 'success',
            'method': method,
            'response': resp,
        }

    def _garanti_validate_card_args(self, card_args):
        """
        Validation method for credit/debit card information
        :param card_args: The card information
        :return: error message if there is any error
        """
        error = ''
        card_number = card_args.get('card_number')
        card_cvv = card_args.get('card_cvv')
        if not card_number or len(card_number) < 16:
            error += _('Card number is not valid.\n')

        if not card_cvv or len(card_cvv) < 3:
            error += _('Card CVV is not valid.\n')

        if not card_args.get('card_name'):
            error += _('Card name is not valid.\n')

        if not card_args.get('card_valid_month') or not card_args.get(
                'card_valid_year'):
            error += _('Card expiration date is not valid.\n')
        return error
