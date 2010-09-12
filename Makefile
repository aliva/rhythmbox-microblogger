# run 'make' to install for current user
all:
	mkdir -p ~/.gnome2/rhythmbox/plugins/rhythmbox-microblogger
	cp * ~/.gnome2/rhythmbox/plugins/rhythmbox-microblogger -Rf
# run 'sudo make allusers' to instal for all users
allusers:
	mkdir -p /usr/lib/rhythmbox/plugins/rhythmbox-microblogger
	cp * /usr/lib/rhythmbox/plugins/rhythmbox-microblogger -Rf
