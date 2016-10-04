# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import BaseTaggableObjectIndex

from cosinnus_poll.models import Poll


class PollIndex(BaseTaggableObjectIndex, indexes.Indexable):
    description = indexes.CharField(model_attr='description', null=True)

    def get_model(self):
        return Poll

