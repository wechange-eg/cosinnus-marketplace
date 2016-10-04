# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.renderer import BaseRenderer
from cosinnus_marketplace.models import Marketplace


class MarketplaceRenderer(BaseRenderer):
    """
    MarketplaceRenderer for Cosinnus attached objects
    """
    model = Marketplace
    
    template = 'cosinnus_marketplace/attached_marketplaces.html'
    template_single = 'cosinnus_marketplace/single_marketplace.html'
    template_list = 'cosinnus_marketplace/marketplace_list_standalone.html'
    
    @classmethod
    def render(cls, context, myobjs):
        return super(MarketplaceRenderer, cls).render(context, marketplaces=myobjs)
