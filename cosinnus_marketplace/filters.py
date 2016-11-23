'''
Created on 05.08.2014

@author: Sascha
'''
from django.utils.translation import ugettext_lazy as _

from cosinnus.views.mixins.filters import CosinnusFilterSet
from cosinnus.forms.filters import AllObjectsFilter, SelectCreatorWidget,\
    DropdownChoiceWidgetWithEmpty
from cosinnus_marketplace.models import Offer, get_categories_grouped
from django_filters.filters import ChoiceFilter


class OfferFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)
    type = ChoiceFilter(label=_('Type'), choices=Offer.TYPE_CHOICES, widget=DropdownChoiceWidgetWithEmpty)
    
    class Meta:
        model = Offer
        fields = ['creator', 'type', 'categories']
        order_by = (
            ('-created', _('Newest Created')),
            ('title', _('Title')),
        )
    
    def get_order_by(self, order_value):
        return super(OfferFilter, self).get_order_by(order_value)
    
    def get_categories_grouped(self):
        return get_categories_grouped(self.form.fields['categories']._queryset)
    
    