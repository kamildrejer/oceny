"""
Model exported as python.
Name : przeciecia_model_processing
Group : 
With QGIS : 32207
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class Przeciecia_model_processing(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('inw', 'inw', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('km', 'km', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('os', 'os', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('pas', 'pas', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Wynik', 'WYNIK', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(11, model_feedback)
        results = {}
        outputs = {}

        # pas linie
        alg_params = {
            'INPUT': parameters['pas'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PasLinie'] = processing.run('native:polygonstolines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Przytnij_inwent_inwestycja
        alg_params = {
            'INPUT': parameters['inw'],
            'OVERLAY': parameters['pas'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Przytnij_inwent_inwestycja'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Rozbij geometrie przyciecie
        alg_params = {
            'INPUT': outputs['Przytnij_inwent_inwestycja']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RozbijGeometriePrzyciecie'] = processing.run('native:multiparttosingleparts', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # numer_plata_przecietego
        alg_params = {
            'FIELD_LENGTH': 50,
            'FIELD_NAME': 'nr_plata',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,  # tekst
            'FORMULA': '"id"||\'-\'||$id',
            'INPUT': outputs['RozbijGeometriePrzyciecie']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Numer_plata_przecietego'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Wydobądź wierzchołki
        alg_params = {
            'INPUT': outputs['Numer_plata_przecietego']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['WydobdWierzchoki'] = processing.run('native:extractvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Macierz odległości
        alg_params = {
            'INPUT': outputs['WydobdWierzchoki']['OUTPUT'],
            'INPUT_FIELD': 'nr_plata',
            'MATRIX_TYPE': 0,  # Liniowa (N*k x 3) macierz odległości
            'NEAREST_POINTS': 1,
            'TARGET': parameters['km'],
            'TARGET_FIELD': 'cngmetry',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MacierzOdlegoci'] = processing.run('qgis:distancematrix', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Kalkulator pól kilometraz
        alg_params = {
            'FIELD_LENGTH': 300,
            'FIELD_NAME': 'calc_kilometraz',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,  # tekst
            'FORMULA': 'concatenate_unique(to_string(floor(minimum("TargetID", group_by:="InputID")/1000))  || \'+\' || lpad(to_string(minimum("TargetID", group_by:="InputID")%1000),3,\'0\')||\' - \' ||to_string(floor(maximum("TargetID", group_by:="InputID")/1000)) || \'+\' || lpad(to_string(maximum("TargetID", group_by:="InputID")%1000),3,\'0\'),group_by:= regexp_substr("InputID", \'\\\\d+-\'), concatenator:=\', \')',
            'INPUT': outputs['MacierzOdlegoci']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['KalkulatorPlKilometraz'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Kalkulator pól kilometraz z ID
        alg_params = {
            'FIELD_LENGTH': 100,
            'FIELD_NAME': 'id',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,  # tekst
            'FORMULA': 'regexp_substr("InputID", \'\\\\d+\')',
            'INPUT': outputs['KalkulatorPlKilometraz']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['KalkulatorPlKilometrazZId'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Złącz atrybuty według wartości pola
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'id',
            'FIELDS_TO_COPY': ['calc_kilometraz'],
            'FIELD_2': 'id',
            'INPUT': parameters['inw'],
            'INPUT_2': outputs['KalkulatorPlKilometrazZId']['OUTPUT'],
            'METHOD': 1,  # przyjmuj atrybuty tylko z pierwszego pasującego obiektu (jeden do jednego)
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZczAtrybutyWedugWartociPola'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Wynik kalkulator pól KM
        alg_params = {
            'FIELD_LENGTH': 250,
            'FIELD_NAME': 'wynik_km',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,  # tekst
            'FORMULA': 'case when "calc_kilometraz" is null then "km" else "calc_kilometraz" end',
            'INPUT': outputs['ZczAtrybutyWedugWartociPola']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['WynikKalkulatorPlKm'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Kalkulator pól
        alg_params = {
            'FIELD_LENGTH': 400,
            'FIELD_NAME': 'wynik_dist_pas',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,  # tekst
            'FORMULA': 'length(make_line(closest_point ($geometry, overlay_nearest( layer:= \'{}\' , expression:=$geometry)[0]), overlay_nearest( layer:= \'{}\' , expression:=$geometry)[0]))\r\n'.format(parameters['km'], parameters['km']),
            'INPUT': outputs['WynikKalkulatorPlKm']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['KalkulatorPl'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Usuń pola
        alg_params = {
            'COLUMN': ['calc_kilometraz'],
            'INPUT': outputs['KalkulatorPl']['OUTPUT'],
            'OUTPUT': parameters['Wynik']
        }
        outputs['UsuPola'] = processing.run('native:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
                
        results['Wynik'] = outputs['KalkulatorPl']['OUTPUT']
        return results

    def name(self):
        return 'przeciecia_model_processing'

    def displayName(self):
        return 'przeciecia_model_processing'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Przeciecia_model_processing()
