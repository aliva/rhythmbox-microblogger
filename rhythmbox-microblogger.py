#-*- coding: utf8 -*-
#
# Copyright (C) 2010 Ali Vakilzade <ali.vakilzade@gmail.com>
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

__version__='0.3.1'
__auther__ ='Ali Vakilzade'
__name__   ='rhythmbox-microblogger'

import rb
import rhythmdb

import base64
import gtk
import gconf
import hashlib
import hmac
import random
import threading
import time
import urllib
import urllib2
import urlparse
import webbrowser

import oauth2 as oauth

# --------------------------------------------------------------------------------

DEFAULT_TEMPLATE='[Rhythmbox] {title} by {artist} from {album}'

UI_TOOLBAR='''
<ui>
    <toolbar name='ToolBar'>
        <placeholder name='PluginPlaceholder'>
            <toolitem name='ToolBarMicroBlogger-%d' action='SendNotice-%d'/>
        </placeholder>
    </toolbar>
</ui>
'''

ACCOUNT_TYPE=(
    'identica',
    'twitter',
    'statusnet',
)

IDENTICA_CONSUMER={
    'key'   :'NzljNWU2MDFjNmQzMTU0ZDRhMTkwMTRmZmI1MWU2Zjk=',
    'secret':'YzgyYmJiZDg3NWVlYmM2ZWZkODA3OTEwYjg3M2VhMDk=',
}

TWITTER_CONSUMER={
    'key'   :'NlFmM0JtVmpETk1UOUlYek9oa1E0Zw==',
    'secret':'QVd6SnBldWNvM0dPU0pXRlpGcGJpeXlJOGNlSnRWb1k4TmRZdHQzVVpn',
}

IDENTICA_URL={
    'request_token':'http://identi.ca/api/oauth/request_token',
    'access_token' :'http://identi.ca/api/oauth/access_token',
    'authorize'    :'http://identi.ca/api/oauth/authorize',
    'post'         :'http://identi.ca/api/statuses/update.json'
}

TWITTER_URL={
    'request_token':'http://twitter.com/oauth/request_token',
    'access_token' :'http://twitter.com/oauth/access_token',
    'authorize'    :'http://twitter.com/oauth/authorize',
    'post'         :'http://twitter.com/statuses/update.json'
}

# --------------------------------------------------------------------------------

class microblogger(rb.Plugin):
    def __init__(self):
        rb.Plugin.__init__(self)

    def activate(self, shell):
        gtk.gdk.threads_init()

        self.SBox={}
        self.RequestToken=None

        self.shell=shell
        self.uim = shell.get_ui_manager()
        self.pl=shell.get_property('shell-player')
        self.db=shell.get_property('db')

        self.RegisterIcons()

        # class
        self.ConfigClass=Settings()
        self.ConfigDialog=ConfigureDialog(self)

        self.AddUI()
        self.AttachSendBox()

    def deactivate(self, shell):
        self.RemoveUI()

    def create_configure_dialog(self, dialog=None):
        return self.ConfigDialog.MainDialog()

    def OpenAuthorizeLink(self, *args):
        authorize, token, key, secret, button=args

        key   =base64.b64decode(key)
        secret=base64.b64decode(secret)

        consumer = oauth.Consumer(key, secret)
        client = oauth.Client(consumer)

        resp, content = client.request(token, "GET")
        if resp['status'] != '200':
            print ("Invalid response %s." % resp['status'])
            button.set_sensitive(True)
            return
        self.RequestToken = dict(urlparse.parse_qsl(content))

        url = "%s?oauth_token=%s" % (authorize, self.RequestToken['oauth_token'])

        webbrowser.open_new(url)

        button.set_sensitive(True)

    def RegisterIcons(self):
        IconFactory=gtk.IconFactory()
        IconFactory.add_default()

        for account in ACCOUNT_TYPE:
            gtk.stock_add([('rb-microblogger-%s' % account, account, 0, 0, '')])
            IconSource=gtk.IconSource()
            IconSet=gtk.IconSet()
    
            IconSource.set_filename(self.find_file('icon/%s.png' % account))
            IconSet.add_source(IconSource)
            IconFactory.add('rb-microblogger-%s' % account, IconSet)

    def AddUI(self):
        self.ui_id=[]
        self.action_groups=[]

        conf=self.ConfigClass.conf

        for key in conf['accountsid']:
            action=gtk.Action('SendNotice-%d' % key,
                              _('Send'),
                              _('%s') % conf['accountslist'][key]['user'],
                              'rb-microblogger-%s' % conf['accountslist'][key]['type'])
            activate_id = action.connect('activate', self.SendClicked, key)
            action_group = gtk.ActionGroup('MicroBloggerPluginActions-%d'% key)
            action_group.add_action(action)
            self.uim.insert_action_group(action_group, 0)

            self.ui_id.append(self.uim.add_ui_from_string(UI_TOOLBAR % (key, key)))
            self.action_groups.append(action_group)

        self.uim.ensure_update()

    def RemoveUI(self):
        for key in self.ui_id:
    		self.uim.remove_ui (key)

        for key in self.action_groups:
    		self.uim.remove_action_group (key)

        del self.ui_id
        del self.action_groups

        self.uim.ensure_update()

    def AttachSendBox(self):
        # box
        box=gtk.HBox()
        self.shell.add_widget (box, rb.SHELL_UI_LOCATION_MAIN_TOP)
        self.SBox['box']=box

        # entry
        w=gtk.Entry()
        w.connect('changed' , self.SBoxEntryChanged)
        w.connect('activate', self.Send)
        box.pack_start(w)
        self.SBox['entry']=w

        # string len label
        w=gtk.Label(' 140 ')
        box.pack_start(w, False, False)
        self.SBox['label']=w

        # send button
        w=gtk.Button('_Send')
        w.connect('clicked', self.Send)
        box.pack_start(w, False, False)
        self.SBox['send']=w

        # cancel button
        w=gtk.Button(stock=gtk.STOCK_CANCEL)
        w.connect('clicked', self.SBoxCancel)
        box.pack_start(w, False, False)
        self.SBox['cancel']=w

        # hide box
        box.hide_all()

    def SendClicked(self, button, key):
        self.SBox['send'].set_data('key', None)
        self.SBox['box'].hide_all()
        text=self.GenerateString()

        if text=='':
            return

        account=self.ConfigClass.conf['accountslist'][key]

        self.SBox['entry'].set_text(text)
        self.SBox['send'].set_label('_Send as %s in %s' %(account['user'], account['type']))
        self.SBox['send'].set_data('key', key)

        if self.ConfigClass.conf['editbefore'] or self.SBox['entry'].get_text_length()>140:
            self.SBox['box'].show_all()
        else:
            self.send(None)

    def Send(self, button):
        key=self.SBox['send'].get_data('key')
        text=self.SBox['entry'].get_text()

        if len(text)==0:
            return

        self.SBox['box'].set_sensitive(False)

        if self.ConfigClass.conf['accountslist'][key]['oauth']:
            func=self.SendThreadOauth
        else:
            func=self.SendThreadNOOauth

        threading.Thread(target=func, args=(text, key)).start()

    # TODO
    def SendThreadOauth(self, *args):
        text, key=args

        account=self.ConfigClass.conf['accountslist'][key]

        if account['type'] in ('identica', 'twitter'):
            if account['type']=='identica':
                consumer=IDENTICA_CONSUMER
                url=IDENTICA_URL
            else:
                consumer=TWITTER_CONSUMER
                url=TWITTER_URL
        else:
            print 'WHAT, WHAT, WHAT?'
            return
    
        dec=base64.b64decode
        token = oauth.Token(key=dec(account['token_key']), secret=dec(account['token_secret']))
        consumer = oauth.Consumer(key=dec(consumer['key']), secret=dec(consumer['secret']))

        params = {
			'oauth_signature_method' : 'HMAC-SHA1',
            'oauth_version' : '1.0',
            'oauth_nonce': oauth.generate_nonce(),
            'oauth_timestamp': str(int(time.time())),
            'user':account['user'],
            'oauth_token':token.key,
            'oauth_consumer_key':consumer.key,
			'oauth_signature_method' : 'HMAC-SHA1',
        }

        #req = oauth.Request(method="POST", url=url, parameters=params)
        #signature_method = oauth.SignatureMethod_HMAC_SHA1()
        #req.sign_request(signature_method, consumer, token)

        params['status'] = urllib.quote(text, '')
        params['oauth_signature'] = hmac.new(
            '%s&%s' % (consumer.secret, token.secret),
            '&'.join([
                'POST',
                urllib.quote(url['post'], ''),
                urllib.quote('&'.join(['%s=%s' % (x, params[x])
                                        for x in sorted(params)]), '')
            ]),
            hashlib.sha1).digest().encode('base64').strip()

        del params['status']

        # post with oauth token
        req = urllib2.Request(url['post'], data = urllib.urlencode(params))
        req.add_data(urllib.urlencode({'status' : text}))
        req.add_header('Authorization', 'OAuth %s' % ', '.join(
            ['%s="%s"' % (x, urllib.quote(params[x], '')) for x in params]))
        res = urllib2.urlopen(req)

        try:
            url = urllib2.urlopen(req)
        except Exception as err:
            self.SBox['box'].show_all()
            self.SBox['box'].set_sensitive(True)
            self.SBox['send'].set_label('S_end %s' % err)
        else:
            url.close()
            self.SBox['box'].hide_all()
        finally:
            self.SBox['box'].set_sensitive(True)

        self.SBox['box'].set_sensitive(True)

    def SendThreadNOOauth(self, (text, key)):
        print 'What the hell?'

    def SBoxEntryChanged(self, entry):
        length=entry.get_text_length()
        self.SBox['label'].set_text(' %d ' % (140-length))
        self.SBox['send'].set_sensitive(0<length<=140)

    def SBoxCancel(self, button):
        self.SBox['box'].hide_all()

    def GenerateString(self):
        if self.pl.get_playing():
            entry=self.pl.get_playing_entry()
            db=self.db

            title =db.entry_get(entry, rhythmdb.PROP_TITLE)
            genre =db.entry_get(entry, rhythmdb.PROP_GENRE)
            artist=db.entry_get(entry, rhythmdb.PROP_ARTIST)
            album =db.entry_get(entry, rhythmdb.PROP_ALBUM)
            rate  =db.entry_get(entry, rhythmdb.PROP_RATING)
            year  =db.entry_get(entry, rhythmdb.PROP_YEAR)
            pcount=db.entry_get(entry, rhythmdb.PROP_PLAY_COUNT)

            try:
                return self.ConfigClass.conf['template'].format(title=title, genre=genre, artist=artist, album=album,
                                                rate=rate, year=year, pcount=pcount)
            except Exception as err:
                print (err)
                return DEFAULT_TEMPLATE.format(title=title, album=album, artist=artist)
        return ''

# --------------------------------------------------------------------------------

class ConfigureDialog:
    def __init__(self, micro):
        self.MicroBlogger=micro

    def MainDialog(self):
        dialog=gtk.Dialog('MicroBlogger prefrences', None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        dialog.connect('response', self.MainDialogResponse)

        self.MainW={}

        # style
        frame=gtk.Frame('Style')
        box=gtk.VBox()
        entry=gtk.Entry()
        label=gtk.Label('Label')

        dialog.vbox.pack_start(frame, False, False)
        frame.add(box)
        box.pack_start(entry)
        box.pack_start(label)

        self.MainW['StyleFrame']=frame
        self.MainW['StyleBox']=box
        self.MainW['StyleEntry']=entry
        self.MainW['StyleLabel']=label

        # edit before
        check=gtk.CheckButton('edit notice before sending')
        dialog.vbox.pack_start(check, False, False)
        self.MainW['EditBefore']=check

        # auto send
        check=gtk.CheckButton('automatically send notice when music changes (You can not edit this message')
        dialog.vbox.pack_start(check, False, False)
        self.MainW['AutoSend']=check

        # add
        button=gtk.Button('_Add account')
        button.connect('clicked', self.AddClicked, dialog)
        dialog.vbox.pack_start(button, False, False)
        self.MainW['Add']=button
        
        # remove
        button=gtk.Button('_Remove account')
        button.connect('clicked', self.RemoveClicked, dialog)
        dialog.vbox.pack_start(button, False, False)
        self.MainW['Remove']=button

        dialog.show_all()
        return dialog

    def MainDialogResponse(self, dialog, response):
        self.MicroBlogger.RemoveUI()
        self.MicroBlogger.AddUI()

        dialog.destroy()

    def AddClicked(self, button, MainDialogWindow):
        dialog=gtk.Dialog('Add Account', MainDialogWindow, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        self.AddW={}

        top=0

        table=gtk.Table()
        dialog.vbox.pack_start(table)

        self.AddW['table']=table

        # type
        label=gtk.Label('Account Type')
        combo=gtk.combo_box_new_text()
        for item in ACCOUNT_TYPE:
            combo.append_text(item)
        combo.set_active(0)

        table.attach(label, 0, 1, top, top+1)
        table.attach(combo, 1, 2, top, top+1)
        self.AddW['TypeLabel']=label
        self.AddW['TypeCombo']=combo

        top+=1
        # Oauth
        button=gtk.CheckButton('Use OAUTH Connection. (recommended)')
        button.set_active(True)
        button.set_sensitive(False)

        table.attach(button, 1, 2, top, top+1)
        self.AddW['Oauth']=button

        top+=1
        # User
        label=gtk.Label('User name')
        entry=gtk.Entry()

        table.attach(label, 0, 1, top, top+1)
        table.attach(entry, 1, 2, top, top+1)
        self.AddW['UserLabel']=label
        self.AddW['UserEntry']=entry

        top+=1
        # authorize 
        label=gtk.Label('Remember to authorize for this account\nrequired step')
        button=gtk.Button('Authorize account')
        
        button.connect('clicked', self.OpenAuthorizeLink)

        table.attach(label , 0, 1, top, top+1)
        table.attach(button, 1, 2,top, top+1)
        self.AddW['AouthLabel']=label
        self.AddW['AouthButton']=button

        dialog.show_all()
        response=dialog.run()

        if self.AddW['Oauth'].get_active():
            text=self.AddW['TypeCombo'].get_active_text()
            if text=='identica' or text=='twitter':
                if self.MicroBlogger.RequestToken is not None:
                    self.MicroBlogger.ConfigClass.AddAccount(atype=text,
                                                             user =self.AddW['UserEntry'].get_text(),
                                                             token_key=self.MicroBlogger.RequestToken['oauth_token'],
                                                             token_secret=self.MicroBlogger.RequestToken['oauth_token_secret'],
                                                             oauth=True,
                                                             )

        dialog.destroy()

    def RemoveClicked(self, button, MainDialogWindow):
        dialog=gtk.Dialog('Remove Account', MainDialogWindow, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        conf=self.MicroBlogger.ConfigClass.conf

        table=gtk.Table()
        top=0

        dialog.vbox.pack_start(table)

        for key in conf['accountsid']:
            user =conf['accountslist'][key]['user']
            atype=conf['accountslist'][key]['type']
            oauth=str(conf['accountslist'][key]['oauth'])

            w=gtk.Label('%d %s in %s oauth=%s ' % (key, user, atype, oauth))
            b=gtk.Button(stock=gtk.STOCK_REMOVE)
            b.connect('clicked', self.RemoveAccount, key)

            table.attach(w, 0, 1, top, top+1)
            table.attach(b, 1, 2, top, top+1)

            top+=1

        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def RemoveAccount(self, button, key):
        button.set_sensitive(False)

        self.MicroBlogger.ConfigClass.RemoveAccount(key)

    def OpenAuthorizeLink(self, button):
        self.MicroBlogger.RequestToken=None
        button.set_sensitive(False)
        text=self.AddW['TypeCombo'].get_active_text()

        if text=='identica':
            key=IDENTICA_CONSUMER['key']
            sec=IDENTICA_CONSUMER['secret']
            ath=IDENTICA_URL['authorize']
            tok=IDENTICA_URL['request_token']
        elif text=='twitter':
            key=TWITTER_CONSUMER['key']
            sec=TWITTER_CONSUMER['secret']
            ath=TWITTER_URL['authorize']
            tok=TWITTER_URL['request_token']
        else:
            return

        threading.Thread(target=self.MicroBlogger.OpenAuthorizeLink, args=(ath, tok, key, sec, button)).start()

# --------------------------------------------------------------------------------

class Settings:
    KEYS={
        'editbefore':'/apps/rhythmbox/plugins/%s/editbefore' % __name__,
        'accounts'  :'/apps/rhythmbox/plugins/%s/accounts/'  % __name__,
        'accountsid':'/apps/rhythmbox/plugins/%s/accountsid' % __name__,
        'version'   :'/apps/rhythmbox/plugins/%s/version'    % __name__,
        'template'  :'/apps/rhythmbox/plugins/%s/template'   % __name__,
    }
    DEFAULT={
        'accountslist':{},
        'editbefore':True,
        'version':__version__,
        'accounts':None,
        'accountsid':'',
        'template':DEFAULT_TEMPLATE,
    }

    def __init__(self):
        conf=self.ReadConf()
        if conf==None:
            conf=self.CreateConf()

        self.conf=conf

    def ReadConf(self):
        conf={}

        client=gconf.client_get_default()
        if client.get_string(self.KEYS['version'])==None:
            return None

        conf['editbefore']=client.get_bool  (self.KEYS['editbefore'])
        conf['version']=client.get_string(self.KEYS['version'])
        conf['accountsid']=client.get_string(self.KEYS['accountsid'])
        conf['template']=client.get_string(self.KEYS['template'])

        conf['accountsid']=self.Str2Conf(conf['accountsid'])

        conf['accountslist']={}
        for key in conf['accountsid']:
            conf['accountslist'][key]={}

            ad=self.KEYS['accounts'] + str(key) + '/'

            conf['accountslist'][key]['oauth']       = client.get_bool  (ad + 'oauth')        or True
            conf['accountslist'][key]['type']        = client.get_string(ad + 'type')         or ''
            conf['accountslist'][key]['user']        = client.get_string(ad + 'user')         or ''
            conf['accountslist'][key]['token_key']   = client.get_string(ad + 'token_key')    or ''
            conf['accountslist'][key]['token_secret']= client.get_string(ad + 'token_secret') or ''

        return conf

    # if key==-1 it will remove all configs
    # else if will remove one account
    def RemoveConf(self, key=-1):
        client=gconf.client_get_default()
        if key==-1:
            add='/apps/rhythmbox/plugins/%s' % __name__
        else:
            add=self.KEYS['accounts'] + str(key)
        client.recursive_unset(add, gconf.UNSET_INCLUDING_SCHEMA_NAMES)

        client.remove_dir(add)

        if key==-1:
            for i in range(100):
                client.remove_dir(add)

    def CreateConf(self):
        client=gconf.client_get_default()
        client.set_bool  (self.KEYS['editbefore'], self.DEFAULT['editbefore'])
        client.set_string(self.KEYS['version']   , self.DEFAULT['version'])
        client.set_string(self.KEYS['accountsid'], self.DEFAULT['accountsid'])
        client.set_string(self.KEYS['template']  , self.DEFAULT['template'])

        return self.DEFAULT

    def AddAccount(self,
                   atype='',
                   oauth=True,
                   user='',
                   token_key='',
                   token_secret=''
                   ):

        if self.conf['accountsid']==[]:
            ID=1
        elif len(self.conf['accountsid'])==1:
            ID=self.conf['accountsid'][0]+1
        else:
            ID=max(self.conf['accountsid'])+1

        self.conf['accountsid'].append(ID)

        ad=self.KEYS['accounts'] + str(ID) + '/'

        client=gconf.client_get_default()

        client.set_string(ad + 'type'        , atype)
        client.set_bool  (ad + 'oauth'       , oauth)
        client.set_string(ad + 'user'        , user)
        client.set_string(ad + 'token_key'   , base64.b64encode(token_key))
        client.set_string(ad + 'token_secret', base64.b64encode(token_secret))

        client.set_string(self.KEYS['accountsid'], self.Conf2Str())

        self.__init__()

    def RemoveAccount(self, key):
        self.conf['accountsid'].remove(key)
        del self.conf['accountslist'][key]

        if len(self.conf['accountsid'])==0:
            self.conf['accountsid']=[]

        self.RemoveConf(key)

        client=gconf.client_get_default()
        client.set_string(self.KEYS['accountsid'], self.Conf2Str())

    def Conf2Str(self):
        tmp=str(self.conf['accountsid'])
        return tmp[1:-1]

    def Str2Conf(self, conflist):
        if conflist=='':
            return []
        else:
            conflist=conflist.split(',')
            conflist=[int(i) for i in conflist]
            return conflist
