# GTK+ 3 Tray Icon Library

I generally prefer informative textual System Tray (Task Bar / Notification Area) apps over less-informative graphical ones.  The best way to write such apps seems to be to use a library that supports the freedesktop.org System Tray Protocol Specification.  This protocol is rather flexible, and apps using this protocol are supported by nearly every window manager.

Unfortunately, while GTK+ (StatusIcon) and QT (QSystemTrayIcon) both support this protocol, they both impose artificial size restrictions on icons (icons must be square and/or a hard-coded size, for compatibility with Windows) that prevent rendering long plain text strings.  To render plain text, both frameworks steer you toward Gnome/KDE-specific libraries for writing panel applets, but these libraries are not compatible with other window managers.  libappindicator is an alternative option that does support plain text strings, however it uses Gnome/KDE-specific panel applets to render plain text and falls back to using a GTK+ StatusIcon (with no text) if the libappindicator panel applet is not running, so this doesn't really help if support for window managers other than Gnome and KDE is needed.

Luckily, GTK+ internally implements a generic freedesktop.org System Tray API that does support rendering plain text, although this API is not exposed.  This library simply extracts that implementation from GTK+ and exposes it for use by applications.

The \*.orig files are copied verbatim from GTK+ 3.10.8.  The files without .orig are modified to build outside the GTK+ source tree and to avoid GIR naming conflicts with the normal GTK+ libraries.

## Installation

```
sudo apt-get install libgirepository1.0-dev gobject-introspection libgtk-3-dev
sudo make install
```

## License

All files in this directory are released under the same license as GTK+:

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see [http://www.gnu.org/licenses/](http://www.gnu.org/licenses/).
