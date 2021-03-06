# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Oceny
                                 A QGIS plugin
 Narzędzie do wykonywania ocen oddziaływania inwestycji na przyrodę.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-04-16
        copyright            : (C) 2021 by Kamil Drejer
        email                : klamot@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load Oceny class from file Oceny.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .oceny import Oceny
    return Oceny(iface)
