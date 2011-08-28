from gi.repository import GObject, Peas, PeasGtk
from gi.repository import Gtk
from gi.repository import RB

import rb

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

    def do_create_configure_widget(self):
        self.request = Requests()
        ui_file = rb.find_plugin_file(self, "microblogger-prefs.ui")
        self.builder = Gtk.Builder()
        self.builder.add_from_file(ui_file)

        self.builder.get_object('add_account').connect('clicked', self.on_add_account_clicked)
        self.builder.get_object('del_account').connect('clicked', self.on_del_account_clicked)

        self.builder.get_object('authorize').connect('clicked', self.on_authorize_clicked)

        self.builder.get_object('cancel').connect('clicked', self.on_cancel_clicked)

        notebook = self.builder.get_object('general')
        notebook.set_show_tabs(False)
        return notebook

    def on_add_account_clicked(self, button):
        self.builder.get_object('general').set_current_page(1)

    def on_del_account_clicked(self, button):
        print ('del')

    def on_cancel_clicked(self, button):
        self.builder.get_object('general').set_current_page(0)

    def on_authorize_clicked(self, button):
        self.request.authorize(self.builder.get_object('note')) 

class Requests:
    def __init__(self):
        pass

    def authorize(self, note):
        note.set_text('start')
        import oauth2 as o
        key, sec = ('79c5e601c6d3154d4a19014ffb51e6f9', 'c82bbbd875eebc6efd807910b873ea09')
        con = o.Consumer(key, sec)
        cli = o.Client(con)
        resp, cont = cli.request('https://identi.ca/api/oauth/request_token?oauth_callback=oob')
        note.set_text(str(resp.status) +'\n'+cont)
