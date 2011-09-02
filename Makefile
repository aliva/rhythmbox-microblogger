
install:
	mkdir -p /usr/share/rhythmbox/plugins/microblogger
	cp microblogger.py microblogger-prefs.ui oauth2/ /usr/share/rhythmbox/plugins/microblogger -Rf
	cp ir.aliva.microblogger.gschema.xml /usr/share/glib-2.0/schemas 
	glib-compile-schemas /usr/share/glib-2.0/schemas 
	
uninstall:
	rm -Rf /usr/share/rhythmbox/plugins/microblogger /usr/share/glib-2.0/schemas/ir.aliva.microblogger.gschema.xml
	glib-compile-schemas /usr/share/glib-2.0/schemas
	
upschema:
	cp ir.aliva.microblogger.gschema.xml /usr/share/glib-2.0/schemas 
	glib-compile-schemas /usr/share/glib-2.0/schemas 
