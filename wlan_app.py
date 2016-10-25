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
# sudo apt-get install libgirepository1.0-dev gobject-introspection gir1.2-gtk-3.0
# sudo apt-get install python-pip ; sudo pip install wpa_supplicant
#
# sudo usermod -a -G netdev <user>
# sudo vi /etc/dbus-1/system.d/wpa_supplicant.conf
#  Copy the '<allow own=.../>' lines from '<policy user="root">' to '<policy user="netdev">'
# sudo service dbus reload
# mkdir -p /etc/systemd/system/wpa_supplicant.service.d/ ; echo -e '[Service]\nExecStart=' | \
#  sudo tee /etc/systemd/system/wpa_supplicant.service.d/no_dbus_autostart.conf
# sudo systemctl daemon-reload
# sudo vi /etc/wpa_supplicant/functions.sh
#  Prepend '-u ' to WPA_SUP_OPTIONS in init_wpa_supplicant()
#



import gi
gi.require_version('Gtkti', '3.0')
from gi.repository import Gtkti, Gtk, Gdk, GLib
import signal, sys, os
import threading
from pydbus import SystemBus
from twisted.internet.selectreactor import SelectReactor
# See https://w1.fi/wpa_supplicant/devel/dbus.html
# and https://pypi.python.org/pypi/wpa_supplicant/
from wpa_supplicant.core import BUS_NAME, WpaSupplicantDriver, WpaSupplicant, Interface
import time

# Ignore log messages from wpa_supplicant.core
# (It spits out some log messages for expected exceptions)
import logging
logger = logging.getLogger('wpasupplicant')
logger.addHandler(logging.NullHandler)

# Default WpaSupplicant.get_interfaces() returns D-Bus paths, which is useless since we have no way
# to retrieve interfaces using those paths.  Monkey patch it to return Interface objects.
def get_interface_for_path(self, interface_path):
    interface = self._interfaces_cache.get(interface_path, None)
    if interface is not None:
        return interface
    else:
        interface = Interface(interface_path, self._conn, self._reactor)
        self._interfaces_cache[interface_path] = interface
        return interface
def get_interfaces(self):
    return map(lambda p: get_interface_for_path(self, p), self.get('Interfaces'))
WpaSupplicant.get_interfaces = get_interfaces

# WARNING: Variable scope for Python inline functions and lambdas does not work like other
# languages!  To ensure that definition-scope variables are passed into the function/lambda's scope
# as expected, explicitly add 'var=var' (optional/defaulted) parameters to the end of the function/
# lambda's parameter list.

class WlanApp:

  def __init__(self):
    self.prefix = 'W:'
    self.suffix = ' '
    self.tooltip_heading = 'Wireless LAN Status:\n'

    self.iface = None  # Set to interface name to override interface selection

    self.build_ui()

    # Needed by wpa_supplicant.core
    self.reactor = SelectReactor()
    thread = threading.Thread(target=self.reactor.run, kwargs={'installSignalHandlers': 0})
    thread.daemon = True
    thread.start()
    time.sleep(0.1)  # let reactor start

    self.wpasup = None
    self.wpasup_running = False
    self.wlan = None
    self.wlan_signal = None

    # Monitor the availability of wpa_supplicant via DBus
    self.dbus = SystemBus()
    # watch_name() fires an event as soon as GLib.MainLoop() starts, so we don't need to explicitly
    # call get_wpa_supplicant() here
    self.dbus.watch_name(BUS_NAME, 0, self.get_wpa_supplicant, self.get_wpa_supplicant)
    self.start_watch_thread()

  def build_ui(self):
    self.tray = tray = Gtkti.TrayIcon()
    self.eventbox = eventbox = Gtk.EventBox()
    eventbox.set_tooltip_text(self.tooltip_heading+'WPA Supplicant not running')
    tray.add(eventbox)
    self.tray_label = tray_label = Gtk.Label(self.prefix+'_'+self.suffix)
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
    if not self.wpasup_running:
      display_str = '_'
      tooltip_str = 'WLAN Interface is down (WPA Supplicant is not running)'
    elif not self.wlan:
      display_str = '_'
      tooltip_str = 'WLAN Interface not found via WPA Supplicant'
    else:
      try:
        ifname = self.wlan.get_ifname()
        tooltip_str = ifname
        state = self.wlan.get_state()
        tooltip_str += ' '+state.title()
        if state == 'interface_disabled':
          display_str = '_'
        elif state == 'disconnected' or state == 'inactive':
          display_str = '-'
        elif state == 'scanning':
          display_str = '?'
        elif state == 'authenticating' or state == 'associating' or state == 'associated' or \
             state == '4way_handshake' or state == 'group_handshake':
          display_str = '@'
        elif state == 'completed':
          display_str = ''
          tooltip_str += ' Connected'
        elif state == 'unknown':
          display_str = '!'
        else:
          display_str = '!'
          print >> sys.stderr, 'Unknown wpa_supplicant state: '+state+' to '+self.wlan.get_current_bss().get_ssid()
        bss = self.wlan.get_current_bss()
        if bss:
          display_str += bss.get_ssid()
          tooltip_str += ' to '+bss.get_ssid()
      except:
        # This is expected if another thread sets self.wlan to None while the above code is
        # executing, or if wpa_supplicant shuts down while the above code is executing.  In either
        # case, another UI update should happen momentarily.
        display_str = '!'
        tooltip_str = 'Unknown (Exception Thrown)'
    self.tray_label.set_text(self.prefix+display_str+self.suffix)
    self.eventbox.set_tooltip_text(self.tooltip_heading+tooltip_str)

    # Return false to unregister this method as a GLib idle handler
    return False

  def select_wlan_interface(self, interfaces):
    if self.wlan_signal:
      wlan_signal = self.wlan_signal  # To avoid race conditions
      self.wlan_signal = None
      wlan_signal.cancel()
    self.wlan = None
    if interfaces:
      if self.iface:
        for interface in interfaces:
          if interface.get_ifname() == self.iface:
            self.wlan = interface
            break
      else:
        self.wlan = interfaces[0]
      self.wlan_signal = \
       self.wlan.register_signal('PropertiesChanged', lambda args: self.update_ui())
    self.update_ui()

  def scan_wpa_interfaces(self, args=None):
    self.wpa_interfaces = self.wpasup.get_interfaces()
    self.select_wlan_interface(self.wpa_interfaces)

  def wlan_interface_removed(self, path):
    # wpa_supplicant sends InterfaceRemoved just before shutting down, and get_interfaces() may
    # throw an exception if it is called while wpa_supplicant is shutting down.  So, instead of
    # calling scan_wpa_interfaces on InterfaceRemoved, it is probably better to keep a cache of the
    # list of interfaces and just delete the relevant interface from the cache.
    self.wpa_interfaces[:] = [i for i in self.wpa_interfaces if not i.get_path() == path]
    self.select_wlan_interface(self.wpa_interfaces)

  def get_wpa_supplicant(self, dbus_name_owner = None):
    if dbus_name_owner:
      self.wpasup_running = True
      if not self.wpasup:
        # Connect to wpa_supplicant
        self.wpasup = WpaSupplicantDriver(self.reactor).connect()
        self.wpasup.register_signal('InterfaceAdded', self.scan_wpa_interfaces)
        self.wpasup.register_signal('InterfaceRemoved', self.wlan_interface_removed)
        self.scan_wpa_interfaces()
      else:
        # If we don't do anything when wpa_supplicant vanishes, then our signals seem to remain
        # registered when wpa_supplicant re-appears.  However, wpa_supplicant doesn't seem to send
        # InterfaceAdded signals when it comes up, so we must explicitly re-scan the interfaces.
        self.scan_wpa_interfaces()
    else:
      self.wpasup_running = False
      self.select_wlan_interface([])

  def start_watch_thread(self):
    thread = threading.Thread(target=GLib.MainLoop().run)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
  WlanApp()

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
