# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import join
import datetime

from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import dateformat
from django.utils.encoding import python_2_unicode_compatible
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.timezone import localtime, now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy


from cosinnus_marketplace.conf import settings
from cosinnus_marketplace.managers import MarketplaceManager
from cosinnus.models import BaseTaggableObjectModel
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user,\
    check_object_read_access
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_marketplace import cosinnus_notifications
from django.contrib.auth import get_user_model
from cosinnus.utils.files import _get_avatar_filename
from cosinnus.models.mixins.images import ThumbnailableImageMixin


def get_marketplace_image_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'images', 'marketplaces')


@python_2_unicode_compatible
class Marketplace(BaseTaggableObjectModel):

    SORT_FIELDS_ALIASES = [
        ('title', 'title'),
    ]

    STATE_VOTING_OPEN = 1
    STATE_CLOSED = 2
    STATE_ARCHIVED = 3

    STATE_CHOICES = (
        (STATE_VOTING_OPEN, _('Voting open')),
        (STATE_CLOSED, _('Voting closed')),
        (STATE_ARCHIVED, _('Marketplace archived')),
    )

    state = models.PositiveIntegerField(
        _('State'),
        choices=STATE_CHOICES,
        default=STATE_VOTING_OPEN,
    )
    description = models.TextField(_('Description'), blank=True, null=True)
    
    multiple_votes = models.BooleanField(_('Multiple options votable'), default=True,
         help_text=_('Does this marketplace allow users to vote on multiple options or just decide for one?'))
    can_vote_maybe = models.BooleanField(_('"Maybe" option enabled'), default=True,
         help_text=_('Is the maybe option enabled? Ignored and defaulting to False if ``multiple_votes==False``'))
    anyone_can_vote = models.BooleanField(_('Anyone can vote'), default=False,
         help_text=_('If true, anyone who can see this marketplace can vote on it. If false, only group members can.'))
    
    closed_date = models.DateTimeField(
        _('Start'), default=None, blank=True, null=True, editable=True)
    winning_option = models.ForeignKey(
        'Option',
        verbose_name=_('Winning Option'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='selected_name',
    )

    objects = MarketplaceManager()
    
    __state = None # pre-save purpose

    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['-created', '-closed_date']
        verbose_name = _('Marketplace')
        verbose_name_plural = _('Marketplaces')
        
    def __init__(self, *args, **kwargs):
        super(Marketplace, self).__init__(*args, **kwargs)
        self.__state = self.state

    def __str__(self):
        if self.state == self.STATE_VOTING_OPEN:
            state_verbose = 'open'
        else:
            state_verbose = 'closed'
        readable = _('Marketplace: %(marketplace)s (%(state)s)') % {'marketplace': self.title, 'state': state_verbose}
        return readable
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Marketplace, self).save(*args, **kwargs)

        if created:
            cosinnus_notifications.marketplace_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk))
        if not created and self.__state == Marketplace.STATE_VOTING_OPEN and self.state == Marketplace.STATE_CLOSED:
            # marketplace went from open to closed, so maybe send a notification for marketplace closed?
            # send signal only for voters as audience!
            voter_ids = list(set(self.options.all().values_list('votes__voter__id', flat=True)))
            if self.creator.id in voter_ids:
                voter_ids.remove(self.creator.id)
            voters = get_user_model().objects.filter(id__in=voter_ids)
            cosinnus_notifications.marketplace_completed.send(sender=self, user=self.creator, obj=self, audience=voters)
        self.__state = self.state

    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:marketplace:detail', kwargs=kwargs)

    def set_winning_option(self, winning_option=None):
        if winning_option is None:
            # No option selected or remove selection
            self.winning_option = None
        elif winning_option.marketplace.pk == self.pk:
            # Make sure to not assign a option belonging to another marketplace.
            self.option = winning_option
        else:
            return
        self.save(update_fields=['winning_option'])

    @classmethod
    def get_current(self, group, user):
        """ Returns a queryset of the current marketplaces """
        qs = Marketplace.objects.filter(group=group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return current_marketplace_filter(qs)
    
    def get_voters_pks(self):
        """ Gets the pks of all Users that have voted for this marketplace.
            Returns an empty list if nobody has voted on the marketplace. """
        return self.options.all().values_list('votes__voter__id', flat=True).distinct()


@python_2_unicode_compatible
class Option(ThumbnailableImageMixin, models.Model):
    
    image_attr_name = 'image'
    
    marketplace = models.ForeignKey(
        Marketplace,
        verbose_name=_('Marketplace'),
        on_delete=models.CASCADE,
        related_name='options',
    )
    
    description = models.TextField(_('Description'), blank=False, null=False)
    image = models.ImageField(
        _('Image'),
        upload_to=get_marketplace_image_filename,
        blank=True,
        null=True)

    count = models.PositiveIntegerField(
        pgettext_lazy('the subject', 'Votes'), default=0, editable=False)

    class Meta:
        ordering = ['marketplace', '-count']
        verbose_name = _('Marketplace Option')
        verbose_name_plural = _('Marketplace Options')

    def __str__(self):
        return 'Marketplace Option for Marketplace id: %s' % str(getattr(self, 'marketplace_id', None))

    def get_absolute_url(self):
        return self.marketplace.get_absolute_url()

    def update_vote_count(self, count=None):
        self.count = self.votes.count()
        self.save(update_fields=['count'])

    @cached_property
    def sorted_votes(self):
        return self.votes.order_by('voter__first_name', 'voter__last_name')

@python_2_unicode_compatible
class Vote(models.Model):
    
    VOTE_YES = 2
    VOTE_MAYBE = 1
    VOTE_NO = 0
    
    VOTE_CHOICES = (
        (VOTE_YES, _('Yes')),
        (VOTE_MAYBE, _('Maybe')),
        (VOTE_NO, _('No')),     
    )
    
    option = models.ForeignKey(
        Option,
        verbose_name=_('Option'),
        on_delete=models.CASCADE,
        related_name='votes',
    )

    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Voter'),
        on_delete=models.CASCADE,
        related_name='marketplace_votes',
    )
    
    choice = models.PositiveSmallIntegerField(_('Vote'), blank=False, null=False,
        default=VOTE_NO, choices=VOTE_CHOICES)
    
    class Meta:
        unique_together = ('option', 'voter')
        verbose_name = pgettext_lazy('the subject', 'Vote')
        verbose_name_plural = pgettext_lazy('the subject', 'Votes')

    def __str__(self):
        return 'Vote for marketplace: "%(marketplace)s" with choice: %(choice)s' % {
            'marketplace': self.option.marketplace.title,
            'choice': self.choice,
        }

    def get_absolute_url(self):
        return self.option.marketplace.get_absolute_url()


@python_2_unicode_compatible
class Comment(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.PROTECT, related_name='marketplace_comments')
    created_on = models.DateTimeField(_('Created'), default=now, editable=False)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    marketplace = models.ForeignKey(Marketplace, related_name='comments')
    text = models.TextField(_('Text'))

    class Meta:
        ordering = ['created_on']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return 'Comment on “%(marketplace)s” by %(creator)s' % {
            'marketplace': self.marketplace.title,
            'creator': self.creator.get_full_name(),
        }

    def get_absolute_url(self):
        if self.pk:
            return '%s#comment-%d' % (self.marketplace.get_absolute_url(), self.pk)
        return self.marketplace.get_absolute_url()
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Comment, self).save(*args, **kwargs)
        if created:
            # comment was created, message marketplace creator
            if not self.marketplace.creator == self.creator:
                cosinnus_notifications.marketplace_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[self.marketplace.creator])
            # message votees (except comment creator and marketplace creator) if voting is still open
            votees_except_creator = [pk for pk in self.marketplace.get_voters_pks() if not pk in [self.creator_id, self.marketplace.creator_id]]
            if votees_except_creator and self.marketplace.state == Marketplace.STATE_VOTING_OPEN:
                cosinnus_notifications.voted_marketplace_comment_posted.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=votees_except_creator))
            # message all taggees (except comment creator)
            if self.marketplace.media_tag and self.marketplace.media_tag.persons:
                tagged_users_without_self = self.marketplace.media_tag.persons.exclude(id=self.creator.id)
                if len(tagged_users_without_self) > 0:
                    cosinnus_notifications.tagged_marketplace_comment_posted.send(sender=self, user=self.creator, obj=self, audience=list(tagged_users_without_self))
    
    @property
    def group(self):
        """ Needed by the notifications system """
        return self.marketplace.group

    def grant_extra_read_permissions(self, user):
        """ Comments inherit their visibility from their commented on parent """
        return check_object_read_access(self.marketplace, user)

@receiver(post_delete, sender=Vote)
def post_vote_delete(sender, **kwargs):
    try:
        kwargs['instance'].option.update_vote_count()
    except Option.DoesNotExist:
        pass


@receiver(post_save, sender=Vote)
def post_vote_save(sender, **kwargs):
    kwargs['instance'].option.update_vote_count()


def current_marketplace_filter(queryset):
    """ Filters a queryset of marketplaces for marketplaces are open or closed (but not archived). """
    return queryset.exclude(state=Marketplace.STATE_ARCHIVED).order_by('state', '-closed_date')

def past_marketplace_filter(queryset):
    """ Filters a queryset of marketplaces for marketplaces that began before today, 
    or have an end date before today. """
    return queryset.filter(state=Marketplace.STATE_ARCHIVED).order_by('-closed_date')


import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_marketplace import cosinnus_app
    cosinnus_app.register()
