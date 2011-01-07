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
import threading
from rbmbRequest import AddAccountRequest
    
class AddDialog(AddAccountRequest):
    def __init__(self, dialog, mb):
        AddAccountRequest.__init__(self)
        
        self.pages=None
        self.mb=mb
        
        assistant=gtk.Assistant()
        
        assistant.set_transient_for(dialog)
        assistant.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        assistant.set_destroy_with_parent(True)
        assistant.set_modal(True)
        
        assistant=self._attach_pages(assistant)
        
        assistant.set_forward_page_func(self._forward_page_func)
        
        assistant.connect('close' , self._signal, 'close')
        assistant.connect('cancel', self._signal, 'cancel')
        assistant.connect('apply' , self._signal, 'apply')
        
        self.assistant=assistant
        
        assistant.show_all()    
    
    def __del__(self):
        del self.pages
        del self.mb
        del self.assistant
    
    def _forward_page_func(self, page):
        # TODO
        # Update this function
        if self.pages==None:
            return -1

        page_id=self._get_page_id(page)
        type=self._get_account_type()
        self.request_set_type(type)
        
        if page==0:
            return 1
        elif page==1:
            return 2
        elif page==2:
            return 3
        elif page==3:
            return 5
        elif page==5:
            return 6
        return -1
      
    def _signal(self, assistant, id):
        if id=='cancel':
            assistant.destroy()
        elif id=='close':
            self.save_account(self.mb)
            self.mb.config_dialog.update_list_store()
            assistant.destroy()
            
        self.pages=None
        
    def _set_hint(self, hint):
        index=self.assistant.get_current_page()
        
        for page in self.pages:
            if page[1]==index:
                w=page[6].get_object('hint')
                
                try:
                    w.set_text(hint)
                except Exception as err:
                    print 'Could not change hint :\n', err
            
    def _attach_pages(self, assistant):
        pages=[
            # 0 - widget
            # 1 - index
            # 2 - title
            # 3 - type
            # 4 - complete
            # 5 - id
            # 6 - ui
            [None, -1 , 'Select a service provider',
             gtk.ASSISTANT_PAGE_CONTENT, True, 'select', None],
            [None, -1 , 'Authorize account',
             gtk.ASSISTANT_PAGE_CONTENT, False, 'authorize', None],
            [None, -1 , 'Pin Code',
             gtk.ASSISTANT_PAGE_CONTENT, False, 'pin', None],
            [None, -1 , 'Exchange Request',
             gtk.ASSISTANT_PAGE_CONTENT, False, 'exchange', None],
            [None, -1 , 'Basic auth',
             gtk.ASSISTANT_PAGE_CONTENT, False, 'basic', None],
            [None, -1 , 'Alias',
             gtk.ASSISTANT_PAGE_CONTENT, False, 'alias', None],
            [None, -1 , 'Finished',
             gtk.ASSISTANT_PAGE_CONFIRM, True, 'finish', None],
        ]
        
        for page in pages:
            page[6]=gtk.Builder()
            page[6].add_from_file(self.mb.find_file('ui/rbmb-add-'+page[5]+'.ui'))
            page[6].connect_signals(self)
        
            page[0]=page[6].get_object('general')
            
            page[1]=assistant.append_page(page[0])
            
            assistant.set_page_title   (page[0], page[2])
            assistant.set_page_type    (page[0], page[3])
            assistant.set_page_complete(page[0], page[4])
            
            if page[5]=='select':
                self._set_service_logo(page[6])
            
        
        self.pages=pages
        return assistant
    
    def _set_service_logo(self, ui):
        for account in self.mb.ACCOUNT_TYPE:
            w=ui.get_object(account+'-image')
            w.set_from_stock('rbmb-'+account, gtk.ICON_SIZE_MENU)
            
    def _get_account_type(self):
        ui=self.pages[0][6]
        
        for account in self.mb.ACCOUNT_TYPE:
            w=ui.get_object(account)
            if w.get_active():
                return account
            
    def _find_page_index(self, id):
        for page in self.pages:
            if page[5]==id:
                return page[1]
        return -1

    def _get_page_id(self, index):
        for page in self.pages:
            if page[1]==index:
                return page[5]
        return None
    
    def _authorize_clicked(self, button):
        page=self.pages[1]
                    
        self._set_hint('')
        
        threading.Thread(target=self.authorize,
                args=(self._set_hint, button, self.assistant, page, self.mb.get_conf('proxy'))
                ).start()
        
    def _exchange_clicked(self, button):
        page=self.pages[3]        
        
        self._set_hint('')
        
        threading.Thread(target=self.exchange,
                args=(self._set_hint, button, self.assistant, page, self.mb.get_conf('proxy'))
                ).start()
        
    def _pin_entry_changed(self, entry):
        len=entry.get_text_length()
        self.pin=entry.get_text()
        
        page=self.pages[2]
        page[4]=bool(len)
        self.assistant.set_page_complete(page[0], page[4])
        
    def _alias_entry_changed(self, entry):
        len=entry.get_text_length()
        self.alias=entry.get_text().strip()
        
        self._set_hint('')
        
        page=self.pages[5]
        
        if self.alias in self.mb.get_conf('a_list'):
            page[4]=False
            self.assistant.set_page_complete(page[0], page[4])
            self._set_hint('Use another alias\n%s is not unique' % self.alias)
            return
        
        page[4]=bool(len)
        self.assistant.set_page_complete(page[0], page[4])
