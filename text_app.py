#!/usr/bin/env python3

#
# Copyright 2014 Paul Donohue <Tray_Apps@PaulSD.com>
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.  If
# not, see <http://www.gnu.org/licenses/>.
#



#
# Prerequisites:
# Install GtkTrayIcon (from the gtktrayicon/ subdirectory)
# sudo apt-get install --no-install-recommends libgirepository1.0-dev gobject-introspection \
#  gir1.2-gtk-3.0
#



import gi
gi.require_version('Gtkti', '3.0')
from gi.repository import Gtkti, Gtk, Gdk, GLib
import signal, sys, os
import threading

# In Python 2, threading.Event().wait() wakes up frequently and burns a lot of CPU.
# This does not happen in Python 3, so I'm simply using Python 3 instead of Python 2 for this app.
# See: http://stackoverflow.com/questions/29082268/python-time-sleep-vs-event-wait
# I don't know if there are any work-arounds for this issue in Python 2.

# WARNING: Variable scope for Python inline functions and lambdas does not work like other
# languages!  To ensure that definition-scope variables are passed into the function/lambda's scope
# as expected, explicitly add 'var=var' (optional/defaulted) parameters to the end of the function/
# lambda's parameter list.

class TextApp:

  def __init__(self, text):
    self.text = text

    self.build_ui()

  def build_ui(self):
    self.tray = tray = Gtkti.TrayIcon()
    eventbox = Gtk.EventBox()
    tray.add(eventbox)
    self.tray_label = tray_label = Gtk.Label(self.text)
    eventbox.add(tray_label)
    tray.show_all()

    menu = Gtk.Menu()
    item_quit = Gtk.MenuItem('Quit')
    def quit(menu_item):
      if sys.version_info < (3, 0):
        os.kill(os.getpid(), signal.SIGINT)
      else:
        Gtk.main_quit()
    item_quit.connect('activate', quit)
    menu.append(item_quit)
    menu.show_all()
    def button_pressed(eventbox, event, menu=menu):
      if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
        menu.popup(None, None, None, None, event.button, event.time)
    eventbox.connect('button-press-event', button_pressed)

if __name__ == '__main__':
  TextApp(' '.join(sys.argv[1:]))

  def on_sigint(_signum, _frame):
    Gtk.main_quit()
  signal.signal(signal.SIGINT, on_sigint)

  # If the main thread is running C code (such as Gtk.main()), then Python signal handlers will not
  # run until that C code returns.  To work around this, run the C code in a separate thread, then
  # sleep the main thread.  Unfortunately, threading.Thread().join() and threading.Event().wait() in
  # Python 2.X (but not 3.X) also block signal handlers (see http://bugs.python.org/issue1167930).
  # To work around this, sleep the main thread using signal.pause(), and wake it from the 'Quit'
  # menu item above using `os.kill(os.getpid(), signal.SIGINT)`.
  thread = threading.Thread(target=Gtk.main)
  thread.start()
  if sys.version_info < (3, 0):
    signal.pause()
  thread.join()
