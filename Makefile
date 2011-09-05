PLUGIN_PATH=/usr/lib/rhythmbox/plugins
install:
	mkdir -p $(PLUGIN_PATH)/microblogger
	cp microblogger.* microblogger-prefs.ui oauth2/ $(PLUGIN_PATH)/microblogger -Rf
	cp ir.aliva.microblogger.gschema.xml /usr/share/glib-2.0/schemas 
	glib-compile-schemas /usr/share/glib-2.0/schemas 
	
uninstall:
	rm -Rf $(PLUGIN_PATH)/microblogger /usr/share/glib-2.0/schemas/ir.aliva.microblogger.gschema.xml
	glib-compile-schemas /usr/share/glib-2.0/schemas
	
upschema:
	cp ir.aliva.microblogger.gschema.xml /usr/share/glib-2.0/schemas 
	glib-compile-schemas /usr/share/glib-2.0/schemas 
