#!/usr/bin/env python

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
#  gir1.2-gtk-3.0 python-pydbus upower
#



import gi
gi.require_version('Gtkti', '3.0')
from gi.repository import Gtkti, Gtk, Gdk, GLib
import signal, sys, os
import threading
from pydbus import SystemBus

# For troubleshooting purposes, `upower --dump` should print the same data as DBus Properties, and
# `dbus-monitor --system` should show the DBus Signals.

# UPower polls the system at relatively infrequent intervals.  (Dynamic intervals, typically around
# 2 minutes.)  If updates are needed more frequently than that, try calling battery.Refresh()
# periodically.  If that doesn't help, or you can parse the output of `acpi -b` instead of using
# UPower via DBus.

# WARNING: Variable scope for Python inline functions and lambdas does not work like other
# languages!  To ensure that definition-scope variables are passed into the function/lambda's scope
# as expected, explicitly add 'var=var' (optional/defaulted) parameters to the end of the function/
# lambda's parameter list.

class BatteryApp:

  def __init__(self):
    self.prefix = 'B:'
    self.separator = '/'
    self.suffix = ' '
    self.tooltip_heading = 'Battery Status:\n'

    self.low_battery_alarm_threshold = 5
    self.low_battery_alarm_visible = False

    self.build_ui()

    self.dbus = SystemBus()
    self.upower = self.dbus.get('.UPower', '/org/freedesktop/UPower')
    self.battery_subscriptions = []
    self.upower.DeviceAdded.connect(lambda name, vals, a: self.get_upower_batteries())
    self.upower.DeviceRemoved.connect(lambda name, vals, a: self.get_upower_batteries())
    self.get_upower_batteries()
    self.start_signal_thread()

  def build_ui(self):
    self.tray = tray = Gtkti.TrayIcon()
    self.eventbox = eventbox = Gtk.EventBox()
    eventbox.set_tooltip_text(self.tooltip_heading+'Unknown')
    tray.add(eventbox)
    self.tray_label = tray_label = Gtk.Label(self.prefix+'?'+self.suffix)
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

  # Update the UI (thread-safe)
  def update_ui(self):
    GLib.idle_add(self.gtk_update_ui)

  # Update the UI (within the GTK main thread ; not thread-safe)
  def gtk_update_ui(self):
    display_str = ''
    tooltip_str = ''
    max_percentage = 0
    for battery in self.upower_batteries:
      if display_str:
        display_str += '/'
        tooltip_str += '\n'
      tooltip_str += battery.NativePath+': '
      state = battery.State
      if state == 1 or state == 5:
        tooltip_str += 'Charging ('+str(battery.Percentage)+'%)'
        display_str += str(int(battery.Percentage))+'+'
      elif state == 2 or state == 3 or state == 6:
        tooltip_str += 'Discharging ('+str(battery.Percentage)+'%)'
        display_str += str(int(battery.Percentage))+'-'
      elif state == 4:
        tooltip_str += 'Full ('+str(battery.Percentage)+'%)'
        display_str += str(int(battery.Percentage))
      else:
        tooltip_str += 'Unknown ('+str(battery.Percentage)+'%)'
        display_str += '?'
      if battery.TimeToFull:
        m, s = divmod(battery.TimeToFull, 60)
        h, m = divmod(m, 60)
        tooltip_str += ', Remaining Charge Time: '+('%dh %02dm %02ds' % (h, m, s))
      if battery.TimeToEmpty:
        m, s = divmod(battery.TimeToEmpty, 60)
        h, m = divmod(m, 60)
        tooltip_str += ', Remaining Discharge Time: '+('%dh %02dm %02ds' % (h, m, s))
      if battery.Percentage > max_percentage:
        max_percentage = battery.Percentage
    self.tray_label.set_text(self.prefix+display_str+self.suffix)
    self.eventbox.set_tooltip_text(self.tooltip_heading+tooltip_str)
    if max_percentage < self.low_battery_alarm_threshold and not self.low_battery_alarm_visible:
      self.low_battery_alarm_visible = True
      dialog = Gtk.Dialog()
      dialog.set_title('Warning')
      dialog.set_default_size(250, 100)
      label = Gtk.Label('Low Battery')
      dialog.get_content_area().add(label)
      dialog.add_button('_Close', -1)  # GTK_RESPONSE_NONE == -1
      def close_pressed(dialog, response_id, self=self):
        self.low_battery_alarm_visible = False
        dialog.destroy()
      dialog.connect('response', close_pressed)
      dialog.show_all()

    # Return false to unregister this method as a GLib idle handler
    return False

  def get_upower_batteries(self):
    paths = self.upower.EnumerateDevices()
    devices = map(lambda p: self.dbus.get('.UPower', p), paths)
    batteries = filter(lambda d: d.Type == 2, devices)
    for s in self.battery_subscriptions:
      s.disconnect()
    self.battery_subscriptions = []
    for battery in batteries:
      s = battery.PropertiesChanged.connect(lambda name, vals, a: self.update_ui())
      self.battery_subscriptions.append(s)
    self.upower_batteries = batteries
    self.update_ui()

  def start_signal_thread(self):
    thread = threading.Thread(target=GLib.MainLoop().run)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
  BatteryApp()

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
