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
import babel.dates
from dateutil import relativedelta
from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

NUMBER_OF_COLS = 12


class MrpMpsReport(models.TransientModel):
    _name = 'mrp.mps.report'
    _inherit = 'mrp.mps.report'

    @api.multi
    def get_data(self, product):
        StockMove = self.env['stock.move']
        ProductCompromise = self.env['product.compromise']
        StockWarehouseOrderpoint = self.env['stock.warehouse.orderpoint']
        result = []
        forecasted = product.mps_forecasted
        date = datetime.datetime.now()
        indirect = self.get_indirect(product)[product.id]
        display = _('To Supply / Produce')
        buy_type = self.env.ref('purchase.route_warehouse0_buy', raise_if_not_found=False)
        mo_type = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
        lead_time = 0
        if buy_type and buy_type.id in product.route_ids.ids:
            _logger.info('LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL')
            lead_time = (product.seller_ids and product.seller_ids[0].delay or 0) + self.env.user.company_id.po_lead
            _logger.info(lead_time)
        if mo_type and mo_type.id in product.route_ids.ids:
            lead_time = product.produce_delay + self.env.user.company_id.manufacturing_lead
        leadtime = date + relativedelta.relativedelta(days=int(lead_time))
        _logger.info('KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK')
        _logger.info(leadtime)
        # Take first day of month or week
        if self.period == 'month':
            date = datetime.datetime(date.year, date.month, 1)
        elif self.period == 'week':
            date = date - relativedelta.relativedelta(days=date.weekday())

        #if date < datetime.datetime.today():
            #initial = product.with_context(to_date=date.strftime('%Y-%m-%d')).qty_available
        #else:
        initial = product.qty_available
        # Compute others cells
        _logger.info('1113333333333333333333333333333333333333333333333333333')
        for p in range(NUMBER_OF_COLS):
            _logger.info('SIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII')
            if self.period == 'month':
                date_to = date + relativedelta.relativedelta(months=1)
                name = date.strftime('%b')
                name = babel.dates.format_date(format="MMM YY", date=date, locale=self._context.get('lang') or 'en_US')
            elif self.period == 'week':
                date_to = date + relativedelta.relativedelta(days=7)
                name = _('Week %s') % date.strftime('%U')
            else:
                date_to = date + relativedelta.relativedelta(days=1)
                name = babel.dates.format_date(format="MMM d", date=date, locale=self._context.get('lang') or 'en_US')
            forecasts = self.env['sale.forecast'].search([
                ('date', '>=', date.strftime('%Y-%m-%d')),
                ('date', '<', date_to.strftime('%Y-%m-%d')),
                ('product_id', '=', product.id),
            ])
            state = 'draft'
            mode = 'auto'
            proc_dec = False
            for f in forecasts:
                if f.mode == 'manual':
                    mode = 'manual'
                if f.state == 'done':  # Still used, state done?
                    state = 'done'
                if f.procurement_id:
                    proc_dec = True
            demand = sum(forecasts.filtered(lambda x: x.mode == 'auto').mapped('forecast_qty'))
            indirect_total = 0.0
            for day, qty in indirect.items():
                if (day >= date.strftime('%Y-%m-%d')) and (day < date_to.strftime('%Y-%m-%d')):
                    indirect_total += qty
            to_supply = product.mps_forecasted - initial + demand + indirect_total
            to_supply = max(to_supply, product.mps_min_supply)
            if product.mps_max_supply > 0:
                to_supply = min(product.mps_max_supply, to_supply)

            # Need to compute auto and manual separately as forecasts are still important
            if mode == 'manual':
                to_supply = sum(forecasts.filtered(lambda x: x.mode == 'manual').mapped('to_supply'))
            if proc_dec:
                to_supply = sum(forecasts.filtered(lambda x: x.procurement_id).mapped('procurement_id').mapped('product_qty'))

#cambios mios
            qty_in = 0
            product_in = 0
            compromise_qty = 0
            point = 0
            calc = 0
            product_out = 0
            if buy_type and buy_type.id in product.route_ids.ids:
                timeback = date - relativedelta.relativedelta(days=int(lead_time))
                _logger.info('oooooooooooooooooooooooooooooooooooooooooooooooo')
                _logger.info(date)
                _logger.info(timeback)
                _logger.info(date_to)
                for res in result:
                    date_date = datetime.datetime.strptime(res['date'], '%Y-%m-%d').date()
                    date_date_to = datetime.datetime.strptime(res['date_to'], '%Y-%m-%d').date()

                    if date_date <= timeback.date() and date_date_to >= timeback.date():
                        qty_in = res['to_supply']

                #busco los pedidos que estan por llegar en ese periodo de tiempo
                stock_moves = StockMove.search([
                        ('date_expected', '>=', date.strftime('%Y-%m-%d')),
                        ('date_expected', '<=', date_to.strftime('%Y-%m-%d')),
                        ('picking_type_id.code', '=', 'incoming'),
                        ('state', 'not in', ['cancel', 'done']),
                        ('product_id.id', '=', product.id)])
                for move in stock_moves:
                    product_in += move.product_uom_qty
                    _logger.info('SIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII')
                    _logger.info(product_in)
                    product_compromise = ProductCompromise.search([
                                        ('stock_move_in_id.id', '=', move.id)])
                    for compromise in product_compromise:
                        compromise_qty += compromise.qty_compromise

                stock_move_outs = StockMove.search([
                    ('raw_material_production_id.sale_id.date_promised','>=',date.strftime('%Y-%m-%d')),
                    ('raw_material_production_id.sale_id.date_promised','<=',date_to.strftime('%Y-%m-%d')),
                    ('state', 'not in', ['cancel', 'done']),
                    ('product_id.id', '=', product.id)])
                for move_out in stock_move_outs:
                    product_out += move_out.product_uom_qty
                    _logger.info('kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
                    _logger.info(product_out)
            forecasted = qty_in - demand + initial - product_out + product_in - compromise_qty
            stock_warehouse = StockWarehouseOrderpoint.search([
                                    ('product_id.id', '=', product.id)])

            if stock_warehouse:
                point = stock_warehouse.product_min_qty
            calc = forecasted - point
            if calc < 0:
                calc = abs(calc)
            else:
                calc = 0

#hasta aqui mis cambios
            #forecasted = to_supply - demand + initial - indirect_total
            _logger.info('222222222222222222222222222222222222222222222222222222')
            result.append({
                'period': name,
                'date': date.strftime('%Y-%m-%d'),
                'date_to': date_to.strftime('%Y-%m-%d'),
                'initial': initial,
                'product_in': product_in,
                'product_out': product_out,
                'compromise_qty': compromise_qty,
                'demand': demand,
                'mode': mode,
                'state': state,
                'indirect': indirect_total,
                #'to_supply': to_supply,
                'to_supply': calc,
                'forecasted': forecasted,
                'route_type': display,
                'procurement_enable': True if not proc_dec and leadtime >= date else False,
                'procurement_done': proc_dec,
                'lead_time': leadtime.strftime('%Y-%m-%d'),
            })
            initial = forecasted
            date = date_to
        _logger.info(result)
        return result

    @api.model
    def get_html(self, domain=[]):
        res = self.search([], limit=1)
        if not res:
            res = self.create({})
        domain.append(['mps_active', '=', True])
        rcontext = {
            'products': map(lambda x: (x, res.get_data(x)), self.env['product.product'].search(domain, limit=20)),
            'nb_periods': NUMBER_OF_COLS,
            'company': self.env.user.company_id,
            'format_float': self.env['ir.qweb.field.float'].value_to_html,
        }
        _logger.info('nnnnnnnnnnnnnnnnnnnnnuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu')
        _logger.info(rcontext)
        result = {
            'html': self.env.ref('mrp_mps.report_inventory').render(rcontext),
            'report_context': {'nb_periods': NUMBER_OF_COLS, 'period': res.period},
        }
        return result