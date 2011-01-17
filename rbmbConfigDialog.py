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

import gtk
import gobject
from rbmbAddDialog import AddDialog

class ConfigDialog:
    '''Configure dialog. add/remove account and change settings'''
    def __init__(self, mb):
        self.mb=mb
        self.lstore=None
        self.dialog=None
        self.view=None
        
    def __del__(self):
        del self.mb
        del self.lstore
        del self.dialog
        del self.view
        
    def create_main_window(self):
        '''This is the most important function in this class. every thing
        depends to it.'''
        
        self.dialog=gtk.Dialog('Microblogger preferences', None,
                          gtk.DIALOG_DESTROY_WITH_PARENT,
                          (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.dialog.connect('response', self._main_dialog_response)
        
        notebook=gtk.Notebook()
        
        self.dialog.vbox.pack_start(notebook)
        
        # create a dictionary of tabs
        tabs={
             'General' :'ui/rbmb-tab-general.ui',
             'Accounts':'ui/rbmb-tab-accounts.ui',
             'Proxy'   :'ui/rbmb-tab-proxy.ui',
        }
        
        # create a list store for all accounts
        self._create_list_store()
        self.update_list_store()
        
        # create tabs then attach them to note book.
        for key in tabs:
            tabui=gtk.Builder()
            tabui.add_from_file(self.mb.find_file(tabs[key]))
            tabui.connect_signals(self)
        
            tab=tabui.get_object(key)
            label=gtk.Label(key)
        
            notebook.append_page(tab, label)
            
            if key=='Accounts':
                view=tabui.get_object('accounts-tree-view')
                view.set_model(self.lstore)
                view.get_selection().set_mode(gtk.SELECTION_SINGLE)
                self._add_columns(view)
                self.view=view
            elif key=='General':
                self.entry_template=tabui.get_object('template')
                self.entry_template.set_text(self.mb.get_conf('template'))

                self.progress_bar=tabui.get_object('progress')
                self.progress_bar.set_active(self.mb.get_conf('progress'))
            elif key=='Proxy':
                try:
                    import socks

                    frame=tabui.get_object('manual-frame')
                    tabui.get_object('noproxy').connect('toggled', self._proxy_radio_changed, frame, False)
                    tabui.get_object('manual' ).connect('toggled', self._proxy_radio_changed, frame, True )

                    proxy=self.mb.get_conf('proxy', 0)
                    if proxy=='none':
                        tabui.get_object('noproxy').set_active(True)
                        frame.set_sensitive(False)
                    else:
                        tabui.get_object('manual').set_active(True)
                        tabui.get_object(proxy).set_active(True)
                        frame.set_sensitive(True)
                    tabui.get_object('proxy_server').set_text(self.mb.get_conf('proxy_server', 0))
                    tabui.get_object('proxy_port').set_value (self.mb.get_conf('proxy_port'  , 0))

                    self.proxy_widgets=tabui
                except ImportError:
                    for w in ('noproxy', 'manual', 'manual-frame'):
                        tabui.get_object(w).set_sensitive(False)
                    self.proxy_widgets=None
                    tabui.get_object('hint').set_text(
'install python socks module from package manger\nor Source forge to active this page\nSF link: http://sourceforge.net/projects/socksipy/')
        
                    tabui.get_object('hint').set_sensitive(True)
        # show it        
        self.dialog.show_all()
        return self.dialog

    def _proxy_radio_changed(self, radio, frame, active):
            frame.set_sensitive(active)
        
    def _main_dialog_response(self, dialog, id):
        self.mb.remove_ui()     
        self.mb.add_ui()

        uc=self.mb.settings.update_conf

        uc('template', self.entry_template.get_text())
        uc('progress', self.progress_bar.get_active())

        if self.proxy_widgets!=None:
            w=self.proxy_widgets
            for i in ('http', 'socks4', 'socks5'):
                if w.get_object(i).get_active():
                    proxy=i
            if w.get_object('noproxy').get_active():
                proxy='none'
            uc('proxy'       , proxy)
            uc('proxy_server', w.get_object('proxy_server').get_text())
            uc('proxy_port'  , int(w.get_object('proxy_port'  ).get_value()))
        
        dialog.destroy()
        
        self.lstore=None
        self.dialog=None
        self.pages=None
        
    def _create_list_store(self):
        # TODO
        # add pixbuf
        self.lstore=gtk.ListStore(
            gobject.TYPE_STRING,  # alias
            gobject.TYPE_STRING,  # type
            gobject.TYPE_STRING,  # service url
        )
    
    def update_list_store(self):
        self.lstore.clear()
        
        for alias in self.mb.get_conf('a_list'):
            iter = self.lstore.append()
            a=self.mb.get_conf('a', alias)
            self.lstore.set(iter,
                            0, a['alias'],
                            1, a['type'],
                            2, a['url'])
            
    def _add_columns(self, treeview):
        model=treeview.get_model()

        # column for alias
        renderer=gtk.CellRendererText()
        column=gtk.TreeViewColumn('Alias', renderer, text=0)
        treeview.append_column(column)
        
        # column for account type
        renderer=gtk.CellRendererText()
        column=gtk.TreeViewColumn('Type', renderer, text=1)
        treeview.append_column(column)
        
        # column for service url
        renderer=gtk.CellRendererText()
        column=gtk.TreeViewColumn('Service', renderer, text=2)
        treeview.append_column(column)
        
    def _add_button_clicked(self, button):
        AddDialog(self.dialog, self.mb)
        
    def _remove_button_clicked(self, button):
        selection = self.view.get_selection()
        model, iter = selection.get_selected()
        
        if iter==None:
            return
        
        alias=model.get_value(iter, 0)
        
        self.mb.settings.remove_account(alias)
        
        self.update_list_store()
