from PyQt4.QtCore import Qt
from PyQt4.QtGui import QComboBox, QSortFilterProxyModel, QStandardItemModel, QStandardItem

from qgis.core import QgsMessageLog, QgsMapLayerRegistry, QgsExpression, QgsFeatureRequest

from roam.flickwidget import FlickCharm

import roam.utils
import qgis.core

from roam.editorwidgets.core import WidgetsRegistry, EditorWidget

def nullconvert(value):
    if value == qgis.core.NULL:
        return None
    return value


class ListFilter(QSortFilterProxyModel):
    """
    Filter a model to hide the given types of layers
    """
    def __init__(self, parent=None):
        super(ListFilter, self).__init__(parent)
        self.expression = None
        self.setDynamicSortFilter(True)

    def setExpressionString(self, expression, layer=None):
        if expression is None or layer is None:
            self.expression = None
            return

        self.expression = QgsExpression(expression)
        self.expression.prepare(layer.pendingFields())

    def filterAcceptsRow(self, sourcerow, soureparent):
        if not self.expression:
            print "No Expression"
            return True

        index = self.sourceModel().index(sourcerow, 0, soureparent)
        if not index.isValid():
            return False

        feature = index.data(ListWidget.FeatureRole)
        if feature:
            return self.expression.evaluate(feature)
        else:
            return True


class ListWidget(EditorWidget):
    widgettype = 'List'
    DataRole = Qt.UserRole + 1
    FeatureRole = Qt.UserRole + 2

    def __init__(self, *args):
        super(ListWidget, self).__init__(*args)
        self.itemmodel = QStandardItemModel()
        self.layerfilter = ListFilter()

    def createWidget(self, parent):
        return QComboBox(parent)

    def _buildfromlist(self, widget, listconfig):
        items = listconfig['items']
        self.layerfilter.setExpressionString(None)

        for item in items:
            parts = item.split(';')
            data = parts[0]
            try:
                desc = parts[1]
            except IndexError:
                desc = data

            item = QStandardItem(desc)
            item.setData(data, ListWidget.DataRole)
            self.itemmodel.appendRow(item)

    def _buildfromlayer(self, widget, layerconfig):
        layername = layerconfig['layer']
        keyfield = layerconfig['key']
        valuefield = layerconfig['value']
        filterexp = layerconfig.get('filter', None)

        try:
            layer = QgsMapLayerRegistry.instance().mapLayersByName(layername)[0]
        except IndexError:
            roam.utils.warning("Can't find layer {} in project".format(layername))
            return

        keyfieldindex = layer.fieldNameIndex(keyfield)
        valuefieldindex = layer.fieldNameIndex(valuefield)
        if keyfieldindex == -1 or valuefieldindex == -1:
            roam.utils.warning("Can't find key or value column")
            return

        if self.allownulls:
            item = QStandardItem('(no selection)')
            item.setData(None, ListWidget.DataRole)
            self.itemmodel.appendRow(item)

        for feature in layer.getFeatures(QgsFeatureRequest()):
            keyvalue = nullconvert(feature[keyfieldindex])
            valuvalue = nullconvert(feature[valuefield])
            item = QStandardItem(unicode(keyvalue))
            item.setData(unicode(valuvalue), ListWidget.DataRole)
            item.setData(feature, ListWidget.FeatureRole)
            self.itemmodel.appendRow(item)

        if filterexp:
            self.layerfilter.setExpressionString(filterexp, layer)

    def initWidget(self, widget):
        if widget.isEditable():
            widget.editTextChanged.connect(self.validate)

        self.charm = FlickCharm()
        self.charm.activateOn(widget.view())
        widget.currentIndexChanged.connect(self.validate)

        #self.layerfilter.setSourceModel(self.itemmodel)
        widget.setModel(self.itemmodel)

    def updatefromconfig(self):
        print "Update from config"
        self.itemmodel.clear()

        if 'list' in self.config:
            listconfig = self.config['list']
            self._buildfromlist(self.widget, listconfig)
        elif 'layer' in self.config:
            layerconfig = self.config['layer']
            self._buildfromlayer(self.widget, layerconfig)

    @property
    def allownulls(self):
        return self.config.get('allownull', False)

    def validate(self, *args):
        if (not self.allownulls and (not self.widget.currentText() or
            self.widget.currentText() == "(no selection)")):
            self.raisevalidationupdate(False)
        else:
            self.raisevalidationupdate(True)

        self.emitvaluechanged()

    def setvalue(self, value):
        index = self.widget.findData(value)
        self.widget.setCurrentIndex(index)
        if index == -1 and self.widget.isEditable():
            if value is None and not self.config['allownull']:
                return

            self.widget.addItem(str(value))
            index = self.widget.count() - 1
            self.widget.setCurrentIndex(index)

    def value(self):
        index = self.widget.currentIndex()
        value = self.widget.itemData(index)
        text = self.widget.currentText()
        if value is None and self.widget.isEditable() and not text == '(no selection)':
            return self.widget.currentText()

        return value

