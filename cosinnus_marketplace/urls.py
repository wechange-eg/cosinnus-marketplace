# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url


cosinnus_group_patterns = patterns('cosinnus_marketplace.views',
    url(r'^$', 'index_view', name='index'),

    url(r'^list/$', 'offer_list_view', name='list', kwargs={'offer_view': 'all'}),
    url(r'^list/mine/$', 'offer_list_view', name='list_mine', kwargs={'offer_view': 'mine'}),
    
    
    url(r'^add/$', 'offer_add_view',  {'form_view': 'add'},  name='add'),
    url(r'^(?P<slug>[^/]+)/$', 'offer_detail_view', {'form_view': 'edit'},  name='detail'),
    url(r'^(?P<slug>[^/]+)/edit/$', 'offer_edit_view', {'form_view': 'edit'}, name='edit'),
    url(r'^(?P<slug>[^/]+)/delete/$', 'offer_delete_view', {'form_view': 'delete'}, name='delete'),
    url(r'^(?P<slug>[^/]+)/activate/$', 'offer_activate_or_deactivate_view', {'mode': 'activate'}, name='activate'),
    url(r'^(?P<slug>[^/]+)/deactivate/$', 'offer_activate_or_deactivate_view', {'mode': 'deactivate'}, name='deactivate'),
    
    
    url(r'^(?P<offer_slug>[^/]+)/comment/$', 'comment_create', name='comment'),
    url(r'^comment/(?P<pk>\d+)/$', 'comment_detail', name='comment-detail'),
    url(r'^comment/(?P<pk>\d+)/delete/$', 'comment_delete', name='comment-delete'),
    url(r'^comment/(?P<pk>\d+)/update/$', 'comment_update', name='comment-update'),
)


cosinnus_root_patterns = patterns(None)
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
