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

__auther__ ='Ali Vakilzade'
__name__   ='rhythmbox-microblogger'
__version__='0.5.2'

import base64
import gconf

KEYS={
    'version'   :'/apps/rhythmbox/plugins/%s/version'    % __name__,
    'template'  :'/apps/rhythmbox/plugins/%s/template'   % __name__,
    'progress'  :'/apps/rhythmbox/plugins/%s/progress'   % __name__,
    'a_list'    :'/apps/rhythmbox/plugins/%s/accounts'   % __name__,
    'a'         :'/apps/rhythmbox/plugins/%s/account/'   % __name__,
}

DEFAULT={
    'template'  :'[Rhythmbox] {title} by #{artist} from {album}',
    'a_list'    :[],
    'progress'  :True,
}

class Settings:
    def __init__(self):
        #self._remove_conf(None)
        self.conf=self._read_conf()
        if self.conf is None:
            self.conf=self._create_conf()
        
    def __del__(self):
        del self.conf
        
    def _read_conf(self):
        conf={}

        client=gconf.client_get_default()
        if client.get_string(KEYS['version'])==None:
            return None
        
        ver=client.get_string(KEYS['version'])

        if ver=='0.5.0':
            client.set_string(KEYS['template'], DEFAULT['template'])

        if ver in ('0.5.0', '0.5.1'):
            client.set_bool(KEYS['progress'], DEFAULT['progress'])

        ver=ver.split('.')
        if int(ver[1])<5:
            self._remove_conf(None)
            return None

        
        client.set_string(KEYS['version'], __version__)
        
        conf['template']  =client.get_string(KEYS['template'])
        conf['progress']  =client.get_bool  (KEYS['progress'])
        conf['a_list']    =client.get_list  (KEYS['a_list'], gconf.VALUE_STRING)
        
        conf['a']={}
        
        for alias in conf['a_list']:
            conf['a'][alias]={}
            
            ad=KEYS['a']+alias+'/'
        
            conf['a'][alias]['type']=client.get_string(ad + 'type')
            conf['a'][alias]['alias']=client.get_string(ad + 'alias')
            conf['a'][alias]['token_key']=client.get_string(ad + 'token_key')
            conf['a'][alias]['token_secret']=client.get_string(ad + 'token_secret')
            conf['a'][alias]['url']=client.get_string(ad + 'url')
            conf['a'][alias]['oauth']=client.get_bool(ad + 'oauth')
            conf['a'][alias]['maxlen']=client.get_int(ad + 'maxlen')
        
        return conf
    
    def update_conf(self, text, val):
        client=gconf.client_get_default()

        if text=='progress':
            client.set_bool(KEYS['progress'], val)
            self.conf['progress']=val
        elif text=='template':
            if len(val)==0:
                client.set_string(KEYS['template'], DEFAULT['template'])
            else:
                client.set_string(KEYS['template'], val)
            self.conf['template']  =client.get_string(KEYS['template'])

    def _create_conf(self):
        client=gconf.client_get_default()
        
        client.set_string(KEYS['version'], __version__)
        client.set_string(KEYS['template'], DEFAULT['template'])
        client.set_bool  (KEYS['progress'], DEFAULT['progress'])
        client.set_list  (KEYS['a_list'], gconf.VALUE_STRING, DEFAULT['a_list'])

        return DEFAULT
    
    def remove_account(self, alias):
        self.conf['a_list'].remove(alias)
        del self.conf['a'][alias]

        self._remove_conf(alias)

        client=gconf.client_get_default()
        client.set_list(KEYS['a_list'], gconf.VALUE_STRING, self.conf['a_list'])
            
    def _remove_conf(self, key):
        client=gconf.client_get_default()
        if key==None:
            add='/apps/rhythmbox/plugins/%s' % __name__
        else:
            add=KEYS['a'] + str(key)
        client.recursive_unset(add, gconf.UNSET_INCLUDING_SCHEMA_NAMES)
        client.remove_dir(add)

        if key==None:
            for i in range(100):
                client.remove_dir(add)
                
    def add_account(self,
                    type,
                    alias,
                    token,
                    token_secret,
                    url,
                    oauth,
                    maxlen):
        
        self.conf['a_list'].append(alias)
        
        ad=KEYS['a']+alias+'/'
        
        client=gconf.client_get_default()
        client.set_string(ad + 'type'        , type)
        client.set_string(ad + 'alias'       , alias)
        client.set_string(ad + 'token_key'   , token)
        client.set_string(ad + 'token_secret', token_secret)
        client.set_string(ad + 'url'         , url)
        client.set_bool  (ad + 'oauth'       , oauth)
        client.set_int   (ad + 'maxlen'      , maxlen)
        client.set_list  (KEYS['a_list'], gconf.VALUE_STRING, self.conf['a_list'])
        
        self.__init__()
