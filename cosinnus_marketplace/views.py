# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import DeleteView, UpdateView, CreateView
from django.views.generic.list import ListView
from django.utils.timezone import now

from extra_views import (CreateWithInlinesView, FormSetView, InlineFormSet,
    UpdateWithInlinesView)

from django_ical.views import ICalFeed

from cosinnus.views.export import CSVExportView
from cosinnus.views.mixins.group import (RequireReadMixin, RequireWriteMixin,
    GroupFormKwargsMixin, FilterGroupMixin)
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus.views.attached_object import AttachableViewMixin

from cosinnus_marketplace.conf import settings
from cosinnus_marketplace.forms import CommentForm, OfferForm
from cosinnus_marketplace.models import Offer, current_offer_filter, Comment
from django.shortcuts import get_object_or_404
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_marketplace.filters import OfferFilter
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user,\
    check_object_read_access, check_ug_membership
from cosinnus.core.decorators.views import require_read_access,\
    require_user_token_access
from django.contrib.sites.models import Site, get_current_site
from annoying.functions import get_object_or_None
from cosinnus.templatetags.cosinnus_tags import has_write_access
from annoying.exceptions import Redirect
from django import forms


class MarketplaceIndexView(RequireReadMixin, RedirectView):

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:offer:list', kwargs={'group': self.group})

index_view = MarketplaceIndexView.as_view()


class OfferListView(RequireReadMixin, FilterGroupMixin, CosinnusFilterMixin, ListView):

    model = Offer
    filterset_class = OfferFilter
    offer_view = 'all'   # 'all', 'selling' or 'buying'
    template_name = 'cosinnus_marketplace/offer_list.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.offer_view = kwargs.get('offer_view', 'all')
        return super(OfferListView, self).dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """ In the calendar we only show scheduled marketplaces """
        qs = super(OfferListView, self).get_queryset()
        self.unfiltered_qs = qs
        if self.offer_view == 'selling':
            qs = qs.filter(state=Offer.TYPE_SELLING)
        elif self.offer_view == 'buying':
            qs = qs.filter(state=Offer.TYPE_BUYING)
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(OfferListView, self).get_context_data(**kwargs)
        context.update({
            'offer_view': self.offer_view,
            'offers': context['object_list'],
        })
        return context

offer_list_view = OfferListView.as_view()


    
class OfferFormMixin(RequireWriteMixin, FilterGroupMixin, GroupFormKwargsMixin,
                     UserFormKwargsMixin):
    
    form_class = OfferForm
    model = Offer
    message_success = _('Offer "%(title)s" was edited successfully.')
    message_error = _('Offer "%(title)s" could not be edited.')
    
    def dispatch(self, request, *args, **kwargs):
        self.form_view = kwargs.get('form_view', None)
        return super(OfferFormMixin, self).dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super(OfferFormMixin, self).get_context_data(**kwargs)
        tags = Offer.objects.tags()
        context.update({
            'tags': tags,
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        kwargs = {'group': self.group}
        # no self.object if get_queryset from add/edit view returns empty
        if hasattr(self, 'object'):
            kwargs['slug'] = self.object.slug
            urlname = 'cosinnus:offer:detail'
        else:
            urlname = 'cosinnus:offer:list'
        return group_aware_reverse(urlname, kwargs=kwargs)


class OfferAddView(OfferFormMixin, AttachableViewMixin, CreateWithInlinesView):
    
    message_success = _('Offer "%(title)s" was added successfully.')
    message_error = _('Offer "%(title)s" could not be added.')

    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        ret = super(OfferAddView, self).forms_valid(form, inlines)

        return ret

offer_add_view = OfferAddView.as_view()


class OfferEditView(OfferFormMixin, AttachableViewMixin, UpdateWithInlinesView):
    
    def get_object(self, queryset=None):
        obj = super(OfferEditView, self).get_object(queryset=queryset)
        self.object = obj
        return obj
    
offer_edit_view = OfferEditView.as_view()


class OfferDeleteView(OfferFormMixin, DeleteView):
    message_success = _('Offer "%(title)s" was deleted successfully.')
    message_error = _('Offer "%(title)s" could not be deleted.')

    def get_success_url(self):
        return group_aware_reverse('cosinnus:offer:list', kwargs={'group': self.group})

offer_delete_view = OfferDeleteView.as_view()


class CommentCreateView(RequireWriteMixin, FilterGroupMixin, CreateView):

    form_class = CommentForm
    group_field = 'offer__group'
    model = Comment
    template_name = 'cosinnus_marketplace/offer_vote.html'
    
    message_success = _('Your comment was added successfully.')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.offer = self.offer
        messages.success(self.request, self.message_success)
        return super(CommentCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(CommentCreateView, self).get_context_data(**kwargs)
        # always overwrite object here, because we actually display the offer as object, 
        # and not the comment in whose view we are in when form_invalid comes back
        context.update({
            'offer': self.offer,
            'object': self.offer, 
        })
        return context

    def get(self, request, *args, **kwargs):
        self.offer = get_object_or_404(Offer, group=self.group, slug=self.kwargs.get('offer_slug'))
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.offer = get_object_or_404(Offer, group=self.group, slug=self.kwargs.get('offer_slug'))
        self.referer = request.META.get('HTTP_REFERER', self.offer.group.get_absolute_url())
        return super(CommentCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_create = CommentCreateView.as_view()


class CommentDeleteView(RequireWriteMixin, FilterGroupMixin, DeleteView):

    group_field = 'offer__group'
    model = Comment
    template_name_suffix = '_delete'
    
    message_success = _('Your comment was deleted successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CommentDeleteView, self).get_context_data(**kwargs)
        context.update({'offer': self.object.offer})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.offer.group.get_absolute_url())
        return super(CommentDeleteView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        messages.success(self.request, self.message_success)
        return self.referer

comment_delete = CommentDeleteView.as_view()


class CommentDetailView(SingleObjectMixin, RedirectView):

    model = Comment

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        return HttpResponseRedirect(obj.get_absolute_url())

comment_detail = CommentDetailView.as_view()


class CommentUpdateView(RequireWriteMixin, FilterGroupMixin, UpdateView):

    form_class = CommentForm
    group_field = 'offer__group'
    model = Comment
    template_name_suffix = '_update'

    def get_context_data(self, **kwargs):
        context = super(CommentUpdateView, self).get_context_data(**kwargs)
        context.update({'offer': self.object.offer})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.offer.group.get_absolute_url())
        return super(CommentUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_update = CommentUpdateView.as_view()

