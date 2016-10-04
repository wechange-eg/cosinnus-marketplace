# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_marketplace.models import Marketplace, Option, Vote


class VoteInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('description', 'image', 'marketplace')
    model = Vote


class OptionAdmin(admin.ModelAdmin):
    inlines = (VoteInlineAdmin,)
    list_display = ('marketplace', 'count')
    list_filter = ('marketplace__state', 'marketplace__creator', 'marketplace__group',)
    readonly_fields = ('marketplace', 'count')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            # we create a new option and the user should be able to select
            # an marketplace.
            return filter(lambda x: x != 'marketplace', self.readonly_fields)
        return super(OptionAdmin, self).get_readonly_fields(request, obj)


class OptionInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('description', 'image', 'marketplace', 'count')
    model = Option
    readonly_fields = ('count',)


class MarketplaceAdmin(admin.ModelAdmin):
    inlines = (OptionInlineAdmin,)
    list_display = ('title', 'creator', 'group', 'state')
    list_filter = ('state', 'creator', 'group',)
    search_fields = ('title', 'description', 'user__first_name', 'user__last_name', 'user__email', 'group__name')


admin.site.register(Marketplace, MarketplaceAdmin)
admin.site.register(Option, OptionAdmin)
