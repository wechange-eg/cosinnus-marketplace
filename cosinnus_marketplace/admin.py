# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_marketplace.models import Offer, OfferCategory, OfferCategoryGroup


class OfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'creator', 'group',)
    list_filter = ('type', 'creator', 'group',)
    search_fields = ('title', 'description', 'user__first_name', 'user__last_name', 'user__email', 'group__name')

admin.site.register(Offer, OfferAdmin)


class OfferCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'name_ru', 'name_uk', 'category_group')

admin.site.register(OfferCategory, OfferCategoryAdmin)


class OfferCategoryGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'name_ru', 'name_uk', 'order_key')

admin.site.register(OfferCategoryGroup, OfferCategoryGroupAdmin)
