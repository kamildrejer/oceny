# import os
import os.path, math, ntpath, re
import processing

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
  QgsVectorLayer,
  QgsCoordinateReferenceSystem,
  QgsCoordinateTransform,
  QgsCoordinateTransformContext,
  QgsSpatialIndex,
  QgsProcessing,
  QgsProcessingAlgorithm,
  QgsProcessingContext,
  QgsFeatureIterator,

)
from PyQt5.QtCore import *

def kmFormat(km):
    km_format = str(math.floor(km/1000)) + '+' + str(int(km%1000)).rjust(3,'0')
    return km_format

class Layer:
    def __init__(self, layer):
        self.layer = layer
        self.pt = QgsPoint()
        self.prefix = ''
        self.result_paths_and_prefix = []

    def getLayer(self):
        return self.layer

    # def setAttributes(self):

    def makeSpatialIndex(self):
        spIndex = QgsSpatialIndex()
        # for feat in km_inst.getFeatures():
        for feat in self.layer.getFeatures():
            spIndex.insertFeature(feat)
        return spIndex

    def czyPolygon(self):
        if self.layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            polygon = True
        else:
            polygon = False
        # print("wkbtype: " + str(self.layer.geometryType()))
        return polygon

    def makePrefix(self, prefix):
        self.prefix = prefix
    # def transformCRS(self):

    # def addResultPath(self, path):
    #     self.result_paths.append(path)

    def addResultPathAndPrefix(self, path, prefix):
        self.result_paths_and_prefix.append([path, prefix])

    def getResultPathsAndPrefix(self):
        return self.result_paths_and_prefix

    # def getResultPaths(self):
    #     return self.result_paths

    def getPrefix(self):
        return self.prefix

    def setPrefix(self, prefix):
        self.prefix = prefix

    def distansStrona(self, os):
        self.error = 0
        self.layer.startEditing()
        # spIndex = km.makeSpatialIndex()
        line_feats = [ feat for feat in os.getLayer().getFeatures() ] #os.getFeatures()
        layer_feats = [ feat for feat in self.layer.getFeatures() ]
        for feat in layer_feats:
            if feat.geometry() is not None:
                dist_od_osi = 999999999
                pos = ''
                feat_to_point_geom = QgsGeometry()
                pt = QgsPoint()

                for line_feat in line_feats: #----->zabezpieczyć na wypadek pustej geometrii!!!<------
                    if line_feat.geometry() is not None:
                        feat_to_point_geom_temp = line_feat.geometry().nearestPoint(feat.geometry()) #najblizszy punkt na osi
                        feat_to_point_geom_feature_temp = feat.geometry().nearestPoint(line_feat.geometry()) #najblizszy punkt na obiekcie
                        dist_od_osi_temp = QgsGeometry.distance(feat_to_point_geom_temp, feat.geometry())
                        if dist_od_osi_temp  < dist_od_osi:
                            feat_to_point_geom = feat_to_point_geom_temp
                            pt = feat_to_point_geom_feature_temp.asPoint()

                            dist_od_osi = round(dist_od_osi_temp,1)

                            point_in_line = line_feat.geometry().closestSegmentWithContext(pt)[3] #numer 3 pokazuje która strona, numer 1 daje punkt

                            if point_in_line > 0:
                                pos = 'prawa'
                            elif point_in_line < 0:
                                pos = 'lewa'
                            else:
                                pos = 'na osi'

                            if line_feat.geometry().crosses(feat.geometry()) or line_feat.geometry().intersects(feat.geometry()):
                                pos = 'na osi'

                            # nearestIds = spIndex.nearestNeighbor(feat_to_point_geom,1) # we need only one neighbour
                    else:
                        self.error = 3 #pusta geometria osi
            else:
                self.error = 4 #pusta geometrai w warstwie przecinanej
            self.pt = pt
            idx_dist_od_osi = self.layer.fields().indexFromName('dist_od_osi')
            # print( self.layer.fields().names())
            feat[idx_dist_od_osi] = round(float(dist_od_osi),3)

            ###################
            idx_strona = self.layer.fields().indexFromName('strona')
            feat[idx_strona] = pos

            self.layer.updateFeature( feat )
        #############
        self.layer.commitChanges()
        return self.error

    def przeciecia(self, km, os, pas, km_checked, os_checked, pas_checked, kmfield):
        self.layer.startEditing()
        crs92 = "EPSG:2180"
        spIndex = km.makeSpatialIndex()
        layer_feats = [ feat for feat in self.layer.getFeatures() ]
        i=0
        pt = self.pt
        for feat in layer_feats:
            # dist_od_osi = 999999999
            pos = ''
            if pas_checked:
                obszar_fts = pas.getLayer().getFeatures()
            else:
                obszar_fts = QgsFeatureIterator()

            if os_checked:
                os_fts = os.getLayer().getFeatures()
            else:
                os_fts = []

            pos_zakres = 'poza zakresem inwestycji'

            geoms = QgsGeometry.fromWkt('GEOMETRYCOLLECTION()')
            for feature in os_fts:
                geom = feature.geometry()
                # print(geom)
                geoms = geoms.combine(geom)

            dist_to_pas = []
            area = 0

            #tworzy nową warstwę na przecięcia
            przeciecia_fts = QgsVectorLayer(QgsWkbTypes.displayString(QgsWkbTypes.Point)+"?crs="+crs92, "przecięcia", "memory")
            przeciecia_fts.startEditing()
            fieldid = QgsField("id", QVariant.Int)
            fieldids = QgsFields()
            fieldids.append(fieldid)
            przeciecia_fts.addAttribute(fieldid)

            intersections_fts = []
            #pętla po obszarach

            if not obszar_fts.isValid():
                feat_ring = feat.geometry().convertToType(1,False) #wybranie granic poligonów inwentaryzacji w celu przecięć
                print(feat.geometry().intersection(geoms.buffer(0.01,50)).isEmpty())
                print(geoms.buffer(0.01,50))

                if not feat.geometry().intersection(geoms.buffer(0.01,50)).isEmpty():
                    intersections_fts.append(feat.geometry().intersection(geoms.buffer(0.01,50)))#          feat.geometry().buffer(0.01,50)) #dodanie oryginalnych obiektów do listy z przecięciami jeśli nie analizujemy pasa
                # else:
                #     intersections_fts.append(feat.geometry().buffer(0.01,50)) #dodanie oryginalnych obiektów do listy z przecięciami jeśli nie analizujemy pasa
                przeciecia_pts = feat_ring.intersection(geoms.convertToType(5,False))#.buffer(0.01,50).convertToType(1,False)) #uzyskanie punktów przecięcia

                if not (przeciecia_pts.isEmpty()):
                    points = przeciecia_pts.asMultiPoint() #################### błąd typu osi
                    for point in points:
                        i+=1
                        new_feature = QgsFeature(fieldids)
                        new_feature.setGeometry(QgsPoint(point))
                        new_feature.setAttribute(0,i)
                        przeciecia_fts.addFeature(new_feature)
                else:
                    new_feature = QgsFeature(fieldids)
                    if km_checked and os_checked:
                        new_feature.setGeometry(QgsPoint(feat.geometry().nearestPoint(geoms).asPoint()))
                        new_feature.setAttribute(0,i)
                        przeciecia_fts.addFeature(new_feature)

                    else:
                        if not obszar_ft.geometry().isNull():
                            new_feature.setGeometry(QgsPoint(feat.geometry().nearestPoint(obszar_ft.geometry().buffer(0.01,50)).asPoint()))
                            new_feature.setAttribute(0,i)
                            przeciecia_fts.addFeature(new_feature)


            for obszar_ft in obszar_fts:
                if obszar_ft.geometry().buffer(0.01,50).crosses(feat.geometry()) or obszar_ft.geometry().buffer(0.01,50).intersects(feat.geometry()) or obszar_ft.geometry().buffer(0.01,50).contains(feat.geometry()):
                    pos_zakres = 'w zakresie inwestycji' #modyfikacja pola pozycja
                dist_to_pas.append(float(QgsGeometry.distance(obszar_ft.geometry().buffer(0.01,50),feat.geometry()))) #dodanie do listy odległości w celu wybrania najmniejszej

                if self.czyPolygon():
                    feat_ring = feat.geometry().convertToType(1,False) #wybranie granic poligonów inwentaryzacji w celu przecięć
                    przeciecia_pts = QgsGeometry() #warstwa z punktami przecięcia
                    if pas_checked:
                        przeciecia = feat.geometry().intersection(obszar_ft.geometry().buffer(0.01,50))
                        area += przeciecia.area() #dodanie do liczby z powierzchni przecięcia danego fragmentu
                        obszar_ring = obszar_ft.geometry().buffer(0.01,50).convertToType(1,False)

                        if not przeciecia.isEmpty():
                            intersections_fts.append(przeciecia) #dodanie obiektów do listy z przecięciami

                        przeciecia_pts = feat_ring.intersection(obszar_ring) #uzyskanie punktów przecięcia
                    else:
                        intersections_fts.append(feat.geometry().buffer(0.01,50)) #dodanie oryginalnych obiektów do listy z przecięciami jeśli nie analizujemy pasa
                        przeciecia_pts = feat_ring.intersection(geoms.geometry().buffer(0.01,50))#.buffer(0.01,50).convertToType(1,False)) #uzyskanie punktów przecięcia
                        ############### doddć przecięcia z osią!!!!
                        # przeciecia_pts = feat_ring.intersection(os) #uzyskanie punktów przecięcia

                    if not (przeciecia_pts.isEmpty()):
                        points = przeciecia_pts.asMultiPoint()
                        for point in points:
                            i+=1
                            new_feature = QgsFeature(fieldids)
                            new_feature.setGeometry(QgsPoint(point))
                            new_feature.setAttribute(0,i)
                            przeciecia_fts.addFeature(new_feature)
                    else:
                        new_feature = QgsFeature(fieldids)
                        if km_checked and os_checked:
                            new_feature.setGeometry(QgsPoint(feat.geometry().nearestPoint(geoms).asPoint()))
                            new_feature.setAttribute(0,i)
                            przeciecia_fts.addFeature(new_feature)

                        else:
                            if not obszar_ft.geometry().isNull():
                                new_feature.setGeometry(QgsPoint(feat.geometry().nearestPoint(obszar_ft.geometry().buffer(0.01,50)).asPoint()))
                                new_feature.setAttribute(0,i)
                                przeciecia_fts.addFeature(new_feature)



            przeciecia_fts.commitChanges()

            przeciecia_km = [[0]]
            przeciecia_km[0].clear()
            przeciecie_km_str = ''

            print(intersections_fts)

            if self.czyPolygon():
                idx_powierzchnia = self.layer.fields().indexFromName('powierzchnia')
                feat[idx_powierzchnia] = round(feat.geometry().area(),3)
                if pas_checked:
                    idx_powierzchnia_przec = self.layer.fields().indexFromName('pow_prze')
                    feat[idx_powierzchnia_przec] = round(area,3)
                    idx_procent = self.layer.fields().indexFromName('procent')
                    feat[idx_procent] = round(area*100/feat.geometry().area(),2)
                if km_checked and os_checked:
                    if  len(intersections_fts)>0:
                        liczba_obszarow = 0
                        for intersection in intersections_fts:
                            if intersection.isMultipart()==True:
                                # print('multi')
                                for intersection_geom in intersection.asGeometryCollection():

                                    km_przeciec_obszaru = []
                                    for intersection_geom_pt in intersection_geom.asPolygon()[0]:
                                        nearestIds = spIndex.nearestNeighbor(intersection_geom_pt,1)
                                        km_przeciec_obszaru.append(km.getLayer().getFeature(nearestIds[0]).attributes()[kmfield])

                                    przeciecia_km.append([])
                                    przeciecia_km[liczba_obszarow].append(min(km_przeciec_obszaru))
                                    przeciecia_km[liczba_obszarow].append(max(km_przeciec_obszaru))

                                    print(min(km_przeciec_obszaru))
                                    print(max(km_przeciec_obszaru))

                                    for przeciecia_ft in przeciecia_fts.getFeatures():
                                        if intersection_geom.contains(przeciecia_ft.geometry()) or intersection_geom.intersects(przeciecia_ft.geometry()):
                                            nearestIds = spIndex.nearestNeighbor(przeciecia_ft.geometry(),1)
                                            przeciecia_km.append([])
                                            przeciecia_km[liczba_obszarow].append(km.getLayer().getFeature(nearestIds[0]).attributes()[kmfield])

                                    liczba_obszarow +=1
                            else:
                                # print('single')
                                for przeciecia_ft in przeciecia_fts.getFeatures():
                                    if intersection.contains(przeciecia_ft.geometry()) or intersection.intersects(przeciecia_ft.geometry()):
                                        # print('zawiera')
                                        nearestIds = spIndex.nearestNeighbor(przeciecia_ft.geometry(),1)
                                        przeciecia_km[liczba_obszarow].append(km.getLayer().getFeature(nearestIds[0]).attributes()[kmfield])

                                    km_przeciec_obszaru = []

                                    for intersection_pt in intersection.asPolygon()[0]:

                                        nearestIds = spIndex.nearestNeighbor(intersection_pt,1)
                                        km_przeciec_obszaru.append(km.getLayer().getFeature(nearestIds[0]).attributes()[kmfield])

                                    przeciecia_km[liczba_obszarow].append(min(km_przeciec_obszaru))
                                    przeciecia_km[liczba_obszarow].append(max(km_przeciec_obszaru))

                    else:

                        for przeciecia_ft in przeciecia_fts.getFeatures():
                            nearestIds = spIndex.nearestNeighbor(przeciecia_ft.geometry(),1)
                            # przeciecia_km.append([])
                            przeciecia_km[0].append(km.getLayer().getFeature(nearestIds[0]).attributes()[kmfield])
                        # pt = feat.geometry().nearestPoint(obszar_ft.geometry())#.asPoint()
                        # nearestIds = spIndex.nearestNeighbor(pt,1)#QgsGeometry.fromPointXY(pt),1)
                        # przeciecia_km[0].append(km.getLayer().getFeature(nearestIds[0]).attributes()[kmfield])

            else:
                if km_checked and os_checked:
                    nearestIds = spIndex.nearestNeighbor(feat.geometry(),1)
                    przeciecia_km[0].append(km.getLayer().getFeature(nearestIds[0]).attributes()[kmfield])



            if km_checked and os_checked:
                i=1
                for przeciecie_km in przeciecia_km:
                    if len(przeciecie_km)>0:
                        przec_min = float(min(przeciecie_km))
                        przec_max = float(max(przeciecie_km))
                        przeciecie_km_str+= kmFormat(przec_min)
                        if przec_min != przec_max:
                            przeciecie_km_str+= ' - '
                            przeciecie_km_str+= kmFormat(przec_max)
                        if len(przeciecia_km) != i: przeciecie_km_str+= ',  '
                    i+=1
                idx_km = self.layer.fields().indexFromName('km')
                # print(idx_km)
                # print(przeciecie_km_str)
                feat[idx_km] = str(przeciecie_km_str)

            if pas_checked:
                idx_czy_przecina = self.layer.fields().indexFromName('czy_przecina')
                idx_dist_od_pasa = self.layer.fields().indexFromName('dist_od_pasa')
                # print(idx_czy_przecina)
                # print(pos_zakres)
                feat[idx_czy_przecina] = pos_zakres
                feat[idx_dist_od_pasa] = min(dist_to_pas)

            self.layer.updateFeature( feat )
                #############
        self.layer.commitChanges()

class LoadOuterLayers:
    def __init__(self):
        self.dsu = QgsDataSourceURI()
        pass
        # self.layers = []
        # self.licznik_warstw = 0
        # self.new_layers = []
        # self.sp_indexes = []
        # self.prefix = []
    def loadWFS(self):
        dsu = QgsDataSourceURI()
        dsu.setParam( 'url', 'http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/wfs/Carta_geologica.map' )
        dsu.setParam( 'version', '1.1.0' )
        dsu.setParam( 'typename', 'GE.CARTAGEOLOGICA' )
        dsu.setParam( 'InvertAxisOrientation', '1' )
        layer = QgsVectorLayer( dsu.uri(), "my wfs layer", "WFS" )

        res = QgsVectorFileWriter.writeAsVectorFormat( layer,
                                                       '/tmp/wfs_features.shp',
                                                       'System', # encoding
                                                       None, #crs
                                                       'ESRI Shapefile')

        if res != QgsVectorFileWriter.NoError:
            print ('Error number:' + res)
        else:
            print ("WFS saved!")


class LoadLayers:
    def __init__(self):
        self.layers = []
        self.licznik_warstw = 0
        self.new_layers = []
        self.sp_indexes = []
        self.prefix = []


    def checkLayerValidity(self):
        wynik = 0
        layers_out = []
        for layer_klasa in self.layers:
            layer = layer_klasa.getLayer()
            if layer is not None and layer.featureCount()>0 and layer.isValid() and layer.isSpatial():
                #przebiegnij po rekordach i zobaczy czy nie ma pustej geometrii, jeśli tak to błąd
                for ft in layer.getFeatures():
                    if ft.geometry().isNull():
                        wynik = 1
                self.licznik_warstw+=1
                layers_out.append(Layer(layer))
        # jeśli nie znaleziono żadnej poprawnej warstwy, wyświetl komunikat i koniec
        if self.licznik_warstw==0:
            wynik = 2
        return wynik

    def getLayers(self):
        return self.layers

    def getLayersByPrefix(self, prefix):
        layer_by_prefix = None
        for layer_klasa in self.new_layers:

            if layer_klasa.getPrefix() == prefix:
                layer_by_prefix = layer_klasa
        return layer_by_prefix

    def getNewLayers(self):
        return self.new_layers

    def getPrefixes(self):
        return self.prefix

    def newLayers(self):
        return self.new_layers

    def loadLayer(self, layer, prefix):
        layer_save = Layer(layer)
        layer_save.makePrefix(prefix)
        self.layers.append(layer_save)
        self.prefix.append(prefix)

    def loadLayersFromStringList(self, layersStringList):
        self.layers = []
        for laer_orygin_str in layersStringList:  #weź listę plików
            filename = ntpath.basename(laer_orygin_str) #wyodrębnij nazwę pliku z warstwą
            layer = QgsVectorLayer(laer_orygin_str, filename, "ogr") #twórz warstwę

            prefix = re.findall('\A[a-zA-Z0-9]+_', filename)[0] if len(re.findall('\A[a-zA-Z0-9]+_', filename))>0 else '_'
            layer_save = Layer(layer)
            layer_save.makePrefix(prefix)
            self.layers.append(layer_save)
            self.prefix.append(prefix)


    def makeNewLayers(self):
        self.new_layers = []
        crs92 = "EPSG:2180"
        for layer_orygin_klasa in self.layers:
            layer_orygin = layer_orygin_klasa.getLayer()
            #twórz nową warstwę do której będzie kopiować obiekty dla każdej z warstw
            layer = QgsVectorLayer(QgsWkbTypes.displayString(layer_orygin.wkbType())+"?crs="+crs92, layer_orygin.name(), "memory")

            attr = layer_orygin.dataProvider().fields().toList()
            layer.setProviderEncoding('UTF-8')
            layer.dataProvider().addAttributes(attr)

            layer.updateFields()

            #przygotuj transformację
            crs_system = layer_orygin.sourceCrs() #QgsCoordinateReferenceSystem(crs)
            crs_system92 = QgsCoordinateReferenceSystem(crs92)
            xform = QgsCoordinateTransform(crs_system, crs_system92, QgsProject.instance())
            #CRS transformation
            feats = []

            for f in layer_orygin.getFeatures():
                g = f.geometry()
                g.transform(xform)
                f.setGeometry(g)
                feats.append(f)
            # dodaj przetransformowane do układu 92 obiekty do warstwy w układzie 92
            layer.dataProvider().addFeatures(feats)

            layer_save = Layer(layer)
            layer_save.setPrefix(layer_orygin_klasa.getPrefix())
            self.new_layers.append(layer_save)

    def addFields(self, km_checked, os_checked, pas_checked):
        #czy poligon-------------
        for layer_klasa in self.new_layers:

            layer = layer_klasa.getLayer()
            # layer_orygin
            polygon = layer_klasa.czyPolygon()
            #dodaje atrybuty ze źródłowej warstwy
            attr = layer.dataProvider().fields().toList()
            # layer.dataProvider().addAttributes(attr)
            # layer.updateFields()

            field_names = layer.fields().names()
            field_names = [each_string.lower() for each_string in field_names]

            layer.startEditing() #zaczynam edycję warstwy

            #dodaję pola jeśli nie ma w warstwie
            if 'id' not in field_names:
                field = QgsField( 'id', QVariant.String )
                layer.addAttribute( field )
            idx_id = layer.fields().indexFromName('id') #pobierz id koolumny żeby później uzupełnić

            if ('strona' not in field_names) and (km_checked and os_checked):
            	field = QgsField( 'strona', QVariant.String )
            	layer.addAttribute( field )
            idx_strona = layer.fields().indexFromName('strona') #pobierz id koolumny żeby później uzupełnić

            if ('km' not in field_names) and (km_checked and os_checked):
            	field = QgsField( 'km', QVariant.String )
            	layer.addAttribute( field )
            idx_km = layer.fields().indexFromName('km')

            if ('dist_od_osi' not in field_names) and (km_checked and os_checked):
            	field = QgsField( 'dist_od_osi', QVariant.String )
            	layer.addAttribute( field )
            idx_dist_od_osi = layer.fields().indexFromName('dist_od_osi')

            if ('dist_od_pasa' not in field_names) and pas_checked:
            	field = QgsField( 'dist_od_pasa', QVariant.String )
            	layer.addAttribute( field )
            idx_dist_od_pasa = layer.fields().indexFromName('dist_od_pasa')

            if ('czy_przecina' not in field_names) and pas_checked:
            	field = QgsField( 'czy_przecina', QVariant.String )
            	layer.addAttribute( field )
            idx_czy_przecina = layer.fields().indexFromName('czy_przecina')

            #pola jedynie dla poligonów
            if polygon == True:
                if ('powierzchnia'  not in field_names):
                	field = QgsField( 'powierzchnia', QVariant.Double )
                	layer.addAttribute( field )
                powierzchnia = layer.fields().indexFromName('powierzchnia')

                if ('pow_prze' not in field_names) and pas_checked:
                	field = QgsField( 'pow_prze', QVariant.Double )
                	layer.addAttribute( field )
                powierzchnia_przec = layer.fields().indexFromName('pow_prze')

                if ('procent' not in field_names) and pas_checked:
                	field = QgsField( 'procent', QVariant.Double )
                	layer.addAttribute( field )
                procent = layer.fields().indexFromName('procent')

            id2=0
            for f in layer.getFeatures():
                id2+=1
                f[idx_id] = str(id2)
                layer.updateFeature( f )
            layer.commitChanges()



class ZlaczWarianty:
    def __init__(self, paths_and_prefix):
        self.prefix = []
        self.paths = []
        # self_warstwyzlaczone = []
        for pex in paths_and_prefix:
            self.prefix.append(pex[1])
            self.paths.append(pex[0])

        # print(self.prefix)
        # print(self.paths)

        self.output_path = QgsProcessing.TEMPORARY_OUTPUT

        self.results = {}
        self.outputs = {}
    def mergeLayers(self, output):
        path1 = None
        path2 = None
        # print(path1)
        # print(path2)
        i = 0
        context = QgsProcessingContext()
        for path in self.paths:
            i+=1
            # print(i)
            if i == len(self.paths):
                self.output_path = output
            if path1 is not None and path2 is not None:
                path2 = path
                path1 = self.outputs['ZczAtrybutyWedugWartociPola']['OUTPUT']
            if path2 is None and path1 is not None:
                path2 = path
            if path1 is None:
                path1 = path

            input1 = None
            if path1 is not None and path2 is not None:
                if i<3:
                    wariant_fieldname = str(i-1) + ''+ 'wariant'

                    # Kalkulator pól
                    alg_params = {
                        'FIELD_LENGTH': 200,
                        'FIELD_NAME': wariant_fieldname,
                        'FIELD_PRECISION': 0,
                        'FIELD_TYPE': 2,  # tekst
                        'FORMULA': "'" + self.prefix[i-2].replace('_','') + "'",
                        'INPUT': path1,
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }
                    self.outputs['KalkulatorPl1'] = processing.run('native:fieldcalculator', alg_params, context=context, is_child_algorithm=True)
                    input1 = self.outputs['KalkulatorPl1']['OUTPUT']

                else:
                    input1 = self.outputs['ZczAtrybutyWedugWartociPola']['OUTPUT']

                # Kalkulator pól


                alg_params = {
                    'FIELD_LENGTH': 200,
                    'FIELD_NAME': wariant_fieldname,
                    'FIELD_PRECISION': 0,
                    'FIELD_TYPE': 2,  # tekst
                    'FORMULA': "'" + self.prefix[i-1].replace('_','') + "'",
                    'INPUT': path2,
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
                self.outputs['KalkulatorPl2'] = processing.run('native:fieldcalculator', alg_params, context=context, is_child_algorithm=True)

                alg_params = {
                    'DISCARD_NONMATCHING': False,
                    'FIELD': 'id',
                    'FIELDS_TO_COPY': ['strona', 'km', 'dist_od_os', 'dist_od_pa', 'czy_przeci','powierzchn', 'pow_prze', 'procent', wariant_fieldname],
                    'FIELD_2': 'id',
                    'INPUT': input1,
                    'INPUT_2': self.outputs['KalkulatorPl2']['OUTPUT'],
                    'METHOD': 1,  # przyjmuj atrybuty tylko z pierwszego pasującego obiektu (jeden do jednego)
                    'PREFIX': i,
                    'OUTPUT': self.output_path
                }
                # print( self.output_path)
                self.outputs['ZczAtrybutyWedugWartociPola'] = processing.run('native:joinattributestable', alg_params, context=context, is_child_algorithm=True)

        self.results['Wynik'] = self.outputs['ZczAtrybutyWedugWartociPola']['OUTPUT']

        return self.results['Wynik']
