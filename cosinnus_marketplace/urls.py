# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url


cosinnus_group_patterns = patterns('cosinnus_marketplace.views',
    url(r'^$', 'index_view', name='index'),

    url(r'^list/$', 'offer_list_view', name='list', kwargs={'offer_view': 'all'}),
    url(r'^list/offering/$', 'offer_list_view', name='list_past', kwargs={'offer_view': 'selling'}),
    url(r'^list/looking/$', 'offer_list_view', name='list_past', kwargs={'offer_view': 'buying'}),
    
    url(r'^add/$', 'offer_add_view',  {'form_view': 'add'},  name='add'),
    url(r'^(?P<slug>[^/]+)/$', 'offer_vote_view', {'form_view': 'edit'},  name='detail'),
    url(r'^(?P<slug>[^/]+)/edit/$', 'offer_edit_view', {'form_view': 'edit'}, name='edit'),
    url(r'^(?P<slug>[^/]+)/delete/$', 'offer_delete_view', {'form_view': 'delete'}, name='delete'),

    url(r'^(?P<offer_slug>[^/]+)/comment/$', 'comment_create', name='comment'),
    url(r'^comment/(?P<pk>\d+)/$', 'comment_detail', name='comment-detail'),
    url(r'^comment/(?P<pk>\d+)/delete/$', 'comment_delete', name='comment-delete'),
    url(r'^comment/(?P<pk>\d+)/update/$', 'comment_update', name='comment-update'),
)


cosinnus_root_patterns = patterns(None)
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
