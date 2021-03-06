# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Oceny
                                 A QGIS plugin
 Narzędzie do wykonywania ocen oddziaływania inwestycji na przyrodę.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-04-16
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Kamil Drejer
        email                : klamot@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from PyQt5 import QtCore, QtGui, QtWidgets #works for pyqt5
from qgis.gui import QgsFileWidget

from qgis.core import QgsVectorLayerJoinInfo
from qgis.core import QgsProject
from qgis.core import QgsField
from qgis.core import QgsLayerTreeLayer
from qgis.core import QgsVectorLayer, QgsDataSourceUri
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsCoordinateTransformContext
from qgis.core import QgsVectorFileWriter
from qgis.core import Qgis, QgsSpatialIndex
from qgis.core import (
  QgsGeometry, QgsGeometryCollection,
  QgsPoint,
  QgsPolygon,
  QgsField,
  QgsFields,
  QgsMultiPoint,
  QgsFeature,
  QgsPointXY,
  QgsWkbTypes,
  QgsProject,
  QgsFeatureRequest,
  QgsVectorLayer,
  QgsDistanceArea,
  QgsUnitTypes,
)
from qgis.core import QgsMapLayerProxyModel
from qgis.utils import iface
from PyQt5.QtCore import QVariant
import processing
import re, ntpath, math
from .chainagetool import points_along_line

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .oceny_dialog import OcenyDialog
import os.path


class Oceny:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Oceny_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Oceny')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Oceny', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/oceny/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Oceny'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = OcenyDialog()

        self.dlg.obszar.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.dlg.os.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.dlg.km.setFilters(QgsMapLayerProxyModel.PointLayer)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed


        if result:
            layers_orygin=[]
            licznik_warstw = 0
            licznik_warstw_geom = 0

            if not self.dlg.checkFolder.isChecked():
                licznik_warstw+=1
                licznik_warstw_geom+=1
                layers_orygin.append(self.dlg.layer_proj.currentLayer())
            else:
                layers_orygin_str = QgsFileWidget.splitFilePaths(self.dlg.pliki_list.filePath())
                for laer_orygin_str in layers_orygin_str:
                    filename = ntpath.basename(laer_orygin_str)
                    layer = QgsVectorLayer(laer_orygin_str, filename, "ogr")
                    if layer.isValid() and layer.isSpatial():
                        licznik_warstw+=1
                        if layer.featureCount()>0:
                            licznik_warstw_geom+=1
                            layers_orygin.append(layer)

            if licznik_warstw_geom==0:
                iface.messageBar().pushMessage("Ojej! ", "nie znaleziono żadnej poprawnej warstwy lub warstwy są puste", level=Qgis.Critical)
                pass


            # tempdir = self.dlg.output_path.filePath()
            # print(layers_orygin)

            #------------> zapętlić dla wybranego katalogu z warstwami
            os = self.dlg.os.currentLayer()
            km = self.dlg.km.currentLayer()
            obszar = self.dlg.obszar.currentLayer()

            for layer_orygin in layers_orygin:
                feats = [feat for feat in layer_orygin.getFeatures()]

                uri = QgsDataSourceUri()
                uri.setSrid("2180")
                uri.setWkbType(layer_orygin.wkbType())

                crs = str(layer_orygin.crs().authid())
                crs_system = QgsCoordinateReferenceSystem(crs)
                layer = QgsVectorLayer(QgsWkbTypes.displayString(layer_orygin.wkbType())+"?crs="+crs, layer_orygin.name(), "memory")


                layer_data = layer.dataProvider()
                attr = layer_orygin.dataProvider().fields().toList()
                layer_data.addAttributes(attr)
                layer.updateFields()
                layer_data.addFeatures(feats)

                #czy poligon-------------
                if layer_orygin.wkbType()==QgsWkbTypes.Polygon or layer_orygin.wkbType()==QgsWkbTypes.MultiPolygon:
                    polygon = True
                else:
                    polygon = False
                #------------------------

                # layer = layer_orygin


                field_names = layer.fields().names()
                field_names = [each_string.lower() for each_string in field_names]

                layer.startEditing()

                if 'strona' not in field_names:
                	field = QgsField( 'strona', QVariant.String )
                	layer.addAttribute( field )
                idx_strona = layer.fields().indexFromName('strona')

                if 'km' not in field_names:
                	field = QgsField( 'km', QVariant.String )
                	layer.addAttribute( field )
                idx_km = layer.fields().indexFromName('km')

                if 'dist_od_osi' not in field_names:
                	field = QgsField( 'dist_od_osi', QVariant.String )
                	layer.addAttribute( field )
                idx_dist_od_osi = layer.fields().indexFromName('dist_od_osi')

                if 'dist_od_pasa' not in field_names:
                	field = QgsField( 'dist_od_pasa', QVariant.String )
                	layer.addAttribute( field )
                idx_dist_od_pasa = layer.fields().indexFromName('dist_od_pasa')

                if 'czy_przecina' not in field_names:
                	field = QgsField( 'czy_przecina', QVariant.String )
                	layer.addAttribute( field )
                czy_przecina = layer.fields().indexFromName('czy_przecina')

                if polygon == True:
                    if 'powierzchnia' not in field_names:
                    	field = QgsField( 'powierzchnia', QVariant.Double )
                    	layer.addAttribute( field )
                    powierzchnia = layer.fields().indexFromName('powierzchnia')

                    if 'powierzchnia_przec' not in field_names:
                    	field = QgsField( 'powierzchnia_przec', QVariant.Double )
                    	layer.addAttribute( field )
                    powierzchnia_przec = layer.fields().indexFromName('powierzchnia_przec')

                    if 'procent' not in field_names:
                    	field = QgsField( 'procent', QVariant.Double )
                    	layer.addAttribute( field )
                    procent = layer.fields().indexFromName('procent')

                spIndex = QgsSpatialIndex()
                for feat in km.getFeatures():
                    spIndex.insertFeature(feat)
                #


                # registry = QgsMapLayerRegistry.instance()

                layer_feats = [ feat for feat in layer.getFeatures() ]
                line_feats = [ feat for feat in os.getFeatures() ] #os.getFeatures()

                #
                # layer.startEditing()
                i=0
                for feat in layer_feats:
                    dist_od_osi = 999999999
                    pos = ''
                    # line_feat_multi =
                    # line_feat_multi =QgsGeometryCollection()
                    feat_to_point_geom = QgsGeometry()
                    pt = QgsPoint()
                    print('zaczynam')
                    for line_feat in line_feats:
                        feat_to_point_geom_temp = line_feat.geometry().nearestPoint(feat.geometry()) #najblizszy punkt na osi
                        feat_to_point_geom_feature_temp = feat.geometry().nearestPoint(line_feat.geometry()) #najblizszy punkt na obiekcie
                        dist_od_osi_temp = QgsGeometry.distance(feat_to_point_geom_temp, feat.geometry())
                        if dist_od_osi_temp  < dist_od_osi:
                            feat_to_point_geom = feat_to_point_geom_temp
                            pt = feat_to_point_geom_feature_temp.asPoint()
                            dist_od_osi = dist_od_osi_temp

                            point_in_line = line_feat.geometry().closestSegmentWithContext(pt)[3] #numer 3 pokazuje która strona, numer 1 daje punkt

                            if point_in_line > 0:
                                pos = 'lewa'
                            elif point_in_line < 0:
                                pos = 'prawa'
                            else:
                                pos = 'na osi'

                            if line_feat.geometry().crosses(feat.geometry()) or line_feat.geometry().intersects(feat.geometry()):
                                pos = 'na osi'

                            nearestIds = spIndex.nearestNeighbor(feat_to_point_geom,1) # we need only one neighbour

                    feat[idx_dist_od_osi] = dist_od_osi



                    # az = pt.azimuth(point_in_line)

                    ###################
                    feat[idx_strona] = pos
                    ###################
                    # feat[idx_km] = str(km.getFeature(nearestIds[0]).attributes()[1])
                    ###################


                    obszar_fts = obszar.getFeatures()
                    pos_zakres = 'poza zakresem inwestycji'
                    dist_to_pas = []
                    area = 0

                    przeciecia_fts = QgsVectorLayer(QgsWkbTypes.displayString(QgsWkbTypes.Point)+"?crs="+crs, "przecięcia", "memory")
                    przeciecia_fts.startEditing()
                    fieldid = QgsField("id", QVariant.Int)
                    fieldids = QgsFields()
                    fieldids.append(fieldid)
                    przeciecia_fts.addAttribute(fieldid)



###################################################################
                    intersections_fts = []
                    for obszar_ft in obszar_fts:
                        if obszar_ft.geometry().crosses(feat.geometry()) or obszar_ft.geometry().intersects(feat.geometry()) or obszar_ft.geometry().contains(feat.geometry()):
                            pos_zakres = 'w zakresie inwestycji'
                        dist_to_pas.append(QgsGeometry.distance(obszar_ft.geometry(),feat.geometry()))


                        if polygon == True:
                            przeciecia = feat.geometry().intersection(obszar_ft.geometry())
                            area+= przeciecia.area()

                            # intersections_fts =  QgsVectorLayer(QgsWkbTypes.displayString(QgsWkbTypes.MultiPolygon)+"?crs="+crs, "przecięcia_obszary", "memory")
                            # intersections_fts.addAttribute(fieldid)
                            if not przeciecia.isEmpty():
                                intersections_fts.append(feat.geometry().intersection(obszar_ft.geometry()))
                            # print('intersections_fts ' + str(intersections_fts))

                            feat_ring = feat.geometry().convertToType(1,False)
                            obszar_ring = obszar_ft.geometry().convertToType(1,False)

                            przeciecia_pts = feat_ring.intersection(obszar_ring)
                            # print('przeciecia_pts ' + str(przeciecia_pts))

                            if not (przeciecia_pts.isEmpty()):
                                points = przeciecia_pts.asMultiPoint()
                                for point in points:
                                    i+=1
                                    new_feature = QgsFeature(fieldids)
                                    new_feature.setGeometry(QgsPoint(point))
                                    new_feature.setAttribute(0,i)
                                    # print(new_feature.isValid())
                                    przeciecia_fts.addFeature(new_feature)
                            else:
                                new_feature = QgsFeature(fieldids)
                                new_feature.setGeometry(QgsPoint(feat.geometry().nearestPoint(line_feat.geometry()).asPoint()))
                                new_feature.setAttribute(0,i)
                                # print(new_feature.isValid())
                                przeciecia_fts.addFeature(new_feature)


                    przeciecia_fts.commitChanges()

                    # print('liczba przeciec')
                    # print(przeciecia_fts.featureCount())
                    # print(przeciecia_fts)
                    przeciecia_km = [[0]]
                    przeciecia_km[0].clear()
                    przeciecie_km_str = ''

                    if polygon == True:

                        feat[powierzchnia] = round(feat.geometry().area(),3)
                        feat[powierzchnia_przec] = round(area,3)
                        feat[procent] = round(area*100/feat.geometry().area(),2)

                        if  len(intersections_fts)>0:
                            liczba_obszarow = 0
                            for intersection in intersections_fts:
                                if intersection.isMultipart()==True:
                                    for intersection_geom in intersection.asGeometryCollection():
                                        # line_feat.geometry().nearestPoint(feat.geometry()) #najblizszy punkt na osi
                                        nearestIds = spIndex.nearestNeighbor(przeciecia_ft.geometry(),1)
                                        przeciecia_km.append([])
                                        przeciecia_km[liczba_obszarow].append(km.getFeature(nearestIds[0]).attributes()[1])

                                        km_przeciec_obszaru = []
                                        for intersection_geom_pt in intersection_geom.asPolygon()[0]:
                                            nearestIds = spIndex.nearestNeighbor(intersection_geom_pt,1)
                                            km_przeciec_obszaru.append(km.getFeature(nearestIds[0]).attributes()[1])

                                        przeciecia_km[liczba_obszarow].append(min(km_przeciec_obszaru))
                                        przeciecia_km[liczba_obszarow].append(max(km_przeciec_obszaru))
                                        # przeciecia_km.append(str(str(km.getFeature(nearestIds[0]).attributes()[1])+' '))

                                        for przeciecia_ft in przeciecia_fts.getFeatures():
                                            if intersection_geom.contains(przeciecia_ft.geometry()) or intersection_geom.intersects(przeciecia_ft.geometry()):
                                                # print('zawiera')
                                                nearestIds = spIndex.nearestNeighbor(przeciecia_ft.geometry(),1)
                                                przeciecia_km[liczba_obszarow].append(km.getFeature(nearestIds[0]).attributes()[1])

                                        liczba_obszarow +=1
                                    # print('przeciecia km multi' +str(przeciecia_km))
                                else:
                                    # print('single part')
                                    for przeciecia_ft in przeciecia_fts.getFeatures():
                                        if intersection.contains(przeciecia_ft.geometry()) or intersection.intersects(przeciecia_ft.geometry()):
                                            # print('zawiera')
                                            nearestIds = spIndex.nearestNeighbor(przeciecia_ft.geometry(),1)
                                            przeciecia_km[liczba_obszarow].append(km.getFeature(nearestIds[0]).attributes()[1])

                                            # intersection_pts = intersection.convertToType(4,True)
                                            # print('int to pointd  ' +str(intersection_pts))


                                            km_przeciec_obszaru = []

                                            for intersection_pt in intersection.asPolygon()[0]:
                                                # print(intersection_pt)


                                                # intersection_pt = feat.geometry().nearestPoint(line_feat.geometry())
                                                nearestIds = spIndex.nearestNeighbor(intersection_pt,1)
                                                km_przeciec_obszaru.append(km.getFeature(nearestIds[0]).attributes()[1])

                                            przeciecia_km[liczba_obszarow].append(min(km_przeciec_obszaru))
                                            przeciecia_km[liczba_obszarow].append(max(km_przeciec_obszaru))
                                            # przeciecia_km.append(str(str(km.getFeature(nearestIds[0]).attributes()[1])))
                                    # print('przeciecia km single' +str(przeciecia_km))

                        else:
                            # print('bez przeciecia')
                            nearestIds = spIndex.nearestNeighbor(QgsGeometry.fromPointXY(pt),1)
                            przeciecia_km[0].append(km.getFeature(nearestIds[0]).attributes()[1])


                    else:
                        nearestIds = spIndex.nearestNeighbor(feat.geometry(),1)
                        przeciecia_km[0].append(km.getFeature(nearestIds[0]).attributes()[1])
                        # przec_min = przeciecia_km[0]
                        # przec_max = przeciecia_km[0]


                        # print(przeciecia_km)
                    for przeciecie_km in przeciecia_km:

                        print(przeciecie_km)
                        if len(przeciecie_km)>0:
                            przec_min = float(min(przeciecie_km))
                            przec_max = float(max(przeciecie_km))


                            if przec_min%1000==0:
                                if przec_min == 0:
                                    przeciecie_km_str += str('0+000')
                                elif len(str(math.floor(przec_min/1000))) == 1:
                                    przeciecie_km_str += str(przec_min/1000)+'+'.ljust(5,'0')
                                elif len(str(math.floor(przec_min/1000))) == 2:
                                    przeciecie_km_str += str(przec_min/1000)+'+'.ljust(6,'0')
                                else:
                                    przeciecie_km_str+= str(przec_min/1000)+'+'.ljust(7,'0')

                            else:
                                if len(str(math.floor(przec_min/1000))) == 1:
                                    print(str(przec_min/1000).replace('.','+').ljust(5,'0'))
                                    przeciecie_km_str += str(przec_min/1000).replace('.','+').ljust(5,'0')
                                elif len(str(math.floor(przec_min/1000))) == 2:
                                    print(str(przec_min/1000).replace('.','+').ljust(6,'0'))
                                    przeciecie_km_str += str(przec_min/1000).replace('.','+').ljust(6,'0')
                                else:
                                    print(str(przec_min/1000).replace('.','+').ljust(7,'0'))
                                    przeciecie_km_str += str(przec_min/1000).replace('.','+').ljust(7,'0')



                            if przec_min != przec_max:
                                przeciecie_km_str+= ' - '
                                if przec_max%1000==0:
                                    if przec_min == 0:
                                        przeciecie_km_str += str('0+000')
                                    elif len(str(math.floor(przec_max/1000))) == 1:
                                        przeciecie_km_str += str(przec_max/1000)+'+'.ljust(5,'0')
                                    elif len(str(math.floor(przec_max/1000))) == 2:
                                        przeciecie_km_str += str(przec_max/1000)+'+'.ljust(6,'0')
                                    else:
                                        przeciecie_km_str+= str(przec_max/1000)+'+'.ljust(7,'0')

                                else:
                                    if len(str(math.floor(przec_max/1000))) == 1:
                                        przeciecie_km_str += str(przec_max/1000).replace('.','+').ljust(5,'0')
                                    elif len(str(math.floor(przec_max/1000))) == 2:
                                        przeciecie_km_str += str(przec_max/1000).replace('.','+').ljust(6,'0')
                                    else:
                                        przeciecie_km_str += str(przec_max/1000).replace('.','+').ljust(7,'0')

                                przeciecie_km_str+= '  '


                    feat[idx_km] = str(przeciecie_km_str)










                    ###################
                    feat[czy_przecina] = pos_zakres
                    ###################
                    feat[idx_dist_od_pasa] = min(dist_to_pas)



                    ##### UPDATE
                    layer.updateFeature( feat )
                    #############
                layer.commitChanges()

                #kilometraz Qchaninage

                layerout ='kilometraz'
                startpoint = 0
                endpoint = 0
                distance = 10
                label = False
                layer_os = os

                ####################################
                # points_along_line(
                #     layerout,
                #     startpoint,
                #     endpoint,
                #     distance,
                #     label,
                #     layer_os)

                ####################################

                # QgsMapLayerRegistry.instance().addMapLayer(layer)

                root = QgsProject.instance().layerTreeRoot()

                destination = self.dlg.output_path.filePath()+'\\'+layer.name() #'C:\temp\a.shp'

                error = QgsVectorFileWriter.writeAsVectorFormat(layer, destination, "UTF-8", crs_system , "ESRI Shapefile")

                if destination[-3]!='shp':
                    destination_shp = destination + '.shp'
                else:
                    destination_shp = destination
                layer_out_res = QgsVectorLayer(destination_shp, layer.name(), "ogr")

                QgsProject.instance().addMapLayer(layer_out_res, False)
                root.addLayer(layer_out_res)

                # QgsProject.instance().addMapLayer(feat_lines, False)
                # root.addLayer(feat_lines)

                # for przeciecia_ft in przeciecia_fts:
                #     QgsProject.instance().addMapLayer(przeciecia_ft, False)
                #     root.addLayer(przeciecia_ft)
            if licznik_warstw_geom == licznik_warstw:
                iface.messageBar().pushMessage("Sukces! ", "Przerobiono "+ str(licznik_warstw_geom) +" warstw", level=Qgis.Success)
                # iface.messageBar().pushMessage("Sukces! ", "Warstwa "+ iface.activeLayer().name() +"została podłączona", level=Qgis.Success)
            else:
                puste = licznik_warstw - licznik_warstw_geom
                iface.messageBar().pushMessage("Prawie sukces! ", "Przerobiono "+ str(licznik_warstw_geom) +" warstw, " + puste + " warstw nie zawiera obiektów" , level=Qgis.Warning)
