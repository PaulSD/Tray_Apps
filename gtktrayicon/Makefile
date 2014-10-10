#
# Copyright 2014 Paul Donohue <Tray_Apps@PaulSD.com>
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU
# Lesser General Public License as published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along with this program.
# If not, see <http://www.gnu.org/licenses/>.
#

NAMESPACE=Gtkti
NSVERSION=3.0
LIBNAME=gtk-ti
TI_SOURCES=gtktrayicon-x11.c gtktrayicon.h
TI_OBJECT=gtktrayicon.lo
SOURCES=$(TI_SOURCES)
OBJECTS=$(TI_OBJECT)

CC=gcc
C_INCLUDES=`pkg-config --cflags gobject-2.0 gtk+-3.0`
CFLAGS=$(C_INCLUDES) -g
LIBS=`pkg-config --libs gobject-2.0 gtk+-3.0`
LIBDIR=/usr/local/lib
GIR_FILE=$(NAMESPACE)-$(NSVERSION).gir
TYPELIB_FILE=$(NAMESPACE)-$(NSVERSION).typelib
GIR_DIR=/usr/lib/girepository-1.0

all: lib$(LIBNAME).la $(TYPELIB_FILE)

lib$(LIBNAME).la: $(OBJECTS)
	libtool link $(CC) $(LIBS) -rpath $(LIBDIR) $(OBJECTS) -o $@

$(TI_OBJECT): $(TI_SOURCES)
	libtool compile $(CC) $(CFLAGS) -c $< -o $@

$(TYPELIB_FILE): $(GIR_FILE)
	g-ir-compiler $(GIR_FILE) --output=$(TYPELIB_FILE)

$(GIR_FILE): $(SOURCES)
	libtool exec g-ir-scanner $^ --library=$(LIBNAME) $(C_INCLUDES) --include=GObject-2.0 --include=Gtk-3.0 --namespace=$(NAMESPACE) --nsversion=$(NSVERSION) --output=$@

install: all
	libtool install install -c lib$(LIBNAME).la $(LIBDIR)/lib$(LIBNAME).la
	install -d $(GIR_DIR)
	install --mode=644 $(TYPELIB_FILE) $(GIR_DIR)/$(TYPELIB_FILE)
	ldconfig

clean:
	-rm -f *.o *.lo *.la *.gir *.typelib
	-rm -rf .libs
