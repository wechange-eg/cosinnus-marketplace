# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse

from cosinnus_marketplace.models import Marketplace


NOTIFY_MODELS = [Marketplace]
NOTIFY_POST_SUBSCRIBE_URLS = {
    'marketplace.Marketplace': {
        'show': lambda obj, group: obj.get_absolute_url(),
        'list': lambda obj, group: reverse('sinn_marketplace-entry-list', kwargs={'group': group.pk}),
    },
}
