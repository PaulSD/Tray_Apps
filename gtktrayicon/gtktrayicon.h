/* gtktrayicon.h
 * Copyright (C) 2002 Anders Carlsson <andersca@gnu.org>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library. If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __GTKTI_TRAY_ICON_H__
#define __GTKTI_TRAY_ICON_H__

//#include "gtkplug.h"
#include <gtk/gtkx.h>

G_BEGIN_DECLS

#define GTKTI_TYPE_TRAY_ICON		(gtkti_tray_icon_get_type ())
#define GTKTI_TRAY_ICON(obj)		(G_TYPE_CHECK_INSTANCE_CAST ((obj), GTKTI_TYPE_TRAY_ICON, GtktiTrayIcon))
#define GTKTI_TRAY_ICON_CLASS(klass)	(G_TYPE_CHECK_CLASS_CAST ((klass), GTKTI_TYPE_TRAY_ICON, GtktiTrayIconClass))
#define GTKTI_IS_TRAY_ICON(obj)		(G_TYPE_CHECK_INSTANCE_TYPE ((obj), GTKTI_TYPE_TRAY_ICON))
#define GTKTI_IS_TRAY_ICON_CLASS(klass)	(G_TYPE_CHECK_CLASS_TYPE ((klass), GTKTI_TYPE_TRAY_ICON))
#define GTKTI_TRAY_ICON_GET_CLASS(obj)	(G_TYPE_INSTANCE_GET_CLASS ((obj), GTKTI_TYPE_TRAY_ICON, GtktiTrayIconClass))
	
typedef struct _GtktiTrayIcon        GtktiTrayIcon;
typedef struct _GtktiTrayIconPrivate GtktiTrayIconPrivate;
typedef struct _GtktiTrayIconClass   GtktiTrayIconClass;

struct _GtktiTrayIcon
{
  GtkPlug parent_instance;

  GtktiTrayIconPrivate *priv;
};

struct _GtktiTrayIconClass
{
  GtkPlugClass parent_class;

  /* Padding for future expansion */
  void (*_gtk_reserved1);
  void (*_gtk_reserved2);
  void (*_gtk_reserved3);
  void (*_gtk_reserved4);
};

//GDK_AVAILABLE_IN_ALL
GType          gtkti_tray_icon_get_type         (void) G_GNUC_CONST;

GtktiTrayIcon   *gtkti_tray_icon_new_for_screen  (GdkScreen   *screen,
					       const gchar *name);

GtktiTrayIcon   *gtkti_tray_icon_new             (const gchar *name);

guint          gtkti_tray_icon_send_message    (GtktiTrayIcon *icon,
					       gint         timeout,
					       const gchar *message,
					       gint         len);
void           gtkti_tray_icon_cancel_message  (GtktiTrayIcon *icon,
					       guint        id);

GtkOrientation gtkti_tray_icon_get_orientation (GtktiTrayIcon *icon);
gint           gtkti_tray_icon_get_padding     (GtktiTrayIcon *icon);
gint           gtkti_tray_icon_get_icon_size   (GtktiTrayIcon *icon);

G_END_DECLS

#endif /* __GTKTI_TRAY_ICON_H__ */
