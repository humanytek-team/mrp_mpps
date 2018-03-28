# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017 Humanytek (<www.humanytek.com>).
#    Rubén Bravo <rubenred18@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import datetime

from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import logging
_logger = logging.getLogger(__name__)


class SaleForecast(models.Model):
    _name = 'sale.forecast'
    _inherit = 'sale.forecast'

    def generate_procurement(self, product_id=False, limit=False):
        """ Create procurements related to """
        product = self.env['product.product'].browse(product_id)
        #date = fields.Datetime.from_string(fields.Datetime.now()) #necessary?
        mps_report = self.env['mrp.mps.report'].search([])[0]
        #if not limit:
        result = [x for x in mps_report.get_data(product) if (x['product_in_forecasted'] and x['product_in_forecasted'] > 0)]
        for data in result:
            date_cmp = data['date']
            if date_cmp < fields.Datetime.now():
                date = fields.Datetime.now()
            else:
                date = date_cmp
            procurement_id = self._action_procurement_create(product, data['product_in_forecasted'], date)
            if procurement_id:
                #domain = [('date', '<', data['date_to']),
                        #('date', '>=', data['date']),
                        #('product_id', '=', product_id),
                        #('state', '!=', 'done'),
                        #('procurement_id', '=', False)]
                #forecasts = self.search(domain)
                #if forecasts:
                    #forecasts.write({'procurement_id': procurement_id, 'state': 'done'})
                #else:
                self.create({'date': date_cmp, 'product_id': product_id, 'forecast_qty': 0.0,
                             'procurement_id': procurement_id, 'state': 'done'})
        #else:
            #result = [x for x in mps_report.get_data(product) if not x['procurement_done']]
            #if result:
                #data = result[0]
                #date_cmp = data['date']
                #if date_cmp < fields.Datetime.now():
                    #date = fields.Datetime.now()
                #else:
                    #date = date_cmp
                #procurement_id = self._action_procurement_create(product, data['product_in_forecasted'], date)
                #if procurement_id:
                    #domain = [('date', '>=', data['date']),
                            #('date', '<', data['date_to']),
                            #('product_id', '=', product_id),
                            #('state', '!=', 'done'),
                            #('procurement_id', '=', False)]
                    #forecasts = self.search(domain)
                    #if forecasts:
                        #forecasts.write({'procurement_id': procurement_id, 'state': 'done'})
                    #else:
                        #self.create({'date': date_cmp, 'product_id': product_id, 'forecast_qty': 0.0,
                                     #'procurement_id': procurement_id, 'state': 'done'})
        return True
