# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm

from cosinnus_marketplace.models import Offer, current_offer_filter


class CurrentMarketplacesForm(DashboardWidgetForm):
    amount = forms.IntegerField(label="Amount", initial=5, min_value=0,
        help_text="0 means unlimited", required=False)
    template_name = 'cosinnus_marketplace/widgets/marketplace_widget_form.html'
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('group', None)
        super(CurrentMarketplacesForm, self).__init__(*args, **kwargs)


class CurrentMarketplaces(DashboardWidget):

    app_name = 'marketplace'
    form_class = CurrentMarketplacesForm
    model = Offer
    title = _('Current Offers')
    user_model_attr = None  # No filtering on user page
    widget_name = 'current'
    template_name = 'cosinnus_marketplace/widgets/current.html'
    
    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        count = int(self.config['amount'])
        all_current_marketplaces = self.get_queryset().\
                filter(is_active=True).\
                order_by('-created').\
                select_related('group').all()
        marketplaces = all_current_marketplaces
        
        if count != 0:
            marketplaces = marketplaces.all()[offset:offset+count]
        
        data = {
            'marketplaces': marketplaces,
            'all_current_marketplaces': all_current_marketplaces,
            'no_data': _('No current marketplaces'),
            'group': self.config.group,
        }
        return (render_to_string(self.template_name, data), len(marketplaces), len(marketplaces) >= count)

    def get_queryset(self):
        qs = super(CurrentMarketplaces, self).get_queryset()
        return current_offer_filter(qs)
