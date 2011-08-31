#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import oauth2 as oauth

import base64
import urlparse
import webbrowser

import rb
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Peas
from gi.repository import PeasGtk
from gi.repository import RB

class Microblogger(GObject.Object, Peas.Activatable):
    __gtype_name = 'MicroBloggerPlugin'
    object = GObject.property (type = GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)
        
    def do_activate(self):
        pass

    def do_deactivate(self):
        pass


class MicrobloggerConfigurable(GObject.Object, PeasGtk.Configurable):
    __gtype_name__ = 'MicrobloggerConfigurable'
    
    def __init__(self):
        self.settings = Gio.Settings("ir.aliva.microblogger")

    def do_create_configure_widget(self):
        ui_file = rb.find_plugin_file(self, "microblogger-prefs.ui")
        self.builder = Gtk.Builder()
        self.builder.add_from_file(ui_file)

        self.builder.get_object('add_account').connect('clicked', self.on_add_account_clicked)
        self.builder.get_object('del_account').connect('clicked', self.on_del_account_clicked)
        
        self.builder.get_object('identica').connect('toggled', self.on_type_change)
        self.builder.get_object('twitter').connect('toggled', self.on_type_change)
        self.builder.get_object('getglue').connect('toggled', self.on_type_change)

        self.builder.get_object('authorize').connect('clicked', self.on_authorize_clicked)
        self.builder.get_object('exchange').connect('clicked', self.on_exchange_clicked)
        self.builder.get_object('save').connect('clicked', self.on_save_clicked)
        self.builder.get_object('alias').connect('changed', self.on_alias_changed)
        
        self.builder.get_object('cancel').connect('clicked', self.on_cancel_clicked)
        
        model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        tree = self.builder.get_object('treeview')
        tree.set_model(model)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Alias', renderer, text=0)
        tree.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Account', renderer, text=1)
        tree.append_column(column)
        
        self.update_accounts_list()
        
        self.request = Requests(self.builder.get_object('note'))

        notebook = self.builder.get_object('general')
        notebook.set_show_tabs(False)
        return notebook

    def update_accounts_list(self):
        model = self.builder.get_object('treeview').get_model()
        model.clear()
        
        for account in self.settings['accounts']:
            iter = model.append()
            model.set_value(iter, 0, account[0])
            model.set_value(iter, 1, account[1])
            
    
    def on_add_account_clicked(self, button):
        self.builder.get_object('general').set_current_page(1)

    def on_del_account_clicked(self, button):
        tree = self.builder.get_object('treeview')
        selection = tree.get_selection()
        model, iter = selection.get_selected()
        
        if iter == None:
            return
        
        alias = model.get_value(iter, 0)
              
        accounts = []
        
        for account in self.settings['accounts']:
            if account[0] != alias:
                accounts.append(account)
                
        self.settings['accounts'] = accounts
        
        model.remove(iter)
                
        

    def on_cancel_clicked(self, button):
        self.on_type_change(None)
        self.builder.get_object('general').set_current_page(0)

    def on_authorize_clicked(self, button):
        if self.builder.get_object('identica').get_active():
            account = 'identi.ca'
        elif self.builder.get_object('twitter').get_active():
            account = 'twitter'
        else:
            account = 'getglue'
            
        result = self.request.authorize(account)
        
        if result:
            self.builder.get_object('authorize').set_sensitive(False)
            self.builder.get_object('pin').set_sensitive(True)
            self.builder.get_object('exchange').set_sensitive(True)
            
    def on_exchange_clicked(self, button):
        pin_code = self.builder.get_object('pin').get_text()
        
        result = self.request.exchange(pin_code)
        
        if result:
            self.builder.get_object('alias').set_sensitive(True)
            self.builder.get_object('pin').set_sensitive(False)
            self.builder.get_object('exchange').set_sensitive(False)
            
    def on_type_change(self, radio):
        self.builder.get_object('authorize').set_sensitive(True)
        self.builder.get_object('pin').set_text('')
        self.builder.get_object('pin').set_sensitive(False)
        self.builder.get_object('exchange').set_sensitive(False)
        self.builder.get_object('alias').set_text('')
        self.builder.get_object('alias').set_sensitive(False)
        
    def on_alias_changed(self, entry):
        r = entry.get_text_length() > 0 # and unique
        self.builder.get_object('save').set_sensitive(r)
        
    def on_save_clicked(self, button):
        new_account = (self.builder.get_object('alias').get_text(),
                       self.request.account,
                       self.request.access_token,
                       self.request.access_token_secret)
        accounts = self.settings['accounts']
        accounts.append(new_account)
        self.settings['accounts']  = accounts
        self.on_cancel_clicked(None)
        
            
class Requests:
    IDENTICA = {
        'key'   :'NzljNWU2MDFjNmQzMTU0ZDRhMTkwMTRmZmI1MWU2Zjk=',
        'secret':'YzgyYmJiZDg3NWVlYmM2ZWZkODA3OTEwYjg3M2VhMDk=',
        'request_token':'https://identi.ca/api/oauth/request_token?oauth_callback=oob',
        'access_token' :'https://identi.ca/api/oauth/access_token',
        'authorization':'https://identi.ca/api/oauth/authorize',
        'post':'https://identi.ca/api/statuses/update.json',
        }

    TWITTER = {
         'key'   :'NlFmM0JtVmpETk1UOUlYek9oa1E0Zw==',
         'secret':'QVd6SnBldWNvM0dPU0pXRlpGcGJpeXlJOGNlSnRWb1k4TmRZdHQzVVpn',
         'request_token':'https://twitter.com/oauth/request_token',
         'access_token' :'https://twitter.com/oauth/access_token',
         'authorization':'https://twitter.com/oauth/authorize',
         'post': 'https://twitter.com/statuses/update.json',
    }

    GETGLUE = {
        'key'   :'YzAzMGU0NGUxZmJmNzllZWU4Zjg2YjA0ZDAzNGYxZWI=',
        'secret':'NWEyZjc5M2FhMGVlNTBhNWM5MWEwN2VhYzhhYjBmNmI=',
        'request_token':'http://api.getglue.com/oauth/request_token',
        'access_token' :'http://api.getglue.com/oauth/access_token',
        'authorization':'http://getglue.com/oauth/authorize',
        'post': 'http://api.getglue.com/v2/user/addCheckin?',
    }
    
    def __init__(self, note):
        self.note_label = note
        
        self.consumer = None
        self.request_token = None
        self.api = None
        self.account = None

    def authorize(self, account):
        self.account = account
        
        if account == 'twitter':
            self.api = self.TWITTER
        elif account == 'identi.ca':
            self.api = self.IDENTICA
        else:
            self.api = self.GETGLUE
            
        self.request_token = None
        
        key = base64.b64decode(self.api['key'])
        secret = base64.b64decode(self.api['secret'])
        
        self.consumer = oauth.Consumer(key, secret)
        client = oauth.Client(self.consumer)
        
        resp, content = client.request(self.api['request_token'])
        
        if resp['status'] != '200':
            self.note_label.set_text(content)
            return False
        
        self.request_token = dict(urlparse.parse_qsl(content))
        
        url = "%s?oauth_token=%s" % (self.api['authorization'] , self.request_token['oauth_token'])
        self.note_label.set_markup('Opening authorize link in default web browser.')
        webbrowser.open_new(url)
        return True
    
    def exchange(self, pin_code):
        token = oauth.Token(self.request_token['oauth_token'], self.request_token['oauth_token_secret'])
        token.set_verifier(pin_code)
        
        client = oauth.Client(self.consumer, token)
        
        resp, content = client.request(self.api['access_token'], "POST")
        
        if resp['status'] != '200':
            self.note_label.set_text(content)
            return False
        
        access_token = dict(urlparse.parse_qsl(content))
        
        self.access_token = access_token['oauth_token']
        self.access_token_secret = access_token['oauth_token_secret']
        
        self.note_label.set_text('Done! Choose an alias and save')
        return True