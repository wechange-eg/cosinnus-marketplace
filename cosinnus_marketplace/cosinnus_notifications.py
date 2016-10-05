# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _

""" Cosinnus:Notifications configuration etherpad. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""


""" Signal definitions """
marketplace_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
marketplace_expired = dispatch.Signal(providing_args=["user", "obj", "audience"])
marketplace_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
tagged_marketplace_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
voted_marketplace_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])


""" Notification definitions.
    These will be picked up by cosinnus_notfications automatically, as long as the 
    variable 'notifications' is present in the module '<app_name>/cosinnus_notifications.py'.
    
    Both the mail and subject template will be provided with the following context items:
        :receiver django.auth.User who receives the notification mail
        :sender django.auth.User whose action caused the notification to trigger
        :receiver_name Convenience, full name of the receiver
        :sender_name Convenience, full name of the sender
        :object The object that was created/changed/modified and which the notification is about.
        :object_url The url of the object, if defined by get_absolute_url()
        :object_name The title of the object (only available if it is a BaseTaggableObject)
        :group_name The name of the group the object is housed in (only available if it is a BaseTaggableObject)
        :site_name Current django site's name
        :domain_url The complete base domain needed to prefix URLs. (eg: 'http://sinnwerkstatt.com')
        :notification_settings_url The URL to the cosinnus notification settings page.
        :site Current django site
        :protocol Current portocol, 'http' or 'https'
        
    
""" 
notifications = {
    'marketplace_created': {
        'label': _('A user created a new marketplace'), 
        'mail_template': 'cosinnus_marketplace/notifications/marketplace_created.txt',
        'subject_template': 'cosinnus_marketplace/notifications/marketplace_created_subject.txt',
        'signals': [marketplace_created],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'marketplace',
        'event_text': _('New marketplace by %(sender_name)s'),
        'notification_text': _('%(sender_name)s created a new marketplace'),
        'subject_text': _('A new marketplace: "%(object_name)s" was created in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
    }, 
    'marketplace_expired': {
        'label': _('A marketplace has expired'), 
        'mail_template': 'cosinnus_marketplace/notifications/marketplace_completed.txt',
        'subject_template': 'cosinnus_marketplace/notifications/marketplace_completed_subject.txt',
        'signals': [marketplace_expired],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'marketplace',
        'event_text': _("%(sender_name)s completed the marketplace"),
        'notification_text': _('%(sender_name)s completed a marketplace'),
        'subject_text': _('Marketplace "%(object_name)s" was completed in %(team_name)s.'),
        'data_attributes': {
            'object_name': 'title', 
            'object_url': 'get_absolute_url', 
            'object_text': 'description',
        },
    },  
    'marketplace_comment_posted': {
        'label': _('A user commented on one of your marketplaces'), 
        'mail_template': 'cosinnus_marketplace/notifications/marketplace_comment_posted.html',
        'subject_template': 'cosinnus_marketplace/notifications/marketplace_comment_posted_subject.txt',
        'signals': [marketplace_comment_posted],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'marketplace',
        'event_text': _('%(sender_name)s commented on your marketplace'),
        'notification_text': _('%(sender_name)s commented on one of your marketplaces'),
        'subject_text': _('%(sender_name)s commented on one of your marketplaces'),
        'sub_event_text': _('%(sender_name)s'),
        'data_attributes': {
            'object_name': 'marketplace.title', 
            'object_url': 'get_absolute_url', 
            'image_url': 'marketplace.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'sub_image_url': 'creator.cosinnus_profile.get_avatar_thumbnail_url', # the comment creators
            'sub_object_text': 'text',
        },
    },    
    'tagged_marketplace_comment_posted': {
        'label': _('A user commented on a marketplace you were tagged in'), 
        'mail_template': 'cosinnus_marketplace/notifications/tagged_marketplace_comment_posted.html',
        'subject_template': 'cosinnus_marketplace/notifications/tagged_marketplace_comment_posted_subject.txt',
        'signals': [tagged_marketplace_comment_posted],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'marketplace',
        'event_text': _('%(sender_name)s commented on a marketplace you were tagged in'),
        'subject_text': _('%(sender_name)s commented on a marketplace you were tagged in in %(team_name)s'),
        'sub_event_text': _('%(sender_name)s'),
        'data_attributes': {
            'object_name': 'marketplace.title', 
            'object_url': 'get_absolute_url', 
            'image_url': 'marketplace.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'sub_image_url': 'creator.cosinnus_profile.get_avatar_thumbnail_url', # the comment creators
            'sub_object_text': 'text',
        },
    },  
    'voted_marketplace_comment_posted': {
        'label': _('A user commented on an marketplace you voted in'), 
        'mail_template': 'cosinnus_marketplace/notifications/voted_marketplace_comment_posted.html',
        'subject_template': 'cosinnus_marketplace/notifications/voted_marketplace_comment_posted_subject.txt',
        'signals': [voted_marketplace_comment_posted],
        'default': True,
        
        'is_html': True,
        'snippet_type': 'marketplace',
        'event_text': _('%(sender_name)s commented on a marketplace you voted in'),
        'subject_text': _('%(sender_name)s commented on a marketplace you voted in in %(team_name)s'),
        'sub_event_text': _('%(sender_name)s'),
        'data_attributes': {
            'object_name': 'marketplace.title', 
            'object_url': 'get_absolute_url', 
            'image_url': 'marketplace.creator.cosinnus_profile.get_avatar_thumbnail_url', # note: receiver avatar, not creator's!
            'sub_image_url': 'creator.cosinnus_profile.get_avatar_thumbnail_url', # the comment creators
            'sub_object_text': 'text',
        },
    },  
}
