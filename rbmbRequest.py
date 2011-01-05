#! /usr/bin/python2
# -*- coding: utf8 -*-
#
# Rhythmbox-Microblogger - <http://github.com/aliva/Rhythmbox-Microblogger>
# Copyright (C) 2010 Ali Vakilzade <ali.vakilzade in Gmail>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import base64
import hashlib
import hmac
import pynotify
import random
import time
import urlparse
import urllib
import urllib2
import webbrowser
import oauth2 as oauth

IDENTICA={
    'key'   :'NzljNWU2MDFjNmQzMTU0ZDRhMTkwMTRmZmI1MWU2Zjk=',
    'secret':'YzgyYmJiZDg3NWVlYmM2ZWZkODA3OTEwYjg3M2VhMDk=',
    'request_token':'https://identi.ca/api/oauth/request_token',
    'access_token' :'https://identi.ca/api/oauth/access_token',
    'authorization':'https://identi.ca/api/oauth/authorize',
    'post':'https://identi.ca/api/statuses/update.json',
    'call_back':'oob',
    'maxlen':140,
}

TWITTER={
    'key'   :'NlFmM0JtVmpETk1UOUlYek9oa1E0Zw==',
    'secret':'QVd6SnBldWNvM0dPU0pXRlpGcGJpeXlJOGNlSnRWb1k4TmRZdHQzVVpn',
    'request_token':'https://twitter.com/oauth/request_token',
    'access_token' :'https://twitter.com/oauth/access_token',
    'authorization':'https://twitter.com/oauth/authorize',
    'post': 'https://twitter.com/statuses/update.json',
    'call_back':None,
    'maxlen':140,
}

class AddAccountRequest():
    def __init__(self):
        self.api=None
        self.type=None
        
        self.request_token=None
        self.pin=None
        self.alias=None

        
    def __del__(self):
        pass

        
    def request_set_type(self, t):
        self.type=t
        
    def authorize(self, *args):
        set_hint, button, assistant, page=args
        
        button.set_sensitive(False)
           
        if self.type=='identica':
            api=IDENTICA
        elif self.type=='twitter':
            api=TWITTER

        self.api=api            
        
        self.consumer=oauth.Consumer(decode(api['key']), decode(api['secret']))
        client=oauth.Client(self.consumer)
           
        try:     
            resp, content = client.request(api['request_token'], "GET",
                                           call_back=api['call_back'])
        except Exception as err:
            set_hint('ERR: %s' % err)
            button.set_sensitive(True)
            return
        
        if resp['status'] != '200':
            set_hint('ERR: %s\n%Check Your pin code' % (resp['status']))
            button.set_sensitive(True)
            return
        
        self.request_token=dict(urlparse.parse_qsl(content))
        
        
        url = "%s?oauth_token=%s" % (self.api['authorization'] , self.request_token['oauth_token'])
        set_hint('Opening your web browser')
        print url
        webbrowser.open_new(url)
        
        page[4]=True
        assistant.set_page_complete(page[0], page[4])

    def exchange(self, *args):
        set_hint, button, assistant, page=args
        
        button.set_sensitive(False)
        token=oauth.Token(self.request_token['oauth_token'],
                          self.request_token['oauth_token_secret'])
        token.set_verifier(self.pin)
        client = oauth.Client(self.consumer, token)
        
        try:
            resp, content = client.request(self.api['access_token'], "POST")
        except Exception as err:
            set_hint('ERR: %s' % err)
            button.set_sensitive(True)
            return
        
        if resp['status'] != '200':
            set_hint('ERR: %s\n%s' % (resp['status'], content))
            button.set_sensitive(True)
            return
        
        access_token = dict(urlparse.parse_qsl(content))

        self.access_token = access_token['oauth_token']
        self.access_token_secret = access_token['oauth_token_secret']
        
        set_hint('Done!\nnow you can forward to next page')
        
        page[4]=True
        assistant.set_page_complete(page[0], page[4])
    
    def save_account(self, mb):
        mb.settings.add_account(
                type=self.type,
                alias=self.alias,
                token=encode(self.access_token),
                token_secret=encode(self.access_token_secret),
                url='',
                maxlen=self.api['maxlen'])

class Post:
    def __init__(self, mb):
        self.mb=mb
        
    def post(self, *args):
        ui, alias=args
        
        conf=self.mb.get_conf('a', alias)
        
        if conf['type']=='twitter':
            api=TWITTER
        elif conf['type']=='identica':
            api=IDENTICA
        
        get=ui.get_object
        self.get=get
        
        w=get('general')
        w.set_sensitive(False)
        
        w=get('entry')
        text=w.get_text()

        if len(text)==0:
            self._get_out()
            return

            
        params = {
            'oauth_consumer_key' : decode(api['key']),
            'oauth_signature_method' : 'HMAC-SHA1',
            'oauth_timestamp' : str(int(time.time())),
            'oauth_nonce' : str(random.getrandbits(64)),
            'oauth_version' : '1.0',
            'oauth_token' : decode(conf['token_key']),
            }
        
        params['status'] = urllib.quote(text, '')
        params['oauth_signature'] = hmac.new(
            '%s&%s' % (decode(api['secret']), decode(conf['token_secret'])),
            '&'.join([
                'POST',
                urllib.quote(api['post'], ''),
                urllib.quote('&'.join(['%s=%s' % (x, params[x])
                                       for x in sorted(params)]), '')
                ]),
            hashlib.sha1).digest().encode('base64').strip()
        del params['status']

        # post with oauth token
        req = urllib2.Request(api['post'], data = urllib.urlencode(params))
        req.add_data(urllib.urlencode({'status' : text}))
        req.add_header('Authorization', 'OAuth %s' % ', '.join(
            ['%s="%s"' % (x, urllib.quote(params[x], '')) for x in params]))
        try:
            res = urllib2.urlopen(req)
        except Exception as err:
            w=get('type')
            w.set_text('Err: %s' % err)
            return
        finally:
            self._get_out()
        
        notif=pynotify.Notification('Message sent to %s' % conf['alias'],
                                    'rbmb',
                                    self.mb.find_file('icon/%s.png' % conf['type']))
        notif.show()
        
        w=get('general')
        w.hide_all()

    def _get_out(self):
        self.get('general').set_sensitive(True)
        self.mb.sending=False
        

def decode(string):
    return base64.b64decode(string)
    
def encode(string):
    return base64.b64encode(string)
