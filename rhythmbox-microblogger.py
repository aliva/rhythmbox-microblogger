# -*- coding: utf8 -*-
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

__version__='0.2'

import rb
import rhythmdb
import gtk
import os
import urllib
import urllib2
import threading

ui_toolbar_button = '''
<ui>
  <toolbar name='ToolBar'>
    <placeholder name='PluginPlaceholder'>
      <toolitem name='ToolBarMicroBlogger-%s-%s' action='SendNotice-%s-%s'/>
    </placeholder>
  </toolbar>
</ui>
'''

ConfPath = os.path.expanduser('~')+'/.local/share/rhythmbox/microblogger.conf'
DefaultStyle="[Rhythmbox] {title} by {artist} from {album}"
AccountType=('identica', 'twitter', 'statusnet')

class microblogger(rb.Plugin):
    def __init__ (self):
        rb.Plugin.__init__(self)
        gtk.gdk.threads_init()

    def activate(self, shell):
        self.shell=shell
        self.uim = shell.get_ui_manager()
        self.db=shell.get_property('db')
        self.pl=shell.get_property('shell-player')

        self.LoadSettings()
        self.register_icons()
        self.add_ui()
        self.create_entry_box()

    def deactivate(self, shell):
        self.SaveSettings()
        self.remove_ui()
        self.entrybox['box'].destroy()
        del self.entrybox['box']

    def create_configure_dialog(self, dialog=None):
        dialog=gtk.Dialog('MicroBlogger prefrences', None, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        dialog.connect('response', self.prefrences_response)

        self.ConfDialogWidgets={}
        
        w=gtk.Entry()
        w.set_text(self.set['style'])
        dialog.vbox.pack_start(w, False, False)
        self.ConfDialogWidgets['style']=w

        w=gtk.Label('Valid Meta data:\n{title} {genre} {artist} {album} {rate} {year} {pcount}\nUse {{ for { and }} for }')
        dialog.vbox.pack_start(w, False, False)

        w=gtk.CheckButton('edit notice before send')
        w.set_active(self.set['edit'])
        dialog.vbox.pack_start(w, False, False)
        self.ConfDialogWidgets['edit']=w

        w=gtk.Button('_Add account')
        w.connect('clicked', self.add_account, dialog)
        dialog.vbox.pack_start(w)

        w=gtk.Button('_Remove account')
        w.connect('clicked', self.remove_account, dialog)
        dialog.vbox.pack_start(w, False, False)

        dialog.show_all()
        return dialog

    def prefrences_response(self, dialog, response):
        self.set['style']=self.ConfDialogWidgets['style'].get_text()
        self.set['edit'] =self.ConfDialogWidgets['edit' ].get_active()
        dialog.destroy()
        del self.ConfDialogWidgets
        self.remove_ui()
        self.add_ui()

    def LoadSettings(self):
        if os.path.isfile(ConfPath):
            with open(ConfPath, 'rb') as file:
                import pickle
                self.set=pickle.load(file)
        else:
            self.set={'style':DefaultStyle, 'edit':True, 'accounts':[]}

    def SaveSettings(self):
            file=open(ConfPath, 'wb+')
            import pickle
            pickle.dump(self.set, file)
            file.close()

    def register_icons(self):
        IconFactory=gtk.IconFactory()
        IconFactory.add_default()

        for account in AccountType:
            gtk.stock_add([('rb-microblogger-%s' % account, account, 0, 0, '')])
            IconSource=gtk.IconSource()
            IconSet=gtk.IconSet()
    
            IconSource.set_filename(self.find_file('%s.png' % account))
            IconSet.add_source(IconSource)
            IconFactory.add('rb-microblogger-%s' % account, IconSet)

    def add_ui(self):
        self.ui_id=[]
        self.action_groups=[]

        for acnt in self.set['accounts']:
            action = gtk.Action('SendNotice-%s-%s' % (acnt['user'], acnt['api']),
                                    _('Send'),
                                    _('%s' % acnt['user']),
                                    'rb-microblogger-%s' % acnt['type'])
            activate_id = action.connect('activate', self.send_clicked, acnt)
            action_group = gtk.ActionGroup('MicroBloggerPluginActions-%s-%s'% (acnt['user'], acnt['api'], ))
            action_group.add_action(action)
            self.uim.insert_action_group(action_group, 0)
            self.ui_id.append(self.uim.add_ui_from_string(ui_toolbar_button % 
                    (acnt['user'], acnt['api'], acnt['user'], acnt['api'])))
            self.action_groups.append(action_group)
            self.uim.ensure_update()

    def remove_ui(self):
        for key in self.ui_id:
    		self.uim.remove_ui (key)

        for key in self.action_groups:
    		self.uim.remove_action_group (key)

        del self.ui_id
        del self.action_groups

    def send_clicked(self, action, acnt):
        self.entrybox['box'].hide_all()
        text=self.generate_string()
        self.CurrentAccount=acnt

        if text=='':
            self.entrybox['box'].hide_all()
            return

        self.entrybox['entry'].set_text(text)
        self.entrybox['send'].set_label('_Send as %s in %s' %(acnt['user'], acnt['type']))

        if self.set['edit'] or len(text)>140:
            self.entrybox['box'].show_all()

        else:
            self.send(None)
    
    def generate_string(self):
        if self.pl.get_playing():
            entry=self.pl.get_playing_entry()
            db=self.db

            title=db.entry_get(entry, rhythmdb.PROP_TITLE)
            genre=db.entry_get(entry, rhythmdb.PROP_GENRE)
            artist=db.entry_get(entry, rhythmdb.PROP_ARTIST)
            album=db.entry_get(entry, rhythmdb.PROP_ALBUM)
            rate=db.entry_get(entry, rhythmdb.PROP_RATING)
            year=db.entry_get(entry, rhythmdb.PROP_YEAR)
            pcount=db.entry_get(entry, rhythmdb.PROP_PLAY_COUNT)

            try:
                return self.set['style'].format(title=title, genre=genre, artist=artist, album=album,
                                                rate=rate, year=year, pcount=pcount)
            except Exception as err:
                print (err)
                return DefaultStyle.format(title=title, album=album, artist=artist)
        return ''

    def add_account(self, button, maindialog):
        dialog=gtk.Dialog('MicroBlogger prefrences', maindialog, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        self.type=0

        # user name
        hbox=gtk.HBox()
        w=gtk.Label('User name : ')
        hbox.pack_start(w)
        user_w=gtk.Entry()
        hbox.pack_start(user_w)
        dialog.vbox.pack_start(hbox)

        # password
        hbox=gtk.HBox()
        w=gtk.Label('Password : ')
        hbox.pack_start(w)
        pass_w=gtk.Entry()
        pass_w.set_visibility(False)
        hbox.pack_start(pass_w)
        dialog.vbox.pack_start(hbox)

        # service
        hbox=gtk.HBox()
        w=gtk.Label('Service : ')
        hbox.pack_start(w)
        w=gtk.combo_box_new_text()
        w.connect('changed', self.combo_changed)
        for account in AccountType:
            w.append_text(account)
        hbox.pack_start(w)
        dialog.vbox.pack_start(hbox)

        # api address
        hbox=gtk.HBox()
        w=gtk.Label('Api Address : ')
        hbox.pack_start(w)
        self.entry=gtk.Entry()
        self.entry.set_sensitive(False)
        hbox.pack_start(self.entry)
        dialog.vbox.pack_start(hbox)

        # run
        dialog.show_all()
        result=dialog.run()
        if result==gtk.RESPONSE_CLOSE:
            user=user_w.get_text()
            password=pass_w.get_text()
            api=self.entry.get_text()

            if len(api) and len(password) and len(user):
                self.update_accounts_add(api, user, password)
        dialog.destroy()
        del self.entry
        del self.type

    def combo_changed(self, combo):
        text=combo.get_active_text()
        self.entry.set_sensitive(text=='statusnet')

        self.type=text
        if text=='identica':
            self.entry.set_text('http://identi.ca/api')
        elif text=='twitter':
            self.entry.set_text('http://www.twitter.com/api')
        else:
            self.entry.set_text('')

    def update_accounts_add(self, api, user, password):
        for c in range(len(self.set['accounts'])):
            if self.set['accounts'][c]['user']==user and self.set['accounts'][c]['api']==api:
                del self.set['accounts'][c]
                break

        self.set['accounts'].append({'user':user, 'password':password, 'api':api, 'type':self.type})
        self.SaveSettings()

    def update_accounts_remove(self, button, api, user):
        for c in range(len(self.set['accounts'])):
            if self.set['accounts'][c]['user']==user and self.set['accounts'][c]['api']==api:
                del self.set['accounts'][c]
                break
        button.set_sensitive(False)
        self.SaveSettings()

    def remove_account(self, button, maindialog):
        dialog=gtk.Dialog('MicroBlogger prefrences', maindialog, gtk.DIALOG_DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        table=gtk.Table()
        dialog.vbox.pack_start(table)

        checklist=[]

        for c in range(len(self.set['accounts'])):
            w=gtk.Label('%s    %s   %s    ' %
                        (self.set['accounts'][c]['user'], self.set['accounts'][c]['api'], self.set['accounts'][c]['type']))
            table.attach(w, 0, 1, c, c+1)            
            w=gtk.Button(stock=gtk.STOCK_REMOVE)
            table.attach(w, 1, 2, c, c+1)
            w.connect('clicked', self.update_accounts_remove, self.set['accounts'][c]['api'], self.set['accounts'][c]['user'])

        dialog.show_all()
        result=dialog.run()
        dialog.destroy()

    def create_entry_box(self):
        # box
        self.entrybox={}
        box=gtk.HBox()
        self.shell.add_widget (box, rb.SHELL_UI_LOCATION_MAIN_TOP)
        self.entrybox['box']=box

        # entry
        w=gtk.Entry()
        w.connect('changed' , self.entry_box_change)
        w.connect('activate', self.send)
        box.pack_start(w)
        self.entrybox['entry']=w

        # string len label
        w=gtk.Label(' 140 ')
        box.pack_start(w, False, False)
        self.entrybox['label']=w

        # send button
        w=gtk.Button('_Send')
        w.connect('clicked', self.send)
        box.pack_start(w, False, False)
        self.entrybox['send']=w

        # cancel button
        w=gtk.Button(stock=gtk.STOCK_CANCEL)
        w.connect('clicked', self.entry_box_cancel)
        box.pack_start(w, False, False)
        self.entrybox['cancel']=w

        # hide box
        box.hide_all()

    def entry_box_cancel(self, button):
        self.entrybox['box'].hide_all()

    def entry_box_change(self, entry):
        length=entry.get_text_length()
        self.entrybox['label'].set_text(' %d ' % (140-length))
        self.entrybox['send'].set_sensitive(0<length<=140)

    def send(self, button):
        text=self.entrybox['entry'].get_text()
        if len(text)==0:
            del self.CurrentAccount
            return
        acnt=self.CurrentAccount

        pwd_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        pwd_mgr.add_password(None, acnt['api'], acnt['user'], acnt['password'])
        handler = urllib2.HTTPBasicAuthHandler(pwd_mgr)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

        msg=urllib.urlencode({'status':text,'source':'Rhythmbox'})

        url_open=acnt['api']+'/statuses/update.json?%s' % msg
        threading.Thread(target=self.send_thread, args=(url_open,)).start()

    def send_thread(self, *msg):
        self.entrybox['send'].set_label('S_ending...')
        self.entrybox['send'].set_sensitive(False)
        self.entrybox['entry'].set_sensitive(False)

        try:
            url=urllib2.urlopen(msg[0], '')
        except Exception as err:
            self.entrybox['box'].show_all()
            self.entrybox['send'].set_label('S_end %s' % err)
        else:
            url.close()
            self.entrybox['box'].hide_all()
        finally:
            self.entrybox['send'].set_sensitive(True)
            self.entrybox['entry'].set_sensitive(True)
