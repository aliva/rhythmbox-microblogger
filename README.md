

** Buggy! report bugs!

#install

depends on : <code>httplib, rhythmbox3, gtk3</code>

    git clone git://github.com/aliva/rhythmbox-microblogger.git
    cd rhythmbox-microblogger
    sudo make install

#Install on Gnome2

if you are using gnome2 you can install the older version.

    mkdir -p ~/.gnome2/rhythmbox/plugins
    cd ~/.gnome2/rhythmbox/plugins
    git clone git://github.com/aliva/rhythmbox-microblogger.git
    cd rhythmbox-microblogger/
    git checkout Gnome2


restart rhythmbox and in <code>Edit->Plugins</code> activae microblogger. use Prefrences button to add accounts. close window when done


Press Ctrl+M in rhythmbox main window to show Message box then click on send to send notice.
