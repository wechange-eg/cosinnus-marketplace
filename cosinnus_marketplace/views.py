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
from cosinnus_marketplace.forms import MarketplaceForm, OptionForm, VoteForm,\
    MarketplaceNoFieldForm, CommentForm
from cosinnus_marketplace.models import Marketplace, Option, Vote, current_marketplace_filter,\
    past_marketplace_filter, Comment
from django.shortcuts import get_object_or_404
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_marketplace.filters import MarketplaceFilter
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
        return group_aware_reverse('cosinnus:marketplace:list', kwargs={'group': self.group})

index_view = MarketplaceIndexView.as_view()


class MarketplaceListView(RequireReadMixin, FilterGroupMixin, CosinnusFilterMixin, ListView):

    model = Marketplace
    filterset_class = MarketplaceFilter
    marketplace_view = 'current'   # 'current' or 'past'
    template_name = 'cosinnus_marketplace/marketplace_list.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.marketplace_view = kwargs.get('marketplace_view', 'current')
        return super(MarketplaceListView, self).dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """ In the calendar we only show scheduled marketplaces """
        qs = super(MarketplaceListView, self).get_queryset()
        self.unfiltered_qs = qs
        if self.marketplace_view == 'current':
            qs = current_marketplace_filter(qs)
        elif self.marketplace_view == 'past':
            qs = past_marketplace_filter(qs)
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(MarketplaceListView, self).get_context_data(**kwargs)
        running_marketplaces_count = self.queryset.count() if self.marketplace_view == 'current' else current_marketplace_filter(self.unfiltered_qs).count()
        past_marketplaces_count = self.queryset.count() if self.marketplace_view == 'past' else past_marketplace_filter(self.unfiltered_qs).count()
        
        context.update({
            'running_marketplaces_count': running_marketplaces_count,
            'past_marketplaces_count': past_marketplaces_count,
            'marketplace_view': self.marketplace_view,
            'marketplaces': context['object_list'],
        })
        return context

marketplace_list_view = MarketplaceListView.as_view()


class OptionInlineFormset(InlineFormSet):
    extra = 25
    max_num = 25
    form_class = OptionForm
    model = Option
    
    
class MarketplaceFormMixin(RequireWriteMixin, FilterGroupMixin, GroupFormKwargsMixin,
                     UserFormKwargsMixin):
    form_class = MarketplaceForm
    model = Marketplace
    inlines = [OptionInlineFormset]
    message_success = _('Marketplace "%(title)s" was edited successfully.')
    message_error = _('Marketplace "%(title)s" could not be edited.')
    pre_voting_editing_enabled = True
    
    def dispatch(self, request, *args, **kwargs):
        self.form_view = kwargs.get('form_view', None)
        return super(MarketplaceFormMixin, self).dispatch(request, *args, **kwargs)
    
    def _deactivate_non_editable_fields_after_votes_or_completion(self):
        """ Shuts of all fields or formsets that shouldn't be editable
            after votes have been placed or the marketplace has been closed. """
        self.inlines = []
        self.pre_voting_editing_enabled = False
    
    def get_object(self, *args, **kwargs):
        marketplace = super(MarketplaceFormMixin, self).get_object(*args, **kwargs)
        if marketplace.state != Marketplace.STATE_VOTING_OPEN or marketplace.options.filter(votes__isnull=False).count() > 0:
            self._deactivate_non_editable_fields_after_votes_or_completion()
        return marketplace
    
    def get_context_data(self, **kwargs):
        context = super(MarketplaceFormMixin, self).get_context_data(**kwargs)
        tags = Marketplace.objects.tags()
        context.update({
            'tags': tags,
            'form_view': self.form_view,
            'pre_voting_editing_enabled': self.pre_voting_editing_enabled,
        })
        return context

    def get_success_url(self):
        kwargs = {'group': self.group}
        # no self.object if get_queryset from add/edit view returns empty
        if hasattr(self, 'object'):
            kwargs['slug'] = self.object.slug
            urlname = 'cosinnus:marketplace:detail'
        else:
            urlname = 'cosinnus:marketplace:list'
        return group_aware_reverse(urlname, kwargs=kwargs)

    def forms_valid(self, form, inlines):
        ret = super(MarketplaceFormMixin, self).forms_valid(form, inlines)
        messages.success(self.request,
            self.message_success % {'title': self.object.title})
        return ret

    def forms_invalid(self, form, inlines):
        ret = super(MarketplaceFormMixin, self).forms_invalid(form, inlines)
        if self.object:
            messages.error(self.request,
                self.message_error % {'title': self.object.title})
        return ret



class MarketplaceAddView(MarketplaceFormMixin, AttachableViewMixin, CreateWithInlinesView):
    message_success = _('Marketplace "%(title)s" was added successfully.')
    message_error = _('Marketplace "%(title)s" could not be added.')

    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        form.instance.state = Marketplace.STATE_VOTING_OPEN  # be explicit
        ret = super(MarketplaceAddView, self).forms_valid(form, inlines)

        # Check for non or a single option and set it and inform the user
        num_options = self.object.options.count()
        if num_options == 0:
            messages.info(self.request, _('You should define at least one marketplace option!'))
        return ret

marketplace_add_view = MarketplaceAddView.as_view()

class NoLongerEditableException(Exception):
    pass

class MarketplaceEditView(MarketplaceFormMixin, AttachableViewMixin, UpdateWithInlinesView):
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super(MarketplaceEditView, self).dispatch(request, *args, **kwargs)
        except NoLongerEditableException:
            messages.error(self.request, _('This marketplace is archived and cannot be edited anymore!'))
            return HttpResponseRedirect(self.object.get_absolute_url())
    
    def get_object(self, queryset=None):
        obj = super(MarketplaceEditView, self).get_object(queryset=queryset)
        self.object = obj
        if obj.state == Marketplace.STATE_ARCHIVED:
            raise NoLongerEditableException()
        return obj
    
    def get_context_data(self, *args, **kwargs):
        context = super(MarketplaceEditView, self).get_context_data(*args, **kwargs)
        context.update({
            'has_active_votes': self.object.options.filter(votes__isnull=False).count() > 0,
        })
        return context
    
    def forms_valid(self, form, inlines):
        
        # Save the options first so we can directly
        # access the amount of options afterwards
        #for formset in inlines:
        #    formset.save()


        return super(MarketplaceEditView, self).forms_valid(form, inlines)

marketplace_edit_view = MarketplaceEditView.as_view()


class MarketplaceDeleteView(MarketplaceFormMixin, DeleteView):
    message_success = _('Marketplace "%(title)s" was deleted successfully.')
    message_error = _('Marketplace "%(title)s" could not be deleted.')

    def get_success_url(self):
        return group_aware_reverse('cosinnus:marketplace:list', kwargs={'group': self.group})

marketplace_delete_view = MarketplaceDeleteView.as_view()


class MarketplaceVoteView(RequireReadMixin, FilterGroupMixin, SingleObjectMixin,
        FormSetView):

    message_success = _('Your votes were saved successfully.')
    message_error = _('Your votes could not be saved.')

    extra = 0
    form_class = VoteForm
    model = Marketplace
    template_name = 'cosinnus_marketplace/marketplace_vote.html'
    mode = 'vote' # 'vote' or 'view'
    MODES = ('vote', 'view',)
    
    @require_read_access()
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        marketplace = self.object
        self.mode = 'view'
        if marketplace.state == Marketplace.STATE_VOTING_OPEN and request.user.is_authenticated():
            if check_object_read_access(marketplace, request.user) and (marketplace.anyone_can_vote or check_ug_membership(request.user, self.group)):
                self.mode = 'vote'
        try:
            return super(MarketplaceVoteView, self).dispatch(request, *args, **kwargs)
        except Redirect:
            return HttpResponseRedirect(self.object.get_absolute_url())
        
    def post(self, request, *args, **kwargs):
        if self.mode != 'vote':
            messages.error(request, _('The voting phase for this marketplace is over. You cannot vote for it any more.'))
            return HttpResponseRedirect(self.get_object().get_absolute_url())
        return super(MarketplaceVoteView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(MarketplaceVoteView, self).get_context_data(**kwargs)
        
        self.option_formsets_dict = {} # { option-pk --> form }
        if self.mode == 'vote':
            # create a formset dict matching forms to option-pks so we can pull them together in the template easily
            for form in context['formset'].forms:
                self.option_formsets_dict[form.initial['option']] = form
        
        context.update({
            'object': self.object,
            'options': self.options,
            'option_formsets_dict': self.option_formsets_dict,
            'user_votes_dict': self.user_votes_dict,
            'options_votes_dict': self.options_votes_dict,
            'mode': self.mode,
        })
        return context

    def get_initial(self):
        """ get initial and create user-vote-dict """
        self.object = self.get_object()
        self.options = self.object.options.all().order_by('pk')
        
        self.max_num = self.options.count()
        self.initial = []
        self.user_votes_dict = {} # {<option-pk --> vote-choice }
        self.options_votes_dict = {} # {<option-pk --> [num_votes_no, num_votes_maybe, num_votes_yes] }
        
        for option in self.options:
            vote = None
            if self.request.user.is_authenticated():
                try:
                    vote = option.votes.filter(voter=self.request.user).get()
                except Vote.DoesNotExist:
                    pass
            self.initial.append({
                'option': option.pk,
                'choice': vote.choice if vote else 0,
            })
            self.user_votes_dict[option.pk] = vote.choice if vote else -1
            
            # count existing votes
            option_counts = [0, 0, 0] # [num_votes_no, num_votes_maybe, num_votes_yes]
            for vote in option.votes.all():
                option_counts[vote.choice] += 1
            self.options_votes_dict[option.pk] = option_counts
            
        return self.initial

    def get_success_url(self):
        return self.object.get_absolute_url()

    def formset_valid(self, formset):
        option_choices = {} # { option_id --> choice }
        
        for form in formset:
            cd = form.cleaned_data
            option = int(cd.get('option'))
            choice = int(cd.get('choice', 0))
            if option:
                option_choices[option] = choice
        
        if not self.object.multiple_votes and not len([True for choice in option_choices.values() if choice == Vote.VOTE_YES]) == 1:
            messages.error(self.request, _('In this marketplace you must vote for exactly one item!'))
            raise Redirect()
        
        for option, choice in option_choices.items():
            if not self.object.can_vote_maybe and choice == Vote.VOTE_MAYBE:
                choice = Vote.VOTE_NO
            vote, _created = Vote.objects.get_or_create(option_id=option, voter=self.request.user)
            vote.choice = choice
            vote.save()
            
        
        ret = super(MarketplaceVoteView, self).formset_valid(formset)
        messages.success(self.request, self.message_success )
        return ret
    
    def formset_invalid(self, formset):
        ret = super(MarketplaceVoteView, self).formset_invalid(formset)
        if self.object:
            messages.error(self.request, self.message_error)
        return ret


marketplace_vote_view = MarketplaceVoteView.as_view()


class MarketplaceCompleteView(RequireWriteMixin, FilterGroupMixin, UpdateView):
    """ Completes a marketplace for a selected option, setting the marketplace to completed/archived.
        Notification triggers are handled in the model. """
    form_class = MarketplaceNoFieldForm
    model = Marketplace
    option_id = None
    mode = 'complete' # 'complete' or 'reopen' or 'archive'
    MODES = ('complete', 'reopen', 'archive')
    
    def dispatch(self, request, *args, **kwargs):
        self.option_id = kwargs.pop('option_id', None)
        self.mode = kwargs.pop('mode')
        return super(MarketplaceCompleteView, self).dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        obj = super(MarketplaceCompleteView, self).get_object(queryset)
        return obj
    
    def get(self, request, *args, **kwargs):
        # we don't accept GETs on this, just POSTs
        messages.error(request, _('The complete request can only be sent via POST!'))
        return HttpResponseRedirect(self.get_object().get_absolute_url())
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        marketplace = self.object
        
        # check if valid action requested depending on marketplace state
        if self.mode not in self.MODES:
            messages.error(request, _('Invalid action for this marketplace. The request could not be completed!'))
            return HttpResponseRedirect(self.object.get_absolute_url())
        if (marketplace.state, self.mode) not in \
                ((Marketplace.STATE_VOTING_OPEN, 'complete'), (Marketplace.STATE_CLOSED, 'reopen'), (Marketplace.STATE_CLOSED, 'archive')):
            messages.error(request, _('This action is not permitted for this marketplace at this stage!'))
            return HttpResponseRedirect(marketplace.get_absolute_url())

        # change marketplace state        
        if (marketplace.state, self.mode) == (Marketplace.STATE_VOTING_OPEN, 'complete'):
            # complete the marketplace. a winning option may be selected, but doesn't have to be
            option = get_object_or_None(Option, pk=self.option_id)
            if option:
                marketplace.winning_option = option
            marketplace.closed_date = now()
            marketplace.state = Marketplace.STATE_CLOSED
            marketplace.save()
            messages.success(request, _('The marketplace was closed successfully.'))
        if (marketplace.state, self.mode) == (Marketplace.STATE_CLOSED, 'reopen'):
            # reopen marketplace, set winning option and closed_date to none
            marketplace.winning_option = None
            marketplace.closed_date = None
            marketplace.state = Marketplace.STATE_VOTING_OPEN
            marketplace.save()
            messages.success(request, _('The marketplace was re-opened successfully.'))
        if (marketplace.state, self.mode) == (Marketplace.STATE_CLOSED, 'archive'):
            marketplace.state = Marketplace.STATE_ARCHIVED
            marketplace.save()
            messages.success(request, _('The marketplace was archived successfully.'))
        
        return HttpResponseRedirect(self.object.get_absolute_url())
    
marketplace_complete_view = MarketplaceCompleteView.as_view()



class CommentCreateView(RequireWriteMixin, FilterGroupMixin, CreateView):

    form_class = CommentForm
    group_field = 'marketplace__group'
    model = Comment
    template_name = 'cosinnus_marketplace/marketplace_vote.html'
    
    message_success = _('Your comment was added successfully.')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.marketplace = self.marketplace
        messages.success(self.request, self.message_success)
        return super(CommentCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(CommentCreateView, self).get_context_data(**kwargs)
        # always overwrite object here, because we actually display the marketplace as object, 
        # and not the comment in whose view we are in when form_invalid comes back
        context.update({
            'marketplace': self.marketplace,
            'object': self.marketplace, 
        })
        return context

    def get(self, request, *args, **kwargs):
        self.marketplace = get_object_or_404(Marketplace, group=self.group, slug=self.kwargs.get('marketplace_slug'))
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.marketplace = get_object_or_404(Marketplace, group=self.group, slug=self.kwargs.get('marketplace_slug'))
        self.referer = request.META.get('HTTP_REFERER', self.marketplace.group.get_absolute_url())
        return super(CommentCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_create = CommentCreateView.as_view()


class CommentDeleteView(RequireWriteMixin, FilterGroupMixin, DeleteView):

    group_field = 'marketplace__group'
    model = Comment
    template_name_suffix = '_delete'
    
    message_success = _('Your comment was deleted successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CommentDeleteView, self).get_context_data(**kwargs)
        context.update({'marketplace': self.object.marketplace})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.marketplace.group.get_absolute_url())
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
    group_field = 'marketplace__group'
    model = Comment
    template_name_suffix = '_update'

    def get_context_data(self, **kwargs):
        context = super(CommentUpdateView, self).get_context_data(**kwargs)
        context.update({'marketplace': self.object.marketplace})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.marketplace.group.get_absolute_url())
        return super(CommentUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_update = CommentUpdateView.as_view()

