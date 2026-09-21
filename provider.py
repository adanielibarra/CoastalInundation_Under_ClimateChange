import os

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider

from .algorithm import CoastalInundationAlgorithm


class CoastalInundationProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(CoastalInundationAlgorithm())

    def id(self):
        return "coastal_inundation_under_climate_change"

    def name(self):
        return "Coastal Inundation Under Climate Change"

    def longName(self):
        return "Coastal Inundation Under Climate Change"

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))
