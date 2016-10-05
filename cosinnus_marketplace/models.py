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
from cosinnus.models import BaseTaggableObjectModel
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user,\
    check_object_read_access
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_marketplace import cosinnus_notifications
from django.contrib.auth import get_user_model
from cosinnus.utils.files import _get_avatar_filename
from cosinnus.models.mixins.images import ThumbnailableImageMixin

from phonenumber_field.modelfields import PhoneNumberField
from django.core.exceptions import ImproperlyConfigured
from cosinnus.utils.lanugages import MultiLanguageFieldMagicMixin
from cosinnus.models.tagged import CosinnusBaseCategory
from cosinnus_marketplace.managers import OfferManager


def get_marketplace_image_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'images', 'marketplaces')


class OfferCategory(MultiLanguageFieldMagicMixin, CosinnusBaseCategory):
    
    class Meta:
        ordering = ['order_key']
    
    order_key = models.CharField(_('Order Key'), max_length=30, blank=True, 
         help_text='Set this to the same key for multiple categories to group them together on the form.')
    

@python_2_unicode_compatible
class Offer(BaseTaggableObjectModel):

    SORT_FIELDS_ALIASES = [
        ('title', 'title'),
    ]

    TYPE_BUYING = 1
    TYPE_SELLING = 2

    TYPE_CHOICES = (
        (TYPE_BUYING, _('Buying')),
        (TYPE_SELLING, _('Selling')),
    )

    type = models.PositiveIntegerField(
        _('Type'),
        choices=TYPE_CHOICES,
        default=TYPE_BUYING,
    )
    
    is_active = models.BooleanField(_('Offer currently active?'), default=False)
    
    description = models.TextField(_('Description'), blank=True, null=True)
    phone_number = PhoneNumberField(blank=True)
    
    categories = models.ManyToManyField(OfferCategory, verbose_name=_('Offer Category'), 
        related_name='offers', blank=True, null=True)
    

    objects = OfferManager()
    

    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['-created']
        verbose_name = _('Offer')
        verbose_name_plural = _('Offers')
        
    def __init__(self, *args, **kwargs):
        super(Offer, self).__init__(*args, **kwargs)

    def __str__(self):
        if self.type == self.TYPE_BUYING:
            type_verbose = 'buying'
        else:
            type_verbose = 'selling'
        readable = _('Offer: %(offer)s (%(type)s)') % {'offer': self.title, 'type': type_verbose}
        return readable
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Offer, self).save(*args, **kwargs)

        if created:
            cosinnus_notifications.marketplace_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk))
        
        
        # TODO: offer has expired: implement
        """
        if not created and self.__state == Offer.STATE_VOTING_OPEN and self.state == Offer.STATE_CLOSED:
            # offer went from open to closed, so maybe send a notification for offer closed?
            # send signal only for voters as audience!
            voter_ids = list(set(self.options.all().values_list('votes__voter__id', flat=True)))
            if self.creator.id in voter_ids:
                voter_ids.remove(self.creator.id)
            voters = get_user_model().objects.filter(id__in=voter_ids)
            cosinnus_notifications.marketplace_expired.send(sender=self, user=self.creator, obj=self, audience=voters)
        """

    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:marketplace:detail', kwargs=kwargs)

    @classmethod
    def get_current(self, group, user):
        """ Returns a queryset of the current marketplaces """
        qs = Offer.objects.filter(group=group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return current_offer_filter(qs)
    
    @property
    def has_expired(self):
        return self.is_active == False and self.created < now() - datetime.timedelta(days=settings.COSINNUS_MARKETPLACE_OFFER_ACTIVITY_DURATION_DAYS)
    


@python_2_unicode_compatible
class Comment(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.PROTECT, related_name='marketplace_comments')
    created_on = models.DateTimeField(_('Created'), default=now, editable=False)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    offer = models.ForeignKey(Offer, related_name='comments')
    text = models.TextField(_('Text'))

    class Meta:
        ordering = ['created_on']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return 'Comment on “%(offer)s” by %(creator)s' % {
            'offer': self.offer.title,
            'creator': self.creator.get_full_name(),
        }

    def get_absolute_url(self):
        if self.pk:
            return '%s#comment-%d' % (self.offer.get_absolute_url(), self.pk)
        return self.offer.get_absolute_url()
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Comment, self).save(*args, **kwargs)
        if created:
            # comment was created, message offer creator
            if not self.offer.creator == self.creator:
                cosinnus_notifications.marketplace_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[self.offer.creator])
            # message all taggees (except comment creator)
            if self.offer.media_tag and self.offer.media_tag.persons:
                tagged_users_without_self = self.offer.media_tag.persons.exclude(id=self.creator.id)
                if len(tagged_users_without_self) > 0:
                    cosinnus_notifications.tagged_marketplace_comment_posted.send(sender=self, user=self.creator, obj=self, audience=list(tagged_users_without_self))
    
    @property
    def group(self):
        """ Needed by the notifications system """
        return self.offer.group

    def grant_extra_read_permissions(self, user):
        """ Comments inherit their visibility from their commented on parent """
        return check_object_read_access(self.offer, user)


def current_offer_filter(queryset):
    """ Filters a queryset of marketplaces for marketplaces are open or closed (but not archived). """
    return queryset.exclude(is_active=True).order_by('-created')


import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_marketplace import cosinnus_app
    cosinnus_app.register()
