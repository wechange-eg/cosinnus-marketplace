# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import get_form
from cosinnus.forms.user import UserKwargModelFormMixin

from cosinnus_marketplace.models import Offer, Comment
from cosinnus.forms.attached_object import FormAttachable


class _OfferForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                 FormAttachable):
    
    class Meta:
        model = Offer
        fields = ('type', 'title', 'description', 'phone_number', 'is_active', 'categories')
    
    def clean(self, *args, **kwargs):
        cleaned_data = super(_OfferForm, self).clean(*args, **kwargs)
        return cleaned_data
        
OfferForm = get_form(_OfferForm)


class OfferNoFieldForm(forms.ModelForm):

    class Meta:
        model = Offer
        fields = ()

        
class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ('text',)

