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
from odoo import api, models, _, fields
import logging
_logger = logging.getLogger(__name__)

NUMBER_OF_COLS = 12


class MrpMpsReport(models.TransientModel):
    _name = 'mrp.mps.report'
    _inherit = 'mrp.mps.report'

    @api.multi
    def get_data(self, product):
        StockMove = self.env['stock.move']
        StockQuant = self.env['stock.quant']
        MrpMpsLocation = self.env['mrp.mps.location']
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
            lead_time = (product.seller_ids and product.seller_ids[0].delay or 0) + self.env.user.company_id.po_lead
            _logger.info(lead_time)
        if mo_type and mo_type.id in product.route_ids.ids:
            lead_time = product.produce_delay + self.env.user.company_id.manufacturing_lead
        leadtime = date + relativedelta.relativedelta(days=int(lead_time))
        # Take first day of month or week
        if self.period == 'month':
            date = datetime.datetime(date.year, date.month, 1)
        elif self.period == 'week':
            date = date - relativedelta.relativedelta(days=date.weekday())

        #if date < datetime.datetime.today():
            #initial = product.with_context(to_date=date.strftime('%Y-%m-%d')).qty_available
        #else:

        mrp_mps_locations = MrpMpsLocation.search([])
        list_location = []
        len_location = len(mrp_mps_locations)
        cont = 1
        for mrp_mps_location in mrp_mps_locations:
            tuple_location = ('location_id', '=', mrp_mps_location.location_id.id)
            if cont < len_location:
                list_location.append('|')
            list_location.append(tuple_location)
            cont += 1
        initial = 0
        if len(list_location) > 0:
            domain_quant = [('product_id', '=', product.id)] + list_location
            stock_quants = StockQuant.search(domain_quant)

            for quant in stock_quants:
                initial += quant.qty
        else:
            initial = product.qty_available

        # Compute others cells
        for p in range(NUMBER_OF_COLS):
            if self.period == 'month':
                date_to = date + relativedelta.relativedelta(months=1)
                name = date.strftime('%b')
                name = babel.dates.format_date(format="MMM YY", date=date, locale=self._context.get('lang') or 'en_US')
            elif self.period == 'week':
                #_logger.info('DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD')
                #_logger.info(date.strftime('%U'))
                #_logger.info(date)
                date_to = date + relativedelta.relativedelta(days=7)
                #_logger.info(date_to)
                name = _('Week %s') % date.strftime('%W')
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
            #if mode == 'manual':
                #to_supply = sum(forecasts.filtered(lambda x: x.mode == 'manual').mapped('to_supply'))
            #if proc_dec:
                #to_supply = sum(forecasts.filtered(lambda x: x.procurement_id).mapped('procurement_id').mapped('product_qty'))

            qty_in = 0
            product_in = 0
            compromise_qty = 0
            point = 0
            calc = 0
            product_out = 0
            compromise_out_qty = 0
            qty_late_in = 0
            band = False
            if buy_type and buy_type.id in product.route_ids.ids:
                timeback = date - relativedelta.relativedelta(days=int(lead_time))
                for res in result:
                    date_date = datetime.datetime.strptime(res['date'], '%Y-%m-%d').date()
                    date_date_to = datetime.datetime.strptime(res['date_to'], '%Y-%m-%d').date()
                    if date_date <= timeback.date() and date_date_to > timeback.date() and res['to_supply'] > 0:
                        qty_in = res['to_supply']
                    else:
                        if date_date >= timeback.date():
                            qty_late_in += res['to_supply']
                        if res['in'] == 1 and date_date >= timeback.date():
                            qty_late_in = res['to_supply']
                            band = True

                mrp_mps_locations = MrpMpsLocation.search([])
                list_location = []
                len_location = len(mrp_mps_locations)
                cont = 1
                for mrp_mps_location in mrp_mps_locations:
                    tuple_location = ('location_dest_id', '=', mrp_mps_location.location_id.id)
                    if cont < len_location:
                        list_location.append('|')
                    list_location.append(tuple_location)
                    cont += 1

                domain = [
                        ('date_expected', '>=', date.strftime('%Y-%m-%d')),
                        ('date_expected', '<', date_to.strftime('%Y-%m-%d')),
                        ('picking_type_id.code', '=', 'incoming'),
                        ('state', 'not in', ['cancel', 'done']),
                        ('product_id.id', '=', product.id)]
                #domain = domain + list_location

                stock_moves = StockMove.search(domain)
                for move in stock_moves:
                    product_in += move.product_uom_qty
                    product_compromise = ProductCompromise.search([
                                        ('stock_move_in_id.id', '=', move.id),
                                        ('state', '=', 'assigned')])
                    for compromise in product_compromise:
                        compromise_qty += compromise.qty_compromise

                domain2 = [
                    ('raw_material_production_id.sale_id.date_promised', '>=', date.strftime('%Y-%m-%d')),
                    ('raw_material_production_id.sale_id.date_promised', '<', date_to.strftime('%Y-%m-%d')),
                    ('state', 'not in', ['cancel', 'done']),
                    ('product_id.id', '=', product.id)]
                #domain2 = domain2 + list_location
                stock_move_outs = StockMove.search(domain2)
                for move_out in stock_move_outs:
                    product_out += move_out.product_uom_qty
                    product_out_compromise = ProductCompromise.search([
                                    ('stock_move_out_id.id', '=', move_out.id),
                                    ('state', '=', 'assigned')])
                    for compromise_out in product_out_compromise:
                        compromise_out_qty += compromise_out.qty_compromise

                if self.period == 'day' or self.period == 'week':
                    if p == 0:
                        date_old = datetime.datetime(date.year, date.month, 1)
                        domain3 = [
                            ('raw_material_production_id.sale_id.date_promised', '>=', date_old.strftime('%Y-%m-%d')),
                            ('raw_material_production_id.sale_id.date_promised', '<', date.strftime('%Y-%m-%d')),
                            ('state', 'not in', ['cancel', 'done']),
                            ('product_id.id', '=', product.id)]
                        stock_move_outs = StockMove.search(domain3)
                        for move_out in stock_move_outs:
                            product_out += move_out.product_uom_qty
                            product_out_compromise = ProductCompromise.search([
                                            ('stock_move_out_id.id', '=', move_out.id)])
                            for compromise_out in product_out_compromise:
                                compromise_out_qty += compromise_out.qty_compromise

                #elif self.period == 'week':
                    #date = date - relativedelta.relativedelta(days=date.weekday())
            product_in_forecasted = 0
            prod_in = 0
            _logger.info(band)
            _logger.info(qty_in)
            if qty_in > 0 and not band:
                _logger.info(qty_in)
                _logger.info(qty_late_in)
                product_in_forecasted = qty_in + qty_late_in
                prod_in = 1


            product_out -= compromise_out_qty
            forecasted = product_in_forecasted - demand + initial - product_out + product_in - compromise_qty
            stock_warehouse = StockWarehouseOrderpoint.search([
                                    ('product_id.id', '=', product.id)])
            if prod_in == 1:
                qty_late_in = 0
            if stock_warehouse:
                point = stock_warehouse.product_min_qty
            calc = forecasted - point + qty_late_in
            if calc < 0:
                calc = abs(calc)
            else:
                calc = 0

            if mode == 'manual':
                to_supply = sum(forecasts.filtered(lambda x: x.mode == 'manual').mapped('to_supply'))
            else:
                to_supply = calc

            result.append({
                'period': name,
                'date': date.strftime('%Y-%m-%d'),
                'date_to': date_to.strftime('%Y-%m-%d'),
                'initial': initial,
                'product_in': product_in,
                'product_out': product_out,
                'compromise_qty': compromise_qty,
                'product_in_forecasted': product_in_forecasted,
                'in': prod_in,
                'demand': demand,
                'mode': mode,
                'state': state,
                'indirect': indirect_total,
                'to_supply': to_supply,
                'forecasted': forecasted,
                'route_type': display,
                'procurement_enable': True if not proc_dec and leadtime >= date else False,
                'procurement_done': proc_dec,
                'lead_time': leadtime.strftime('%Y-%m-%d'),
            })
            #_logger.info(result)
            _logger.info(prod_in)
            _logger.info(product_in_forecasted)
            _logger.info(prod_in)
            _logger.info(to_supply)
            _logger.info(forecasted)
            _logger.info(product_in)
            _logger.info(product_out)
            initial = forecasted
            date = date_to
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
        result = {
            'html': self.env.ref('mrp_mps.report_inventory').render(rcontext),
            'report_context': {'nb_periods': NUMBER_OF_COLS, 'period': res.period},
        }
        return result


class MrpMpsLocation(models.Model):
    _name = "mrp.mps.location"

    location_id = fields.Many2one('stock.location', 'Location', required=True)
    active = fields.Boolean('Active', default=True)
