# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def register():
    # Import here to prmarketplace import side effects
    from django.utils.translation import ugettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import (app_registry,
        attached_object_registry, url_registry, widget_registry)

    app_registry.register('cosinnus_marketplace', 'marketplace', _('Marketplaces'), deactivatable=True)
    attached_object_registry.register('cosinnus_marketplace.Marketplace',
                             'cosinnus_marketplace.utils.renderer.MarketplaceRenderer')
    url_registry.register_urlconf('cosinnus_marketplace', 'cosinnus_marketplace.urls')
    widget_registry.register('marketplace', 'cosinnus_marketplace.dashboard.CurrentMarketplaces')
    
    # makemessages replacement protection
    name = pgettext_lazy("the_app", "marketplace")
