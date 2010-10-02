# run 'make' to install for current user
# IMPORTANT: do not use 'sudo make' 
all:
	mkdir -p ~/.gnome2/rhythmbox/plugins/rhythmbox-microblogger
	cp * ~/.gnome2/rhythmbox/plugins/rhythmbox-microblogger -Rf
