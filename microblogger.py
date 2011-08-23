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
        w = Gtk.Window()
        w.show_all()

    def do_deactivate(self):
        print "deactivating sample python plugin"


class MicrobloggerConfigurable(GObject.Object, PeasGtk.Configurable):
    __gtype_name__ = 'MicrobloggerConfigurable'

    def do_create_configure_widget(self):
        ui_file = rb.find_plugin_file(self, "microblogger-prefs.ui")
        builder = Gtk.Builder()
        builder.add_from_file(ui_file)
        return builder.get_object('general')
