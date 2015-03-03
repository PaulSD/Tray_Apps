#!/usr/bin/env python

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
# sudo apt-get install libgirepository1.0-dev gobject-introspection gir1.2-gtk-3.0
#



from gi.repository import Gtkti, Gtk, Gdk, GLib
import signal, sys, os
import threading
import datetime

# WARNING: Variable scope for Python inline functions and lambdas does not work like other
# languages!  To ensure that definition-scope variables are passed into the function/lambda's scope
# as expected, explicitly add 'var=var' (optional/defaulted) parameters to the end of the function/
# lambda's parameter list.

class TimeApp:

  def __init__(self):
    self.show_date = True
    self.prefix = ''
    #self.date_format = '%x '  # Locale-appropriate date format
    self.date_format = '%Y.%m.%d '
    self.time_format = '%H:%M'
    self.show_seconds = False
    self.seconds_format = ':%S'
    self.suffix = ' '

    self.time_fudge = datetime.timedelta(seconds=.25)

    self.build_ui()
    self.start_update_thread()

  def build_ui(self):
    self.tray = tray = Gtkti.TrayIcon()
    eventbox = Gtk.EventBox()
    tray.add(eventbox)
    self.tray_label = tray_label = Gtk.Label('')
    self.gtk_update_ui()
    eventbox.add(tray_label)
    tray.show_all()

    menu = Gtk.Menu()
    item_show_date = Gtk.CheckMenuItem('Show Date')
    item_show_date.set_active(self.show_date)
    def toggle_date(item_show_date, self=self):
      self.show_date = item_show_date.get_active()
      self.gtk_update_ui()
    item_show_date.connect('toggled', toggle_date)
    menu.append(item_show_date)
    item_show_seconds = Gtk.CheckMenuItem('Show Seconds')
    item_show_seconds.set_active(self.show_seconds)
    self.toggle_seconds_event = threading.Event()
    def toggle_seconds(item_show_seconds, self=self):
      self.show_seconds = item_show_seconds.get_active()
      # Wake the update thread, which will update the UI, then sleep again
      self.toggle_seconds_event.set()
    item_show_seconds.connect('toggled', toggle_seconds)
    menu.append(item_show_seconds)
    item_quit = Gtk.MenuItem('Quit')
    def quit(menu_item):
      if sys.version_info < (3, 0):
        os.kill(os.getpid(), signal.SIGINT)
      else:
        Gtk.main_quit()
    item_quit.connect('activate', quit)
    menu.append(item_quit)
    menu.show_all()
    def show_menu(eventbox, event, menu=menu):
      if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
        menu.popup(None, None, None, None, event.button, event.time)
    eventbox.connect('button-press-event', show_menu)

  # Update the UI (thread-safe)
  def update_ui(self):
    GLib.idle_add(self.gtk_update_ui)

  # Update the UI (within the GTK main thread ; not thread-safe)
  def gtk_update_ui(self):
    fmt = self.prefix
    if self.show_date: fmt += self.date_format
    fmt += self.time_format
    if self.show_seconds: fmt += self.seconds_format
    fmt += self.suffix

    # Update events should fire as close as possible to the second or minute boundary, but if they
    # fire early, the previous time will incorrectly be displayed until the next update.  Fudge the
    # time to make sure the display is incremented even if the event fires slightly early.
    now = datetime.datetime.now() + self.time_fudge

    self.tray_label.set_text(now.strftime(fmt))

    # Return false to unregister this method as a GLib idle handler
    return False

  def start_update_thread(self):
    def run_in_thread(self=self):
      while True:
        fired_update = datetime.datetime.utcnow()
        self.update_ui()
        now = datetime.datetime.utcnow()
        if self.show_seconds:
          time_to_next_update = 1 - now.microsecond/1000000.0
          if (1000000.0 - fired_update.microsecond) < self.time_fudge.microseconds:
            time_to_next_update += 1
        else:
          time_to_next_update = 60 - now.second - now.microsecond/1000000.0
          if time_to_next_update < 1 and (1000000.0 - fired_update.microseconds) < self.time_fudge.microseconds:
            time_to_next_update += 60
        if self.toggle_seconds_event.wait(time_to_next_update):
          self.toggle_seconds_event.clear()
    thread = threading.Thread(target=run_in_thread)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
  TimeApp()

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
