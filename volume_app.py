#!/usr/bin/env python3

#
# Copyright 2016 Paul Donohue <Tray_Apps@PaulSD.com>
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
# git clone https://github.com/larsimmisch/pyalsaaudio.git
# cd pyalsaaudio ; python3 setup.py build ; sudo python3 setup.py install
# (See https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=613091 )
#
# TODO: Switch to https://pypi.org/project/pulsectl/

# Use `None` for a transparent background.
# In Ubuntu 18.04 (trayer 1.1.7, gtk 3.22.30), transparency worked fine.  However, in Ubuntu 20.04
# (trayer 1.1.8, gtk 3.24.20), transparency does not work.  Specifically, the visual area of the
# icon is never cleared, so at startup any existing icon that was moved to make space for the new
# icon will remain visible in the new icon's background, and any updates to the icon text will draw
# over the previous text.  I'm not sure what is causing it, but a simple fix is to set a background
# color instead of using a transparent background.
#background_color = None
background_color = '#9A9A9A'



import gi
gi.require_version('Gtkti', '3.0')
from gi.repository import Gtkti, Gtk, Gdk, GLib
import signal, sys, os
import threading
import alsaaudio  # See /usr/share/doc/python-alsaaudio/examples/mixertest.py
import select

# WARNING: Variable scope for Python inline functions and lambdas does not work like other
# languages!  To ensure that definition-scope variables are passed into the function/lambda's scope
# as expected, explicitly add 'var=var' (optional/defaulted) parameters to the end of the function/
# lambda's parameter list.

class VolumeApp:

  def __init__(self):
    self.prefix = 'V:'
    self.suffix = ' '

    alsa_device = 'default'
    alsa_control = 'Master'
    self.alsa_ctl = alsaaudio.Mixer(control=alsa_control, device=alsa_device)

    self.scroll_step = 4  # Amount to change volume for each scroll event

    self.build_ui()
    self.gtk_update_ui()
    self.start_monitor_thread()

  def build_ui(self):
    self.tray = tray = Gtkti.TrayIcon()
    eventbox = Gtk.EventBox()
    if background_color:
      css = Gtk.CssProvider()
      css.load_from_data(('* { background-color: '+background_color+'; }').encode())
      Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    tray.add(eventbox)
    self.tray_label = tray_label = Gtk.Label(label=self.prefix+self.suffix)
    eventbox.add(tray_label)
    tray.show_all()

    menu = Gtk.Menu()
    item_quit = Gtk.MenuItem(label='Quit')
    def quit(menu_item):
      if sys.version_info < (3, 0):
        os.kill(os.getpid(), signal.SIGINT)
      else:
        Gtk.main_quit()
    item_quit.connect('activate', quit)
    menu.append(item_quit)
    menu.show_all()
    def show_menu(event, menu=menu):
      menu.popup(None, None, None, None, event.button, event.time)

    window = Gtk.Window(type=Gtk.WindowType.POPUP)
    box = Gtk.VBox()
    window.add(box)
    slider = Gtk.VScale()
    slider.set_size_request(0,200)
    slider.set_range(0,100)
    slider.set_inverted(True)
    slider.set_draw_value(False)
    def slider_changed(slider):
      self.alsa_ctl.setvolume(int(slider.get_value()))
      self.gtk_update_ui(True)
    slider.connect('value-changed', slider_changed)
    box.add(slider)
    button = Gtk.Button.new_with_label('M')
    def button_clicked(button):
      if self.alsa_ctl.getmute()[0]:
        self.alsa_ctl.setmute(0)
        button.set_label('m')
      else:
        self.alsa_ctl.setmute(1)
        button.set_label('M')
      self.gtk_update_ui(True)
    button.connect('clicked', button_clicked)
    box.add(button)
    self.window_visible = False
    def update_window(self=self, slider=slider, button=button):
      if self.window_visible:
        slider.set_value(self.alsa_ctl.getvolume()[0])
        if self.alsa_ctl.getmute()[0]:
          button.set_label('M')
        else:
          button.set_label('m')
    self.update_window = update_window
    # Need to render the window briefly so that window.get_size() will be accurate
    window.show_all()
    window.hide()
    def toggle_window(self=self, window=window):
      if self.window_visible:
        window.hide()
        self.window_visible = False
      else:
        tray_window = self.tray.get_window()
        tray_pos = tray_window.get_origin()
        tray_x = tray_pos[1]
        tray_y = tray_pos[2]
        tray_monitor = tray_window.get_display().get_monitor_at_window(tray_window)
        screen_height = tray_monitor.get_geometry().height
        if tray_y < (screen_height / 2):
          # Put window below tray
          tray_height = self.tray.get_size()[1]
          window.move(tray_x, tray_y+tray_height)
        else:
          # Put window above tray
          window_height = window.get_size()[1]
          window.move(tray_x, tray_y-window_height)
        self.window_visible = True
        self.update_window()
        window.show_all()

    def button_pressed(eventbox, event, show_menu=show_menu, toggle_window=toggle_window):
      if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
        show_menu(event)
      elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
        toggle_window()
    eventbox.connect('button-press-event', button_pressed)

    def scrolled(eventbox, event):
      if event.direction == Gdk.ScrollDirection.UP:
        if self.alsa_ctl.getmute()[0]:
          self.alsa_ctl.setmute(0)
          self.alsa_ctl.setvolume(self.scroll_step)
        else:
          cur_vol = self.alsa_ctl.getvolume()[0]
          if cur_vol > (100-self.scroll_step):
            self.alsa_ctl.setvolume(100)
          else:
            self.alsa_ctl.setvolume(cur_vol+self.scroll_step)
      elif event.direction == Gdk.ScrollDirection.DOWN:
        cur_vol = self.alsa_ctl.getvolume()[0]
        if cur_vol < self.scroll_step:
          self.alsa_ctl.setvolume(0)
          self.alsa_ctl.setmute(1)
        else:
          self.alsa_ctl.setvolume(cur_vol-self.scroll_step)
      self.gtk_update_ui()
    eventbox.connect('scroll-event', scrolled)

  # Update the UI (thread-safe)
  def update_ui(self, window_changed=False):
    GLib.idle_add(self.gtk_update_ui, window_changed)

  # Update the UI (within the GTK main thread ; not thread-safe)
  def gtk_update_ui(self, window_changed=False):
    if self.alsa_ctl.getmute()[0] == 1:
      self.tray_label.set_text(self.prefix+'M'+self.suffix)
    else:
      volume = self.alsa_ctl.getvolume()[0]
      self.tray_label.set_text(self.prefix+str(volume)+self.suffix)

    if not window_changed:
      self.update_window()

    # Return false to unregister this method as a GLib idle handler
    return False

  def start_monitor_thread(self):
    def run_in_thread(self=self):
      alsa_poll = select.poll()
      alsa_poll.register(*(self.alsa_ctl.polldescriptors()[0]))
      while True:
        # Wait for an event
        # We don't get events when we make changes,
        # only when other processes make changes
        alsa_poll.poll()
        self.alsa_ctl.handleevents()
        self.update_ui()
    thread = threading.Thread(target=run_in_thread)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
  VolumeApp()

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
