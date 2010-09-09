# -*- coding: utf8 -*-
#
# Rhythmbox-Microblogger - <http://github.com/aliva/Rhythmbox-Microblogger>
# Copyright (C) 2010 Ali Vakilzade <ali.vakilzade [__at__] gmail [__dot__] com>
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

__version__='0.4'
__auther__ ='Ali Vakilzade'
__name__   ='rhythmbox-microblogger'

import rb
import rhythmdb

import base64
import gconf
import gtk
import threading
import webbrowser

import tweepy

# --------------------------------------------------------------------------------

DEFAULT_TEMPLATE='[Rhythmbox] {title} by {artist} from {album}'

TEMPLATE_GUIDE='''Valid Meta data:
{title} {genre} {artist} {album} {rate} {year} {pcount}
Use {{ for { and }} for }
Empty for default'''

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
    'host':'identi.ca/api',
    'send':'identi.ca',
    'api':'/api',
}

TWITTER_URL={
    'host':'api.twitter.com',
    'send':'api.twitter.com',
    'api':'/1',
}
# --------------------------------------------------------------------------------

class microblogger(rb.Plugin):
    def __init__(self):
        rb.Plugin.__init__(self)

    def activate(self, shell):
        gtk.gdk.threads_init()

        self.shell=shell
        self.uim = shell.get_ui_manager()
        self.pl=shell.get_property('shell-player')
        self.db=shell.get_property('db')

        self.RequestToken=None
        self.AccessToken=None
        self.SBox={}

        # class
        self.SettingsClass=Settings()
        self.DialogClass=ConfigureDialog(self)

        self.RegisterIcons()

        self.AddUI()
        self.AttachSendBox()

    def deactivate(self, shell):
        self.RemoveUI()

    def create_configure_dialog(self, dialog=None):
        return self.DialogClass.MainDialog()

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

    def SendClicked(self, button, key):
        self.SBox['send'].set_data('key', None)
        self.SBox['box'].hide_all()
        text=self.GenerateString()

        if text=='':
            return

        account=self.SettingsClass.conf['accountslist'][key]

        self.SBox['entry'].set_text(text)
        self.SBox['send'].set_label('_Send as %s in %s' %(account['user'], account['type']))
        self.SBox['send'].set_data('key', key)

        if self.SettingsClass.conf['editbefore'] or self.SBox['entry'].get_text_length()>140:
            self.SBox['box'].show_all()
        else:
            self.send(None)

    def Send(self, button):
        key=self.SBox['send'].get_data('key')
        text=self.SBox['entry'].get_text()

        if len(text)==0:
            return

        self.SBox['box'].set_sensitive(False)

        threading.Thread(target=self.SendThread, args=(text, key)).start()

    def SendThread(self, *args):
        text, key=args
        account=self.SettingsClass.conf['accountslist'][key]

        if account['type']=='identica':
            url=IDENTICA_URL
            con=IDENTICA_CONSUMER
        else:
            url=TWITTER_URL
            con=TWITTER_CONSUMER

        consumer_key   =base64.b64decode(con['key'])
        consumer_secret=base64.b64decode(con['secret'])

        token_key   =base64.b64decode(account['token_key'])
        token_secret=base64.b64decode(account['token_secret'])

        secure=account['secure']

        tweepy.OAuthHandler.OAUTH_HOST=url['host']

        auth=tweepy.OAuthHandler(consumer_key, consumer_secret, secure=secure)
        auth.set_access_token(token_key, token_secret)
        api=tweepy.API(auth, url['send'], api_root=url['api'])

        try:
            api.update_status(text)
        except Exception as err:
            self.SBox['box'].show_all()
            self.SBox['box'].set_sensitive(True)
            self.SBox['send'].set_label('S_end %s' % err)
        else:
            self.SBox['box'].hide_all()
        finally:
            self.SBox['box'].set_sensitive(True)

    def GetToken(self, *args):
        mod, secure, wid=args

        if mod=='identica':
            url=IDENTICA_URL
            con=IDENTICA_CONSUMER
            message='click on allow in web browser then come back and click on Exchange'
        else:
            url=TWITTER_URL
            con=TWITTER_CONSUMER
            message='click on allow in web browser copy pin code here and then click on Exchange'

        consumer_key   =base64.b64decode(con['key'])
        consumer_secret=base64.b64decode(con['secret'])

        tweepy.OAuthHandler.OAUTH_HOST=url['host']

        auth=tweepy.OAuthHandler(consumer_key, consumer_secret, secure=secure)

        try:
            url = auth.get_authorization_url()
        except Exception as err:
            wid['label'].set_text('ERR: %s' % err)
            wid['OauthButton'].set_sensitive(True)
            return

        self.RequestToken=(auth.request_token.key, auth.request_token.secret)

        wid['label'].set_text('Try to open : %s\n%s' % (url, message))
        webbrowser.open_new(url)

        if mod=='twitter':
            wid['PinLabel'].show()
            wid['PinEntry'].show()
        wid['exchange'].show()

    def exchange(self, *args):
        mod, secure, wid=args

        wid['label'].set_text('Working...')

        if mod=='identica':
            url=IDENTICA_URL
            con=IDENTICA_CONSUMER
            verifier=self.RequestToken[0]
        else:
            url=TWITTER_URL
            con=TWITTER_CONSUMER
            verifier=wid['PinEntry'].get_text()
            if verifier=='':
                wid['label'].set_text('No pin code')
                wid['exchange'].set_sensitive(True)
                return

        consumer_key   =base64.b64decode(con['key'])
        consumer_secret=base64.b64decode(con['secret'])

        tweepy.OAuthHandler.OAUTH_HOST=url['host']

        auth=tweepy.OAuthHandler(consumer_key, consumer_secret, secure=secure)
        auth.set_request_token(self.RequestToken[0], self.RequestToken[1])

        try:
            access_token=auth.get_access_token(verifier)
        except Exception as err:
            wid['label'].set_text('ERR: %s' % err)
            wid['exchange'].set_sensitive(True)
            return

        self.AccessToken=(access_token.key, access_token.secret)

        auth=tweepy.OAuthHandler(consumer_key, consumer_secret, secure=secure)
        auth.set_access_token(access_token.key, access_token.secret)
        api=tweepy.API(auth, url['send'], api_root=url['api'])

        wid['label'].set_text('Done! Close configure window to see what happens!')


        self.SettingsClass.AddAccount(atype=mod,
                                      user=wid['UserEntry'].get_text(),
                                      token=self.AccessToken,
                                      secure=secure
                    )
        return

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
                return self.SettingsClass.conf['template'].format(title=title, genre=genre, artist=artist, album=album,
                                                rate=rate, year=year, pcount=pcount)
            except Exception as err:
                print (err)
                return DEFAULT_TEMPLATE.format(title=title, album=album, artist=artist)
        return ''

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

    def AddUI(self):
        self.ui_id=[]
        self.action_groups=[]

        conf=self.SettingsClass.conf

        for key in conf['accountsid']:
            action=gtk.Action('SendNotice-%d' % key,
                              _('%s') % conf['accountslist'][key]['user'],
                              _('Send as %s to %s') % (conf['accountslist'][key]['user'], conf['accountslist'][key]['type']),
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
        'accountsid':[],
        'template':DEFAULT_TEMPLATE,
    }

    def __init__(self):
        #self.RemoveConf(-1)
        self.conf=self.ReadConf()
        if self.conf is None:
            self.conf=self.CreateConf()

    def destroy(self):
        del self.conf

    def ReadConf(self):
        conf={}

        client=gconf.client_get_default()
        if client.get_string(self.KEYS['version'])==None:
            return None

        conf['editbefore']=client.get_bool  (self.KEYS['editbefore'])
        conf['version']   =client.get_string(self.KEYS['version'])
        conf['accountsid']=client.get_string(self.KEYS['accountsid'])
        conf['template']  =client.get_string(self.KEYS['template'])

        conf['accountsid']=self.Str2Conf(conf['accountsid'])

        conf['accountslist']={}

        for key in conf['accountsid']:
            conf['accountslist'][key]={}

            ad=self.KEYS['accounts'] + str(key) + '/'

            conf['accountslist'][key]['type']        = client.get_string(ad + 'type')         or ''
            conf['accountslist'][key]['user']        = client.get_string(ad + 'user')         or ''
            conf['accountslist'][key]['token_key']   = client.get_string(ad + 'token_key')    or ''
            conf['accountslist'][key]['token_secret']= client.get_string(ad + 'token_secret') or ''
            conf['accountslist'][key]['secure']      = client.get_bool  (ad + 'secure')       or False

        return conf

    def AddAccount(self,
                   atype='',
                   user='',
                   token=None,
                   secure=False
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
        client.set_string(ad + 'user'        , user)
        client.set_bool  (ad + 'secure'      , secure)
        client.set_string(ad + 'token_key'   , base64.b64encode(token[0]))
        client.set_string(ad + 'token_secret', base64.b64encode(token[1]))

        client.set_string(self.KEYS['accountsid'], self.Conf2Str())

        self.__init__()

    def CreateConf(self):
        client=gconf.client_get_default()
        client.set_bool  (self.KEYS['editbefore'], self.DEFAULT['editbefore'])
        client.set_string(self.KEYS['version']   , self.DEFAULT['version'])
        client.set_string(self.KEYS['accountsid'], '')
        client.set_string(self.KEYS['template']  , self.DEFAULT['template'])

        return self.DEFAULT

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

    def UpdateConf(self, *args):
        template, editbefore=args

        if template=='':
            template=self.DEFAULT['template']
        self.conf['template']  =template
        self.conf['editbefore']=editbefore

        client=gconf.client_get_default()
        client.set_bool  (self.KEYS['editbefore'], editbefore)
        client.set_string(self.KEYS['template']  , template)

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

# --------------------------------------------------------------------------------

class ConfigureDialog:
    def __init__(self, micro):
        self.MicroBlogger=micro
        self.SetClass=micro.SettingsClass

        self.MainW=None
        self.AddW =None

    def destroy(self):
        del self.MicroBlogger
        del self.SetClass
        del self.MainW
        del self.AddW

    def MainDialog(self):
        dialog=gtk.Dialog('MicroBlogger prefrences', None, gtk.DIALOG_DESTROY_WITH_PARENT,
                          (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        dialog.connect('response', self.MainDialogResponse)

        self.MainW={}

        # style
        frame=gtk.Frame('Style')
        box=gtk.VBox()
        entry=gtk.Entry()
        entry.set_text(self.SetClass.conf['template'])
        label=gtk.Label(TEMPLATE_GUIDE)

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
        check.set_active(self.SetClass.conf['editbefore'])
        dialog.vbox.pack_start(check, False, False)
        self.MainW['EditBefore']=check

        # Add/Remove Frame
        frame=gtk.Frame()
        box=gtk.VBox()
        dialog.vbox.pack_start(frame, False, False)
        frame.add(box)

        # add
        button=gtk.Button('_Add account')
        button.connect('clicked', self.AddClicked, dialog)
        box.pack_start(button)
        self.MainW['Add']=button
        
        # remove
        button=gtk.Button('_Remove account')
        button.connect('clicked', self.RemoveClicked, dialog)
        box.pack_start(button)
        self.MainW['Remove']=button

        dialog.show_all()
        return dialog

    def MainDialogResponse(self, dialog, response):
        self.MicroBlogger.RemoveUI()
        self.MicroBlogger.AddUI()

        self.GetNewSettings()
        self.MainW=None
        dialog.destroy()

    def GetNewSettings(self):
        template  =self.MainW['StyleEntry'].get_text()
        editbefore=self.MainW['EditBefore'].get_active()

        self.SetClass.UpdateConf(template, editbefore)

    def AddClicked(self, button, MainDialogWindow):
        dialog=gtk.Dialog('Add Account', MainDialogWindow, gtk.DIALOG_DESTROY_WITH_PARENT,
                          (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        self.AddW={}
        self.MicroBlogger.RequestToken=None
        self.MicroBlogger.AccessToken=None

        # type
        label=gtk.Label('Account Type')
        combo=gtk.combo_box_new_text()
        combo.connect('changed', self.AddComboChanged)
        for item in ACCOUNT_TYPE:
            combo.append_text(item)

        box=gtk.HBox()
        box.pack_start(label)
        box.pack_start(combo)
        self.AddW['TypeLabel']=label
        self.AddW['TypeCombo']=combo
        dialog.vbox.pack_start(box, False, False)

        top=0

        # table
        table=gtk.Table()
        dialog.vbox.pack_start(table)
        self.AddW['table']=table

        # User
        top+=1
        label=gtk.Label('User name')
        entry=gtk.Entry()

        table.attach(label, 0, 1, top, top+1)
        table.attach(entry, 1, 2, top, top+1)
        self.AddW['UserLabel']=label
        self.AddW['UserEntry']=entry

        # secure
        top+=1
        check=gtk.CheckButton('Use secure connection')

        table.attach(check, 1, 2, top, top+1)
        self.AddW['secure']=check

        # authorize 
        top+=1
        button=gtk.Button('Authorize')
        button.connect('clicked', self.GetToken)

        table.attach(button, 0, 2,top, top+1)
        self.AddW['OauthButton']=button

        # pin
        top+=1
        label=gtk.Label('Pin')
        entry=gtk.Entry()

        table.attach(label, 0, 1, top, top+1)
        table.attach(entry, 1, 2, top, top+1)
        self.AddW['PinLabel']=label
        self.AddW['PinEntry']=entry

        # exchange
        top+=1
        button=gtk.Button('Exchange')
        button.connect('clicked', self.exchange)

        table.attach(button, 0, 2, top, top+1)
        self.AddW['exchange']=button

        # label
        top+=1
        label=gtk.Label()
        label.set_selectable(True)
        self.AddW['label']=label
        dialog.vbox.pack_start(label, False, False)

        dialog.show_all()
        # hide
        self.AddW['UserLabel'].hide()
        self.AddW['UserEntry'].hide()
        self.AddW['OauthButton'].hide()
        self.AddW['secure'].hide()
        self.AddW['PinLabel'].hide()
        self.AddW['PinEntry'].hide()
        self.AddW['exchange'].hide()

        # run
        dialog.run()
        dialog.destroy()
        self.AddW=None

    def RemoveClicked(self, button, MainDialogWindow):
        dialog=gtk.Dialog('Remove Account', MainDialogWindow, gtk.DIALOG_DESTROY_WITH_PARENT,
                          (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        conf=self.SetClass.conf

        table=gtk.Table()
        top=0

        dialog.vbox.pack_start(table)

        for key in conf['accountsid']:
            user =conf['accountslist'][key]['user']
            atype=conf['accountslist'][key]['type']

            w=gtk.Label('%d %s in %s ' % (key, user, atype))
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

        self.SetClass.RemoveAccount(key)

    def AddComboChanged(self, combo):
        combo.set_sensitive(False)
        text=combo.get_active_text()

        if text=='statusnet':
            self.AddW['label'].set_text('sorry! Not available yet.')

        else:
            self.AddW['OauthButton'].show()
            self.AddW['secure'].show()
            self.AddW['UserEntry'].show()
            self.AddW['UserLabel'].show()

            self.AddW['label'].set_text(
                'click on authorize button\nI\'ll try to open your webbrowser')

    def GetToken(self, button):
        if not self.AddW['UserEntry'].get_text_length():
            self.AddW['label'].set_text('Don\'t have a name?')
            return

        self.AddW['label'].set_text('Requesting for access token')

        self.AddW['OauthButton'].set_sensitive(False)
        self.AddW['UserEntry'].set_sensitive(False)
        self.AddW['UserLabel'].set_sensitive(False)
        self.AddW['secure'].set_sensitive(False)

        text=self.AddW['TypeCombo'].get_active_text()
        secure=self.AddW['secure'].get_active()

        threading.Thread(target=self.MicroBlogger.GetToken,
                         args=(text, secure, self.AddW)
                        ).start()

    def exchange(self, button):
        self.AddW['exchange'].set_sensitive(False)

        text=self.AddW['TypeCombo'].get_active_text()
        secure=self.AddW['secure'].get_active()

        threading.Thread(target=self.MicroBlogger.exchange,
                         args=(text, secure, self.AddW)
                        ).start()
