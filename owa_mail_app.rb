#!/usr/bin/env ruby

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
# gem install gir_ffi-gtk
# gem install viewpoint
#
# Configuration:
# In the same directory as this script, create a file called 'owa_mail_config.rb' and put something
# like the following in it:
# $config = {
#   check_interval: 30,  # minutes
#   display_prefix: 'M:',
#   display_suffix: ' ',
#   accounts: {
#     'Ex1' => {
#       url: 'https://mail.example.com/ews/Exchange.asmx',
#       username: 'user',
#       password: 'pass'
#       folders: ['Inbox', 'Mailing Lists']
#     },
#     'Ex2' => {
#       url: 'https://mail.example2.com/ews/Exchange.asmx',
#       username: 'user2',
#       password: 'pass2'
#       folders: ['Inbox']
#     }
#   }
# }
#



$default_config = {
  check_interval: 30,  # minutes
  display_prefix: 'M:',
  display_suffix: ' '
}

if __FILE__ == $PROGRAM_NAME
  $LOAD_PATH.unshift(File.dirname(File.expand_path(__FILE__)))
  require 'owa_mail_config'
end

require 'viewpoint'
include Viewpoint::EWS

require 'gir_ffi-gtk3'
GirFFI.setup :Gtkti

# WARNING: Uncaught Exceptions in callbacks are silently ignored.  Therefore, it is a good idea to
# wrap all callbacks in a begin/rescue block that catches all Exceptions (not just StandardError),
# and at least prints a message to the console.  (See
# https://github.com/mvz/gir_ffi/wiki/Exceptions-in-callbacks and
# http://stackoverflow.com/questions/10048173/why-is-it-bad-style-to-rescue-exception-e-in-ruby )

class OwaMailApp

  def initialize(config)
    raise 'Config must be defined before starting' unless config
    raise 'Accounts must be configured before starting' unless config[:accounts]
    @accounts = config[:accounts]
    @config = $default_config.merge(config)

    # Build the EWSClient objects for each account
    # No network traffic is generated at this point
    @accounts.each_value do |account|
      account[:ews] = Viewpoint::EWSClient.new(account[:url], account[:username], account[:password])
    end

    build_ui
    start_check_thread
  end

  def build_ui
    @tray = tray = Gtkti::TrayIcon.new('OwaMailApp')
    eventbox = Gtk::EventBox.new
    tray.add(eventbox)
    @tray_label = tray_label = Gtk::Label.new(@config[:display_prefix]+@config[:display_suffix])
    eventbox.add(tray_label)
    tray.show_all()

    tooltip_status = ''
    @accounts.each_key do |account_name|
      tooltip_status << ' ' unless tooltip_status.empty?
      tooltip_status << "#{account_name}:?"
    end
    tray.set_tooltip_text(tooltip_status)

    menu = Gtk::Menu.new
      item_now = Gtk::MenuItem.new_with_label('Check Now')
      GObject.signal_connect(item_now, 'activate') do |menu_item, user_data|
        Thread.new { check_accounts }
      end
      menu.append(item_now)
      item_status = Gtk::MenuItem.new_with_label('Show Status')
      GObject.signal_connect(item_status, 'activate') do |menu_item, user_data|
        begin
          message = "OWA Mail Status:"
          @accounts.each do |account_name, account|
            message << "\n#{account_name}: #{account.has_key?(:unread) ? account[:unread] : '?'}"
            message << "\n  Last successful check at #{account[:last_success]}" if account.has_key? :last_success
            if account.has_key? :exception and not account[:exception].nil?
              e = account[:exception]
              message << "\n  Exception at #{account[:last_attempt]}: #{e.class}: #{e.message}"
            end
          end
          show_big_text('OWA Mail Status', message)
        rescue Exception => e
          puts "#{e.class}: #{e.message}"
        end
      end
      menu.append(item_status)
      item_quit = Gtk::MenuItem.new_with_label('Quit')
      GObject.signal_connect(item_quit, 'activate') do |menu_item, user_data|
        Gtk.main_quit
      end
      menu.append(item_quit)
    menu.show_all
    GObject.signal_connect(eventbox, 'button-press-event') do |eventbox, event, user_data|
      if event.type == :button_press and event.button == 3
        menu.popup(nil, nil, nil, nil, event.button, event.time)
      end
    end
  end

  # Update the UI (thread-safe)
  def update_ui(account_name, unread_messages, exception)
    time = Time.now
    run_in_gtk = Proc.new do
      gtk_update_ui(time, account_name, unread_messages, exception)
    end
    GLib.idle_add(GLib::PRIORITY_DEFAULT_IDLE, run_in_gtk, nil, nil)
  end

  # This is used to filter Exceptions when we're offline
  @@exceptions_to_ignore = [SocketError, HTTPClient::ReceiveTimeoutError]

  # Update the UI (within the GTK main thread ; not thread-safe)
  def gtk_update_ui(time, account_name, unread_messages, exception)
    begin

      # Open a notification window for unexpected Exceptions
      unless exception.nil? or @@exceptions_to_ignore.include?(exception.class)
        show_notification('OWA Mail Error', "Exception checking #{account_name} mail at #{time}: #{exception.class}: #{exception.message}")
      end

      # Open a notification window if there were no unread messages but there are some now
      if unread_messages > 0 and (not @accounts[account_name].has_key? :unread or @accounts[account_name][:unread] == 0)
        show_notification('OWA Mail Notice', "New mail at #{account_name}")
      end

      # Save state for the "Show Status" function
      @accounts[account_name][:last_attempt] = time
      @accounts[account_name][:exception] = exception
      if exception.nil?
        @accounts[account_name][:last_success] = time
        @accounts[account_name][:unread] = unread_messages
      end

      # Update display and tooltip
      # Display is only visible if we have messages or an unexpected Exception
      # Tooltip shows ? if there is any Exception (including expected Exceptions)
      display_status = @config[:display_prefix].clone
      tooltip_status = ''
      @accounts.each do |account_name, account|
        unless exception.nil? or @@exceptions_to_ignore.include?(exception.class)
          display_status << ' ' unless display_status.empty?
          display_status << "#{account_name}:#{account.has_key?(:unread) ? account[:unread] : ''}?"
        else
          if account.has_key? :unread and account[:unread] > 0
            display_status << ' ' unless display_status.empty?
            display_status << "#{account_name}:#{account[:unread]}"
          end
        end
        tooltip_status << ' ' unless tooltip_status.empty?
        tooltip_status << "#{account_name}:#{account.has_key?(:unread) ? account[:unread] : ''}#{exception.nil? ? '' : '?'}"
      end
      display_status << @config[:display_suffix]
      @tray_label.set_text(display_status)
      @tray.set_tooltip_text(tooltip_status)

    rescue Exception => e
      show_notification('OWA Mail Error', "Error in the owa_mail_app.rb script: #{e.class}: #{e.message}")
    end

    # Return false to unregister this method as a GLib idle handler
    false
  end

  def show_notification(title, message)
    dialog = Gtk::Dialog.new
    dialog.set_title(title)
    label = Gtk::Label.new(message)
    dialog.get_content_area.add(label)
    dialog.add_button('_OK', -1)  # GTK_RESPONSE_NONE == -1
    GObject.signal_connect(dialog, 'response') do |dialog, response_id, user_data|
      dialog.destroy
    end
    dialog.show_all
  end

  def show_big_text(title, text)
    window = Gtk::Window.new :toplevel
    window.set_title(title)
    window.set_default_size(500, 150)
    scroll = Gtk::ScrolledWindow.new(nil, nil)
    window.add(scroll)
    textarea = Gtk::TextView.new
    textarea.get_buffer.insert_at_cursor(text, text.length)
    textarea.set_editable(false)
    textarea.set_cursor_visible(false)
    scroll.add(textarea)
    window.show_all
  end

  def start_check_thread
    # This thread automatically dies after Gtk.main_quit is called
    Thread.new do
      check_interval_sec = @config[:check_interval] * 60
      while true do
        check_accounts

        puts "[#{Time.now}] Sleeping #{check_interval_sec}s"
        sleep(check_interval_sec)
      end
    end
  end

  def check_accounts
    @accounts.each do |account_name, account|
      begin
        puts "[#{Time.now}] Checking for unread messages at #{account_name}"
        count = 0
        account[:folders].each do |folder|
          # Server is actually contacted on get_folder_by_name() calls.  It is not contacted again
          # on folder.unread_count() calls, so do not cache the folder object.
          count += account[:ews].get_folder_by_name(folder).unread_count
        end
        puts "[#{Time.now}] Successful check at #{account_name}: #{count} unread"
        update_ui(account_name, count, nil)
      rescue => e
        puts "[#{Time.now}] Exception checking #{account_name}: #{e.class}: #{e.message}"
        update_ui(account_name, -1, e)
      end
    end
  end

end

if __FILE__ == $PROGRAM_NAME
  Gtk.init

  OwaMailApp.new($config)

  trap('SIGINT') { Gtk.main_quit }
  Gtk.main
end
