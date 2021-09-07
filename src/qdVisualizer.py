#####################################
#### Q-D Visualization software #####
#####################################
# Author: Tanguy Ropitault          #
# email: tanguy.ropitault@nist.gov  #
#####################################

######################################################################################################
# NIST-developed software is expressly provided "AS IS." NIST MAKES NO                               #               
# WARRANTY OF ANY KIND, EXPRESS, IMPLIED, IN FACT OR ARISING BY                                      #
# OPERATION OF LAW, INCLUDING, WITHOUT LIMITATION, THE IMPLIED                                       #
# WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE,                                     #
# NON-INFRINGEMENT AND DATA ACCURACY. NIST NEITHER REPRESENTS                                        #
# NOR WARRANTS THAT THE OPERATION OF THE SOFTWARE WILL BE                                            #
# UNINTERRUPTED OR ERROR-FREE, OR THAT ANY DEFECTS WILL BE                                           #
# CORRECTED. NIST DOES NOT WARRANT OR MAKE ANY REPRESENTATIONS                                       #
# REGARDING THE USE OF THE SOFTWARE OR THE RESULTS THEREOF,                                          #
# INCLUDING BUT NOT LIMITED TO THE CORRECTNESS, ACCURACY,                                            #
# RELIABILITY, OR USEFULNESS OF THE SOFTWARE.                                                        #
#                                                                                                    #
#                                                                                                    #
# You are solely responsible for determining the appropriateness of using                            #
# and distributing the software and you assume all risks associated with its use, including          #
# but not limited to the risks and costs of program errors, compliance with applicable               #
# laws, damage to or loss of data, programs or equipment, and the unavailability or                  #
# interruption of operation. This software is not intended to be used in any situation               #
# where a failure could cause risk of injury or damage to property. The software                     #
# developed by NIST is not subject to copyright protection within the United                         #
# States.                                                                                            #
######################################################################################################

import cProfile
import io
import math
import os
import pickle
import pstats
import sys
import time
from multiprocessing.dummy import freeze_support
from pstats import SortKey
import numpy as np
import pyqtgraph as pg
import vtk
from PyQt5.QtGui import *
from mayavi import mlab
from mayavi.api import Engine
from mayavi.core.ui.api import SceneEditor
from mayavi.core.ui.mayavi_scene import MayaviScene
from mayavi.mlab import *
from mayavi.modules.labels import Labels
from mayavi.modules.surface import Surface
from mayavi.tools.mlab_scene_model import MlabSceneModel
from pyface.api import GUI
from pyface.image_resource import ImageResource
from pyface.qt import QtGui
from traits.api import (Bool, Button, HasTraits, Instance, List, Range, Enum,
                        Str, Int, Float, Trait, on_trait_change, Color)
from traits.etsconfig.api import ETSConfig
from traitsui.api import (ButtonEditor, CheckListEditor, Group, HGroup, HSplit,
                          ImageEnumEditor, Item, RangeEditor,
                          TreeEditor, TreeNode, VGroup, View, ColorEditor)
from tvtk.api import tvtk
from matplotlib import cm
import globals
import qdPropagationLoss
import qdRealization
import codebook
from environment import constructEnvironment
from environment import SceneVisualizationProperties
import quaternionUtils
from preprocessData import computeSuMimoBft
from preprocessData import computeMuMimoBft
from nsInput import getNsSlsResultsTxRxTrace
from nsInput import getNsSlsResultsBftId
from nsInput import getNumberOfBft

ETSConfig.toolkit = 'qt4'  # Force PyQt4 utilization

os.environ['ETS_TOOLKIT'] = 'qt5'
defaultStaModel = "staDefault.obj"
defaultApModel = "apDefault.obj"


######################################################################################################
###########                 CLASSES TO SAVE THE VISUALIZATION CONFIGURATION               ############
######################################################################################################
class ComponentsVisualizationConfig:
    """
    A class to represent the visualization configuration of the STAs/APs, Antenna Patterns, and MPCs
    """
    def __init__(self, mpcProperties, stasNodesSize, apsNodesSize, stasModelScale, apsModelScale,
                 apAntennaPatternMagnifier, apAntennaPatternOpacity,
                 staAntennaPatternMagnifier, staAntennaPatternOpacity, txPaaMagnifier, rxPaaMagnifier):
        self.mpcProperties = mpcProperties
        self.stasNodesSize = stasNodesSize
        self.apsNodesSize = apsNodesSize
        self.stasModelScale = stasModelScale
        self.apsModelScale = apsModelScale
        self.apAntennaPatternMagnifier = apAntennaPatternMagnifier
        self.apAntennaPatternOpacity = apAntennaPatternOpacity
        self.staAntennaPatternMagnifier = staAntennaPatternMagnifier
        self.staAntennaPatternOpacity = staAntennaPatternOpacity
        self.txPaaMagnifier = txPaaMagnifier
        self.rxPaaMagnifier = rxPaaMagnifier


class TargetsVisualizationProperties:
    """
    A class to represent the visualization configuration of the targets and their associated MPCs
    """

    def __init__(self, targetsVisualizationConfig, mpcsTxRxHidden, mpcsNodesTargetHidden):
        self.targetsVisualizationConfig = targetsVisualizationConfig
        self.mpcsTxRxHidden = mpcsTxRxHidden
        self.mpcsNodesTargetHidden = mpcsNodesTargetHidden


class TargetsVisualizationConfig:
    """
    A class to represent the visualization configuration of the targets and their associated MPCs
    """

    def __init__(self, mpcWidth, colorTargetMpc):
        self.mpcWidth = mpcWidth
        self.colorTargetMpc = colorTargetMpc


class SceneVisualizerConfig:
    """
    A class to represent the visualization of the 3D environment
    """
    def __init__(self, sceneVisualizationProperties, sceneObjects):
        self.sceneVisualizationProperties = sceneVisualizationProperties
        self.sceneObjects = sceneObjects


class MimoVisualizationConfig:
    """
    A class to represent the visualization configuration of the MIMO mode
    """
    def __init__(self, mpcProperties, streamAntennaPatternSize, streamColor, streamOpacity, streamEdgesSize):
        self.mpcProperties = mpcProperties
        self.streamAntennaPatternSize = streamAntennaPatternSize
        self.streamColor = streamColor
        self.streamOpacity = streamOpacity
        self.streamEdgesSize = streamEdgesSize


class MpcsVisualizationProperties:
    """
    A class to represent the visualization parameters of the MPCs of a reflection order
    """
    def __init__(self, width, color, hidden):
        self.width = width
        self.color = color
        self.hidden = hidden

######################################################################################################
###########                            PLOTS MANAGEMENT                                   ############
######################################################################################################
# TODO Pretty temporary code - Will change once we know what users really need to interact with the plots
class Plot(HasTraits):
    """GUI Plot class - Allow the user to interact and select which plots to display
    """
    name = Str('Not Defined')
    guiTxCurvesNodesList = 0
    guiRxCurvesNodesList = 0
    guiTxCurvesNodesSelected = List(editor=CheckListEditor(name='guiTxCurvesNodesList', cols=10))
    guiRxCurvesNodesSelected = List(editor=CheckListEditor(name='guiRxCurvesNodesList', cols=10))

    @on_trait_change('guiTxCurvesNodesSelected,guiRxCurvesNodesSelected')
    def updateCurvesNewSelection(self):
        """Handle a new selection made by the user for the plot to display
        """

        # Display all curves selected Tx to all Rxs
        for strTxId in self.guiTxCurvesNodesList:
            # Iterate over all the possible TX node ID values
            # and check if strTxId value is selected in the list of all possible values
            if strTxId not in self.guiTxCurvesNodesSelected:
                # if strTxId value is not selected, clear the corresponding plots, remove the corresponding legends, and update the curves filter
                txId = int(strTxId)
                for rxId in range(qdScenario.nbNodes):
                    if txId != rxId:
                        for paaTx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(txId))):
                            for paaRx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(rxId))):
                                if (
                                        self.name, txId, rxId, paaTx, paaRx,
                                        0) in Y_CURVE_FILTER:  # 0 if for TX 1 for RX TODO
                                    CURVES_DIC[(self.name, txId, rxId, paaTx, paaRx)].setData([0], [0],
                                                                                              clear=True)  # Clear the plot
                                    Y_CURVE_LEGEND[self.name].removeItem(
                                        "TX:" + str(txId) + " => " + "RX:" + str(rxId) + " PAA_TX:" + str(
                                            paaTx) + " PAA_RX:" + str(
                                            paaRx) + " :Power Received (dB)")  # Clear the legend
                                    del Y_CURVE_FILTER[(
                                        self.name, txId, rxId, paaTx, paaRx,
                                        0)]  # Remove from the curve filter dictionary
            else:
                # if strTxId value is selected, update the plots, the legend and the curves filter
                txId = int(strTxId)
                for rxId in range(qdScenario.nbNodes):
                    if txId != rxId:
                        for paaTx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(txId))):
                            for paaRx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(rxId))):
                                # Update the legend (remove and add it) TODO: Use the filter to know if it was already existing
                                Y_CURVE_LEGEND[self.name].removeItem(
                                    "TX:" + str(txId) + " => " + "RX:" + str(rxId) + " PAA_TX:" + str(
                                        paaTx) + " PAA_RX:" + str(paaRx) + " :Power Received (dB)")
                                Y_CURVE_LEGEND[self.name].addItem(CURVES_DIC[("Power", txId, rxId, paaTx, paaRx)],
                                                                  "TX:" + str(txId) + " => " + "RX:" + str(
                                                                      rxId) + " PAA_TX:" + str(
                                                                      paaTx) + " PAA_RX:" + str(
                                                                      paaRx) + " :Power Received (dB)")

                                # pyqtgraph cannot handle only infinite value - handle this
                                onlyInfiniteValues = np.all(
                                    np.asarray(Y_CURVE_DATA_DIC[(self.name, txId, rxId, paaTx, paaRx)]) == -math.inf)
                                Y_CURVE_FILTER[(self.name, txId, rxId, paaTx, paaRx, 0)] = 1  # Update the curve filter
                                if not onlyInfiniteValues:
                                    # Update the TX curves
                                    CURVES_DIC[(self.name, txId, rxId, paaTx, paaRx)].setData(
                                        Y_CURVE_DATA_DIC[(self.name, txId, rxId, paaTx, paaRx)])

        # Display all curves all Txs to selected Rx
        for strRxId in self.guiRxCurvesNodesList:
            # Iterate over all the possible nodes values
            # and check if strTxId value is selected in the list of all possible values
            if strRxId not in self.guiRxCurvesNodesSelected:
                # if strRxId value is not selected, clear the corresponding plots, remove the corresponding legends, and update the curves filter
                rxId = int(strRxId)
                for txId in range(qdScenario.nbNodes):
                    if txId != rxId:
                        for paaTx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(txId))):
                            for paaRx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(rxId))):
                                if (self.name, txId, rxId, paaTx, paaRx, 1) in Y_CURVE_FILTER:
                                    CURVES_DIC[(self.name, txId, rxId, paaTx, paaRx)].setData([0], [0],
                                                                                              clear=True)  # Clear the plot
                                    Y_CURVE_LEGEND[self.name].removeItem(
                                        "TX:" + str(txId) + " => " + "RX:" + str(rxId) + " PAA_TX:" + str(
                                            paaTx) + " PAA_RX:" + str(
                                            paaRx) + " :Power Received (dB)")  # Clear the legend
                                    del Y_CURVE_FILTER[(
                                        self.name, txId, rxId, paaTx, paaRx,
                                        1)]  # Remove from the curve filter dictionary
            else:
                # if strTxId value is selected, update the plots, the legend and the curves filter
                rxId = int(strRxId)
                for txId in range(qdScenario.nbNodes):
                    if txId != rxId:
                        for paaTx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(txId))):
                            for paaRx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(rxId))):
                                # Update the legend (remove and add it) TODO: Use the filter to know if it was already existing
                                Y_CURVE_LEGEND[self.name].removeItem(
                                    "TX:" + str(txId) + " => " + "RX:" + str(rxId) + " PAA_TX:" + str(
                                        paaTx) + " PAA_RX:" + str(
                                        paaRx) + " :Power Received (dB)")
                                Y_CURVE_LEGEND[self.name].addItem(CURVES_DIC[("Power", txId, rxId, paaTx, paaRx)],
                                                                  "TX:" + str(txId) + " => " + "RX:" + str(
                                                                      rxId) + " PAA_TX:" + str(
                                                                      paaTx) + " PAA_RX:" + str(
                                                                      paaRx) + " :Power Received (dB)")

                                # pyqtgraph cannot handle only infinite value - handle this
                                onlyInfiniteValues = np.all(
                                    np.asarray(
                                        Y_CURVE_DATA_DIC[(self.name, txId, rxId, paaTx, paaRx)]) == -math.inf)
                                Y_CURVE_FILTER[
                                    (self.name, txId, rxId, paaTx, paaRx, 1)] = 1  # Update the curve filter
                                if not onlyInfiniteValues:
                                    # Update the curves
                                    CURVES_DIC[(self.name, txId, rxId, paaTx, paaRx)].setData(
                                        Y_CURVE_DATA_DIC[(self.name, txId, rxId, paaTx, paaRx)])


class GuiCurvesMenu(HasTraits):
    """GUI to interact with the curves
    """
    name = Str('<unknown>')
    listPlots = List(Plot)


# Define the tree view that the user will interact with to change GuiCurvesMenu
tree_editor = TreeEditor(
    nodes=[
        TreeNode(node_for=[GuiCurvesMenu],
                 auto_open=False,
                 children='listPlots',
                 label='=Plots',
                 view=View(),
                 ),
        TreeNode(node_for=[Plot],
                 auto_open=False,
                 label='name',
                 view=View(
                     VGroup(
                         VGroup(
                             Item('guiTxCurvesNodesSelected', label='Tx Nodes', style='custom', show_label=True),
                             Item('guiRxCurvesNodesSelected', label='Rx Nodes', style='custom', show_label=True),
                             label='Curves filter',
                             show_border=True),
                     ),
                 ),
                 ),
    ]
)

######################################################################################################
###########                      VISUALIZER GUI AND EVENTS                                ############
######################################################################################################
class Visualization(HasTraits):
    global qdScenario, txParam, codebooks, environmentFile, maxReflectionOrder
    qdScenario, txParam, codebooks, environmentFile, maxReflectionOrder = globals.initializeOracle(
        useVisualizer=True)  # Parse input files and command-line parameters
    # Define the engine and create the two views used
    # qdScenario.preprocessedSlsData, qdScenario.preprocessedAssociationData,qdScenario.dataIndex
    engine1 = Instance(Engine, args=())
    view1 = Instance(MlabSceneModel, ())
    view2 = Instance(MlabSceneModel, ())
    if qdScenario.qdInterpreterConfig.sensing:
        # In case of sensing, we add a third view to display the doppler range map
        view3 = Instance(MlabSceneModel, ())

    # Gui Elements
    #########################################################
    #                DEVICES AND PAAs                       #
    #########################################################
    # DropDown to select TX and Rx node
    # TODO There are way better ways to handle the creation of dropdown list element - Fix it (it should not be str)
    guiTxNodeSelected = Str  # The Tx node selected in the GUI
    guiRxNodeSelected = Str  # The Rx node selected in the GUI
    guiTxNodeSelectedChoices = List()  # The list of choices for the Tx Node in the GUI
    guiRxNodeSelectedChoices = List()  # The list of choices for the Rx Node in the GUI
    guiSwitchTxRxNode = Button('Switch')  # Button used to switch Tx and Rx node

    # DropDown to select PAA Tx and PAA Rx
    guiTxPaaSelected = Str  # The PAA Tx node selected in the GUI
    guiTxPaaSelectedChoices = List()  # The list of choices for the PAA Tx in the GUI
    guiRxPaaSelected = Str  # The PAA Rx node selected in the GUI
    guiRxPaaSelectedChoices = List()  # The list of choices for the PAA Rx in the GUI

    # To change STAs and APs labels and colors
    guiApsLabels = Str
    guiApsLabelsColor = Color()
    guiStasLabels = Str
    guiStasLabelsColor = Color()

    # To Select on which scene to display the elements
    guiNodesScene = Enum("View1", "View2")
    guiNodesLabelsScene = Enum("View1", "View2")
    guiPaasScene = Enum("View1", "View2")
    guiBeamformingPatternsScene = Enum("View1", "View2")

    guiDisplayNodesObjects = Bool(False)  # Used to show or hide the device 3D model model
    guiApThreeDModeScale = Range(0.0, 10.0, 1.0) # Scale of the AP 3D model
    guiStaThreeDModeScale = Range(0.0, 10.0, 1.0) # Scale of the STA 3D model

    guiApsNodesSize = Range(0.0, 10.0, 1.0)  # Scale of the APs (3D sphere)
    guiStasNodesSize = Range(0.0, 10.0, 1.0) # Scale of the STAs (3D sphere)

    guiApPaaMagnifier = Range(0.0, 10.0, 1.0)  # Used to change TX PAA elements size
    guiStaPaaMagnifier = Range(0.0, 10.0, 1.0)  # Used to change RX PAA elements size

    # Orientation axes of devices and PAAs
    guiDisplayDeviceTxAxis = Bool  # Use to display Tx Device Axis
    guiDisplayDeviceRxAxis = Bool  # Use to display Rx Device Axis
    guiDisplayPaaTxAxis = Bool  # Use to display Paa Tx Axis
    guiDisplayPaaRxAxis = Bool  # Use to display Paa Rx Axis

    #########################################################
    #                         SLS                           #
    #########################################################
    # Information about the best sector and received power for the SLS
    guiTxssTxRxBestSector = Int(-1)  # Display the TxSS best sector in the GUI for the Tx/Rx/PaaTx/PaaRx selected
    guiTxssTxRxRcvPower = Float  # Display the TxSS received power in the GUI for the Tx/Rx/PaaTx/PaaRx selected
    guiTxssRxTxBestSector = Int(-1)  # Display the TxSS best sector in the GUI for the Rx/Tx/PaaRx/PaaTx selected
    guiTxssRxTxRcvPower = Float  # Display the TxSS received power in the GUI for the Rx/Tx/PaaRx/PaaTx selected
    # Iterate using the SLS bft ID (used only when ns-3 sls mode is selected)
    guiIterateSlsBftId = Int()
    guiMinSlsBftId = 0
    guiMaxSlsBftId = Int()




    if qdScenario.qdInterpreterConfig.slsEnabled:
        guiDisplayGroupSls = Str("True")
        guiDisplaySls = Bool(True)
    else:
        guiDisplayGroupSls = Str("False")
        guiDisplaySls = Bool(False)
    guiSlsMode = Enum("Oracle", "ns-3")

    if qdScenario.qdInterpreterConfig.dataMode == "preprocessed":
        guiSlsDataModePreprocessed = Bool(True)
    else:
        guiSlsDataModePreprocessed = Bool(False)

    guiTxssTxRxTxId = Str
    guiTxssTxRxTxType = Str
    guiTxssTxRxRxId = Str
    guiTxssTxRxRxType = Str
    guiTxssRxTxTxId = Str
    guiTxssRxTxTxType = Str
    guiTxssRxTxRxId = Str
    guiTxssRxTxRxType = Str

    #########################################################
    #                         PLOTS                         #
    #########################################################
    # Creation of the components used to interact with the plots selections in the GUI
    guiCurvesMenu = Instance(GuiCurvesMenu)
    allNodesList = []
    for nodeId in range(qdScenario.nbNodes):
        allNodesList.append(str(nodeId))

    if qdScenario.qdInterpreterConfig.plotData:
        guiDisplayGroupCurves = Str("True")
    else:
        guiDisplayGroupCurves = Str("False")

    powerPlot = Plot(name='Power', guiTxCurvesNodesList=allNodesList, guiRxCurvesNodesList=allNodesList)
    psdPlot = Plot(name='PSD', guiTxCurvesNodesList=allNodesList, guiRxCurvesNodesList=allNodesList)
    powerPerSectorPlot = Plot(name='Power Per Sector', guiTxCurvesNodesList=allNodesList,
                              guiRxCurvesNodesList=allNodesList)
    # Create the tree to interact with the plots
    if qdScenario.qdInterpreterConfig.dataMode == "online":
        # PSD plot is available only in online mode
        guiCurvesMenu = GuiCurvesMenu(
            name='Parameters',
            listPlots=[powerPlot, powerPerSectorPlot, psdPlot]

        )
    else:
        guiCurvesMenu = GuiCurvesMenu(
            name='Parameters',
            listPlots=[powerPlot, powerPerSectorPlot]
        )

    #########################################################
    #                    ENVIRONMENT                        #
    #########################################################
    guiObjectName = Str("") # Name of the object selected
    guiObjectId = Str("") # ID of the object selected
    guiMaterialId = Str("") # Material ID of the object selected
    guiMaterialName = Str("") # Material Name of the object selected
    guiHideObject = Bool # Hide the object selected
    guiFrontFaceCulling = Bool # Hide the object if its normal is facing the camera
    guiBackFaceCulling = Bool  # Hide the object if its normal is back to the camera
    guiEdgeVisibility = Bool # Display the edge of the entire scene
    guiObjectOpacity = Range(0.0, 1.0,
                             1.0) # Opacity of the object selected

    guiTextureMaterial = Enum('Texture', 'Material') # Display the material color or texture for the selected scene
    guiTextureMode = Enum('plane', 'cylinder', 'sphere', 'none') # Texture mode to apply for the object selected
    guiViewSelected = Str("None") # View currently selected
    guiButtonSaveEnvironment = Button('Save Environment') # Button to save the 3d Environment configuration applied
    guiObjectColor = Color() # Color of the material of the object selected
    guiTexturesImages = []
    for objFileToWrite in os.listdir(globals.textureFolder):
        # Read all the obj files that are available in the cached folder
        guiTexturesImages.append(objFileToWrite)
    guiVisualizerTextures = Trait(editor=ImageEnumEditor(values=guiTexturesImages,
                                                         path=globals.textureFolder,
                                                         cols=1, ),
                                  width=0.1,
                                  *guiTexturesImages)  # Used to select texture to apply to a surface

    #########################################################
    #                 SCENARIO NAVIGATION                   #
    #########################################################
    #  The slider used to iterate over the traces
    traceIndex = Int()  #
    guiMinTrace = 0
    guiMaxTrace = qdScenario.nbTraces - 1

    # Create the menu with icons to interact with the visualization (play,back, pause, stop)
    guiInteractionImages = ['back', 'stop', 'pause', 'play']  # Image for the visualization interaction
    guiVisualizerInteractions = Trait(editor=ImageEnumEditor(values=guiInteractionImages,
                                                             path='Pictures/Interface',
                                                             cols=4, ),
                                      width=10,
                                      *guiInteractionImages)  # Used to interact with the visualizer (play, back, pause, and stop)
    guiTraceIncrement = Range(1, 1000,
                              1)  # Configure the step of trace iteration when the play or back button is pressed
    guiDisplayStaAssociation = Bool(False)  # Used to show the STA associations to their APs
    guiShowSlsBestAp = Bool(False)  # When a STA is selected as a TX, it shows the SLS results with the best AP

    #########################################################
    #                      MIMO                             #
    #########################################################
    guiDisplayMimo = Bool  # Display the MIMO

    # SU-MIMO GUI
    if qdScenario.qdInterpreterConfig.mimo != "none":
        guiDisplayGroupMimo = Str("True")
    else:
        guiDisplayGroupMimo = Str("False")

    guiMimoStream = Range(0, qdScenario.maxSupportedStreams, 0)  # Stream selected
    guiMimoData = Enum("ns-3", "Oracle")  # Mode to perform the MIMO (works only for SU and MU MIMO)
    guiMimoTxStreamIdentifier = Int() # For SU-MIMO and MU-MIMO, it's the TX PAA of the stream
    guiMimoRxStreamIdentifier = Int() # For SU-MIMO, it's the RX PAA of the stream and for MU-MIMO, it's the responder ID of the stream
    guiMimoTxSector = Int() # Tx Sector of the stream
    guiMimoRxSector = Int() # Rx Sector of the stream
    guiMimoStreamOpacity = Range(0.0, 1.0,
                                   1.0) # Opacity of the stream

    guiMimoEdgesSize = Range(0.0, 1.0,
                               1.0) # Edge size of the stream

    guiMimoStreamSize = Range(0.0, 4.0, 1.0) # Size of the stream Antenna Patterns
    guiMimoStreamColor = Color() # Color of the stream Antenna Patterns edges and MPCs
    guiMimoStreamMpcSize = Range(0.0, 2.0, 1.0) # Size of the stream MPCs
    guiButtonSaveMimoConfig = Button('Save MIMO') # Button to save the MIMO visualization configuration
    # The identifiers are different depending on the MIMO mode
    # For beamtracking and SU-MIMO, it's the Tx Stream PAA and Rx Stream PAA while for MU-MIMO
    # It's the Tx Stream PAA and RX Stream Node ID
    guiMimoTxStreamIdentifierLabel = ''
    guiMimoRxStreamIdentifierLabel = ''
    if  qdScenario.qdInterpreterConfig.mimo == "beamTracking" or qdScenario.qdInterpreterConfig.mimo == "suMimo":

        guiMimoTxStreamIdentifierLabel = 'Tx Paa:'
        guiMimoRxStreamIdentifierLabel = 'Rx Paa:'
    elif qdScenario.qdInterpreterConfig.mimo == "muMimo":
        guiMimoTxStreamIdentifierLabel = 'Tx Paa:'
        guiMimoRxStreamIdentifierLabel = 'Rx Id:'

    #########################################################
    #                  BEAMTRACKING                         #
    #########################################################
    guiBeamtrackingType = Enum('Analog', 'Hybrid')
    if qdScenario.qdInterpreterConfig.mimo == "beamTracking":
        guiDisplayBeamTrackingParameters = Str("True")
    else:
        guiDisplayBeamTrackingParameters = Str("False")

    #########################################################
    #                    CODEBOOK                           #
    #########################################################

    if qdScenario.qdInterpreterConfig.codebookTabEnabled:
        guiDisplayGroupCodebook = Bool(True)
    else:
        guiDisplayGroupCodebook = Bool(False)

    guiIterateTxSectors = Int()  # Used to iterate over the Transmitter Sectors in the GUI
    guiIterateRxSectors = Int()  # Used to iterate over the Receiver Sectors in the GUI

    guiCodebookLabel = Str  # Display the codebook properties in the GUI

    guiTxRefineAwvSelected = Str  # The Refine AWV chosen
    guiTxRefineAwvChoices = List()  # The list of choices for the Tx Node in the GUI

    guiTxMinSectorId = Int()  # Minimun sector ID of the transmitter
    guiTxMaxSectorId = Int()  # Maximum sector ID of the transmitter
    guiRxMinSectorId = Int()  # Minimun sector ID of the receiver
    guiRxMaxSectorId = Int()  # Maximun sector ID of the receiver

    #########################################################
    #                      MPCS                             #
    #########################################################
    guiMpcReflection = Range(0, maxReflectionOrder, 0)  # Used to select the MPCs reflection
    guiMpcColor = Color()  # Used to change the MPCs color of a given reflection order
    guiMpcsHidden = Bool # Hide the MPCs of a given reflection order
    guiButtonSaveTweak = Button('') # Save the MPCs configuation
    guiMpcsMagnifier = Range(0.0, 10.0, 1.0)  # Used to change the MPCs size of a given reflection order

    #########################################################
    #                    ANTENNA PATTERNS                   #
    #########################################################
    guiApAntennaPatternMagnifier = Range(0.0, 10.0, 1.0)  # Used to change AP Antenna Pattern size
    guiApAntennaPatternOpacity = Range(0.0, 1.0, 1.0)  # Used to change the AP Antenna Pattern opacity
    guiStaAntennaPatternMagnifier = Range(0.0, 10.0, 1.0)  # Used to change STA Antenna Pattern size
    guiStaAntennaPatternOpacity = Range(0.0, 1.0, 1.0)  # Used to change the STA Antenna Pattern opacity

    #########################################################
    #                       SENSING                         #
    #########################################################
    if qdScenario.qdInterpreterConfig.sensing:
        guiDisplayGroupSensing = Str("True")
    else:
        guiDisplayGroupSensing = Str("False")
    guiTargetSelected = Str # Target selected
    guiTargetSelectedChoices = List() # All possible Target choices
    guiSensingTargetColor = Color()  # Color of the target selected
    guiDisplayTxRxMpcs = Bool(True) # Display the communication MPCs
    guiDisplayTargetMpcs = Bool(True) # Display the target MPCs
    guiButtonSaveSensingConfig = Button('Save Config') # Save the sensing visualization conmfiguration

    @on_trait_change('view2.activated')
    def initializePicker(self):
        """Initialize the pickers for the views (pickers are used to select objects from the 3D environment)
        """
        global pickerView1
        global pickerView2
        pickerView1 = self.view1.mayavi_scene.on_mouse_pick(self.picker_callback, type='cell')
        pickerView2 = self.view2.mayavi_scene.on_mouse_pick(self.picker_callback, type='cell')
        pickerView1.tolerance = 0.0000001
        pickerView2.tolerance = 0.0000001

    def picker_callback(self, picker):
        """Get the object that was picked (if any) and color it in red while applying the GUI representation for of all the other objects
        """
        global currentSelectedObject
        global currentPicker
        # Catch the errors here
        output = vtk.vtkFileOutputWindow()
        output.SetFileName("log.txt")
        vtk.vtkOutputWindow().SetInstance(output)
        pickerOutside = True
        if picker == pickerView1:
            # The picker tried to pick something on view1
            viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            currentPicker = pickerView1
            # Update the GUI
            self.guiViewSelected = "View1"
            self.guiTextureMaterial = self.scenesProperties[self.view1.mayavi_scene].representation
            self.guiEdgeVisibility = self.scenesProperties[self.view1.mayavi_scene].edgeVisibility
        else:
            # The picker tried to pick something on view2
            viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            currentPicker = pickerView2
            # Update the GUI
            self.guiViewSelected = "View2"
            self.guiTextureMaterial = self.scenesProperties[self.view2.mayavi_scene].representation
            self.guiEdgeVisibility = self.scenesProperties[self.view2.mayavi_scene].edgeVisibility

        # Check if the object picked belongs to the objects of the view
        for i in range(len(viewObjects)):
            if picker.actor in viewObjects[i].mesh.actor.actors:
                # The user picked an object in the objects of the view
                pickerOutside = False
                # Update the visualization
                viewObjects[
                    i].mesh.actor.mapper.scalar_visibility = False  # Disable the scalar colors assigned to the object
                viewObjects[i].mesh.actor.property.color = (1, 0, 0)  # Color the picked object in red
                viewObjects[
                    i].mesh.actor.property.line_width = 8  # Increase slighly the size of the wireframe edges

                # Update the GUI to reflect the object properties
                currentSelectedObject = i
                self.guiObjectName = viewObjects[i].name
                self.guiObjectId = viewObjects[i].id
                self.guiMaterialId = viewObjects[i].materialId
                self.guiMaterialName = self.materialProperties.materialNameDic[viewObjects[i].materialId]
                self.guiHideObject = viewObjects[i].hidden
                self.guiFrontFaceCulling = viewObjects[i].frontFaceCulling
                self.guiBackFaceCulling = viewObjects[i].backFaceCulling
                self.guiObjectOpacity = viewObjects[i].opacity
            else:
                # The object was not picked - Apply the visualization configured through the GUI representation
                viewObjects[i].mesh.actor.property.line_width = 2
                if self.guiTextureMaterial == 'Material':
                    # The GUI is configured to display the Material colors
                    self.assignMaterialColor(viewObjects[i])
                else:
                    # The GUI is configured to display the textures
                    # Check if it exists a texture for the object
                    if self.materialProperties.materialNameDic[
                        viewObjects[i].materialId] not in self.materialProperties.materialPathDic and viewObjects[
                        i].customTexture == "":
                        # No texture exists (not in the material library neither configured by the user) - Apply the material color
                        self.assignMaterialColor(viewObjects[i])
                    else:
                        # A texture exists and is already applied - Just remove the material color, i.e, apply white
                        viewObjects[i].mesh.actor.property.color = (1.0, 1.0, 1.0)

        if pickerOutside:
            # The picker did not select an object belonging to our LIST_AMF_OBJECTS - Update the GUI to reflect it
            self.guiMaterialId = ""
            self.guiObjectName = ""
            self.guiObjectId = "No Object Selected"
            self.guiMaterialName = ""
            currentSelectedObject = -1
            self.guiHideObject = False
            self.guiFrontFaceCulling = False
            self.guiBackFaceCulling = False
            # self.guiEdgeVisibility = False
            self.guiObjectOpacity = 1.0

        self.forceRender()

    def __init__(self):
        """Constructor for the visualization class
        """
        self.engine1.start()
        # Set the background color for view1 and view2
        self.view1.background = (0.2901960784313726, 0.2901960784313726, 0.2901960784313726)
        self.view2.background = (0.2901960784313726, 0.2901960784313726, 0.2901960784313726)

        # Check if the user previously saved the components configuration to configure the visualization
        self.savedComponentsConfig = False
        self.componentsConfig = None
        componentsConfigFile = os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder,
                                            globals.componentsConfigFile)
        if os.path.exists(componentsConfigFile):
            # A configuration exits - Load it
            self.componentsConfig = pickle.load(
                open(componentsConfigFile, "rb"))  # Load the config
            self.savedComponentsConfig = True
            print("A previous saved configuration file exists for the visualization components - Load it")

        print("************************************************")
        print("*           VISUALIZATION CREATION             *")
        print("************************************************")

        # Load AP and STAs visuals
        self.apsVisObj, self.apsLabels, self.stasVisObj, self.stasLabels, self.apModelVisObj, self.apTextureMode, self.staModelVisObj, self.staTextureMode = self.createDevicesVisuals()
        # Create the PAAs visuals for APs and STAs
        self.paasElementsVisObj = self.createPaasVisuals()
        # Create the devices and PAAs orientation axes
        self.createPaaDeviceOrientationAxes()
        # Build the 3D environment
        self.createEnvironmentVisuals()

        if qdScenario.qdInterpreterConfig.sensing:
            # Create the sensing visuals if enabled
            self.targetJointsVisObj, self.targetJointsConnectionsVisObj, self.targetVisualizationConfig, self.targetsVisualizationProperties, self.colorTargetsRgb, \
            self.pointsNodesTargetsReflections, self.mpcNodesTargetsReflections, \
            self.pointsNodesAllTargetsReflections, self.mpcNodesAllTargetsReflections, self.velocityHigh, self.velocityLow, self.filteredIndexes, self.dopplerRangeObjVis, self.axesDopplerRange = self.createSensingVisuals()

        # Create the MPCs visualization properties
        if self.savedComponentsConfig:
            # If the user saved his config, use it
            self.mpcReflectionsProperties = self.componentsConfig.mpcProperties
        else:
            # Use default value
            self.mpcReflectionsProperties = {}
            mpcReflectionsColors = self.createDefaultSlsMpcsProperties()
            for reflectionOrder in range(8):
                # We consider that the maximum reflection order won't be greater than 0
                self.mpcReflectionsProperties[reflectionOrder] = MpcsVisualizationProperties(0.1, mpcReflectionsColors[reflectionOrder], False)

        # Atrributes for the SLS MPCs
        self.mpcTubesDicVisObj = {}
        self.mpcVerticesDicVisObj = {}
        self.mpcEdgesDicVisObj = {}

        if qdScenario.qdInterpreterConfig.slsEnabled or qdScenario.qdInterpreterConfig.codebookTabEnabled:
            # Create the SLS Antenna Patterns
            self.txSectorsAntennaPatternVisObj, self.quasiOmniAntennaPatternVisObj = self.createAntennaPatternSectors()
            qdScenario.qdInterpreterConfig.codebookTabEnabled = True
        else:
            # Need to be added to hangle GUI Interaction
            # TODO Remove the Antenna Pattern Item from the GUI if not created
            self.txSectorsAntennaPatternVisObj = []

        # Default GUI starting values
        # TODO Allow to change the default starting value (not everything hardcoded)
        self.guiVisualizerInteractions = "pause"  # Start the visualizer paused
        # By default, the Tx Node is set to be the node 0 and the Rx node to be the node 1
        txNodeChoices = []
        for i in range(qdScenario.nbNodes):
            if i != 1:  # We don't want to add the receiver 1 as a possible choice for the transmitter when we start
                txNodeChoices.append(str(i))
        self.guiTxNodeSelectedChoices = txNodeChoices  # The list of choices for the Tx Node

        # We have for now the choices of AWVs hardcoded (as done in ns-3: 5 choices by default)
        txRefineAwvChoices = []
        txRefineAwvChoices.append("None")
        for i in range(5):
            txRefineAwvChoices.append(str(i))
        self.guiTxRefineAwvChoices = txRefineAwvChoices
        self.guiTxRefineAwvSelected = "None"

        # MIMO
        self.mimoStreamPatterns = {} # Contains the Tx and Rx patterns for a given MIMO stream
        self.mimoTubeObjects = {} # Contains the objects for the MPCs
        self.mimoTubeMesh = {} # Contains the mesh for the MIMO MPCs
        self.mimoStreamProperties = {}
        self.mimoStreamPatternSize = {}
        self.mimoStreamEdgeSize = {}
        self.mpcVerticesDicVisObjMIMO = {}
        self.bestreamPaaIdCombination = []
        self.bestSectorsCombination = []

        if qdScenario.qdInterpreterConfig.mimo != "none":
            # Check if a MIMO visualization config file is available
            self.savedMimoConfig = False
            mimoConfigFile = os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder,
                                          globals.mimoConfigFile)
            if os.path.exists(mimoConfigFile):
                # A configuration exits - Load it
                self.mimoConfig = pickle.load(
                    open(mimoConfigFile, "rb"))  # Load the config
                self.savedMimoConfig = True
                print("A previous saved configuration file exists for the MIMO components - Load it")
            if self.savedMimoConfig:
                # If the user saved his config, use it to configure the visualization
                self.mimoStreamProperties = self.mimoConfig.mpcProperties
                self.mimoStreamPatternSize = self.mimoConfig.streamAntennaPatternSize
                self.mimoStreamEdgeSize = self.mimoConfig.streamEdgesSize
            else:
                # Load the default configuration for the visualization of the MIMO streams
                self.defaultMimoStreamColor = self.createDefaultMimoStreamProperties()
                for stream in range(8):
                    # We have maximum 8 MIMO streams for IEEE 802.11ay
                    self.mimoStreamProperties[stream] = MpcsVisualizationProperties(0.1,
                                                                                    self.defaultMimoStreamColor[stream],
                                                                                    False)
                    self.mimoStreamPatternSize[stream] = 1
                    self.mimoStreamEdgeSize[stream] = 0.5

        rxNodeChoices = []
        for i in range(qdScenario.nbNodes):
            if i != 0:  # We don't want to add the transmitter 0 as a possible choice for the receiver when we start
                rxNodeChoices.append(str(i))

        self.guiRxNodeSelectedChoices = rxNodeChoices  # The list of choices for the Rx Node
        # self.guiTxNodeSelected = "0"  # Start the visualizer with Node 0 as the Transmitter
        self.guiRxNodeSelected = "1"  # Start the visualizer with Node 1as the Receiver

        # The visualizer is started with node 0 as a transmitter and node 1 as a receiver
        # Update the PAA Tx choices according to node 0 type and PAA Rx choices according to node 1 type
        paaTxChoices = []
        for i in range(codebooks.getNbPaaNode(qdScenario.getNodeType(0))):
            paaTxChoices.append(str(i))
        self.guiTxPaaSelectedChoices = paaTxChoices  # The list of choices for the Tx Node
        paaRxChoices = []
        for i in range(codebooks.getNbPaaNode(qdScenario.getNodeType(1))):
            paaRxChoices.append(str(i))
        self.guiRxPaaSelectedChoices = paaRxChoices
        # By default, the Tx and Rx PAA are set to 0
        self.guiTxPaaSelected = "0"
        self.guiRxPaaSelected = "0"

        # Sensing
        if qdScenario.qdInterpreterConfig.sensing:
            targetChoices = []
            for i in range(qdScenario.nbTargets):
                targetChoices.append(str(i))
            targetChoices.append("All")
            self.guiTargetSelectedChoices = targetChoices  # The list of choices for the Tx Node
            self.guiTargetSelected = "0"

        # Create the objects used to display the STA associations to their APs
        xSTACoordinates, ySTACoordinates, zSTACoordinates = qdScenario.getAllSTAsPosition(self.traceIndex)
        color = np.arange(len(xSTACoordinates))
        self.stasAssociationVisObj = mlab.points3d(xSTACoordinates, ySTACoordinates, zSTACoordinates, color,
                                                   scale_factor=1, scale_mode="none", opacity=0.5,
                                                   vmin=0, vmax=qdScenario.nbNodes,
                                                   figure=self.view1.mayavi_scene, name="stasAssociationVisObj",
                                                   mode='sphere',
                                                   reset_zoom=False)
        self.stasAssociationVisObj.actor.actor.property.lighting = False
        self.stasAssociationVisObj.actor.property.line_width = 4.0
        self.makeInvisible(self.stasAssociationVisObj)

        self.refinedAwvTxPattern = 0 # Used to display Antenna Pattern using refined AWV (not activated)
        HasTraits.__init__(self)

    def clearDisplay(self):
        """Clear all the elements previously displayed in the visualizer scenes
        """
        # Color every PAA in White and hide all quasi-omni patterns
        for nodeId in range(qdScenario.nbNodes):
            for paaId in range(codebooks.getNbPaaNode(nodeId)):
                self.paasElementsVisObj[(nodeId, paaId)].actor.actor.property.color = (1.0, 1.0, 1.0)
                if qdScenario.qdInterpreterConfig.slsEnabled:
                    # The antenna Patterns are created only if SLS Mode is activated
                    self.makeInvisible(self.quasiOmniAntennaPatternVisObj[qdScenario.getNodeType(nodeId), paaId])
                # Hide PAA orientation axis
                self.makeInvisible(self.paasOrientationAxesVisObj[(qdScenario.getNodeType(nodeId), True, paaId)])
                self.makeInvisible(self.paasOrientationAxesVisObj[(qdScenario.getNodeType(nodeId), False, paaId)])

        # Hide the device Orientation Axis
        self.makeInvisible(self.txDeviceOrientationAxesVisObj)
        self.makeInvisible(self.rxDeviceOrientationAxesVisObj)
        # Hide every MPC
        for txId in range(qdScenario.nbNodes):
            for rxId in range(qdScenario.nbNodes):
                if (min(int(txId), rxId), max(int(txId), rxId)) in self.mpcVerticesDicVisObj:
                    MPCPointOneNode = self.mpcVerticesDicVisObj[min(int(txId), rxId), max(int(txId), rxId)]
                    for MPCReflectionOneNode in MPCPointOneNode:
                        self.makeInvisible(MPCReflectionOneNode)  # Hide the points
                    tubeOneNode = self.mpcEdgesDicVisObj[min(txId, int(rxId)), max(txId, int(rxId))]
                    for tubeReflectionOneNode in tubeOneNode:
                        self.makeInvisible(tubeReflectionOneNode)  # Hide the tube (paths)

        # Hide every TX Antenna Pattern
        if qdScenario.qdInterpreterConfig.slsEnabled:
            for paaId in range(codebooks.getNbPaaPerAp()):
                for sectorId in range(codebooks.getNbSectorPerApAntenna()):
                    for role in range(2):
                        self.makeInvisible(
                            self.txSectorsAntennaPatternVisObj[globals.NodeType.AP.value, paaId, sectorId, role])
            for paaId in range(codebooks.getNbPaaPerSta()):
                for sectorId in range(codebooks.getNbSectorPerStaAntenna()):
                    for role in range(2):
                        self.makeInvisible(
                            self.txSectorsAntennaPatternVisObj[globals.NodeType.STA.value, paaId, sectorId, role])

        # Hide every MIMO pattern if needed
        if qdScenario.qdInterpreterConfig.mimo == "suMimo" or qdScenario.qdInterpreterConfig.mimo == "muMimo":
                if self.mimoStreamPatterns:
                    for streamId in range(qdScenario.maxSupportedStreams+1):
                        for pattern in self.mimoStreamPatterns[streamId]:
                            self.makeInvisible(pattern)
        elif qdScenario.qdInterpreterConfig.mimo == "beamTracking":
            for streamId in range(qdScenario.maxSupportedStreams + 1):
                if ("Analog", streamId) in self.mimoStreamPatterns:
                    for pattern in self.mimoStreamPatterns["Analog", streamId]:
                        self.makeInvisible(pattern)
            for streamId in range(qdScenario.maxSupportedStreams + 1):
                if ("Hybrid", streamId) in self.mimoStreamPatterns:
                    for pattern in self.mimoStreamPatterns["Hybrid", streamId]:
                        self.makeInvisible(pattern)


    #######################################################################
    #            FUNCTION TO CREATE THE VISUALIZATION                     #
    #######################################################################
    def createDevicesVisuals(self):
        """Create the visuals for the STAs and APs
        """
        print("\tCreate APs and STAs Nodes")
        globals.logger.info("Create STA and AP Nodes")

        # Create STA + AP nodes (they are represented by simple 3D spheres or 3D models objects)
        if self.savedComponentsConfig:
            # If the user saved his config, use it
            scaleFactorAp = self.componentsConfig.apsNodesSize
            self.guiApsNodesSize = self.componentsConfig.apsNodesSize
            scaleFactorSta = self.componentsConfig.stasNodesSize
            self.guiStasNodesSize = self.componentsConfig.stasNodesSize
        else:
            # Default value
            scaleFactorAp = 1
            scaleFactorSta = 1

        # APs 3D Spheres
        # Get the AP nodes coordinates
        xAPCoordinates, yAPCoordinates, zAPCoordinates = qdScenario.getAllAPsPosition(self.traceIndex)
        # Assign the AP colors
        colorAPs = np.arange(len(xAPCoordinates))
        viewToDisplay = self.view1.mayavi_scene
        # if qdScenario.qdInterpreterConfig.dataMode != "none":
        #     # When mode is not none, we want to display the APs and STAs nodes on view1 (left view)
        #     viewToDisplay = self.view1.mayavi_scene
        # else:
        #     # When mode is none, we want to display the APs and STAs nodes on view2 (right view)
        #     viewToDisplay = self.view2.mayavi_scene
        # Creation of the APs 3d spheres Objects
        apsVisObj = mlab.points3d(xAPCoordinates, yAPCoordinates, zAPCoordinates,
                                  colorAPs, vmin=0, vmax=qdScenario.nbNodes - 1, scale_factor=scaleFactorAp,
                                  scale_mode="none", figure=viewToDisplay, name="AP_Nodes", reset_zoom=False)

        # Add a label for every AP
        apsLabels = Labels()
        vtk_data_source = apsVisObj
        self.engine1.add_filter(apsLabels, vtk_data_source)
        apsLabels.mapper.label_format = ("AP %d")
        apsLabels.mapper.label_mode = ('label_field_data')
        apsLabels.property.font_size = 18

        # STAs 3D Points
        # Get the STAs nodes coordinates
        xSTACoordinates, ySTACoordinates, zSTACoordinates = qdScenario.getAllSTAsPosition(self.traceIndex)
        # Assign the STAs colors
        colorSTAs = np.arange(qdScenario.nbAps, qdScenario.nbNodes)
        # Creation of the STAs 3d spheres Objects
        stasVisObj = mlab.points3d(xSTACoordinates, ySTACoordinates, zSTACoordinates,
                                   colorSTAs, vmin=0, vmax=np.amax(colorSTAs), scale_factor=scaleFactorSta,
                                   scale_mode="none",
                                   figure=viewToDisplay, name="STA_Nodes",
                                   reset_zoom=False)
        # Add a label for every STA
        stasLabels = Labels()
        vtk_data_source = stasVisObj
        self.engine1.add_filter(stasLabels, vtk_data_source)

        if not qdScenario.qdInterpreterConfig.sensing:
            stasLabels.mapper.label_format = ("STA %d")
        else:
            # The sensing scenario do not really have STA, just change the label (TODO: find a better fix)
            stasLabels.mapper.label_format = ("AP %d")
        stasLabels.mapper.label_mode = ('label_field_data')
        stasLabels.property.font_size = 18

        ## APs and STAs 3D model
        if self.savedComponentsConfig:
            apModelVisObj, apTextureMode = self.loadObjectModel(True, defaultApModel, self.engine1, self.view1,
                                                                self.componentsConfig.apsModelScale)
            staModelVisObj, staTextureMode = self.loadObjectModel(False, defaultStaModel, self.engine1,
                                                                  self.view1, self.componentsConfig.stasModelScale)
        else:
            apModelVisObj, apTextureMode = self.loadObjectModel(True, defaultApModel, self.engine1, self.view1,
                                                                1)
            staModelVisObj, staTextureMode = self.loadObjectModel(False, defaultStaModel, self.engine1,
                                                                  self.view1, 1)
        return apsVisObj, apsLabels, stasVisObj, stasLabels, apModelVisObj, apTextureMode, staModelVisObj, staTextureMode

    def loadObjectModel(self, isAp, modelFile, engine, view, scale):
        """Load and create the 3D models associated to the APs or the STAs

        Parameters
        ----------
        isAp : Bool
            Are we creating for APs or STAs (True = APs, False = STAs)

        modelFile : String
            The name of the 3D model to load

        engine: Mayavi Engine
            The engine where to add the 3D model

        view: Mayavi View
            The view where to display the 3D model

        scale: Float
            The scale factor to apply to the 3D model

        Returns
        -------
        modelVisObj : List
            List storing the 3D objects created for every APs or STAs nodes

        textureMode : String
            The type of texture used to texture the 3D model
        """
        # We can import obj file
        # OBJ can be made of:
        # - Just a single .obj file and then we don't have any additional information besides the object shape
        # - An .obj file and a .mtl file - MTL stores the texture information
        # - An .obj file and a .jpg file - jpg file is the texture to apply to the mesh
        # The loading of the texture will work only if the texture file (.jpg or .mtl) is the same name of the .obj
        texture = os.path.splitext(modelFile)
        textureFileName = os.path.join(globals.modelFolder, texture[0] + ".mtl")
        if os.path.exists(textureFileName):
            textureMode = "mtl"
        else:
            textureFileName = os.path.join(globals.modelFolder, texture[0] + ".jpg")
            if os.path.exists(textureFileName):
                textureMode = "jpg"
            else:
                textureMode = "none"

        modelVisObj = []
        if isAp:
            nbNodes = qdScenario.nbAps
        else:
            nbNodes = qdScenario.nbStas
        objFileName = os.path.join(globals.modelFolder, modelFile)
        if textureMode == "mtl":
            # Case where the texture information is inside the .mtl file
            for i in range(nbNodes):
                # Load the model for every device (APs or STAs)
                polyReader = tvtk.OBJImporter()
                polyReader.file_name = objFileName
                polyReader.file_name_mtl = textureFileName
                polyReader.texture_path = globals.modelFolder
                polyReader.read()
                objectsTextured = []
                for individualActor in polyReader.renderer.actors:
                    # The polyreader contains one actor per texture to associate - Iterate through all of them to add them to the view
                    view.add_actor(individualActor)
                    objectsTextured.append(individualActor)
                    individualActor.visibility = False
                    individualActor.scale = [scale, scale, scale]

                modelVisObj.append(objectsTextured)  # Keep every textured actors that made of object for one device
        else:
            # Case where it's only .obj or .obj + .jpg texture file
            # The loading of the model is the same in both cases
            polyReader = engine.open(objFileName, view)
            for i in range(nbNodes):
                objectDevice = Surface()  # The object associated to the device to display
                if textureMode == "jpg":
                    # A texture file has been provided - Load it and apply it to the 3d model
                    img = tvtk.JPEGReader()
                    img.file_name = textureFileName
                    texture = tvtk.Texture(input_connection=img.output_port, interpolate=0)
                    objectDevice.actor.enable_texture = True
                    objectDevice.actor.tcoord_generator_mode = 'none'
                    objectDevice.actor.actor.texture = texture
                else:
                    # No texture file - Active the edges visibility to create a nicer representation
                    objectDevice.actor.property.edge_visibility = True
                    objectDevice.actor.property.line_width = 0.5
                objectDevice.actor.actor.scale = [scale, scale, scale]
                engine.add_module(objectDevice, polyReader)
                self.makeInvisible(objectDevice)
                modelVisObj.append(objectDevice)
        return modelVisObj, textureMode

    def createPaaDeviceOrientationAxes(self):
        """Create the visuals for the orientation axes of the devices and PAAs

        Parameters
        ----------
        self : Class
            The self class holding the entire self (GUIs, visual objects, etc)
        """
        self.txDeviceOrientationAxesVisObj = self.createOrientationAxis(self.view2.mayavi_scene, "TX DEVICE AXES")
        self.rxDeviceOrientationAxesVisObj = self.createOrientationAxis(self.view2.mayavi_scene, "RX DEVICE AXES")

        # Create the PAA orientation axes
        self.paasOrientationAxesVisObj = {}

        # Create the PAA orientations axes (take into account device rotation + PAA initial orientation)
        # We create them for both STA and AP and if they are respectively transmitter or receiver
        for paaId in range(codebooks.getNbPaaPerAp()):
            # PAA orientation axes for AP when being a transmitter (The True Boolean)
            self.paasOrientationAxesVisObj[(globals.NodeType.AP, True, paaId)] = self.createOrientationAxis(
                self.view1.mayavi_scene,
                "PAA AXES" + str(
                    globals.NodeType.AP) + "Transmitter:" + str(
                    True))
            # PAA orientation axes for AP when being a receiver (The False Boolean)
            self.paasOrientationAxesVisObj[(globals.NodeType.AP, False, paaId)] = self.createOrientationAxis(
                self.view1.mayavi_scene,
                "PAA AXES" + str(
                    globals.NodeType.AP) + "Transmitter:" + str(
                    False))

        for paaId in range(codebooks.getNbPaaPerSta()):
            # PAA orientation axes for STA when being a transmitter (The True Boolean)
            self.paasOrientationAxesVisObj[(globals.NodeType.STA, True, paaId)] = self.createOrientationAxis(
                self.view1.mayavi_scene,
                "PAA AXES" + str(
                    globals.NodeType.STA) + "Transmitter:" + str(
                    True))
            # PAA orientation axes for STA when being a receiver (The False Boolean)
            self.paasOrientationAxesVisObj[(globals.NodeType.STA, False, paaId)] = self.createOrientationAxis(
                self.view1.mayavi_scene,
                "PAA AXES" + str(
                    globals.NodeType.STA) + "Transmitter:" + str(
                    False))

    def createPaasVisuals(self):
        """Create Antenna Elements self for boths APs and STAs

        Parameters
        ----------
        self : Class
            The self class holding the entire self (GUIs, visual objects, etc)
        """
        print("\tCreate APs and STAs PAAs")
        paasElementsVisObj = {}  # Dictionary holding the PAA self objects - The key is made of the tuple (int:nodeId,int:PaaId)
        # APs
        globals.logger.info("Create STAs and APs Antenna Elements ")
        # We get the position of the antenna elements and we magnified it as in reality, the antenna elements are too close to each other to be visualized
        paaMagnifier = 50
        xAntennaElementPositionAP = codebooks.getApPaaElementPositions()[::3] * paaMagnifier
        yAntennaElementPositionAP = codebooks.getApPaaElementPositions()[1::3] * paaMagnifier
        zAntennaElementPositionAP = codebooks.getApPaaElementPositions()[2::3] * paaMagnifier

        if self.savedComponentsConfig:
            # If the user saved his config, use it
            scale = self.componentsConfig.txPaaMagnifier
            self.guiApPaaMagnifier = self.componentsConfig.txPaaMagnifier
        else:
            # Default value
            scale = 1

        for apID in range(qdScenario.nbAps):
            for paaID in range(codebooks.getNbPaaPerAp()):
                paasElementsVisObj[(apID, paaID)] = mlab.points3d(xAntennaElementPositionAP, yAntennaElementPositionAP,
                                                                  zAntennaElementPositionAP,
                                                                  scale_factor=0.1,
                                                                  scale_mode="none",
                                                                  figure=self.view1.mayavi_scene,
                                                                  mode='cube',
                                                                  name="AP: " + str(apID) + " PAA:" + str(paaID),
                                                                  reset_zoom=False)
                paasElementsVisObj[(apID, paaID)].actor.property.edge_visibility = True
                paasElementsVisObj[(apID, paaID)].actor.property.line_width = 0.6
                if self.savedComponentsConfig:
                    paasElementsVisObj[(apID, paaID)].actor.actor.scale = (
                        scale, scale, scale)

        # STAs
        # We get the position of the antenna elements and we magnified it as in reality, the antenna elements are too close to each other to be visualized
        xAntennaElementPositionSTA = codebooks.getStaPaaElementPositions()[::3] * paaMagnifier
        yAntennaElementPositionSTA = codebooks.getStaPaaElementPositions()[1::3] * paaMagnifier
        zAntennaElementPositionSTA = codebooks.getStaPaaElementPositions()[2::3] * paaMagnifier

        if self.savedComponentsConfig:
            # If the user saved his config, use it
            scale = self.componentsConfig.rxPaaMagnifier
            self.guiStaPaaMagnifier = self.componentsConfig.rxPaaMagnifier
        else:
            # Default value
            scale = 1

        for staID in range(qdScenario.nbAps, qdScenario.nbNodes):
            for paaID in range(codebooks.getNbPaaPerSta()):
                paasElementsVisObj[(staID, paaID)] = mlab.points3d(xAntennaElementPositionSTA,
                                                                   yAntennaElementPositionSTA,
                                                                   zAntennaElementPositionSTA,
                                                                   scale_factor=0.1, scale_mode="none",
                                                                   figure=self.view1.mayavi_scene, mode='cube',
                                                                   name="STA:" + str(staID) + " PAA", reset_zoom=False)
                paasElementsVisObj[(staID, paaID)].actor.property.edge_visibility = True
                paasElementsVisObj[(staID, paaID)].actor.property.line_width = 0.6

                if self.savedComponentsConfig:
                    paasElementsVisObj[(staID, paaID)].actor.actor.scale = (
                        scale, scale, scale)
                # self.updatePaaGeometry(self.traceIndex, staID, paaID)
        return paasElementsVisObj

    def createSensingVisuals(self):
        """Create the visuals for the sensing mode

        Parameters
        ----------
        self : Class
            The visualization class holding the entire visualization (GUIs, visual objects, etc)
        """
        print("\tCreate Sensing Targets")
        targetJointsVisObj = []
        targetJointsConnectionsVisObj = []
        ################### Targets Creation ########################
        viridis = cm.get_cmap('viridis', qdScenario.nbTargets)

        targetVisualizationConfig = []

        savedSensingConfig = False
        sensingConfigFile = os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder,
                                         globals.sensingConfigFile)
        if os.path.exists(sensingConfigFile):
            # A configuration exits - Load it
            colorTargetsRgb = pickle.load(
                open(sensingConfigFile, "rb"))
            savedSensingConfig = True
        else:
            colorTargetsRgb = []

        for i in range(qdScenario.nbTargets):
            # Create the visualization for each individual target
            jointsConnections = qdScenario.targetConnection[i] # Get the joint connections for the target
            # Start with the joints visualization
            xTargetCoordinates, yTargetCoordinates, zTargetCoordinates = qdScenario.targetPosition[i][0, ::, ::]
            targetJointsVisObj.append(mlab.points3d(xTargetCoordinates, yTargetCoordinates, zTargetCoordinates,
                                                    vmin=0, vmax=qdScenario.nbTargets,
                                                    scale_factor=0.1,
                                                    scale_mode="none", figure=self.view2.mayavi_scene,
                                                    name="PointsTarget" + str(i), reset_zoom=False))
            if not savedSensingConfig:
                # Color the target joints based on their IDs using Viridis colormap
                colorToAssign = viridis(i / (qdScenario.nbTargets))
                # We keep the color assigned for the targets in (r,g,b) format
                colorTargetsRgb.append([colorToAssign[0] * 255, colorToAssign[1] * 255, colorToAssign[2] * 255, 255])
            else:
                colorToAssign = [colorTargetsRgb[i][0] / 255, colorTargetsRgb[i][1] / 255, colorTargetsRgb[i][2] / 255]
            targetJointsVisObj[-1].actor.property.color = (
                colorToAssign[0], colorToAssign[1], colorToAssign[2])
            self.makeInvisible(targetJointsVisObj[i])

            # Create the visualization for the joints connections
            targetJointsVisObj[i].mlab_source.dataset.lines = np.array(
                jointsConnections)
            tube = mlab.pipeline.tube(targetJointsVisObj[i],
                                      figure=self.view2.mayavi_scene)
            tube.filter.number_of_sides = 6
            targetJointsConnectionsVisObj.append(
                mlab.pipeline.surface(tube, name="TubesTarget" + str(i), figure=self.view2.mayavi_scene))
            targetJointsConnectionsVisObj[-1].actor.property.color = (
                colorToAssign[0], colorToAssign[1], colorToAssign[2])
            self.makeInvisible(targetJointsConnectionsVisObj[i])

            # Keep the visualization config of the target (hardcoded 1 corresponds to the MPCs width that can't be change right now)
            targetVisualizationConfig.append(TargetsVisualizationConfig(1, colorToAssign))

        # Create all targets visualization
        # All targets are stored in the last element to speed-up the display
        # It's faster to udpate one objects containing x targets than x Targets objects

        # Get the coordinates of all targets
        xTargetCoordinates, yTargetCoordinates, zTargetCoordinates = qdScenario.targetPosition[-1][0, ::, ::]
        # To color the targets, we are going to use scalar values
        # We need to color all the joints of each target according to the color sets to each individual target
        s = np.arange(xTargetCoordinates.shape[0])
        lut = np.zeros((xTargetCoordinates.shape[0], 4))  # Colormap containing only the color assigned to each target
        nbJointsAllTargets = 0
        for targetId in range(qdScenario.nbTargets):
            jointsConnections = qdScenario.targetConnection[targetId]
            # Construct the colormap with the colors assigned to each individual target
            nbJointsTarget = qdScenario.targetPosition[targetId][0, ::, ::][0].shape[0]
            lut[nbJointsAllTargets:nbJointsAllTargets + nbJointsTarget] = np.full((nbJointsTarget, 4),
                                                                                  colorTargetsRgb[targetId])
            # We create the connections between all the joints for each target
            if targetId == 0:
                allTargetConnections = np.asarray(jointsConnections)
            else:
                npConnectionHumanTargetCurrent = np.array(jointsConnections) + nbJointsAllTargets
                allTargetConnections = np.append(allTargetConnections, npConnectionHumanTargetCurrent, axis=0)
            nbJointsAllTargets += nbJointsTarget

        targetJointsVisObj.append(
            mlab.points3d(xTargetCoordinates, yTargetCoordinates, zTargetCoordinates, s, scale_factor=0.1,
                          scale_mode="none",
                          figure=self.view2.mayavi_scene,
                          name="AllPointsTargets", reset_zoom=False))
        # Assign the colormap to the targets
        if len(s) != 1:
            # When there is only one joint, we can't color them according to a colormap as it would require two colors TODO: Check how to fix this cornercase
            targetJointsVisObj[-1].module_manager.scalar_lut_manager.lut.number_of_colors = len(s)
            targetJointsVisObj[-1].module_manager.scalar_lut_manager.lut.table = lut



        self.makeInvisible(targetJointsVisObj[-1])
        # Create the visualization for all joints connections
        connections = allTargetConnections
        targetJointsVisObj[-1].mlab_source.dataset.lines = np.array(connections)
        tube = mlab.pipeline.tube(targetJointsVisObj[-1],
                                  figure=self.view2.mayavi_scene)
        if len(s)!=1:
            # When there is only one joint, we can't color them according to a colormap as it would require two colors TODO: Check how to fix this cornercase
            targetJointsConnectionsVisObj.append(
                mlab.pipeline.surface(tube, name="TubesTargetAll", figure=self.view2.mayavi_scene))
             # Assign the color of each target to its joints connection
            targetJointsConnectionsVisObj[-1].module_manager.scalar_lut_manager.lut.table = lut
        self.makeInvisible(targetJointsConnectionsVisObj[-1])
        ################### Targets MPCs Creation ########################
        # Create the visualization for the MPCs between Tx and Rx Nodes to the each individual target
        targetsVisualizationProperties = TargetsVisualizationProperties(targetVisualizationConfig, False, False)

        # Create each individual target MPCs
        pointsNodesTargetsReflections = []  # Reflections Points from all nodes to all targets all reflections
        mpcNodesTargetsReflections = []  # MPCs from all nodes to all targets all reflections
        mpcOpacity = [1, 0.05, 0.01]  # TODO Not hardcoded

        for nodeId in range(qdScenario.nbNodes):
            pointsNodeTargetsReflections = []  # Reflections Points from one node to all targets all reflections
            mpcNodeAllTargetsReflections = []  # MPCs from one node to all targets all reflections
            for targetId in range(qdScenario.nbTargets):
                pointsNodeTargetReflections = []  # Reflection Points from one node to one target all reflections
                mpcNodeTargetReflections = []  # MPCs from one node to one target all reflections
                for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                    # Create the visualization for the reflection points from one node to one target for a reflection order
                    xMpcCoordinate, yMpcCoordinate, zMpcCoordinate, connections = qdRealization.getTargetMpcCoordinates(
                        nodeId, targetId, reflectionOrder, self.traceIndex)
                    pointsNodeTargetReflections.append(
                        mlab.points3d(xMpcCoordinate, yMpcCoordinate, zMpcCoordinate,
                                      scale_factor=0.05,
                                      scale_mode="none", figure=self.view2.mayavi_scene,
                                      name="ReflectionPoints Node:" + str(nodeId) + "Target:" + str(
                                          targetId) + "Reflection:" + str(reflectionOrder), reset_zoom=False))
                    pointsNodeTargetReflections[-1].mlab_source.dataset.lines = np.array(connections)
                    self.makeInvisible(pointsNodeTargetReflections[-1])

                    # Create the MPCs connecting one node to one target for a reflection order
                    tube = mlab.pipeline.tube(pointsNodeTargetReflections[-1],
                                              tube_radius=0.007,
                                              figure=self.view2.mayavi_scene)
                    tube.filter.number_of_sides = 3
                    mpcNodeTargetReflections.append(mlab.pipeline.surface(tube, name="MPC Node:" + str(
                        nodeId) + "Target:" + str(targetId) + "Reflection:" + str(reflectionOrder),
                                                                          figure=self.view2.mayavi_scene))
                    if not savedSensingConfig:
                        # Color the target joints based on their IDs using Viridis colormap
                        colorToAssign = viridis(targetId / (qdScenario.nbTargets))
                        # We keep the color assigned for the targets in (r,g,b) format
                        colorTargetsRgb.append(
                            [colorToAssign[0] * 255, colorToAssign[1] * 255, colorToAssign[2] * 255, 255])
                    else:
                        colorToAssign = [colorTargetsRgb[targetId][0] / 255, colorTargetsRgb[targetId][1] / 255,
                                         colorTargetsRgb[targetId][2] / 255]

                    mpcNodeTargetReflections[-1].actor.property.color = (
                        colorToAssign[0], colorToAssign[1], colorToAssign[2])
                    self.makeInvisible(mpcNodeTargetReflections[-1])
                    mpcNodeTargetReflections[-1].actor.property.lighting = False
                    mpcNodeTargetReflections[-1].actor.property.opacity = mpcOpacity[reflectionOrder]

                pointsNodeTargetsReflections.append(pointsNodeTargetReflections)
                mpcNodeAllTargetsReflections.append(mpcNodeTargetReflections)
            pointsNodesTargetsReflections.append(pointsNodeTargetsReflections)
            mpcNodesTargetsReflections.append(mpcNodeAllTargetsReflections)

        # Create all targets MPCs

        pointsNodesAllTargetsReflections = []  # Reflections Points from all to all targets all reflections
        mpcNodesAllTargetsReflections = []  # MPCs connecting all nodes to all targets all reflections

        for nodeId in range(qdScenario.nbNodes):
            pointsNodeAllTargetsReflections = []  # Reflections Points from one node to all targets all reflections
            mpcNodeAllTargetsReflections = []  # MPCs connecting one node to all targets all reflections
            for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                # Create the visualization for the reflection points from one node to all targets for a reflection order
                xMpcCoordinate, yMpcCoordinate, zMpcCoordinate, connections = qdRealization.getTargetAllMpcCoordinates(
                    nodeId, reflectionOrder, self.traceIndex)

                # To color the targets MPCs, we are going to use scalar values
                # We need to color all the MPCs of each target according to the color sets to each individual target
                # and to the correct boundaries of each target MPCs
                s = np.arange(xMpcCoordinate.shape[0])
                lut = np.zeros((xMpcCoordinate.shape[0], 4))
                totalMPCs = 0
                for targetId in range(qdScenario.nbTargets):
                    nbMPCsCurrentTarget = \
                        qdRealization.sizeTrcsNdsRlfsTgtsJts[self.traceIndex][nodeId][reflectionOrder][
                            targetId]
                    # The MPCs boundaries to color are given by the number of MPCs for the current target and the total number of MPCs so far
                    lut[totalMPCs:totalMPCs + nbMPCsCurrentTarget] = np.full((nbMPCsCurrentTarget, 4),
                                                                             colorTargetsRgb[targetId])
                    totalMPCs += nbMPCsCurrentTarget
                pointsNodeAllTargetsReflections.append(
                    mlab.points3d(xMpcCoordinate, yMpcCoordinate, zMpcCoordinate, s,
                                  scale_factor=0.05,
                                  scale_mode="none", figure=self.view2.mayavi_scene,
                                  name="ReflectionPoints Node:" + str(nodeId) + "AllTargets Refl:" + str(
                                      reflectionOrder), reset_zoom=False))
                pointsNodeAllTargetsReflections[
                    -1].module_manager.scalar_lut_manager.lut.number_of_colors = len(s)
                pointsNodeAllTargetsReflections[-1].module_manager.scalar_lut_manager.lut.table = lut
                self.makeInvisible(pointsNodeAllTargetsReflections[-1])

                # Create the MPCs connecting one node to all target for a given reflection order
                tube = mlab.pipeline.tube(pointsNodeAllTargetsReflections[-1],
                                          tube_radius=0.007,
                                          figure=self.view2.mayavi_scene)
                tube.filter.number_of_sides = 3
                mpcNodeAllTargetsReflections.append(mlab.pipeline.surface(tube, name="MPCs Node:" + str(
                    nodeId) + "AllTargets Refl:" + str(reflectionOrder), figure=self.view2.mayavi_scene))
                mpcNodeAllTargetsReflections[-1].module_manager.scalar_lut_manager.lut.table = lut
                mpcNodeAllTargetsReflections[-1].actor.property.lighting = False
                mpcNodeAllTargetsReflections[-1].actor.property.opacity = mpcOpacity[reflectionOrder]

            pointsNodesAllTargetsReflections.append(pointsNodeAllTargetsReflections)
            mpcNodesAllTargetsReflections.append(mpcNodeAllTargetsReflections)

        filteredIndexes = 0
        velocityLow = qdScenario.qdInterpreterConfig.filterVelocity[0]
        velocityHigh = qdScenario.qdInterpreterConfig.filterVelocity[1]
        dopplerRangeObjVis = 0
        axesDopplerRange = 0
        if qdRealization.sensingResults.available:
            # Sensing results were provided
            # Create the doppler range graph
            speedOfLight = 299792458
            x = qdRealization.sensingResults.fastTime * speedOfLight  # Fast Time is delay - Turn it into a range
            # Filter the velocity (default is not to filter velocity as the range is set to -inf +inf)
            filteredIndexes = (qdRealization.sensingResults.velocity < velocityHigh) & (
                    qdRealization.sensingResults.velocity > velocityLow)
            y = qdRealization.sensingResults.velocity[filteredIndexes]
            z = np.zeros((len(y), len(x)))
            z = np.transpose(z, (1, 0))

            dopplerRangeObjVis = mlab.surf(x, y, z, name="DopplerRange", warp_scale=0,
                                           figure=self.view3.mayavi_scene)
            dopplerRangeObjVis.actor.mapper.interpolate_scalars_before_mapping = True
            dopplerRangeObjVis.actor.property.lighting = False
            dopplerRangeObjVis.actor.actor.scale = [10., 5., 1.]

        return targetJointsVisObj, targetJointsConnectionsVisObj, targetVisualizationConfig, targetsVisualizationProperties, colorTargetsRgb, \
               pointsNodesTargetsReflections, mpcNodesTargetsReflections, pointsNodesAllTargetsReflections, mpcNodesAllTargetsReflections, velocityHigh, velocityLow, filteredIndexes, dopplerRangeObjVis, axesDopplerRange

    def createEnvironmentVisuals(self):
        """Create the 3D environments (buildings, walls, etc.)

        Parameters
        ----------
        self : Class
            The self class holding the entire self (GUIs, visual objects, etc)
        """
        print("\tBuild the 3D environment")
        globals.logger.info("Create 3D Environment")

        # global environmentObjects, materialProperties, scenesProperties

        previousConfigurationSaved = False
        sceneVisualizerConfig = {}
        if os.path.exists(
                os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder, globals.view1ConfigFile)):
            # Check if the user saved a previous self configuration
            print("A previous configuration was saved for view1 and view 2 - Load it")
            sceneVisualizerConfig[self.view1.mayavi_scene] = pickle.load(
                open(os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder, globals.view1ConfigFile),
                     "rb"))  # Load the config

            sceneVisualizerConfig[self.view2.mayavi_scene] = pickle.load(
                open(os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder, globals.view2ConfigFile),
                     "rb"))  # Load the config
            previousConfigurationSaved = True

        if previousConfigurationSaved:
            # The Scene properties have been saved - Use them
            view1properties = sceneVisualizerConfig[self.view1.mayavi_scene].sceneVisualizationProperties
            view2properties = sceneVisualizerConfig[self.view2.mayavi_scene].sceneVisualizationProperties
        else:
            # Use the default configuration, i.e., View1 textured and no edge visibility and view 2 the opposite
            view1properties = SceneVisualizationProperties("Texture", False)
            view2properties = SceneVisualizationProperties("Material", True)

        # Construct the 3D representation of the environment
        self.scenesProperties = {}
        self.scenesProperties[self.view1.mayavi_scene] = view1properties
        self.scenesProperties[self.view2.mayavi_scene] = view2properties
        self.objFile, self.materialProperties, self.environmentObjects = constructEnvironment(environmentFile, self.engine1,
                                                                               self.scenesProperties, globals.textureFolder)

        if previousConfigurationSaved:
            # If a previous configuration has been saved, we modify the constructed 3D environment with \
            # the parameters saved for every object (Texures, opacity, etc.)
            for sceneTo in self.scenesProperties.keys():
                for i in range(len(self.environmentObjects[self.view1.mayavi_scene])):
                    self.environmentObjects[sceneTo][i].frontFaceCulling = sceneVisualizerConfig[sceneTo].sceneObjects[
                        i].frontFaceCulling
                    self.environmentObjects[sceneTo][i].mesh.actor.actor.property.frontface_culling = \
                        sceneVisualizerConfig[sceneTo].sceneObjects[i].frontFaceCulling

                    self.environmentObjects[sceneTo][i].mesh.actor.actor.property.backface_culling = \
                        sceneVisualizerConfig[sceneTo].sceneObjects[i].backFaceCulling

                    self.environmentObjects[sceneTo][i].hidden = sceneVisualizerConfig[sceneTo].sceneObjects[i].hidden
                    self.environmentObjects[sceneTo][i].mesh.actor.actor.visibility = not (
                        sceneVisualizerConfig[sceneTo].sceneObjects[i].hidden)

                    self.environmentObjects[sceneTo][i].opacity = sceneVisualizerConfig[sceneTo].sceneObjects[i].opacity
                    self.environmentObjects[sceneTo][i].mesh.actor.property.opacity = \
                        sceneVisualizerConfig[sceneTo].sceneObjects[i].opacity

                    if sceneVisualizerConfig[sceneTo].sceneObjects[i].colorChanged:
                        self.environmentObjects[sceneTo][i].colorChanged = sceneVisualizerConfig[sceneTo].sceneObjects[
                            i].colorChanged
                        self.environmentObjects[sceneTo][i].customColor = sceneVisualizerConfig[sceneTo].sceneObjects[
                            i].customColor

                        colorPicked = sceneVisualizerConfig[sceneTo].sceneObjects[i].customColor
                        self.environmentObjects[sceneTo][i].mesh.actor.property.color = (
                            colorPicked[0], colorPicked[1], colorPicked[2])

                    if sceneVisualizerConfig[sceneTo].sceneObjects[i].customTexture != "":
                        self.environmentObjects[sceneTo][i].customTexture = sceneVisualizerConfig[sceneTo].sceneObjects[
                            i].customTexture
                        self.environmentObjects[sceneTo][i].textureMode = sceneVisualizerConfig[sceneTo].sceneObjects[
                            i].textureMode
                        self.assignMaterialTexture(self.environmentObjects[sceneTo][i])

    def createDefaultSlsMpcsProperties(self):
        """Create the default properties for the SLS MPCs reflection orders

        Parameters
        ----------
        self : Class
            The self class holding the entire self (GUIs, visual objects, etc)
        """

        defaultReflectionOrderColor = []
        # Each reflection order MPC will be colored acoording to these values
        defaultReflectionOrderColor.append((0, 0, 1))  # Blue
        defaultReflectionOrderColor.append((1, 0, 0))  # Red
        defaultReflectionOrderColor.append((0, 1, 0))  # Green
        defaultReflectionOrderColor.append((1.0, 0.7529411764705882, 1.0))  # Pink
        defaultReflectionOrderColor.append((0, 1, 1))  # Cyan
        defaultReflectionOrderColor.append((1, 1, 0))  # Yellow
        defaultReflectionOrderColor.append((1.0, 0.5019607843137255, 0.0))  # Orange
        defaultReflectionOrderColor.append((1.0, 0, 1.0))  # Fuschia
        return defaultReflectionOrderColor

    def createDefaultMimoStreamProperties(self):
        """Create the default properties for the MIMO streams

        Parameters
        ----------
        self : Class
            The self class holding the entire self (GUIs, visual objects, etc)
        """
        defaultMimoStreamColor = []
        # Each stream will be using a given color for its MPCs and antenna pattern edge
        defaultMimoStreamColor.append((1, 0, 0))  # Red
        defaultMimoStreamColor.append((0, 0, 1))  # Blue
        defaultMimoStreamColor.append((0, 1, 0))  # Green
        defaultMimoStreamColor.append((1.0, 0.7529411764705882, 1.0))  # Pink
        defaultMimoStreamColor.append((0, 1, 1))  # Cyan
        defaultMimoStreamColor.append((1, 1, 0))  # Yellow
        defaultMimoStreamColor.append((1.0, 0.5019607843137255, 0.0))  # Orange
        defaultMimoStreamColor.append((1.0, 0, 1.0))  # Fuschia
        return defaultMimoStreamColor

    def createAntennaPatternSectors(self):
        """Create the visuals for the antenna patterns corresponding to the sectors

            Parameters
            ----------
            self : Class
                The self class holding the entire self (GUIs, visual objects, etc)
        """
        # Precreate the sectors Antenna Pattern for the AP and the STA (used for the transmission in the SLS phase)
        # We precreate them in order to obtain best performance once the visualizer is running
        # AP Sectors Antenna Pattern creation
        txSectorsAntennaPatternVisObj = []  # Contain all the Antenna Patterns for STAs and APs all sectors all PAA all role (i.e, transmitter or receiver)
        colorValue = [0, 1]
        globals.printProgressBarWithoutETA(0, qdScenario.nbNodes, prefix='Visualizer: Build AP Antenna Patterns:',
                                           suffix='Complete', length=50)

        if self.savedComponentsConfig:
            # If the user saved his config, use it
            scale = self.componentsConfig.apAntennaPatternMagnifier
            self.guiApAntennaPatternMagnifier = scale
        else:
            # Default value
            scale = 1
        # antennaPatternTxRx[0][26][0] # If TX and sector 26 for PAA 0
        # antennaPatternTxRx[1][4][1] # If Rx and sector 4 for PAA 1
        antennaPatternPaaSectorTxRx = []  # Antenna Patterns for all PAAs all sectors all roles (Tx or Rx)
        activateCprofile = False
        if activateCprofile == True:
            pr = cProfile.Profile()
            pr.enable()
        filterBySize = qdScenario.qdInterpreterConfig.patternQuality

        # We will use numpy array so we want the same shape for both AP and STA antenna patterns data
        if codebooks.getNbPaaPerAp() < codebooks.getNbPaaPerSta():
            # STAs have more PAAs - We must extend the data
            nbPaaIdToIterate = codebooks.getNbPaaPerSta()
        else:
            # APs have more PAAs - Nothing to do
            nbPaaIdToIterate = codebooks.getNbPaaPerAp()

        for paaId in range(nbPaaIdToIterate):
            # antennaPatternTxRx[26][0] # If TX and sector 26
            # antennaPatternTxRx[4][1] # If Rx and sector 4
            antennaPatternSectorTxRx = []  # Antenna Patterns for all sectors all roles (Tx or Rx)
            for sectorId in range(codebooks.getNbSectorPerApAntenna()):
                antennaPatternTxRx = []  # Antenna Patterns for one sector all roles (Tx or Rx)
                # antennaPatternTxRx[0] # If TX
                # antennaPatternTxRx[1] # If Rx
                for role in range(2):
                    if paaId < codebooks.getNbPaaPerAp():
                        # Normal case - We create the APs antenna patterns
                        xAntennaPattern = codebooks.getApSectorPattern(sectorId, paaId)[0][::filterBySize]
                        yAntennaPattern = codebooks.getApSectorPattern(sectorId, paaId)[1][::filterBySize]
                        zAntennaPattern = codebooks.getApSectorPattern(sectorId, paaId)[2][::filterBySize]
                        colorAntennaPattern = codebooks.getApSectorPattern(sectorId, paaId)[3][::filterBySize]
                        antennaPatternTxRx.append(mlab.mesh(xAntennaPattern,
                                                            yAntennaPattern,
                                                            zAntennaPattern,
                                                            vmin=min(colorValue),
                                                            vmax=max(colorValue),
                                                            # tube_radius=0.025,
                                                            resolution=0,
                                                            tube_radius=None,

                                                            # tube_sides = 0,
                                                            tube_sides=0,
                                                            figure=self.view2.mayavi_scene,
                                                            name="Antenna Pattern AP - Sector: " + str(
                                                                sectorId + 1) + " Antenna: " + str(
                                                                paaId + 1) + " Role: " + str(
                                                                role),
                                                            reset_zoom=False,
                                                            scalars=colorAntennaPattern))
                        # antennaPatternTxRx[-1].mlab_source.dataset.poly_data.splitting = False
                        antennaPatternTxRx[-1].actor.property.specular = 1.0
                        antennaPatternTxRx[-1].actor.property.specular_power = 66.0
                        if self.savedComponentsConfig:
                            antennaPatternTxRx[-1].actor.actor.scale = (
                                scale, scale, scale)
                        if role == 1:
                            globals.printProgressBarWithoutETA(
                                (sectorId + paaId * codebooks.getNbSectorPerApAntenna() + 1) * 2,
                                (codebooks.getNbPaaPerAp() * codebooks.getNbSectorPerApAntenna()) * 2,
                                prefix='Visualizer: Build AP Antenna Patterns:',
                                suffix='Complete', length=50)

                        # Hide the antenna pattern
                        antennaPatternTxRx[-1].actor.actor.visibility = False
                    else:
                        # Case where STAs have more PAAs than APs -
                        # Fill the data with zero to obtain the same shape for APs and STAs Antenna Patterns
                        antennaPatternTxRx.append(0)
                antennaPatternSectorTxRx.append(antennaPatternTxRx)
            antennaPatternPaaSectorTxRx.append(antennaPatternSectorTxRx)
        txSectorsAntennaPatternVisObj.append(antennaPatternPaaSectorTxRx)
        if activateCprofile == True:
            pr.disable()
            s = io.StringIO()
            sortby = SortKey.CUMULATIVE
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats()
            f = open("dump.txt", "w")
            f.write(s.getvalue())

        # STA Sectors Antenna Pattern creation
        globals.printProgressBarWithoutETA(0, qdScenario.nbNodes, prefix='Visualizer: Build STA Antenna Patterns:',
                                           suffix='Complete', length=50)
        if self.savedComponentsConfig:
            # If the user saved his config, use it
            scale = self.componentsConfig.staAntennaPatternMagnifier
            self.guiStaAntennaPatternMagnifier = scale
        else:
            # Default value
            scale = 1
        antennaPatternPaaSectorTxRx = []

        # We will use numpy array so we want the same shape for both AP and STA antenna patterns data
        if codebooks.getNbPaaPerSta() < codebooks.getNbPaaPerAp():
            # APs have more PAAs - We must extend the data
            nbPaaIdToIterate = codebooks.getNbPaaPerAp()
        else:
            # STAs have more PAAs - Nothing to do
            nbPaaIdToIterate = codebooks.getNbPaaPerSta()

        for paaId in range(nbPaaIdToIterate):
            antennaPatternSectorTxRx = []
            for sectorId in range(codebooks.getNbSectorPerStaAntenna()):
                antennaPatternTxRx = []
                for role in range(2):
                    if paaId < codebooks.getNbPaaPerSta():
                        # Normal case - We create the STAs antenna patterns
                        xAntennaPattern = codebooks.getStaSectorPattern(sectorId, paaId)[0][::filterBySize]
                        yAntennaPattern = codebooks.getStaSectorPattern(sectorId, paaId)[1][::filterBySize]
                        zAntennaPattern = codebooks.getStaSectorPattern(sectorId, paaId)[2][::filterBySize]
                        colorAntennaPattern = codebooks.getStaSectorPattern(sectorId, paaId)[3][::filterBySize]
                        antennaPatternTxRx.append(mlab.mesh(xAntennaPattern,
                                                            yAntennaPattern,
                                                            zAntennaPattern,
                                                            vmin=min(colorValue),
                                                            vmax=max(colorValue),
                                                            tube_radius=0.025,
                                                            figure=self.view2.mayavi_scene,
                                                            name="Antenna Pattern STA - Sector: " + str(
                                                                sectorId + 1) + " Antenna: " + str(
                                                                paaId + 1) + " Role: " + str(role),
                                                            reset_zoom=False,
                                                            scalars=colorAntennaPattern))
                        antennaPatternTxRx[-1].actor.property.specular = 1.0
                        antennaPatternTxRx[-1].actor.property.specular_power = 66.0
                        # Hide the antenna pattern
                        antennaPatternTxRx[-1].actor.actor.visibility = False

                        if self.savedComponentsConfig:
                            antennaPatternTxRx[-1].actor.actor.scale = (
                                scale, scale, scale)
                        if role == 1:
                            globals.printProgressBarWithoutETA(
                                (sectorId + paaId * codebooks.getNbSectorPerStaAntenna() + 1) * 2,
                                (codebooks.getNbPaaPerSta() * codebooks.getNbSectorPerStaAntenna()) * 2,
                                prefix='Visualizer: Build STA Antenna Patterns:',
                                suffix='Complete', length=50)
                    else:
                        # Case where APs have more PAAs than STAs -
                        # Fill the data with zero to obtain the same shape for APs and STAs Antenna Patterns
                        antennaPatternTxRx.append(0)
                antennaPatternSectorTxRx.append(antennaPatternTxRx)
            antennaPatternPaaSectorTxRx.append(antennaPatternSectorTxRx)
        txSectorsAntennaPatternVisObj.append(antennaPatternPaaSectorTxRx)

        #  Quasi-omni Antenna Pattern creation (not used in this version)
        # Precreate the quasi-omni patterns for both AP and STA
        # global quasiOmniAntennaPatternVisObj
        quasiOmniAntennaPatternVisObj = {}
        # AP quasi-omni pattern

        if self.savedComponentsConfig:
            # If the user saved his config, use it
            scale = self.componentsConfig.apAntennaPatternMagnifier
            self.guiApAntennaPatternMagnifier = scale
        else:
            # Default value
            scale = 1

        for paaId in range(codebooks.getNbPaaPerAp()):
            xAntennaPattern = codebooks.getApQuasiOmniPattern(paaId)[0]
            yAntennaPattern = codebooks.getApQuasiOmniPattern(paaId)[1]
            zAntennaPattern = codebooks.getApQuasiOmniPattern(paaId)[2]
            colorAntennaPattern = codebooks.getApQuasiOmniPattern(paaId)[3]
            quasiOmniAntennaPatternVisObj[globals.NodeType.AP, paaId] = mlab.mesh(xAntennaPattern, yAntennaPattern,
                                                                                  zAntennaPattern,
                                                                                  vmin=min(colorValue),
                                                                                  vmax=max(colorValue),
                                                                                  tube_radius=0.025,
                                                                                  figure=self.view2.mayavi_scene,
                                                                                  name="Quasi-Antenna Pattern AP PAA:" + str(
                                                                                      paaId),
                                                                                  reset_zoom=False,
                                                                                  scalars=colorAntennaPattern)
            quasiOmniAntennaPatternVisObj[globals.NodeType.AP, paaId].actor.property.specular = 1.0
            quasiOmniAntennaPatternVisObj[globals.NodeType.AP, paaId].actor.property.specular_power = 66.0
            quasiOmniAntennaPatternVisObj[globals.NodeType.AP, paaId].actor.actor.visibility = False
            if self.savedComponentsConfig:
                quasiOmniAntennaPatternVisObj[globals.NodeType.AP, paaId].actor.actor.scale = (
                    scale, scale, scale)
            quasiOmniAntennaPatternVisObj[globals.NodeType.AP, paaId].actor.property.opacity = 1

        # STA quasi-omni pattern
        if self.savedComponentsConfig:
            # If the user saved his config, use it
            scale = self.componentsConfig.staAntennaPatternMagnifier
            self.guiStaAntennaPatternMagnifier = scale
        else:
            # Default value
            scale = 1
        for paaId in range(codebooks.getNbPaaPerSta()):
            xAntennaPattern = codebooks.getStaQuasiOmniPattern(paaId)[0]
            yAntennaPattern = codebooks.getStaQuasiOmniPattern(paaId)[1]
            zAntennaPattern = codebooks.getStaQuasiOmniPattern(paaId)[2]
            colorAntennaPattern = codebooks.getStaQuasiOmniPattern(paaId)[3]
            quasiOmniAntennaPatternVisObj[globals.NodeType.STA, paaId] = mlab.mesh(xAntennaPattern, yAntennaPattern,
                                                                                   zAntennaPattern,
                                                                                   vmin=min(colorValue),
                                                                                   vmax=max(colorValue),
                                                                                   tube_radius=0.025,
                                                                                   figure=self.view2.mayavi_scene,
                                                                                   name="Quasi-Antenna Pattern STA PAA:" + str(
                                                                                       paaId),
                                                                                   reset_zoom=False,
                                                                                   scalars=colorAntennaPattern)
            quasiOmniAntennaPatternVisObj[globals.NodeType.STA, paaId].actor.property.specular = 1.0
            quasiOmniAntennaPatternVisObj[globals.NodeType.STA, paaId].actor.property.specular_power = 66.0
            quasiOmniAntennaPatternVisObj[globals.NodeType.STA, paaId].actor.actor.visibility = False
            if self.savedComponentsConfig:
                quasiOmniAntennaPatternVisObj[globals.NodeType.STA, paaId].actor.actor.scale = (
                    scale, scale, scale)
            quasiOmniAntennaPatternVisObj[globals.NodeType.STA, paaId].actor.property.opacity = 1
        return np.asarray(txSectorsAntennaPatternVisObj), quasiOmniAntennaPatternVisObj

    def createOrientationAxis(self, scene, axisName):
        """Create a default orientation axis (oriented in the global coordinate system)

        Parameters
        ----------
        scene : Mayavi Scene
            Scene to display the triangular mesh

        Returns
        -------
        axesObject : Quiver 3d
            The constructed orientation axes
        """

        # Create three vectors aligned in the global coordinates system
        x = [0, 0, 0]
        y = [0, 0, 0]
        z = [0, 0, 0]
        u = [0, 0, 10]
        v = [0, 10, 0]
        w = [10, 0, 0]
        s = [1, 5, 10]
        axesObject = mlab.quiver3d(x, y, z, u, v, w, scalars=s, figure=scene,
                                   name=axisName)
        axesObject.glyph.color_mode = 'color_by_scalar'
        axesObject.actor.property.line_width = 5.0
        self.makeInvisible(axesObject)
        return axesObject

    #######################################################################
    #            FUNCTION TO UPDATE THE VISUALIZATION                     #
    #######################################################################
    @on_trait_change(
        'guiTxNodeSelected,guiRxNodeSelected,guiTargetSelected,guiTxPaaSelected,guiRxPaaSelected,traceIndex,guiDisplayPaaTxAxis,guiDisplayPaaRxAxis,guiDisplayDeviceTxAxis,guiDisplayDeviceRxAxis,guiDisplayMimo,guiBeamtrackingType,guiDisplaySls')
    def updateNewSelection(self, obj, name, old, new):
        """Handle most of the changes occuring in the interface (Tx/Rx selection changed, PAA Tx/Rx changed, etc)

        Parameters
        ----------
        self : Visualization Class
           The visualizer
        name : str
           Name of the selected parameter
       """
        activateCprofile = False
        if activateCprofile == True:
            pr = cProfile.Profile()
            pr.enable()

        # Clear the display
        self.clearDisplay()

        if qdScenario.qdInterpreterConfig.sensing:
            # Update sensing if enabled by user
            self.updateSensingVisuals()

        # Update the GUI messages
        txNode = int(self.guiTxNodeSelected)
        rxNode = int(self.guiRxNodeSelected)




        if txNode == rxNode:
            # Handle the case where the user clicked on switch Tx and Rx which triggers txNode to be equal to rxNode during the switch due to interruption
            return
        paaTx = int(self.guiTxPaaSelected)
        paaRx = int(self.guiRxPaaSelected)
        self.updateGuiTexts(txNode, rxNode, name) # Update the GUI texture Elements
        self.updateDevicesVisuals()  # Update all the visuals for STAs and APs
        globals.logger.debug("Update STA and AP antenna elements position")
        self.updatePaasVisuals(txNode, rxNode, paaTx, paaRx)  # Update the visuals for the PAAs
        self.updateMpcsVisuals(txNode, rxNode, paaTx, paaRx) # Update the MPCs between the selected Tx and Rx nodes
        if self.guiDisplayDeviceTxAxis or self.guiDisplayDeviceRxAxis or self.guiDisplayPaaTxAxis or self.guiDisplayPaaRxAxis:
            # Update orientation vectors
            self.updateOrientationAxes(txNode, rxNode, paaTx, paaRx)

        if qdScenario.qdInterpreterConfig.slsEnabled:
            if self.guiDisplaySls:
                if self.guiSlsMode == "Oracle":
                     if qdScenario.qdInterpreterConfig.dataMode != "none":
                        self.updateSlsVisuals(txNode, rxNode, paaTx, paaRx)
                     else:
                        globals.logger.warning(
                            "SLS mode selected: Oracle but dataMode set to None - Please set dataMode to online or preprocessed when launching the visualizer to visualize SLS with Oracle")
                elif self.guiSlsMode == "ns-3":
                    if not qdScenario.nsSlsResults.empty:
                        # Display SLS between Tx and Rx
                        self.updateSlsVisuals(txNode, rxNode, paaTx, paaRx)
                    else:
                        globals.logger.warning(
                            "SLS mode selected: ns-3 but no SLS results available")


                # Update the BFT ID in the GUI
                self.guiMaxSlsBftId = getNumberOfBft(int(self.guiTxNodeSelected), int(self.guiRxNodeSelected),
                                                     qdScenario) - 1



        if self.guiDisplayMimo!= "none" and self.guiDisplayMimo:
            # MIMO is enabled and user enables its visualization
            if qdScenario.qdInterpreterConfig.mimo == "suMimo":
                # Update SU-MIMO results
                self.updateSuMimoVisuals()
            elif qdScenario.qdInterpreterConfig.mimo == "muMimo":
                # Update MU-MIMO results
                self.updateMuMimoVisuals()
            elif qdScenario.qdInterpreterConfig.mimo == "beamTracking":
                # Update beamtracking results
                self.updateBeamTrackingStreamsPatterns(self.guiBeamtrackingType,
                                                       qdScenario.qdInterpreterConfig.codebookMode, txNode, rxNode,
                                                       self.traceIndex,
                                                       self.view2.mayavi_scene)

            if self.mimoStreamPatterns:
                # Update the GUI
                self.guiMimoStreamSize = self.mimoStreamPatternSize[self.guiMimoStream]
                self.guiMimoStreamColor = (self.mimoStreamProperties[self.guiMimoStream].color[0] * 255,
                                             self.mimoStreamProperties[self.guiMimoStream].color[1] * 255,
                                             self.mimoStreamProperties[self.guiMimoStream].color[2] * 255)

                self.guiMimoStreamMpcSize = self.mimoStreamProperties[self.guiMimoStream].width
                self.guiMimoEdgesSize = self.mimoStreamEdgeSize[self.guiMimoStream]

                if qdScenario.qdInterpreterConfig.mimo != "beamTracking":
                    # BeamTracking don't use the notion of PAA yet
                    self.guiMimoTxStreamIdentifier = self.bestreamPaaIdCombination[self.guiMimoStream][0]
                    self.guiMimoRxStreamIdentifier = self.bestreamPaaIdCombination[self.guiMimoStream][1]
                self.guiMimoTxSector = self.bestSectorsCombination[0][self.guiMimoStream]
                self.guiMimoRxSector = self.bestSectorsCombination[1][self.guiMimoStream]

        # Force the rendering
        self.forceRender()
        if activateCprofile == True:
            pr.disable()
            s = io.StringIO()
            sortby = SortKey.CUMULATIVE
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats()
            f = open("dump.txt", "w")
            f.write(s.getvalue())

    def updateSensingVisuals(self):
        """Update the sensing mode
        """
        if self.guiTargetSelected == "All":
            # User wants to display all targets simultaneously
            # Make invisible all the individual targets joints and their joint connections
            for i in range(len(self.targetJointsVisObj) - 1):
                self.makeInvisible(self.targetJointsVisObj[i])
                self.makeInvisible(self.targetJointsConnectionsVisObj[i])

            # Display all the targets joints and their joints connections
            xTargetCoordinates, yTargetCoordinates, zTargetCoordinates = qdScenario.targetPosition[
                                                                             -1][
                                                                         int(self.traceIndex), ::, ::]

            self.targetJointsVisObj[-1].mlab_source.trait_set(x=xTargetCoordinates,
                                                              y=yTargetCoordinates,
                                                              z=zTargetCoordinates)
            self.makeVisible(self.targetJointsVisObj[-1])
            self.makeVisible(self.targetJointsConnectionsVisObj[-1])

            # Make invisible all the individual MPCs between all nodes and all targets for all reflections
            for nodeId in range(qdScenario.nbNodes):
                for targetId in range(qdScenario.nbTargets):
                    for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                        self.makeInvisible(
                            self.mpcNodesTargetsReflections[nodeId][targetId][
                                reflectionOrder])

            if not self.targetsVisualizationProperties.mpcsNodesTargetHidden:
                # If the user wants to display the target MPCs, display them
                for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                    # From Tx Node to Target
                    xMpcCoordinate, yMpcCoordinate, zMpcCoordinate, connections = qdRealization.getTargetAllMpcCoordinates(
                        int(self.guiTxNodeSelected), reflectionOrder, self.traceIndex)
                    xMpcCoordinate = np.nan_to_num(xMpcCoordinate)
                    yMpcCoordinate = np.nan_to_num(yMpcCoordinate)
                    zMpcCoordinate = np.nan_to_num(zMpcCoordinate)
                    self.pointsNodesAllTargetsReflections[int(self.guiTxNodeSelected)][
                        reflectionOrder].mlab_source.set(x=xMpcCoordinate, y=yMpcCoordinate,
                                                         z=zMpcCoordinate)

                    self.pointsNodesAllTargetsReflections[int(self.guiTxNodeSelected)][
                        reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                    self.makeVisible(
                        self.mpcNodesAllTargetsReflections[int(self.guiTxNodeSelected)][reflectionOrder])

                    # From Rx Node to Target
                    xMpcCoordinate, yMpcCoordinate, zMpcCoordinate, connections = qdRealization.getTargetAllMpcCoordinates(
                        int(self.guiRxNodeSelected), reflectionOrder, self.traceIndex)
                    self.pointsNodesAllTargetsReflections[int(self.guiRxNodeSelected)][
                        reflectionOrder].mlab_source.set(x=xMpcCoordinate, y=yMpcCoordinate,
                                                         z=zMpcCoordinate)

                    self.pointsNodesAllTargetsReflections[int(self.guiRxNodeSelected)][
                        reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                    self.makeVisible(
                        self.mpcNodesAllTargetsReflections[int(self.guiRxNodeSelected)][reflectionOrder])
            else:
                for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                    self.makeInvisible(
                        self.mpcNodesAllTargetsReflections[int(self.guiTxNodeSelected)][reflectionOrder])

                    self.makeInvisible(
                        self.mpcNodesAllTargetsReflections[int(self.guiRxNodeSelected)][reflectionOrder])
        else:
            # Update the GUI color
            self.guiSensingTargetColor = (self.colorTargetsRgb[int(self.guiTargetSelected)][0],
                                          self.colorTargetsRgb[int(self.guiTargetSelected)][1],
                                          self.colorTargetsRgb[int(self.guiTargetSelected)][2])

            # Display the selected target if wanted
            for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                self.makeInvisible(
                    self.mpcNodesAllTargetsReflections[int(self.guiRxNodeSelected)][reflectionOrder])
                self.makeInvisible(
                    self.mpcNodesAllTargetsReflections[int(self.guiTxNodeSelected)][reflectionOrder])
            # Hide previously displayed targets
            for i in range(len(self.targetJointsVisObj) - 1):
                self.makeInvisible(self.targetJointsVisObj[i])
                self.makeInvisible(self.targetJointsConnectionsVisObj[i])
            # Mask all targets
            self.makeInvisible(self.targetJointsVisObj[-1])
            self.makeInvisible(self.targetJointsConnectionsVisObj[-1])

            xTargetCoordinates, yTargetCoordinates, zTargetCoordinates = qdScenario.targetPosition[
                                                                             int(self.guiTargetSelected)][
                                                                         int(self.traceIndex), ::, ::]

            self.targetJointsVisObj[int(self.guiTargetSelected)].mlab_source.trait_set(x=xTargetCoordinates,
                                                                                       y=yTargetCoordinates,
                                                                                       z=zTargetCoordinates)

            self.makeVisible(self.targetJointsVisObj[int(self.guiTargetSelected)])
            self.makeVisible(self.targetJointsConnectionsVisObj[int(self.guiTargetSelected)])

            # Display the selected target MPCs
            if not self.targetsVisualizationProperties.mpcsNodesTargetHidden:
                # User wants to display Target MPCs
                # Hide previously displayed MPCs
                for nodeId in range(qdScenario.nbNodes):
                    # for targetId in range(len(qdScenario.targetPosition)):
                    for targetId in range(qdScenario.nbTargets):
                        for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                            self.makeInvisible(
                                self.mpcNodesTargetsReflections[nodeId][targetId][
                                    reflectionOrder])

                for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                    # From Tx Node to Target
                    xMpcCoordinate, yMpcCoordinate, zMpcCoordinate, connections = qdRealization.getTargetMpcCoordinates(
                        int(self.guiTxNodeSelected), int(self.guiTargetSelected), reflectionOrder,
                        self.traceIndex)

                    self.pointsNodesTargetsReflections[int(self.guiTxNodeSelected)][
                        int(self.guiTargetSelected)][
                        reflectionOrder].mlab_source.set(x=xMpcCoordinate, y=yMpcCoordinate,
                                                         z=zMpcCoordinate)

                    self.pointsNodesTargetsReflections[int(self.guiTxNodeSelected)][
                        int(self.guiTargetSelected)][
                        reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                    self.makeVisible(
                        self.mpcNodesTargetsReflections[int(self.guiTxNodeSelected)][
                            int(self.guiTargetSelected)][
                            reflectionOrder])

                    # From Rx Node to Target
                    xMpcCoordinate, yMpcCoordinate, zMpcCoordinate, connections = qdRealization.getTargetMpcCoordinates(
                        int(self.guiRxNodeSelected), int(self.guiTargetSelected), reflectionOrder,
                        self.traceIndex)
                    self.pointsNodesTargetsReflections[int(self.guiRxNodeSelected)][
                        int(self.guiTargetSelected)][
                        reflectionOrder].mlab_source.set(x=xMpcCoordinate, y=yMpcCoordinate,
                                                         z=zMpcCoordinate)

                    self.pointsNodesTargetsReflections[int(self.guiRxNodeSelected)][
                        int(self.guiTargetSelected)][
                        reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                    self.makeVisible(
                        self.mpcNodesTargetsReflections[int(self.guiRxNodeSelected)][
                            int(self.guiTargetSelected)][
                            reflectionOrder])
            else:
                # User does not want to display Target MPCs
                for nodeId in range(qdScenario.nbNodes):
                    for targetId in range(qdScenario.nbTargets):
                        for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                            self.makeInvisible(
                                self.mpcNodesTargetsReflections[nodeId][targetId][
                                    reflectionOrder])

        if qdRealization.sensingResults.available:
            if self.axesDopplerRange == 0:
                # Axes must be created only once - Create it
                self.axesDopplerRange = mlab.axes(self.dopplerRangeObjVis)
                self.axesDopplerRange.axes.y_axis_visibility = False
                self.axesDopplerRange.axes.x_label = 'Range (m)'
                self.axesDopplerRange.axes.y_label = 'Velocity (m/s)'
                self.axesDopplerRange.axes.use_ranges = True  # Must do that as we scaled the graph
                self.axesDopplerRange.axes.number_of_labels = 3
                self.axesDopplerRange.axes.font_factor = 0.75816  # Change label size
                self.axesDopplerRange.title_text_property.font_size = 4  # Change legend axes size
                self.axesDopplerRange.title_text_property.color = (0.0, 0.0, 0.0)  # Change legend axes color
                self.axesDopplerRange.label_text_property.color = (0.0, 0.0, 0.0)  # Change label color
                self.axesDopplerRange.property.color = (0.0, 0.0, 0.0)  # change axes and ticks colors
                self.axesDopplerRange.property.color = (0.0, 0.0, 0.0)  # change axes and ticks colors

            indexLookFor = -1
            realIndex = 0
            for slowTime in qdRealization.sensingResults.slowTime:
                if self.traceIndex == slowTime:
                    # We found the exact index
                    indexLookFor = slowTime
                    break
                elif self.traceIndex > slowTime:
                    # Trace is superior, keep going
                    indexLookFor = slowTime
                elif self.traceIndex < slowTime:
                    # Trace index is smaller - quit
                    break
                realIndex += 1

            if indexLookFor != -1:
                x = qdRealization.sensingResults.fastTime * 299792458
                z = qdRealization.sensingResults.dopplerRange[self.filteredIndexes,
                        realIndex * len(x):(realIndex + 1) * len(x)]
                z = np.transpose(z, (1, 0))
                self.dopplerRangeObjVis.mlab_source.set(scalars=z)
            else:
                z = np.zeros(
                    (len(qdRealization.sensingResults.velocity[self.filteredIndexes]),
                     len(qdRealization.sensingResults.fastTime)))
                z = np.transpose(z, (1, 0))
                self.dopplerRangeObjVis.mlab_source.set(scalars=z)

    def updateGuiTexts(self, txNode, rxNode, name):
        """Update the GUI text values
        """
        # Handle the lists to select Tx and Rx Node
        if name == "guiTxNodeSelected" or name == "guiRxNodeSelected":
            if qdScenario.nbNodes > 2:
                # Remove Rx (Tx) selected node from the Tx (Rx) list
                if name == "guiTxNodeSelected":
                    nodeChosen = []
                    for i in range(qdScenario.nbNodes):
                        if i != txNode:
                            nodeChosen.append(str(i))
                    self.guiRxNodeSelectedChoices = nodeChosen
                elif name == "guiRxNodeSelected":
                    nodeChosen = []
                    for i in range(qdScenario.nbNodes):
                        if i != rxNode:
                            nodeChosen.append(str(i))
                    self.guiTxNodeSelectedChoices = nodeChosen
            else:
                self.guiTxNodeSelectedChoices = [self.guiTxNodeSelected]
                self.guiRxNodeSelectedChoices = [self.guiRxNodeSelected]

        if self.guiTxNodeSelected == self.guiRxNodeSelected:
            # Exit if the two nodes are identical (can happened during a switch)'
            return

        # Update the GUI messages
        # Handle the TX codebook Text
        txCodebookGuiMessage = "Codebook TX:", str(codebooks.getNbPaaNode(
            qdScenario.getNodeType(txNode))) + "PAA(s) :" + str(codebooks.getNbSectorsPerPaaNode(
            qdScenario.getNodeType(txNode))) + "Sectors"

        # Handle the RX codebook Text
        rxCodebookGuiMessage = "Codebook RX:", str(codebooks.getNbPaaNode(
            qdScenario.getNodeType(rxNode))) + "PAA(s) :" + str(codebooks.getNbSectorsPerPaaNode(
            qdScenario.getNodeType(rxNode))) + "Sectors"

        # Update the Sliders for iterate over the codebook
        self.guiTxMaxSectorId = codebooks.getNbSectorsPerPaaNode(
            qdScenario.getNodeType(txNode)) - 1  # We iterate starting from 0
        self.guiRxMaxSectorId = codebooks.getNbSectorsPerPaaNode(
            qdScenario.getNodeType(rxNode)) - 1  # We iterate starting from 0
        self.guiCodebookLabel = str(txCodebookGuiMessage) + str(rxCodebookGuiMessage)

    def updateDevicesVisuals(self):
        """Update the visuals for STAs and APs devices (3D spheres + 3D models)
        """
        # STAs
        xSTACoordinates, ySTACoordinates, zSTACoordinates = qdScenario.getAllSTAsPosition(
            self.traceIndex)
        self.stasVisObj.mlab_source.trait_set(x=xSTACoordinates, y=ySTACoordinates, z=zSTACoordinates)

        # APs
        xAPCoordinates, yAPCoordinates, zAPCoordinates = qdScenario.getAllAPsPosition(
            self.traceIndex)
        self.apsVisObj.mlab_source.trait_set(x=xAPCoordinates, y=yAPCoordinates, z=zAPCoordinates)

        # Update 3D models
        if self.guiDisplayNodesObjects:
            for apId in range(qdScenario.nbAps):
                if self.apTextureMode == "none" or self.apTextureMode == "jpg":
                    self.apModelVisObj[apId].actor.actor.position = qdScenario.getNodePosition(
                        self.traceIndex, apId)
                    self.apModelVisObj[apId].actor.actor.orientation = (
                        qdScenario.getNodeRotation(self.traceIndex, apId))
                else:
                    # Each AP object is made of individual textures objects - Iterate through all of them
                    for individualObject in self.apModelVisObj[apId]:
                        individualObject.position = qdScenario.getNodePosition(
                            self.traceIndex, apId)
                        individualObject.orientation = (
                            qdScenario.getNodeRotation(self.traceIndex, apId))

            # Display object associated to STA
            for staId in range(qdScenario.nbAps, qdScenario.nbNodes):
                if self.staTextureMode == "none" or self.staTextureMode == "jpg":
                    self.staModelVisObj[staId - qdScenario.nbAps].actor.actor.position = qdScenario.getNodePosition(
                        self.traceIndex, staId)  # staId - qdScenario.nbAps as indexed from 0
                    self.staModelVisObj[staId - qdScenario.nbAps].actor.actor.orientation = (
                        qdScenario.getNodeRotation(self.traceIndex, staId))
                else:
                    # Each STA object is made of individual textures objects - Iterate through all of them
                    for individualObject in self.staModelVisObj[staId - qdScenario.nbAps]:
                        individualObject.position = qdScenario.getNodePosition(
                            self.traceIndex, staId)  # staId - qdScenario.nbAps as indexed from 0
                        individualObject.orientation = (
                            qdScenario.getNodeRotation(self.traceIndex, staId))

    def updatePaasVisuals(self, txNode, rxNode, paaTx, paaRx):
        """Update the PAAs visuals for STAs and APs devices
        """
        # Handle the Paa Tx and Rx selected
        # Color the new TX selected PAA to green
        self.paasElementsVisObj[(txNode, paaTx)].actor.actor.property.color = (0.2, 1.0, 0)
        # Color the new TX selected PAA to red
        self.paasElementsVisObj[(rxNode, paaRx)].actor.actor.property.color = (1.0, 0.0, 0.0)

        # Update Nodes PAAs position and orientation
        for apID in range(qdScenario.nbAps):
            for paaID in range(codebooks.getNbPaaPerAp()):
                self.updatePaaGeometry(self.traceIndex, apID, paaID)

        for staID in range(qdScenario.nbAps, qdScenario.nbNodes):
            for paaID in range(codebooks.getNbPaaPerSta()):
                self.updatePaaGeometry(self.traceIndex, staID, paaID)

    def updatePaaGeometry(self, traceIndex, nodeId, paaId):
        """Display the PAA geometry (antenna elements are represented by a cube)

        Parameters
        ----------
        traceIndex: int
            TraceIndex
        nodeId : int
            Node ID to display the PAA
        paaTx : int
            PAA of the node
        """
        globals.logger.debug("Update antenna elements position")
        self.paasElementsVisObj[(nodeId, paaId)].actor.actor.position = qdScenario.getPaaPosition(nodeId, paaId,
                                                                                                  traceIndex)
        self.paasElementsVisObj[(nodeId, paaId)].actor.actor.orientation = (
            self.computePaaRotationAngles(nodeId, paaId, traceIndex))

    def updateMpcsVisuals(self, txNode, rxNode, paaTx, paaRx):
        """Update the MPCs visuals for tx/paaTx node to rx/paaRx node
        """

        if qdScenario.getNodeType(int(self.guiTxNodeSelected)) == globals.NodeType.STA and self.guiShowSlsBestAp:
            # User wants to display the best AP the STA can associate too
            if self.guiSlsMode == "Oracle" and qdScenario.qdInterpreterConfig.dataMode == "preprocessed":
                self.displayMpcs(
                    qdScenario.preprocessedAssociationData[(int(self.guiTxNodeSelected), int(self.traceIndex))][1], paaRx,
                    txNode, paaTx, self.traceIndex, self.guiMpcsMagnifier)
            else:
                globals.logger.warning(
                    "Display best AP is available only when the dataMode is set to Preprocessed and SLS is set to Oracle")
        else:
            if txNode < rxNode:
                self.displayMpcs(txNode, paaTx, rxNode, paaRx, self.traceIndex, self.guiMpcsMagnifier)
            else:
                self.displayMpcs(rxNode, paaRx, txNode, paaTx, self.traceIndex, self.guiMpcsMagnifier)

    def updateNodesOrientationAxes(self, txNode, rxNode, txAxisVisibility, rxAxisVisibility, traceIndex):
        """Update the visualization to display the Tx and Rx node device orientation axes

        Parameters
        ----------
        txNode : Int
            The Tx Node ID
        rxNode : Int
            The Rx Node ID
        txAxisVisibility : Bool
            The visibility of the Tx device orientation axes
        rxAxisVisibility : Bool
            The visibility of the Rx Device orientation axes
        traceIndex : Int
            The trace index
        """
        # Display the Tx Device orientation depending on its visibility
        self.txDeviceOrientationAxesVisObj.actor.actor.position = qdScenario.getNodePosition(
            traceIndex, txNode)
        self.txDeviceOrientationAxesVisObj.actor.actor.orientation = (
            qdScenario.getNodeRotation(traceIndex, txNode))  # Apply the Tx Device rotation
        self.updateVisibility(self.txDeviceOrientationAxesVisObj, txAxisVisibility)

        # Display the Rx Device orientation depending on its visibility
        self.rxDeviceOrientationAxesVisObj.actor.actor.position = qdScenario.getNodePosition(
            traceIndex, rxNode)
        self.rxDeviceOrientationAxesVisObj.actor.actor.orientation = (
            qdScenario.getNodeRotation(traceIndex, rxNode))  # Apply the Rx Device rotation
        self.updateVisibility(self.rxDeviceOrientationAxesVisObj, rxAxisVisibility)

    def updatePaasOrientationAxes(self, txNode, paaTx, paaTxAxisVisibility, rxNode, paaRx, paaRxAxisVisibility,
                                  traceIndex):
        """Update the visualization to display the Paa Tx and Paa Rx orientation axes

        Parameters
        ----------
        txNode : Int
            The Tx Node ID
        paaTx : Int
            The Paa Tx ID
        paaTxAxisVisibility : Bool
            The visibility of the PAA Tx orientation axes
        rxNode : Int
            The Rx Node ID
        paaRx : Int
            The Paa Rx ID
        paaRxAxisVisibility : Bool
            The visibility of the PAA Rx orientation axes
        traceIndex : Int
            The trace index
        """
        # PAA Tx orientation Axes
        self.paasOrientationAxesVisObj[
            (qdScenario.getNodeType(txNode), True, paaTx)].actor.actor.position = qdScenario.getPaaPosition(
            txNode, paaTx, traceIndex)
        self.paasOrientationAxesVisObj[
            (qdScenario.getNodeType(txNode), True, paaTx)].actor.actor.orientation = self.computePaaRotationAngles(
            txNode,
            paaTx,
            traceIndex)
        self.updateVisibility(
            self.paasOrientationAxesVisObj[(qdScenario.getNodeType(txNode), True, paaTx)],
            paaTxAxisVisibility)
        # PAA Rx orientation Axes
        self.paasOrientationAxesVisObj[
            (qdScenario.getNodeType(rxNode), False, paaRx)].actor.actor.position = qdScenario.getPaaPosition(
            rxNode, paaRx, traceIndex)
        self.paasOrientationAxesVisObj[
            (qdScenario.getNodeType(rxNode), False, paaRx)].actor.actor.orientation = self.computePaaRotationAngles(
            rxNode,
            paaRx,
            traceIndex)
        self.updateVisibility(
            self.paasOrientationAxesVisObj[(qdScenario.getNodeType(rxNode), False, paaRx)],
            paaRxAxisVisibility)

    @on_trait_change('guiVisualizerTextures,guiTextureMode')
    def updateObjectTexture(self):
        """Update the selected object with the custom selected texture and interpolation method
        """
        if currentSelectedObject != -1:
            if currentPicker == pickerView1:
                viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            else:
                viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            viewObjects[currentSelectedObject].textureMode = self.guiTextureMode
            # viewObjects[currentSelectedObject].customTexture = str(globals.textureFolder + self.guiVisualizerTextures)
            viewObjects[currentSelectedObject].customTexture = os.path.join(globals.textureFolder,self.guiVisualizerTextures)
            self.assignMaterialTexture(viewObjects[currentSelectedObject])
            self.forceRender()

    def assignMaterialColor(self, object):
        """Assign the material color to the object

        Parameters
        ----------
        object : EnvironmentObject Class
            The environment object to modify
        """
        if not object.colorChanged:
            # The object color has not been changed in the GUI - Revert back to its original color
            viridis = cm.get_cmap('viridis', len(self.materialProperties.materialNameDic))
            colorToAssign = viridis(int(object.materialId) / len(self.materialProperties.materialNameDic))
            object.mesh.actor.property.color = (
                colorToAssign[0], colorToAssign[1], colorToAssign[2])
        else:
            # The color of the object was changed in the GUI - Revert back to the custom color
            object.mesh.actor.property.color = object.customColor

    def assignMaterialTexture(self, object):
        """Apply the texture to the object (if any)

        Parameters
        ----------
        object : EnvironmentObject Class
            The environment object to modify
        """
        object.mesh.actor.mapper.scalar_visibility = False
        object.mesh.actor.enable_texture = True
        object.mesh.actor.tcoord_generator_mode = object.textureMode
        if object.textureMode != "plane" and object.textureMode != "none":
            # In case sphere or cylinder mode is used, try to wrap the entire texture to the object
            mapper = object.mesh.actor.tcoord_generator
            mapper.prevent_seam = 0
        object.mesh.actor.property.color = (1.0, 1.0, 1.0)

        if self.materialProperties.materialNameDic[
            object.materialId] in self.materialProperties.materialPathDic or object.customTexture != "":
            # The texture is either present in the material library or the user assigned a custom texture
            img = tvtk.JPEGReader()
            if object.customTexture == "":
                # The objet texture has not been changed in the GUI
                img.file_name = str(self.materialProperties.materialPathDic[
                                        self.materialProperties.materialNameDic[object.materialId]])
            else:
                # The user assigned a new texture
                img.file_name = object.customTexture
            texture = tvtk.Texture(input_connection=img.output_port, interpolate=0)
            object.mesh.actor.actor.texture = texture
        else:
            # There was not texture assigned - Assign the material color
            object.mesh.actor.enable_texture = False
            self.assignMaterialColor(object)

    def displayMpcs(self, tx, paaTx, rx, paaRx, traceIndex, mpcsMagnifier):
        """Display MPCs for a given transmitter tx and a given received rx, and a given trace traceIndex

        Parameters
        ----------
        tx : int
            Identifier of the transmitter

        paaTx : int
            Identifier of the transmitter PAA

        rx : int
            Identifier of the receiver

        paaRx : int
            Identifier of the receiver PAA

        traceIndex : int
            Identifier of the trace
        """
        if (tx, rx) not in self.mpcEdgesDicVisObj:
            # Create the placeholder for the future multipath for the relections
            mpcPointCurrent = []  # The vertices of the MPCs
            tubeCurrent = []  # the tube connected the MPCs
            realTube = []
            for reflectionOrder in range(0, maxReflectionOrder + 1):
                mpcPointCurrent.append(
                    mlab.points3d([], [], [],
                                  scale_factor=1,
                                  name="MPC TX:" + str(tx) + "RX:" + str(rx) + "Refl:" + str(
                                      reflectionOrder), figure=self.view2.mayavi_scene, reset_zoom=False))

                # Connect the MPCs points with tubes
                connections = tuple()
                mpcPointCurrent[reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                self.makeInvisible(mpcPointCurrent[-1])
                tube = mlab.pipeline.tube(mpcPointCurrent[reflectionOrder],
                                          # tube_radius=1.5 / ((reflectionOrder + 1) * 10),
                                          figure=self.view2.mayavi_scene)
                realTube.append(tube)
                tube.filter.radius_factor = 1.
                tubeCurrent.append(mlab.pipeline.surface(tube, figure=self.view2.mayavi_scene, reset_zoom=False))
                tubeCurrent[-1].actor.property.lighting = False
                tubeCurrent[reflectionOrder].actor.property.color = self.mpcReflectionsProperties[
                    reflectionOrder].color
            self.mpcVerticesDicVisObj[
                tx, rx] = mpcPointCurrent  # add the MPCs created for a node to the MPCs dictionnary
            self.mpcEdgesDicVisObj[tx, rx] = tubeCurrent

            self.mpcTubesDicVisObj[tx, rx] = realTube

        # Iterate through the reflections order to update the MPCs
        for reflectionOrder in range(0, maxReflectionOrder + 1):
            globals.logger.debug("Create MPCs for reflection:" + str(reflectionOrder))
            # Get the MPCs points coordinates
            xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                tx, paaTx, rx, paaRx, reflectionOrder, traceIndex)
            if len(xMpcCoordinate) > 0:
                # Create the MPCs if it exists at least one MPC for the given reflection
                nbPathToConnect = xMpcCoordinate.size  # Get the total number of MPCs coordinates
                # Reshape the MPC coordinates to 1D as expected by the visualizer library
                xMpcCoordinate = xMpcCoordinate.flatten()
                yMpcCoordinate = yMpcCoordinate.flatten()
                zMpcCoordinate = zMpcCoordinate.flatten()
                connections = tuple()
                # Create the connections between all the MPCs points
                # i.e, which points vertices need to be connected by tubes
                for i in range(0, nbPathToConnect, 2 + reflectionOrder):
                    idConnection = 0
                    for j in range(reflectionOrder + 1):
                        connections = connections + ((i + idConnection, i + 1 + idConnection),)
                        idConnection = idConnection + 1

                # Please note that it's way faster to use the set method than the reset method
                # to update a visual object in Mayavi
                # However, the set method can only be used if the shape of the previous MPCs displayed
                # is equal to the shape of the MPCs to display so we perform this test here
                if (nbPathToConnect ==
                        self.mpcEdgesDicVisObj[tx, rx][reflectionOrder].mlab_source.dataset.points.to_array().shape[0]):
                    # Same shape - Use set
                    self.mpcVerticesDicVisObj[tx, rx][reflectionOrder].mlab_source.set(x=xMpcCoordinate,
                                                                                       y=yMpcCoordinate,
                                                                                       z=zMpcCoordinate)
                else:
                    # The number of MPCs to display is different - Use reset
                    self.mpcVerticesDicVisObj[tx, rx][reflectionOrder].mlab_source.reset(x=xMpcCoordinate,
                                                                                         y=yMpcCoordinate,
                                                                                         z=zMpcCoordinate)
                self.mpcVerticesDicVisObj[tx, rx][reflectionOrder].mlab_source.dataset.lines = np.array(connections)
            else:
                # There was no MPC for the given reflection order - Remove the MPCs
                globals.logger.info("No MPC exist for reflection:" + str(reflectionOrder))
                connections = tuple()
                self.mpcVerticesDicVisObj[tx, rx][reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                self.mpcVerticesDicVisObj[tx, rx][reflectionOrder].mlab_source.reset(x=[], y=[], z=[])
        # Make visible the MPCs
        if (tx, rx) in self.mpcEdgesDicVisObj:
            tubeOneNode = self.mpcEdgesDicVisObj[tx, rx]
            for tubeReflectionOneNode in tubeOneNode:
                # tubeReflectionOneNode.filter.radius_factor = 0.01
                self.makeVisible(tubeReflectionOneNode)

        # Apply the reflection order visualization properties
        if (tx, rx) in self.mpcEdgesDicVisObj:
            for reflectionOrder in range(maxReflectionOrder + 1):
                self.mpcEdgesDicVisObj[tx, rx][reflectionOrder].actor.actor.visibility = not (
                    self.mpcReflectionsProperties[
                        reflectionOrder].hidden)
                self.mpcEdgesDicVisObj[tx, rx][reflectionOrder].actor.property.color = self.mpcReflectionsProperties[
                    reflectionOrder].color
        if (tx, rx) in self.mpcTubesDicVisObj:
            for reflectionOrder in range(maxReflectionOrder + 1):
                self.mpcTubesDicVisObj[tx, rx][reflectionOrder].filter.radius = self.mpcReflectionsProperties[
                    reflectionOrder].width

        self.guiMpcColor = (self.mpcReflectionsProperties[self.guiMpcReflection].color[0] * 255,
                            self.mpcReflectionsProperties[self.guiMpcReflection].color[1] * 255,
                            self.mpcReflectionsProperties[self.guiMpcReflection].color[2] * 255)
        self.guiMpcsMagnifier = self.mpcReflectionsProperties[self.guiMpcReflection].width
        self.guiMpcsHidden = self.mpcReflectionsProperties[self.guiMpcReflection].hidden

    def updateSlsVisuals(self, txNode, rxNode, paaTx, paaRx):
        """Update the SLS visuals for tx/paaTx node to rx/paaRx node and conversely
        """
        if self.guiSlsMode == "Oracle":
            # Compute the Rx Power between every Tx/Rx and PAA_TX/PAA_RX pair
            bestSectorTxRx, bestPowerTxRx = self.computeSls(txNode, paaTx, rxNode, paaRx, int(self.traceIndex),
                                                            int(self.guiTraceIncrement))
            bestSectorRxTx, bestPowerRxTx = self.computeSls(rxNode, paaRx, txNode, paaTx, int(self.traceIndex),
                                                            int(self.guiTraceIncrement))

            self.guiTxssTxRxTxId = self.guiTxNodeSelected
            self.guiTxssTxRxRxId = self.guiRxNodeSelected
            self.guiTxssRxTxTxId = self.guiRxNodeSelected
            self.guiTxssRxTxRxId = self.guiTxNodeSelected
            if qdScenario.isNodeAp(txNode):
                self.guiTxssTxRxTxType = "(AP)"
                self.guiTxssRxTxRxType = "(AP)"
            else:
                self.guiTxssTxRxTxType = "(STA)"
                self.guiTxssRxTxRxType = "(STA)"

            if qdScenario.getNodeType(
                    int(self.guiTxNodeSelected)) == globals.NodeType.STA and self.guiShowSlsBestAp:
                # The user wants to display the best AP to which the STA is associated
                bestApForSta = \
                    qdScenario.preprocessedAssociationData[(int(self.guiTxNodeSelected), int(self.traceIndex))][1]
                self.guiTxssTxRxRxId = str(bestApForSta)
                self.guiTxssRxTxTxId = str(bestApForSta)

            if qdScenario.isNodeAp(rxNode):
                self.guiTxssTxRxRxType = "(AP)"
                self.guiTxssRxTxTxType = "(AP)"
            else:
                self.guiTxssTxRxRxType = "(STA)"
                self.guiTxssRxTxTxType = "(STA)"
            # Handle Tx to Rx TXSS
            role = 0  # Correspond to TX case
            if qdScenario.getNodeType(
                    int(self.guiTxNodeSelected)) == globals.NodeType.STA and self.guiShowSlsBestAp:
                self.displayTxss(txNode, paaTx, bestSectorTxRx[(
                    txNode, bestApForSta,
                    paaTx,
                    paaRx)],
                                 self.traceIndex, role)
            else:
                self.displayTxss(txNode, paaTx, bestSectorTxRx[(txNode, rxNode, paaTx, paaRx)],
                                 self.traceIndex, role)

            # Update GUI labels
            self.guiTxssTxRxBestSector = bestSectorTxRx[(txNode, rxNode, paaTx, paaRx)]
            self.guiTxssTxRxRcvPower = round(bestPowerTxRx[(txNode, rxNode, paaTx, paaRx)], 2)

            # Handle Rx to Tx TXSS
            role = 1  # Correspond to RX case
            if qdScenario.getNodeType(
                    int(self.guiRxNodeSelected)) == globals.NodeType.AP and qdScenario.getNodeType(
                int(self.guiTxNodeSelected)) == globals.NodeType.STA and self.guiShowSlsBestAp:

                bestSectorBestApSta, bestPowerBestApSta = self.computeSls(bestApForSta, paaRx, txNode, paaTx,
                                                                          int(self.traceIndex),
                                                                          int(self.guiTraceIncrement))
                self.displayTxss(bestApForSta, paaRx, bestSectorBestApSta[(bestApForSta, txNode, paaRx, paaTx)],
                                 self.traceIndex, role)
            else:
                self.displayTxss(rxNode, paaRx, bestSectorRxTx[(rxNode, txNode, paaRx, paaTx)],
                                 self.traceIndex, role)

            self.guiTxssRxTxBestSector = bestSectorRxTx[(rxNode, txNode, paaRx, paaTx)]
            self.guiTxssRxTxRcvPower = round(bestPowerRxTx[(rxNode, txNode, paaRx, paaTx)], 2)

            # Quasi-Omni not enabled in this version - We keep the code below commented
            # # Display the Quasi-Omni Rx pattern
            # if qdScenario.getNodeType(
            #         int(self.guiTxNodeSelected)) == globals.NodeType.STA and self.guiShowSlsBestAp:
            #     self.displayQuasiOmniRxPattern(bestSectorTxRx[(
            #         txNode, qdScenario.preprocessedAssociationData[(int(self.guiTxNodeSelected), int(self.traceIndex))][1],
            #         paaTx,
            #         paaRx)],
            #                               qdScenario.preprocessedAssociationData[
            #                                   (int(self.guiTxNodeSelected), int(self.traceIndex))][
            #                                   1], paaRx,
            #                               int(self.traceIndex))
            # else:
            #
            #     self.displayQuasiOmniRxPattern(bestSectorTxRx[(txNode, rxNode, paaTx, paaRx)], rxNode, paaRx,
            #                               int(self.traceIndex))

            if self.guiDisplayStaAssociation:
                # Display the STA association if selected
                self.displayStasAssociation(int(self.traceIndex))

            # Update the labels for best sector and best Rx Power
            if qdScenario.getNodeType(
                    int(self.guiTxNodeSelected)) == globals.NodeType.STA and self.guiShowSlsBestAp:
                self.guiTxssTxRxBestSector = bestSectorTxRx[(
                    txNode,
                    qdScenario.preprocessedAssociationData[(int(self.guiTxNodeSelected), int(self.traceIndex))][1],
                    paaTx,
                    paaRx)]
                self.guiTxssTxRxRcvPower = bestPowerTxRx[(
                    txNode,
                    qdScenario.preprocessedAssociationData[(int(self.guiTxNodeSelected), int(self.traceIndex))][1],
                    paaTx,
                    paaRx)]
            else:
                self.guiTxssTxRxBestSector = bestSectorTxRx[(txNode, rxNode, paaTx, paaRx)]
                self.guiTxssTxRxRcvPower = round(bestPowerTxRx[(txNode, rxNode, paaTx, paaRx)], 2)
        else:
            # ns-3 mode is selected
            if not qdScenario.nsSlsResults.empty:
                # Check that the ns-3 SLS results are provided
                # Handle Tx to Rx TXSS
                role = 0  # Correspond to RX case
                paaTx, bestSector = getNsSlsResultsTxRxTrace(txNode, rxNode, int(self.traceIndex), qdScenario)
                if paaTx != None and bestSector != None:
                    # SLS results available
                    self.displayTxss(txNode, paaTx, bestSector,
                                     self.traceIndex, role)

                    self.guiTxssTxRxBestSector = bestSector
                    self.guiTxssTxRxRcvPower = float('NaN')

                    # Handle Rx to Tx TXSS
                    role = 1  # Correspond to RX case
                    paaRx, bestSector = getNsSlsResultsTxRxTrace(rxNode, txNode, int(self.traceIndex), qdScenario)
                    self.displayTxss(rxNode, paaRx, bestSector,
                                     self.traceIndex, role)
                    self.guiTxssRxTxBestSector = bestSector
                    self.guiTxssRxTxRcvPower = float('NaN')
                else:
                    # No Results available for the given pair - Most probably cause the two devices never performed BFT during the ns-3 simulation
                    globals.logger.warning(
                        "No ns-3 SLS Results Available for the pair Tx:" + str(txNode) + " Rx:" + str(rxNode))
                    self.guiTxssTxRxBestSector = -1  # Not Available
                    self.guiTxssTxRxRcvPower = float('NaN')  # Not Available
                    self.guiTxssRxTxBestSector = -1  # Not Available
                    self.guiTxssRxTxRcvPower = float('NaN')  # Not Available
            else:
                globals.logger.warning("No ns-3 SLS Results Available - Please check you correctly imported ns-3 results")
                self.guiTxssTxRxBestSector = -1  # Not Available
                self.guiTxssTxRxRcvPower = float('NaN')  # Not Available
                self.guiTxssRxTxBestSector = -1  # Not Available
                self.guiTxssRxTxRcvPower = float('NaN')  # Not Available

    def updateSlsPlots(self, txNode, rxNode, paaTx, paaRx, rxPowerTxRx, psdBestSectorTxRx, rxPowerSectorListTxRx,
                       traceIndex,
                       guiTraceIncrement):
        """Update both the data for the plots and the plots itself

        Parameters
        ----------
        txNode : Int
            The Tx Node ID
        rxNode : Int
            The Rx Node ID
        paaTx : Int
            The PAA Tx ID
        paaRx : Int
            The PAA Rx ID
        rxPowerTxRx : Float
            The Received power for the best sector
        psdBestSectorTxRx : Numpy Array
            The Received power per subband for the best sector
        rxPowerSectorListTxRx : Numpy Array
            The received power for all the sectors
        traceIndex : Int
            The trace Index
        guiTraceIncrement : Int
            The trace increment (the step of the animation)
        """
        # Displaying the curves can be expensive in case we keep adding data (it's the case for the power curves that is represented in time)
        # To improve performance of the power curve, we use chunk of 100 data that we expand everytime that it's required
        nextTraceIndex = traceIndex + guiTraceIncrement
        if nextTraceIndex >= \
                Y_CURVE_DATA_DIC[("Power", txNode, rxNode, paaTx, paaRx)].shape[
                    0]:
            # Not enough space remaining to store the power data, double the array size
            tmp = Y_CURVE_DATA_DIC[("Power", txNode, rxNode, paaTx, paaRx)]
            Y_CURVE_DATA_DIC[
                ("Power", txNode, rxNode, paaTx, paaRx)] = np.empty(
                Y_CURVE_DATA_DIC[("Power", txNode, rxNode, paaTx, paaRx)].shape[
                    0] * 2)
            Y_CURVE_DATA_DIC[("Power", txNode, rxNode, paaTx, paaRx)].fill(
                -math.inf)
            Y_CURVE_DATA_DIC[("Power", txNode, rxNode, paaTx, paaRx)][
            :tmp.shape[0]] = tmp

        # Update the data
        Y_CURVE_DATA_DIC[("Power", txNode, rxNode, paaTx, paaRx)][
            traceIndex] = rxPowerTxRx
        if ("Power", txNode, rxNode, paaTx, paaRx, 0) in Y_CURVE_FILTER or (
                "Power", txNode, rxNode, paaTx, paaRx, 1) in Y_CURVE_FILTER:
            # If the user wants to display the power curve
            if rxPowerTxRx != -math.inf:
                # Update the power curve
                CURVES_DIC[("Power", txNode, rxNode, paaTx, paaRx)].setData(
                    Y_CURVE_DATA_DIC[("Power", txNode, rxNode, paaTx, paaRx)][
                    :traceIndex + 1])

        if ("Power Per Sector", txNode, rxNode, paaTx, paaRx, 0) in Y_CURVE_FILTER or (
                "Power Per Sector", txNode, rxNode, paaTx, paaRx, 1) in Y_CURVE_FILTER:
            # If the user wants to display the power curve
            if rxPowerTxRx != -math.inf:
                # Update the power curve
                CURVES_DIC[
                    ("Power Per Sector", txNode, rxNode, paaTx, paaRx)].setData(
                    rxPowerSectorListTxRx)
            else:
                # If infinite power was computed for the best sector, nothing to display for the Power Per Sector curves
                # Just clear the curve
                CURVES_DIC[
                    ("Power Per Sector", txNode, rxNode, paaTx, paaRx)].setData([0], [0],
                                                                                clear=True)

        if qdScenario.qdInterpreterConfig.dataMode == "online":
            # In preprocessed mode, we don't store PSD Curves data
            # Update of the PSD only in online mode
            Y_CURVE_DATA_DIC[("PSD", txNode, rxNode, paaTx, paaRx)] = psdBestSectorTxRx
            if rxPowerTxRx != -math.inf:
                if ("PSD", txNode, rxNode, paaTx, paaRx, 0) in Y_CURVE_FILTER or (
                        "PSD", txNode, rxNode, paaTx, paaRx, 1) in Y_CURVE_FILTER:
                    # if ("PSD", txNode, rxNode, paaTx, paaRx) in Y_CURVE_FILTER:
                    # If the user wants to display the PSD curve, update the curve
                    CURVES_DIC[("PSD", txNode, rxNode, paaTx, paaRx)].setData(
                        psdBestSectorTxRx)
            else:
                # If infinite power was computed for the best sector, nothing to display for the PSD and Power Per Sector curves
                # Just clear the curves
                CURVES_DIC[("PSD", txNode, rxNode, paaTx, paaRx)].setData([0], [0],
                                                                          clear=True)

    def updateBeamTrackingStreamsPatterns(self, mode, codebookMode, mimoInitiatorId, mimoResponderId, traceIndex,
                                          mayaviScene):
        previousIndex = 0
        # Beamtracking is not performed every trace
        # Get the index of the last time beamtracking was performed
        for i in qdScenario.beamTrackingResults.analogBeamTrackingResults.keys():
            if i == traceIndex:
                # Beamforming tracking was performed for the selected trace
                previousIndex = i
                break
            elif i > traceIndex:
                # There is no Beamforming Tracking performed for the current trace - Use the last index
                break
            else:
                # Keep the last index where beamforming tracking was performed
                previousIndex = i

        nbStream = qdScenario.beamTrackingResults.maxSupportedStream + 1

        # Make the right streams (analog or Hybrid) visible
        if mode == "Analog":
            for streamId in range(nbStream):
                if ("Hybrid", streamId) in self.mimoStreamPatterns:
                    # Analog Selected - Hide Hybrid
                    self.makeInvisible(self.mimoStreamPatterns["Hybrid", streamId][0])
                    self.makeInvisible(self.mimoStreamPatterns["Hybrid", streamId][1])
                if ("Analog", streamId) in self.mimoStreamPatterns:
                    # Analog Selected - Show Analog
                    self.makeVisible(self.mimoStreamPatterns["Analog", streamId][0])
                    self.makeVisible(self.mimoStreamPatterns["Analog", streamId][1])
        elif mode == "Hybrid":
            for streamId in range(nbStream):
                if ("Analog", streamId) in self.mimoStreamPatterns:
                    # Hybrid Selected - Hide Analog
                    self.makeInvisible(self.mimoStreamPatterns["Analog", streamId][0])
                    self.makeInvisible(self.mimoStreamPatterns["Analog", streamId][1])
                if ("Hybrid", streamId) in self.mimoStreamPatterns:
                    # Hybrid Selected - Show Hybrid
                    self.makeVisible(self.mimoStreamPatterns["Hybrid", streamId][0])
                    self.makeVisible(self.mimoStreamPatterns["Hybrid", streamId][1])

        # Get the PAAs IDs for the stream
        # Not used for beamtracking as the generation of the results are not consistent with the remaining of the framework
        # Basically, the codebook is only made of one PAA, the nodes as well and the generated MPCs so we can't index using
        # the PAA streams ID used in the beamtracking results (they are indexed with the correct PAA ID)
        # For these reasons, we have two fakes variables set to 0 (i.e., only one PAA with ID 0)
        txPaa = 0
        rxPaa = 0
        # We keep the placeholder for the code in case the Beamtracking code is modified to align with the framework
        # self.bestreamPaaIdCombination = [qdScenario.getTxPaaAnalogBT(previousIndex),
        #                             qdScenario.getRxPaaAnalogBT(previousIndex)]

        # Get the Transmit and Receive sectors for the stream
        txSectorIds = qdScenario.getTxSectorAnalogBT(previousIndex)  # Get the the best Tx Sectors for each stream
        rxSectorIds = qdScenario.getRxSectorAnalogBT(
            previousIndex)  # Get the best Rx Sectors for each stream (not used)
        self.bestSectorsCombination = [txSectorIds, rxSectorIds]

        # Get the AWVs for the streams (Not used - Keep the code as a place holder)
        # txAwvs = qdScenario.getTxAwvAnalogBT(previousIndex) # Get the best Tx AWVs for each stream (not used)
        # rxAwvs = qdScenario.getRxAwvAnalogBT(previousIndex)  # Get the best Rx AWVs for each stream (not used)
        if mode == "Hybrid":
            # Hybrid
            digitalCombiner = qdScenario.beamTrackingResults.digitalCombinerWeights
            digitalPrecoder = qdScenario.beamTrackingResults.digitalPrecoderWeights
            nbSpatialStreams = digitalCombiner.shape[1]
            responderStreamHbf = []  # Contain the hybrid weights for the responder for each stream
            initiatorStreamHbf = [] # Contain the hybrid weights for the initiator for each stream
            for n in range(nbSpatialStreams):
                # Get the digital beamforming applied to each RF chain
                weightTxSector = []
                weightRxSector = []
                for i in range(nbStream):
                    # Add analog weight applied to each antenna/stream
                    weightTxSector.append(codebooks.geElementWeightsNode(qdScenario.getNodeType(mimoInitiatorId),txSectorIds[i]))
                    weightRxSector.append(codebooks.geElementWeightsNode(qdScenario.getNodeType(mimoResponderId), rxSectorIds[i]))
                weightTxSector = np.asarray(weightTxSector)
                weightRxSector = np.asarray(weightRxSector)
                # Compute the Hybrid beamforming of a given stream by applying the digital beamforming to the analog beamforming
                responderDigitalBf = digitalCombiner[traceIndex, :, n].conj().T
                hybridBfResponder = np.matmul(responderDigitalBf, weightRxSector)
                responderStreamHbf.append(hybridBfResponder)
                initiatorDigitalBf = digitalPrecoder[traceIndex, :, n].T
                # hybridBfAp = np.matmul(apDbf, weightTxSector.conj()) # The conjugate had to be removed because of the PHY behavior
                hybridBfInitiator = np.matmul(initiatorDigitalBf, weightTxSector)
                initiatorStreamHbf.append(hybridBfInitiator)

        for streamId in range(nbStream):
            # Display the Antenna Patterns between initiator PAA and responder PAA for every stream
            filterPattern = qdScenario.qdInterpreterConfig.patternQuality
            if mode == "Analog":
                # Analog
                # Get the Antenna Pattern of the iniator
                txxAntennaPattern, txyAntennaPattern, txzAntennaPattern, txcolorAntennaPattern = codebooks.getSectorPatternNode(qdScenario.getNodeType(mimoInitiatorId), txSectorIds, txPaa, streamId,filterPattern)
                txxAntennaPattern =  txxAntennaPattern[::filterPattern]
                txyAntennaPattern = txyAntennaPattern[::filterPattern]
                txzAntennaPattern = txzAntennaPattern[::filterPattern]
                txcolorAntennaPattern = txcolorAntennaPattern[::filterPattern]

                # Get the Antenna Pattern of the responder
                rxxAntennaPattern, rxyAntennaPattern, rxzAntennaPattern, rxcolorAntennaPattern = codebooks.getSectorPatternNode(
                    qdScenario.getNodeType(mimoResponderId), rxSectorIds, rxPaa, streamId, filterPattern)
                rxxAntennaPattern = rxxAntennaPattern[::filterPattern]
                rxyAntennaPattern = rxyAntennaPattern[::filterPattern]
                rxzAntennaPattern = rxzAntennaPattern[::filterPattern]
                rxcolorAntennaPattern = rxcolorAntennaPattern[::filterPattern]
            else:
                # Hybrid
                txxAntennaPattern, txyAntennaPattern, txzAntennaPattern, txcolorAntennaPattern = codebook.computeHybridPattern(
                    codebooks, codebookMode, 0, initiatorStreamHbf[streamId],filterPattern)
                rxxAntennaPattern, rxyAntennaPattern, rxzAntennaPattern, rxcolorAntennaPattern = codebook.computeHybridPattern(
                    codebooks, codebookMode, 0, responderStreamHbf[streamId],filterPattern)

            if (mode, streamId) not in self.mimoStreamPatterns:
                # The Antenna Patterns corresponding to the stream have never been created

                # Creation of the Tx Antenna Pattern for the stream
                txStreamPattern = mlab.mesh(txxAntennaPattern,
                                            txyAntennaPattern,
                                            txzAntennaPattern,
                                            vmin=np.amin(txcolorAntennaPattern),
                                            vmax=np.amax(txcolorAntennaPattern),
                                            tube_radius=0.025,
                                            figure=mayaviScene,
                                            name="BeamTrackingTxStream" + str(streamId),
                                            reset_zoom=False,
                                            scalars=txcolorAntennaPattern)

                # Creation of the Rx Antenna Pattern for the stream
                rxStreamPattern = mlab.mesh(rxxAntennaPattern,
                                            rxyAntennaPattern,
                                            rxzAntennaPattern,
                                            vmin=np.amin(rxcolorAntennaPattern),
                                            vmax=np.amax(rxcolorAntennaPattern),
                                            tube_radius=0.025,
                                            figure=mayaviScene,
                                            name="BeamTrackingRxStream" + str(streamId),
                                            reset_zoom=False,
                                            scalars=rxcolorAntennaPattern)

                # Visualization properties
                txStreamPattern.actor.property.edge_visibility = True
                txStreamPattern.actor.property.specular = 1.0
                txStreamPattern.actor.property.specular_power = 66.0
                txStreamPattern.actor.property.edge_color = self.mimoStreamProperties[
                    streamId].color

                rxStreamPattern.actor.property.edge_visibility = True
                rxStreamPattern.actor.property.specular = 1.0
                rxStreamPattern.actor.property.specular_power = 66.0
                rxStreamPattern.actor.property.edge_color = self.mimoStreamProperties[streamId].color

                if self.savedMimoConfig:
                    txStreamPattern.actor.actor.scale = (
                    self.mimoStreamPatternSize[streamId], self.mimoStreamPatternSize[streamId],
                    self.mimoStreamPatternSize[streamId])
                    txStreamPattern.actor.property.line_width = self.mimoStreamEdgeSize[streamId]

                    rxStreamPattern.actor.actor.scale = (
                        self.mimoStreamPatternSize[streamId], self.mimoStreamPatternSize[streamId],
                        self.mimoStreamPatternSize[streamId])
                    rxStreamPattern.actor.property.line_width = self.mimoStreamEdgeSize[streamId]
                self.mimoStreamPatterns[mode, streamId] = [txStreamPattern, rxStreamPattern]
            else:
                # The Antenna Patterns corresponding to the stream have been created previously - Just update them
                # Tx Antenna Pattern Stream Update
                self.mimoStreamPatterns[mode, streamId][0].mlab_source.set(x=txxAntennaPattern, y=txyAntennaPattern,
                                                                        z=txzAntennaPattern,
                                                                        scalars=txcolorAntennaPattern,
                                                                        vmin=np.amin(txcolorAntennaPattern),
                                                                        vmax=np.amax(txcolorAntennaPattern))
                self.mimoStreamPatterns[mode, streamId][0].module_manager.scalar_lut_manager.data_range = [
                    np.amin(txcolorAntennaPattern), np.amax(txcolorAntennaPattern)]
                txStreamPattern = self.mimoStreamPatterns[mode, streamId][0]

                # Rx Antenna Pattern Stream Update
                self.mimoStreamPatterns[mode, streamId][1].mlab_source.set(x=rxxAntennaPattern, y=rxyAntennaPattern,
                                                                        z=rxzAntennaPattern,
                                                                        scalars=rxcolorAntennaPattern,
                                                                        vmin=np.amin(rxcolorAntennaPattern),
                                                                        vmax=np.amax(rxcolorAntennaPattern))
                self.mimoStreamPatterns[mode, streamId][1].module_manager.scalar_lut_manager.data_range = [
                    np.amin(rxcolorAntennaPattern), np.amax(rxcolorAntennaPattern)]
                rxStreamPattern = self.mimoStreamPatterns[mode, streamId][1]

            # Set the position and orientations of Tx Stream
            txStreamPattern.actor.actor.position = qdScenario.getPaaPosition(mimoInitiatorId,
                                                                             txPaa,
                                                                             traceIndex)
            txStreamPattern.actor.actor.orientation = (
                self.computePaaRotationAngles(mimoInitiatorId, txPaa,
                                              traceIndex))

            # Set the position and orientations of Rx Stream
            rxStreamPattern.actor.actor.position = qdScenario.getPaaPosition(mimoResponderId,
                                                                             rxPaa,
                                                                             traceIndex)
            rxStreamPattern.actor.actor.orientation = (
                self.computePaaRotationAngles(int(mimoResponderId), rxPaa,
                                              int(traceIndex)))

            if mimoInitiatorId < mimoResponderId:
                if streamId not in self.mimoTubeMesh:
                    mpcPointCurrent = []  # The vertices of the MPCs
                    tubeCurrent = []  # the tube connected the MPCs
                    realTube = []
                    for reflectionOrder in range(0, maxReflectionOrder + 1):
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            mimoInitiatorId, txPaa, mimoResponderId,
                            rxPaa, reflectionOrder, traceIndex)
                        if len(xMpcCoordinate) > 0:
                            mpcPointCurrent.append(
                                mlab.points3d(xMpcCoordinate, yMpcCoordinate, zMpcCoordinate,
                                              scale_factor=1, reset_zoom=False,
                                              name="MPC TX:" + str(mimoInitiatorId) + "RX:" + str(
                                                  mimoResponderId) + "Refl:" + str(
                                                  reflectionOrder), figure=mayaviScene))

                            mpcPointCurrent[reflectionOrder].actor.actor.visibility = False
                            # Connect the MPCs points with tubes
                            connections = tuple()
                            nbPathToConnect = xMpcCoordinate.size  # Get the total number of MPCs coordinates
                            for i in range(0, nbPathToConnect, 2 + reflectionOrder):
                                idConnection = 0
                                for j in range(reflectionOrder + 1):
                                    connections = connections + ((i + idConnection, i + 1 + idConnection),)
                                    idConnection = idConnection + 1
                            mpcPointCurrent[reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                            tube = mlab.pipeline.tube(mpcPointCurrent[reflectionOrder],
                                                      # tube_radius=1.5 / ((reflectionOrder + 1) * 10),
                                                      figure=mayaviScene)
                            realTube.append(tube)
                            tube.filter.radius_factor = 0.1
                            tubeCurrent.append(mlab.pipeline.surface(tube, figure=mayaviScene))
                            tubeCurrent[reflectionOrder].actor.property.color = self.mimoStreamProperties[
                            streamId].color
                            realTube[reflectionOrder].filter.radius = self.mimoStreamProperties[
                            streamId].width
                    self.mimoTubeObjects[streamId] = realTube
                    self.mimoTubeMesh[streamId] = tubeCurrent
                    self.mpcVerticesDicVisObjMIMO[streamId] = mpcPointCurrent
                else:
                    for reflectionOrder in range(0, maxReflectionOrder + 1):
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            mimoInitiatorId, txPaa, mimoResponderId,
                            rxPaa, reflectionOrder, traceIndex)
                        self.mpcVerticesDicVisObjMIMO[streamId][reflectionOrder].mlab_source.set(x=xMpcCoordinate,
                                                                                            y=yMpcCoordinate,
                                                                                            z=zMpcCoordinate)
    def updateSuMimoVisuals(self):
        """Update SU-MIMO Visuals
        """
        # Get the MIMO Initator and Receiver using the nodes selected in the GUI
        mimoInitiatorId = int(self.guiTxNodeSelected)
        mimoResponderId = int(self.guiRxNodeSelected)
        mimoKey = (self.traceIndex, mimoInitiatorId, mimoResponderId)
        if self.guiMimoData == "Oracle":
            if qdScenario.qdInterpreterConfig.mimoDataMode == 'none':
                globals.logger.warning(
                    "SU-MIMO Oracle results cannot be displayed if mimoDataMode flag is set to 'none' - Please set the flag to 'online' or 'preprocessed'")
                return
            elif qdScenario.qdInterpreterConfig.mimoDataMode == 'online':
                # SU-MIMO results computed online
                    suMimoResultsToUse = computeSuMimoBft(
                        mimoInitiatorId, mimoResponderId, int(self.traceIndex),
                        qdScenario, qdScenario.qdChannel, txParam, 355, codebooks)
            elif qdScenario.qdInterpreterConfig.mimoDataMode == 'preprocessed':
                suMimoResultsToUse = qdScenario.oracleSuMimoResults[mimoKey]
        elif self.guiMimoData == "ns-3":
            # SU-MIMO results from ns-3
            if qdScenario.nsSuMimoResults:
                suMimoResultsToUse = qdScenario.nsSuMimoResults[mimoKey]
            else:
                # The ns-3 results are not available
                globals.logger.warning("ns-3 SU-MIMO Results not available - Please check that you correctly imported them")
                return

        # In this case, bestStreamIdCombination list contains best stream PAA TX / PAA RX pair
        # format: Stream 0 [PAA TX Stream 0, PAA RX Stream 0] Stream 1 [PAA TX Stream 1,  PAA RX Stream 1]
        self.bestreamPaaIdCombination = suMimoResultsToUse.bestreamIdCombination
        nbStream = len(suMimoResultsToUse.bestreamIdCombination)
        # Initiator MIMO results
        txSectorIds = suMimoResultsToUse.txSectorId  # Get the the best Tx Sectors for each stream
        txAwvs = suMimoResultsToUse.txAwvId  # Get the best Tx AWVs for each stream
        # Responder MIMO results
        rxSectorIds = suMimoResultsToUse.rxSectorId  # Get the best Rx Sectors for each stream
        rxAwvs = suMimoResultsToUse.rxAwvId  # Get the best Rx AWVs for each stream
        self.bestSectorsCombination = [txSectorIds, rxSectorIds]

        # Construct the SU-MIMO Visualization
        for streamId in range(nbStream):
            paaTxStream = self.bestreamPaaIdCombination[streamId][0] # Tx Paa of the MIMO initiator streamIdth stream
            paaRxStream = self.bestreamPaaIdCombination[streamId][1] # Rx Paa of the MIMO responder streamIdth stream
            # Display the Antenna Patterns between initiator PAA and responder PAA for every stream
            # ns-3 does not yet use the custom refined AWV and thus set the AWV to 255
            # If this is the case, we set the AWV to be 2 as it corresponds to the sector
            if txAwvs[streamId] == 255:
                txAwvs[streamId] = 2
            azimuthTx, elevationTx = codebooks.getRefinedAwvAzimuthElevation(txSectorIds[streamId],
                                                                             txAwvs[streamId],
                                                                             qdScenario.getNodeType(
                                                                                 mimoInitiatorId))
            # Get the Antenna Pattern of the initiator
            txxAntennaPattern, txyAntennaPattern, txzAntennaPattern, txcolorAntennaPattern = codebooks.getRefinedAwvRadiationPatternDic(
                azimuthTx, elevationTx, qdScenario.getNodeType(mimoInitiatorId))
            filterPattern = qdScenario.qdInterpreterConfig.patternQuality
            txxAntennaPattern = txxAntennaPattern[::filterPattern]
            txyAntennaPattern = txyAntennaPattern[::filterPattern]
            txzAntennaPattern = txzAntennaPattern[::filterPattern]
            txcolorAntennaPattern = txcolorAntennaPattern[::filterPattern]


            # ns-3 does not yet use the custom refined AWV and thus set the AWV to 255
            # If this is the case, we set the AWV to be 2 as it corresponds to the sector
            if rxAwvs[streamId] == 255:
                rxAwvs[streamId] = 2
            azimuthRx, elevationRx = codebooks.getRefinedAwvAzimuthElevation(rxSectorIds[streamId],
                                                                             rxAwvs[streamId],
                                                                             qdScenario.getNodeType(
                                                                                 mimoResponderId))
            # Get the Antenna Pattern of the responder
            rxxAntennaPattern, rxyAntennaPattern, rxzAntennaPattern, rxcolorAntennaPattern = codebooks.getRefinedAwvRadiationPatternDic(
                azimuthRx, elevationRx, qdScenario.getNodeType(mimoResponderId))
            rxxAntennaPattern = rxxAntennaPattern[::filterPattern]
            rxyAntennaPattern = rxyAntennaPattern[::filterPattern]
            rxzAntennaPattern = rxzAntennaPattern[::filterPattern]
            rxcolorAntennaPattern = rxcolorAntennaPattern[::filterPattern]
            if streamId not in self.mimoStreamPatterns:
                # The Antenna Patterns corresponding to the stream have never been created

                # Creation of the Tx Antenna Pattern for the stream
                txStreamPattern = mlab.mesh(txxAntennaPattern,
                                            txyAntennaPattern,
                                            txzAntennaPattern,
                                            vmin=np.amin(txcolorAntennaPattern),
                                            vmax=np.amax(txcolorAntennaPattern),
                                            tube_radius=0.025,
                                            figure=self.view2.mayavi_scene,
                                            name="SUMIMOTxStream" + str(streamId),
                                            reset_zoom=False,
                                            scalars=txcolorAntennaPattern)



                # Creation of the Rx Antenna Pattern for the stream
                rxStreamPattern = mlab.mesh(rxxAntennaPattern,
                                            rxyAntennaPattern,
                                            rxzAntennaPattern,
                                            vmin=np.amin(rxcolorAntennaPattern),
                                            vmax=np.amax(rxcolorAntennaPattern),
                                            tube_radius=0.025,
                                            figure=self.view2.mayavi_scene,
                                            name="SUMIMORxStream" + str(streamId),
                                            reset_zoom=False,
                                            scalars=rxcolorAntennaPattern)


                # Visualization properties
                txStreamPattern.actor.property.edge_visibility = True
                txStreamPattern.actor.property.specular = 1.0
                txStreamPattern.actor.property.specular_power = 66.0
                txStreamPattern.actor.property.edge_color = self.mimoStreamProperties[
                    streamId].color

                rxStreamPattern.actor.property.edge_visibility = True
                rxStreamPattern.actor.property.specular = 1.0
                rxStreamPattern.actor.property.specular_power = 66.0
                rxStreamPattern.actor.property.edge_color = self.mimoStreamProperties[streamId].color

                if self.savedMimoConfig:
                    txStreamPattern.actor.actor.scale = (self.mimoStreamPatternSize[streamId],self.mimoStreamPatternSize[streamId],self.mimoStreamPatternSize[streamId])
                    txStreamPattern.actor.property.line_width =self.mimoStreamEdgeSize[streamId]

                    rxStreamPattern.actor.actor.scale = (
                    self.mimoStreamPatternSize[streamId], self.mimoStreamPatternSize[streamId], self.mimoStreamPatternSize[streamId])
                    rxStreamPattern.actor.property.line_width = self.mimoStreamEdgeSize[streamId]

                self.mimoStreamPatterns[streamId] = [txStreamPattern, rxStreamPattern]
            else:
                # The Antenna Patterns corresponding to the stream have been created previously - Just update them

                # Tx Antenna Pattern Stream Update
                self.mimoStreamPatterns[streamId][0].mlab_source.set(x=txxAntennaPattern, y=txyAntennaPattern,
                                                                      z=txzAntennaPattern,
                                                                      scalars=txcolorAntennaPattern,
                                                                      vmin=np.amin(txcolorAntennaPattern),
                                                                      vmax=np.amax(txcolorAntennaPattern))
                self.mimoStreamPatterns[streamId][0].module_manager.scalar_lut_manager.data_range = [
                    np.amin(txcolorAntennaPattern), np.amax(txcolorAntennaPattern)]
                txStreamPattern = self.mimoStreamPatterns[streamId][0]

                # Rx Antenna Pattern Stream Update
                self.mimoStreamPatterns[streamId][1].mlab_source.set(x=rxxAntennaPattern, y=rxyAntennaPattern,
                                                                      z=rxzAntennaPattern,
                                                                      scalars=rxcolorAntennaPattern,
                                                                      vmin=np.amin(rxcolorAntennaPattern),
                                                                      vmax=np.amax(rxcolorAntennaPattern))
                self.mimoStreamPatterns[streamId][1].module_manager.scalar_lut_manager.data_range = [
                    np.amin(rxcolorAntennaPattern), np.amax(rxcolorAntennaPattern)]
                rxStreamPattern = self.mimoStreamPatterns[streamId][1]

            # Set the position and orientations of Tx Stream
            txStreamPattern.actor.actor.position = qdScenario.getPaaPosition(mimoInitiatorId,
                                                                             paaTxStream,
                                                                             int(self.traceIndex))
            txStreamPattern.actor.actor.orientation = (
                self.computePaaRotationAngles(mimoInitiatorId, paaTxStream,
                                              int(self.traceIndex)))

            # Set the position and orientations of Rx Stream
            rxStreamPattern.actor.actor.position = qdScenario.getPaaPosition(mimoResponderId,
                                                                             paaRxStream,
                                                                             int(self.traceIndex))
            rxStreamPattern.actor.actor.orientation = (
                self.computePaaRotationAngles(int(mimoResponderId), paaRxStream,
                                              int(self.traceIndex)))

            self.makeVisible(txStreamPattern)
            self.makeVisible(rxStreamPattern)


            if streamId not in self.mimoTubeMesh:
                mpcPointCurrent = []  # The vertices of the MPCs
                tubeCurrent = []  # the tube connected the MPCs
                realTube = []
                for reflectionOrder in range(0, maxReflectionOrder + 1):
                    if mimoInitiatorId < mimoResponderId:
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            mimoInitiatorId, paaTxStream, mimoResponderId,
                            paaRxStream, reflectionOrder, self.traceIndex)
                    else:
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            mimoResponderId, paaRxStream, mimoInitiatorId,
                            paaTxStream, reflectionOrder, self.traceIndex)

                    if len(xMpcCoordinate) > 0:
                        mpcPointCurrent.append(
                            mlab.points3d(xMpcCoordinate, yMpcCoordinate, zMpcCoordinate,
                                          scale_factor=1, reset_zoom=False,
                                          name="MPC TX:" + str(mimoInitiatorId) + "RX:" + str(
                                              mimoResponderId) + "Refl:" + str(
                                              reflectionOrder), figure=self.view2.mayavi_scene))

                        mpcPointCurrent[reflectionOrder].actor.actor.visibility = False
                        # Connect the MPCs points with tubes
                        connections = tuple()
                        nbPathToConnect = xMpcCoordinate.size  # Get the total number of MPCs coordinates
                        for i in range(0, nbPathToConnect, 2 + reflectionOrder):
                            idConnection = 0
                            for j in range(reflectionOrder + 1):
                                connections = connections + ((i + idConnection, i + 1 + idConnection),)
                                idConnection = idConnection + 1
                        mpcPointCurrent[reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                        tube = mlab.pipeline.tube(mpcPointCurrent[reflectionOrder],
                                                  # tube_radius=1.5 / ((reflectionOrder + 1) * 10),
                                                  figure=self.view2.mayavi_scene)
                        realTube.append(tube)
                        tube.filter.radius_factor = 0.1
                        tubeCurrent.append(mlab.pipeline.surface(tube, figure=self.view2.mayavi_scene))
                        tubeCurrent[reflectionOrder].actor.property.color = self.mimoStreamProperties[
                            streamId].color
                        realTube[reflectionOrder].filter.radius = self.mimoStreamProperties[
                            streamId].width
                self.mimoTubeObjects[streamId] = realTube
                self.mimoTubeMesh[streamId] = tubeCurrent
                self.mpcVerticesDicVisObjMIMO[streamId] = mpcPointCurrent
            else:
                for reflectionOrder in range(0, maxReflectionOrder + 1):

                    if mimoInitiatorId < mimoResponderId:
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            mimoInitiatorId, paaTxStream, mimoResponderId,
                            paaRxStream, reflectionOrder, self.traceIndex)
                    else:
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            mimoResponderId, paaRxStream, mimoInitiatorId,
                            paaTxStream, reflectionOrder, self.traceIndex)
                    self.mpcVerticesDicVisObjMIMO[streamId][reflectionOrder].mlab_source.set(x=xMpcCoordinate,
                                                                                             y=yMpcCoordinate,

                                                                                               z=zMpcCoordinate)

    def updateMuMimoVisuals(self):
        """Update MU-MIMO Visuals
        """
        mimoGroupId = 1 # TODO: For now, Group ID is always set to 1 as ns-3 MIMO use-cases only work between a single AP and multiple STAs
        # Get the MIMO Initator and Receiver using the nodes selected in the GUI
        mimoInitiatorId = int(self.guiTxNodeSelected)
        mimoKey = (self.traceIndex, mimoGroupId)
        # We consider the responder to have only one PAA and set the variable fakePaaRx to 0
        # TODO revisit later on
        fakePaaRx = 0
        if self.guiMimoData == "Oracle":
            # Results obtained thanks to Q-D Interpreter Oracle Mode
            if qdScenario.qdInterpreterConfig.mimoDataMode == 'none':
                globals.logger.warning(
                    "MU-MIMO Oracle results cannot be displayed if mimoDataMode flag is set to 'none' - Please set the flag to 'online' or 'preprocessed'")
                return
            elif qdScenario.qdInterpreterConfig.mimoDataMode == 'online':
                # MU-MIMO results computed online
                # For now, we hardcode the MIMO Initiator and MIMO Responders as the GUI to select MIMO group and responders is not available
                # TODO fix that if needed
                mimoInitiatorId = 0
                mimoResponderIds = [1, 2]
                muMimoResultsToUse = computeMuMimoBft(mimoInitiatorId,mimoResponderIds,self.traceIndex,
                     qdScenario, qdScenario.qdChannel, txParam, 355, codebooks)
            elif qdScenario.qdInterpreterConfig.mimoDataMode == 'preprocessed':
                muMimoResultsToUse = qdScenario.oracleMuMimoResults[mimoKey]
        elif self.guiMimoData == "ns-3":
            # MU-MIMO results from ns-3
            if qdScenario.nsMuMimoResults:
                muMimoResultsToUse =  qdScenario.nsMuMimoResults[mimoKey]
            else:
                # The ns-3 results are not available
                globals.logger.warning(
                    "ns-3 SU-MIMO Results not available - Please check that you correctly imported them")
                return

        self.bestreamPaaIdCombination = muMimoResultsToUse.bestreamIdCombination
        nbStream = len(muMimoResultsToUse.txAwvId)
        # Initiator MIMO results
        txSectorIds = muMimoResultsToUse.txSectorId  # Get the the best Tx Sectors for each stream
        txAwvs = muMimoResultsToUse.txAwvId  # Get the best Tx AWVs for each stream
        # Responder MIMO results
        rxSectorIds = muMimoResultsToUse.rxSectorId  # Get the best Rx Sectors for each stream
        rxAwvs = muMimoResultsToUse.rxAwvId  # Get the best Rx AWVs for each stream
        self.bestSectorsCombination = [txSectorIds, rxSectorIds]

        for streamId in range(nbStream):
            paaTxStream = self.bestreamPaaIdCombination[streamId][
                0]  # Tx Paa of the MIMO initiator streamIdth stream
            idRxStream = self.bestreamPaaIdCombination[streamId][
                1]  # Rx Paa of the MIMO responder streamIdth stream

            # ns-3 does not yet use the custom refined AWV and thus set the AWV to 255
            # If this is the case, we set the AWV to be 2 as it corresponds to the sector
            if txAwvs[streamId] == 255:
                txAwvs[streamId] = 2
            # Get the Antenna Pattern of the initiator
            azimuthTx, elevationTx = codebooks.getRefinedAwvAzimuthElevation(txSectorIds[streamId],
                                                                             txAwvs[streamId],
                                                                             qdScenario.getNodeType(
                                                                                 mimoInitiatorId))

            filterPattern = qdScenario.qdInterpreterConfig.patternQuality
            txxAntennaPattern, txyAntennaPattern, txzAntennaPattern, txcolorAntennaPattern = codebooks.getRefinedAwvRadiationPatternDic(
                azimuthTx, elevationTx, qdScenario.getNodeType(mimoInitiatorId))

            txxAntennaPattern = txxAntennaPattern[::filterPattern]
            txyAntennaPattern = txyAntennaPattern[::filterPattern]
            txzAntennaPattern = txzAntennaPattern[::filterPattern]
            txcolorAntennaPattern = txcolorAntennaPattern[::filterPattern]

            # Get the Antenna Pattern of the responder
            # ns-3 does not yet use the custom refined AWV and thus set the AWV to 255
            # If this is the case, we set the AWV to be 2 as it corresponds to the sector
            if rxAwvs[streamId] == 255:
                rxAwvs[streamId] = 2
            azimuthRx, elevationRx = codebooks.getRefinedAwvAzimuthElevation(rxSectorIds[streamId],
                                                                             rxAwvs[streamId],
                                                                             qdScenario.getNodeType(idRxStream))
            rxxAntennaPattern, rxyAntennaPattern, rxzAntennaPattern, rxcolorAntennaPattern = codebooks.getRefinedAwvRadiationPatternDic(
                    azimuthRx, elevationRx, qdScenario.getNodeType(idRxStream))

            rxxAntennaPattern = rxxAntennaPattern[::filterPattern]
            rxyAntennaPattern = rxyAntennaPattern[::filterPattern]
            rxzAntennaPattern = rxzAntennaPattern[::filterPattern]
            rxcolorAntennaPattern = rxcolorAntennaPattern[::filterPattern]

            if streamId not in self.mimoStreamPatterns:
                # The Antenna Patterns corresponding to the stream have never been created
                color = []
                color.append((0.6666666666666666, 1.0, 0.4980392156862745))
                color.append((0.6666666666666666, 1.0, 1.0))
                color.append((1.0, 0.6666666666666666, 1.0))
                color.append((1.0, 0.6666666666666666, 0.4980392156862745))
                # Creation of the Tx Antenna Pattern for the stream
                txStreamPattern = mlab.mesh(txxAntennaPattern,
                                            txyAntennaPattern,
                                            txzAntennaPattern,
                                            vmin=np.amin(txcolorAntennaPattern),
                                            vmax=np.amax(txcolorAntennaPattern),
                                            tube_radius=0.025,
                                            figure=self.view2.mayavi_scene,
                                            name="MUMIMOTxStream" + str(streamId),
                                            reset_zoom=False,
                                            scalars=txcolorAntennaPattern)

                # Creation of the Rx Antenna Pattern for the stream
                rxStreamPattern = mlab.mesh(rxxAntennaPattern,
                                            rxyAntennaPattern,
                                            rxzAntennaPattern,
                                            vmin=np.amin(rxcolorAntennaPattern),
                                            vmax=np.amax(rxcolorAntennaPattern),
                                            tube_radius=0.025,
                                            figure=self.view2.mayavi_scene,
                                            name="MUMIMORxStream" + str(streamId),
                                            reset_zoom=False,
                                            scalars=rxcolorAntennaPattern)

                # Visualization properties
                txStreamPattern.actor.property.edge_visibility = True
                txStreamPattern.actor.property.specular = 1.0
                txStreamPattern.actor.property.specular_power = 66.0
                txStreamPattern.actor.property.edge_color = self.mimoStreamProperties[
                    streamId].color

                rxStreamPattern.actor.property.edge_visibility = True
                rxStreamPattern.actor.property.specular = 1.0
                rxStreamPattern.actor.property.specular_power = 66.0
                rxStreamPattern.actor.property.edge_color = self.mimoStreamProperties[streamId].color

                if self.savedMimoConfig:
                    txStreamPattern.actor.actor.scale = (
                    self.mimoStreamPatternSize[streamId], self.mimoStreamPatternSize[streamId],
                    self.mimoStreamPatternSize[streamId])
                    txStreamPattern.actor.property.line_width = self.mimoStreamEdgeSize[streamId]

                    rxStreamPattern.actor.actor.scale = (
                        self.mimoStreamPatternSize[streamId], self.mimoStreamPatternSize[streamId],
                        self.mimoStreamPatternSize[streamId])
                    rxStreamPattern.actor.property.line_width = self.mimoStreamEdgeSize[streamId]
                self.mimoStreamPatterns[streamId] = [txStreamPattern, rxStreamPattern]
            else:
                # The Antenna Patterns corresponding to the stream have been created previously - Just update them

                # Tx Antenna Pattern Stream Update
                self.mimoStreamPatterns[streamId][0].mlab_source.set(x=txxAntennaPattern, y=txyAntennaPattern,
                                                                 z=txzAntennaPattern, scalars=txcolorAntennaPattern,
                                                                 vmin=np.amin(txcolorAntennaPattern),
                                                                 vmax=np.amax(txcolorAntennaPattern))
                self.mimoStreamPatterns[streamId][0].module_manager.scalar_lut_manager.data_range = [
                    np.amin(txcolorAntennaPattern), np.amax(txcolorAntennaPattern)]
                txStreamPattern = self.mimoStreamPatterns[streamId][0]

                # Rx Antenna Pattern Stream Update
                self.mimoStreamPatterns[streamId][1].mlab_source.set(x=rxxAntennaPattern, y=rxyAntennaPattern,
                                                                 z=rxzAntennaPattern, scalars=rxcolorAntennaPattern,
                                                                 vmin=np.amin(rxcolorAntennaPattern),
                                                                 vmax=np.amax(rxcolorAntennaPattern))
                self.mimoStreamPatterns[streamId][1].module_manager.scalar_lut_manager.data_range = [
                    np.amin(rxcolorAntennaPattern), np.amax(rxcolorAntennaPattern)]
                rxStreamPattern = self.mimoStreamPatterns[streamId][1]


            # Set the position and orientations of Tx Stream
            txStreamPattern.actor.actor.position = qdScenario.getPaaPosition(mimoInitiatorId,
                                                                             paaTxStream,
                                                                             int(self.traceIndex))


            txStreamPattern.actor.actor.orientation = (
                self.computePaaRotationAngles(mimoInitiatorId, paaTxStream,
                                              int(self.traceIndex)))



            # Set the position and orientations of Rx Stream
            rxStreamPattern.actor.actor.position = qdScenario.getPaaPosition(idRxStream,
                                                                             0,
                                                                             int(self.traceIndex)) # TODO Replace with fake 0
            rxStreamPattern.actor.actor.orientation = (
                self.computePaaRotationAngles(idRxStream, 0,
                                              int(self.traceIndex)))
            self.makeVisible(txStreamPattern)
            self.makeVisible(rxStreamPattern)
            # MPCs
            if streamId not in self.mimoTubeMesh:
                mpcPointCurrent = []  # The vertices of the MPCs
                tubeCurrent = []  # the tube connected the MPCs
                realTube = []
                for reflectionOrder in range(0, maxReflectionOrder + 1):
                    if mimoInitiatorId < idRxStream:
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            mimoInitiatorId, paaTxStream, idRxStream,
                            fakePaaRx, reflectionOrder, self.traceIndex) # 0 for PAA ID
                    else:
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            idRxStream, fakePaaRx, mimoInitiatorId,
                            paaTxStream, reflectionOrder, self.traceIndex)

                    if len(xMpcCoordinate) > 0:
                        mpcPointCurrent.append(
                            mlab.points3d(xMpcCoordinate, yMpcCoordinate, zMpcCoordinate,
                                          scale_factor=1, reset_zoom=False,
                                          name="MPC TX:" + str(mimoInitiatorId) + "RX:" + str(idRxStream) + "Refl:" + str(
                                              reflectionOrder), figure=self.view2.mayavi_scene))

                        mpcPointCurrent[reflectionOrder].actor.actor.visibility = False
                        # Connect the MPCs points with tubes
                        connections = tuple()
                        nbPathToConnect = xMpcCoordinate.size  # Get the total number of MPCs coordinates
                        for i in range(0, nbPathToConnect, 2 + reflectionOrder):
                            idConnection = 0
                            for j in range(reflectionOrder + 1):
                                connections = connections + ((i + idConnection, i + 1 + idConnection),)
                                idConnection = idConnection + 1
                        mpcPointCurrent[reflectionOrder].mlab_source.dataset.lines = np.array(connections)
                        tube = mlab.pipeline.tube(mpcPointCurrent[reflectionOrder],
                                                  # tube_radius=1.5 / ((reflectionOrder + 1) * 10),
                                                  figure=self.view2.mayavi_scene)
                        realTube.append(tube)
                        tube.filter.radius_factor = 0.1
                        tubeCurrent.append(mlab.pipeline.surface(tube, figure=self.view2.mayavi_scene))
                        tubeCurrent[reflectionOrder].actor.property.color = color[streamId]
                        tubeCurrent[reflectionOrder].actor.property.color = self.mimoStreamProperties[
                            streamId].color
                self.mimoTubeObjects[streamId] = realTube
                self.mimoTubeMesh[streamId] = tubeCurrent
                self.mpcVerticesDicVisObjMIMO[streamId] = mpcPointCurrent
            else:
                for reflectionOrder in range(0, maxReflectionOrder + 1):
                    if mimoInitiatorId < idRxStream:
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            mimoInitiatorId, self.bestreamPaaIdCombination[streamId][0], idRxStream,
                            fakePaaRx, reflectionOrder, self.traceIndex)
                    else:
                        xMpcCoordinate, yMpcCoordinate, zMpcCoordinate = qdRealization.getMpcCoordinates(
                            idRxStream, fakePaaRx, mimoInitiatorId,
                            self.bestreamPaaIdCombination[streamId][0], reflectionOrder, self.traceIndex)
                    self.mpcVerticesDicVisObjMIMO[streamId][reflectionOrder].mlab_source.reset(x=xMpcCoordinate,
                                                                                          y=yMpcCoordinate,
                                                                                          z=zMpcCoordinate)

    def displayTxss(self, txNode, paaTx, txssSector, traceIndex, role):
        """Display the antenna pattern directivity of the sector txssSector for nodeIndex node

        Parameters
        ----------
        txNode : int
            The Tx Node ID
        paaTx : int
            PAA of the node
        traceIndex: int
            TraceIndex
        """
        if txssSector != -1:
            # Display The txssSector antenna pattern for the node txNode
            xSTACoordinates, ySTACoordinates, zSTACoordinates = qdScenario.getPaaPosition(txNode, paaTx, traceIndex)
            tupleIdentifier = qdScenario.getNodeType(txNode).value, paaTx, txssSector, role
            # Update the antenna pattern position to the STA current position
            self.txSectorsAntennaPatternVisObj[tupleIdentifier].actor.actor.position = (
                xSTACoordinates, ySTACoordinates, zSTACoordinates)
            # Color the antenna pattern (depends from the TX type)
            if qdScenario.isNodeAp(txNode):
                # Node is an AP
                self.txSectorsAntennaPatternVisObj[tupleIdentifier].module_manager.scalar_lut_manager.data_range = [
                    np.amin(codebooks.getApSectorPattern(txssSector, paaTx)[3]),
                    np.amax(codebooks.getApSectorPattern(txssSector, paaTx)[3])]
            else:
                # Node is a STA
                self.txSectorsAntennaPatternVisObj[tupleIdentifier].module_manager.scalar_lut_manager.data_range = [
                    np.amin(codebooks.getStaSectorPattern(txssSector, paaTx)[3]),
                    np.amax(codebooks.getStaSectorPattern(txssSector, paaTx)[3])]
            # Apply both device rotations and PAA initial orientation
            self.txSectorsAntennaPatternVisObj[tupleIdentifier].actor.actor.orientation = (
                self.computePaaRotationAngles(txNode, paaTx, traceIndex))
            # Make the antenna pattern visible
            self.makeVisible(self.txSectorsAntennaPatternVisObj[tupleIdentifier])

    def displayQuasiOmniRxPattern(self, txssSector, rxNode, paaRx, traceIndex):
        """Display the Quasi-Omni Rx Pattern of the Paa Rx

        Parameters
        ----------
        txssSector : Int
            The txssSector ID
        rxNode : Int
            The Rx Node ID
        paaRx : Int
            The Paa Rx ID
        traceIndex : int
            The trace index
        """
        if txssSector != -1:  # TODO Replace -1 with NO_VALID_TXSS
            # We won't display any quasi-omni pattern if the txssSector is not valid
            nodeType = qdScenario.getNodeType(rxNode)
            # Update the position of the Quasi-Rx Omni pattern
            self.quasiOmniAntennaPatternVisObj[nodeType, paaRx].actor.actor.position = qdScenario.getPaaPosition(rxNode,
                                                                                                                 paaRx,
                                                                                                                 traceIndex)
            # Apply the rotations (both device rotation and PAA initial orientation)
            self.quasiOmniAntennaPatternVisObj[nodeType, paaRx].actor.actor.orientation = (
                self.computePaaRotationAngles(rxNode, paaRx, traceIndex))
            # Display the quasi-omni of the selected Rx PAA
            self.makeVisible(self.quasiOmniAntennaPatternVisObj[nodeType, paaRx])

    def updateOrientationAxes(self, txNode, rxNode, paaTx, paaRx):
        """Update the orientation axes visuals for either devices or PAAs
        """
        # Display the TX and RX devices orientation axes
        self.updateNodesOrientationAxes(txNode, rxNode, self.guiDisplayDeviceTxAxis, self.guiDisplayDeviceRxAxis,
                                        int(self.traceIndex))

        # Display Tx and Rx Paa Orientation axes
        self.updatePaasOrientationAxes(txNode, paaTx, self.guiDisplayPaaTxAxis, rxNode, paaRx,
                                       self.guiDisplayPaaRxAxis, int(self.traceIndex))

    def displayStasAssociation(self, traceIndex):
        """Display with a colored sphere around the STAs the AP to which a STA is associated

        Parameters
        ----------
        traceIndex : Int
            The trace index
        """
        if self.guiSlsMode == "Oracle":
            # We can only know the AP the STA is associated if using the Oracle

            if qdScenario.qdInterpreterConfig.dataMode == 'online' and not qdScenario.qdInterpreterConfig.plotData:
                # If using online mode and not displaying the plots, we just compute for the Tx/Rx pair selected
                # so it would be impossible to know to which AP the STA should be associated
                print("STA association cannot be displayed when using online mode and plotData set to 0")

                return
            colorCode = []  # We will color the sphere around the STA with the color of the APs
            for i in range(qdScenario.nbAps, qdScenario.nbNodes):
                if qdScenario.qdInterpreterConfig.dataMode == 'online':
                    # Use the computed data
                    if i in dicBestAPPerSta:
                        colorCode.append(dicBestAPPerSta[(i)][1])
                else:
                    # Use the preprocessed data
                    if (i, int(traceIndex)) in qdScenario.preprocessedAssociationData:
                        colorCode.append(qdScenario.preprocessedAssociationData[(i, traceIndex)][1])
            # Update the positions of the sphere and their color
            xStaCoordinates, yStaCoordinates, zStaCoordinates = qdScenario.getAllSTAsPosition(traceIndex)
            self.stasAssociationVisObj.mlab_source.set(x=xStaCoordinates, y=yStaCoordinates,
                                                       z=zStaCoordinates, scalars=colorCode)

    #######################################################################
    #            FUNCTIONS TO HANDLE GUI INTERACTIONS                     #
    #######################################################################
    # Scenario Interaction Tab
    @on_trait_change('guiVisualizerInteractions')
    def playerInteraction(self):
        """Update the visualization by iterating over the traces if play and back buttons are pressed and to reset if the stop button is pressed
        """
        if self.guiVisualizerInteractions == "play" or self.guiVisualizerInteractions == "back":

            self.animateOneStep()
        elif self.guiVisualizerInteractions == "stop":
            if qdScenario.qdInterpreterConfig.plotData:
                for tx in range(qdScenario.nbNodes):
                    for rx in range(qdScenario.nbNodes):
                        # Creation of Power plots
                        if tx != rx:
                            for apPaaId in range(codebooks.getNbPaaPerAp()):
                                for staPaaId in range(codebooks.getNbPaaPerSta()):
                                    CURVES_DIC[
                                        ("Power", tx, rx, apPaaId, staPaaId)].setData([0], [0],
                                                                                      clear=True)
                                    Y_CURVE_DATA_DIC[("Power", tx, rx, apPaaId, staPaaId)] = np.empty(100)
                                    Y_CURVE_DATA_DIC[("Power", tx, rx, apPaaId, staPaaId)].fill(-math.inf)
            self.traceIndex = 0

    @on_trait_change('guiSwitchTxRxNode')
    def switchTxRX(self):
        """Switch the Tx and Rx selected node
        """
        newTxStr = self.guiRxNodeSelected
        newRxStr = self.guiTxNodeSelected

        if qdScenario.nbNodes > 2:
            # Perform the switch
            self.guiTxNodeSelected = newTxStr
            self.guiRxNodeSelected = newRxStr

            # We need to update the nodes choices
            nodeChosen = []
            for i in range(qdScenario.nbNodes):
                if i != int(newRxStr):
                    nodeChosen.append(str(i))
            self.guiTxNodeSelectedChoices = nodeChosen
            nodeChosen = []
            for i in range(qdScenario.nbNodes):
                if i != int(newTxStr):
                    nodeChosen.append(str(i))

            self.guiRxNodeSelectedChoices = nodeChosen

        else:
            # Perform the switch
            self.guiTxNodeSelected = newTxStr
            self.guiRxNodeSelected = newRxStr
            # We need to update the nodes choices
            self.guiTxNodeSelectedChoices = [newTxStr]
            self.guiRxNodeSelectedChoices = [newRxStr]



    # Visualisation tweak tab
    @on_trait_change('guiStasNodesSize,guiApsNodesSize')
    def updateApsStasSize(self, obj, name, old, new):
        """Change the size of the STAs or APs nodes
        """
        if name == 'guiStasNodesSize':
            # Update STAs size
            self.stasVisObj.glyph.glyph.scale_factor = self.guiStasNodesSize
        else:
            # Update APs size
            self.apsVisObj.glyph.glyph.scale_factor = self.guiApsNodesSize
        self.forceRender()

    @on_trait_change('guiDisplayNodesObjects')
    def showApsStasModels(self):
        """Display the 3D object associated to the STAs and the APSs
        """
        # TODO This code could be easily factorized
        if self.guiDisplayNodesObjects:
            # Display the STA and AP 3D Models
            # APs Objects
            for apId in range(qdScenario.nbAps):
                if self.apTextureMode == "none" or self.apTextureMode == "jpg":
                    # Case where AP object is made of a single mesh
                    # Take care of Assigning the correct positions and rotations
                    self.apModelVisObj[apId].actor.actor.position = qdScenario.getNodePosition(
                        self.traceIndex, apId)
                    self.apModelVisObj[apId].actor.actor.orientation = (
                        qdScenario.getNodeRotation(self.traceIndex, apId))
                    # Make the AP object visible
                    self.makeVisible(self.apModelVisObj[apId])
                else:
                    # Each AP object is made of many individual textures objects - Iterate through all of them
                    for individualObject in self.apModelVisObj[apId]:
                        # Take care of Assigning the correct positions and rotations
                        individualObject.position = qdScenario.getNodePosition(
                            self.traceIndex, apId)
                        individualObject.orientation = (
                            qdScenario.getNodeRotation(self.traceIndex, apId))
                        # Make the AP object visible
                        individualObject.visibility = True

                # Hide the APs PAAs
                for paaID in range(codebooks.getNbPaaPerAp()):
                    self.makeInvisible(self.paasElementsVisObj[(apId, paaID)])
            # Hide the 3D spheres representing the APs
            self.makeInvisible(self.apsVisObj)

            # STAs objects
            for staId in range(qdScenario.nbAps, qdScenario.nbNodes):
                if self.staTextureMode == "none" or self.staTextureMode == "jpg":
                    # Case where STAs object is made of a single mesh
                    # Take care of Assigning the correct positions and rotations
                    self.staModelVisObj[staId - qdScenario.nbAps].actor.actor.position = qdScenario.getNodePosition(
                        self.traceIndex, staId)  # staId - qdScenario.nbAps as indexed from 0
                    self.staModelVisObj[staId - qdScenario.nbAps].actor.actor.orientation = (
                        qdScenario.getNodeRotation(self.traceIndex, staId))
                    # Make the STAs object visible
                    self.makeVisible(self.staModelVisObj[staId - qdScenario.nbAps])
                else:
                    # Each STA object is made of individual textures objects - Iterate through all of them
                    for individualObject in self.staModelVisObj[staId - qdScenario.nbAps]:
                        # Take care of Assigning the correct positions and rotations
                        individualObject.position = qdScenario.getNodePosition(
                            self.traceIndex, staId)
                        individualObject.orientation = (
                            qdScenario.getNodeRotation(self.traceIndex, staId))
                        # Make the STAs object visible
                        individualObject.visibility = True
                # Hide the STAs PAAs
                for paaID in range(codebooks.getNbPaaPerSta()):
                    self.makeInvisible(self.paasElementsVisObj[(staId, paaID)])
            self.makeInvisible(self.stasVisObj)
        else:
            # Just display the STAs and APs simple representation (3D sphere) and PAAs

            # APs
            for apId in range(qdScenario.nbAps):
                # Hide the 3D models
                if self.apTextureMode == "none" or self.apTextureMode == "jpg":
                    self.makeInvisible(self.apModelVisObj[apId])
                else:
                    for individualActor in self.apModelVisObj[apId]:
                        individualActor.visibility = False
                # Display the PAAs
                for paaID in range(codebooks.getNbPaaPerAp()):
                    self.makeVisible(self.paasElementsVisObj[(apId, paaID)])
            # Display the APs 3D spheres
            self.makeVisible(self.apsVisObj)

            # STAs


            for staId in range(qdScenario.nbStas):
                # Hide the 3D models
                if self.staTextureMode == "none" or self.staTextureMode == "jpg":
                    self.makeInvisible(self.staModelVisObj[staId])
                else:
                    for individualActor in self.staModelVisObj[staId]:
                        individualActor.visibility = False
                # Display the PAAs
                for paaID in range(codebooks.getNbPaaPerSta()):
                    self.makeVisible(self.paasElementsVisObj[(staId + qdScenario.nbAps, paaID)])


            # Display the STAs 3D spheres
            self.makeVisible(self.stasVisObj)
        self.forceRender()

    @on_trait_change('guiApThreeDModeScale,guiStaThreeDModeScale')
    def updateApsStasModelScale(self, obj, name, old, new):
        """Update APs or STAs 3D model scale
        """
        if name == 'guiApThreeDModeScale':
            # Update APs scale
            if self.apTextureMode == "jpg" or self.apTextureMode == "none":
                # AP object is made of a single mesh
                for deviceObject in self.apModelVisObj:
                    deviceObject.actor.actor.scale = (
                        self.guiApThreeDModeScale, self.guiApThreeDModeScale, self.guiApThreeDModeScale)
            else:
                # Each AP is made of several textured objects - Change the size for all of them
                for deviceObject in self.apModelVisObj:
                    for individualObject in deviceObject:
                        individualObject.scale = (
                            self.guiApThreeDModeScale, self.guiApThreeDModeScale, self.guiApThreeDModeScale)
        else:
            # Update STAs scale
            if self.staTextureMode == "jpg" or self.staTextureMode == "none":
                # STA object is made of a single mesh
                for deviceObject in self.staModelVisObj:
                    deviceObject.actor.actor.scale = (
                        self.guiStaThreeDModeScale, self.guiStaThreeDModeScale, self.guiStaThreeDModeScale)
            else:
                # Each STA is made of several textured objects - Change the size for all of them
                for deviceObject in self.staModelVisObj:
                    for individualObject in deviceObject:
                        individualObject.scale = (
                            self.guiStaThreeDModeScale, self.guiStaThreeDModeScale, self.guiStaThreeDModeScale)
        self.forceRender()

    @on_trait_change('guiApAntennaPatternMagnifier,guiStaAntennaPatternMagnifier')
    def updateApsStasAntennaPatternSize(self, obj, name, old, new):
        """Change the size of the APs or STAs Antenna Patterns
        """
        if name == 'guiApAntennaPatternMagnifier':
            # Change APs Antenna Pattern size
            for paaId in range(codebooks.getNbPaaPerAp()):
                for sectorId in range(codebooks.getNbSectorPerApAntenna()):
                    for role in range(2):
                        # Update the antenna pattern size
                        tupleIdentifier = globals.NodeType.AP.value, paaId, sectorId, role
                        self.txSectorsAntennaPatternVisObj[tupleIdentifier].actor.actor.scale = (
                            self.guiApAntennaPatternMagnifier, self.guiApAntennaPatternMagnifier,
                            self.guiApAntennaPatternMagnifier)
                self.quasiOmniAntennaPatternVisObj[globals.NodeType.AP, paaId].actor.actor.scale = (
                    self.guiApAntennaPatternMagnifier, self.guiApAntennaPatternMagnifier,
                    self.guiApAntennaPatternMagnifier)
        else:
            # Change STAs Antenna Pattern size
            for paaId in range(codebooks.getNbPaaPerSta()):
                for sectorId in range(codebooks.getNbSectorPerStaAntenna()):
                    for role in range(2):
                        # Update the antenna pattern size
                        tupleIdentifier = globals.NodeType.STA.value, paaId, sectorId, role
                        self.txSectorsAntennaPatternVisObj[tupleIdentifier].actor.actor.scale = (
                            self.guiStaAntennaPatternMagnifier, self.guiStaAntennaPatternMagnifier,
                            self.guiStaAntennaPatternMagnifier)
                self.quasiOmniAntennaPatternVisObj[globals.NodeType.STA, paaId].actor.actor.scale = (
                    self.guiStaAntennaPatternMagnifier, self.guiStaAntennaPatternMagnifier,
                    self.guiStaAntennaPatternMagnifier)
        self.forceRender()

    @on_trait_change('guiApAntennaPatternOpacity,guiStaAntennaPatternOpacity')
    def updateApAntennaPatternOpacity(self, obj, name, old, new):
        """Change the opacity of the APs or STAs Antenna Patterns
        """
        if name == "guiApAntennaPatternOpacity":
            # Change APs antenna pattern opacity
            for paaId in range(codebooks.getNbPaaPerAp()):
                for sectorId in range(codebooks.getNbSectorPerApAntenna()):
                    for role in range(2):
                        # Update the antenna pattern Opacity
                        tupleIdentifier = globals.NodeType.AP.value, paaId, sectorId, role
                        # Update the antenna pattern size
                        self.txSectorsAntennaPatternVisObj[
                            tupleIdentifier].actor.property.opacity = self.guiApAntennaPatternOpacity
        else:
            # Change STAs antenna pattern opacity
            for paaId in range(codebooks.getNbPaaPerSta()):
                for sectorId in range(codebooks.getNbSectorPerStaAntenna()):
                    for role in range(2):
                        # Update the antenna pattern Opacity
                        tupleIdentifier = globals.NodeType.STA.value, paaId, sectorId, role
                        # Update the antenna pattern opacity
                        self.txSectorsAntennaPatternVisObj[
                            tupleIdentifier].actor.property.opacity = self.guiStaAntennaPatternOpacity
        self.forceRender()

    @on_trait_change('guiApPaaMagnifier,guiStaPaaMagnifier')
    def updateApsStasPaaSize(self, obj, name, old, new):
        """Change the PAA elements size for AP or STA (depending on the action)
        """
        if name == "guiApPaaMagnifier":
            for apID in range(qdScenario.nbAps):
                for paaID in range(codebooks.getNbPaaPerAp()):
                    self.paasElementsVisObj[(apID, paaID)].actor.actor.scale = (
                        self.guiApPaaMagnifier, self.guiApPaaMagnifier, self.guiApPaaMagnifier)
        else:
            for staID in range(qdScenario.nbAps, qdScenario.nbNodes):
                for paaID in range(codebooks.getNbPaaPerSta()):
                    self.paasElementsVisObj[(staID, paaID)].actor.actor.scale = (
                        self.guiStaPaaMagnifier, self.guiStaPaaMagnifier, self.guiStaPaaMagnifier)
        self.forceRender()

    @on_trait_change('guiMpcReflection')
    def updateMpcsGuiVisualization(self):
        """Update the GUI Values depending on the MPC reflection order selected
        """
        self.guiMpcColor = (self.mpcReflectionsProperties[self.guiMpcReflection].color[0] * 255,
                            self.mpcReflectionsProperties[self.guiMpcReflection].color[1] * 255,
                            self.mpcReflectionsProperties[self.guiMpcReflection].color[2] * 255)
        self.guiMpcsMagnifier = self.mpcReflectionsProperties[self.guiMpcReflection].width
        self.guiMpcsHidden = self.mpcReflectionsProperties[self.guiMpcReflection].hidden

    @on_trait_change('guiMpcsHidden')
    def updateMpcsVisibility(self):
        """Hide the MPCs for the selected reflection order
        """
        self.mpcReflectionsProperties[self.guiMpcReflection].hidden = self.guiMpcsHidden
        idTx = int(self.guiTxNodeSelected)
        idRx = int(self.guiRxNodeSelected)
        if idTx < idRx:
            self.mpcEdgesDicVisObj[idTx, idRx][self.guiMpcReflection].actor.actor.visibility = not (self.guiMpcsHidden)
        else:
            self.mpcEdgesDicVisObj[idRx, idTx][self.guiMpcReflection].actor.actor.visibility = not (self.guiMpcsHidden)

        self.forceRender()

    @on_trait_change('guiMpcColor')
    def updateMpcsColor(self):
        """Change the MPCs color for the selected reflection order
        """
        colorPicked = self.guiMpcColor.getRgb()
        colorConverted = (colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)
        self.mpcReflectionsProperties[self.guiMpcReflection].color = colorConverted
        idTx = int(self.guiTxNodeSelected)
        idRx = int(self.guiRxNodeSelected)
        if idTx < idRx:
            self.mpcEdgesDicVisObj[idTx, idRx][self.guiMpcReflection].actor.property.color = colorConverted
        else:
            self.mpcEdgesDicVisObj[idRx, idTx][self.guiMpcReflection].actor.property.color = colorConverted
        self.forceRender()

    @on_trait_change('guiMpcsMagnifier')
    def updateMpcsWidth(self):
        """Change the MPC width for the selected reflection order
        """
        self.mpcReflectionsProperties[self.guiMpcReflection].width = self.guiMpcsMagnifier
        idTx = int(self.guiTxNodeSelected)
        idRx = int(self.guiRxNodeSelected)
        if idTx < idRx:
            self.mpcTubesDicVisObj[idTx, idRx][self.guiMpcReflection].filter.radius = self.guiMpcsMagnifier
        else:
            self.mpcTubesDicVisObj[idRx, idTx][self.guiMpcReflection].filter.radius = self.guiMpcsMagnifier
        self.forceRender()

    @on_trait_change('guiButtonSaveTweak')
    def saveComponentsConfig(self):
        """Save the parameters configured by the user (MPCs, size of Antenna Patterns, etc.)
        """
        saveFile = os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder, globals.componentsConfigFile)
        pickleObject = ComponentsVisualizationConfig(self.mpcReflectionsProperties, self.guiStasNodesSize,
                                                     self.guiApsNodesSize, self.guiStaThreeDModeScale,
                                                     self.guiApThreeDModeScale, self.guiApAntennaPatternMagnifier,
                                                     self.guiApAntennaPatternOpacity,
                                                     self.guiStaAntennaPatternMagnifier,
                                                     self.guiStaAntennaPatternOpacity, self.guiApPaaMagnifier,
                                                     self.guiStaPaaMagnifier)
        pickle.dump(pickleObject, open(saveFile, "wb"), protocol=pickle.HIGHEST_PROTOCOL)
        print("Components Config Saved Successfully to:", saveFile)

    @on_trait_change('guiNodesScene')
    def updateNodesScene(self):
        """Update the scene where to display the APs and STAs
        """
        if self.guiNodesScene == "View1":
            scene = self.view1
        else:
            scene = self.view2
        self.apsVisObj.scene = scene
        self.stasVisObj.scene = scene

        # Update the 3D model as well
        # for apId in range(qdScenario.nbAps):
        #     if self.apTextureMode == "none" or self.apTextureMode == "jpg":
        #         self.apModelVisObj[apId].scene = scene
        #     else:
        #         # Each AP object is made of individual textures objects - Iterate through all of them
        #         for individualObject in self.apModelVisObj[apId]:
        #             individualObject.scene = scene

        # Display object associated to STA
        # for staId in range(qdScenario.nbAps, qdScenario.nbNodes):
        #     if self.staTextureMode == "none" or self.staTextureMode == "jpg":
        #         self.staModelVisObj[staId - qdScenario.nbAps].scene = scene
        #     else:
        #         # Each STA object is made of individual textures objects - Iterate through all of them
        #         for individualObject in self.staModelVisObj[staId - qdScenario.nbAps]:
        #             individualObject.scene = scene
        self.forceRender()

    @on_trait_change('guiNodesLabelsScene')
    def updateNodesLabelsScene(self):
        """Update the scene where to display the APs and STAs
        """
        if self.guiNodesLabelsScene == "View1":
            scene = self.view1
        else:
            scene = self.view2
        self.apsLabels.scene = scene
        self.stasLabels.scene = scene
        self.forceRender()

    @on_trait_change('guiApsLabels')
    def updateApsLabels(self):
        """Update the APs Labels
        """
        self.apsLabels.mapper.label_format = (self.guiApsLabels + " %d")
        self.forceRender()

    @on_trait_change('guiApsLabelsColor')
    def updateApsLabelsColors(self):
        """Update the color of the APs labels
        """
        colorPicked = self.guiApsLabelsColor.getRgb()
        colorConverted = (colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)
        self.apsLabels.property.color = colorConverted
        self.forceRender()

    @on_trait_change('guiStasLabels')
    def updateStasLabels(self):
        """Update the scene where to display the APs and STAs
        """
        self.stasLabels.mapper.label_format = (self.guiStasLabels + " %d")
        self.forceRender()

    @on_trait_change('guiStasLabelsColor')
    def updateStasLabelsColors(self):
        """Update the color of the STAs labels
        """
        colorPicked = self.guiStasLabelsColor.getRgb()
        colorConverted = (colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)
        self.stasLabels.property.color = colorConverted
        self.forceRender()

    @on_trait_change('guiPaasScene')
    def updatePaasScene(self):
        """Update the scene where to display the PAAs of APs and STAs
        """
        if self.guiPaasScene == "View1":
            scene = self.view1
        else:
            scene = self.view2
        for apID in range(qdScenario.nbAps):
            for paaID in range(codebooks.getNbPaaPerAp()):
                self.paasElementsVisObj[(apID, paaID)].scene = scene

        for staID in range(qdScenario.nbAps, qdScenario.nbNodes):
            for paaID in range(codebooks.getNbPaaPerSta()):
                self.paasElementsVisObj[(staID, paaID)].scene = scene
        self.forceRender()

    @on_trait_change('guiBeamformingPatternsScene')
    def updateAntennaPatternsScene(self):
        """Update the scene where to display the Antenna Patterns
        """
        if qdScenario.qdInterpreterConfig.slsEnabled:
            if self.guiBeamformingPatternsScene == "View1":
                scene = self.view1
            else:
                scene = self.view2
            for paaId in range(codebooks.getNbPaaPerAp()):
                for sectorId in range(codebooks.getNbSectorPerApAntenna()):
                    for role in range(2):
                        self.txSectorsAntennaPatternVisObj[
                            globals.NodeType.AP.value, paaId, sectorId, role].scene = scene

            for paaId in range(codebooks.getNbPaaPerSta()):
                for sectorId in range(codebooks.getNbSectorPerStaAntenna()):
                    for role in range(2):
                        self.txSectorsAntennaPatternVisObj[
                            globals.NodeType.STA.value, paaId, sectorId, role].scene = scene
            self.forceRender()

    @on_trait_change('guiSlsMode')
    def changeSlsMode(self):
        """Update the SLS results based on the mode selected
        """
        self.updateNewSelection('', 'guiSlsMode', '', '')
        # Update the BFT ID in the GUI
        self.guiMaxSlsBftId = getNumberOfBft(int(self.guiTxNodeSelected),int(self.guiRxNodeSelected), qdScenario) - 1


        # Update the visibility of STA association
        if self.guiSlsMode == "ns-3":
            # We cannot know to which AP is associated the STA when using ns-3 results
            self.makeInvisible(self.stasAssociationVisObj)
        else:
            # Oracle is used
            if self.guiDisplayStaAssociation:
                # The user selected to display the STA association
                if (qdScenario.qdInterpreterConfig.dataMode == "preprocessed") or (
                        qdScenario.qdInterpreterConfig.dataMode == "online" and qdScenario.qdInterpreterConfig.plotData):
                    self.makeVisible(self.stasAssociationVisObj)

    @on_trait_change('guiDisplayStaAssociation')
    def showStaAssociation(self):
        """Display or hide the STA association information
        """
        if self.guiSlsMode == "Oracle":
            if (qdScenario.qdInterpreterConfig.dataMode == "preprocessed") or (qdScenario.qdInterpreterConfig.dataMode == "online" and qdScenario.qdInterpreterConfig.plotData):
                if self.guiDisplayStaAssociation:
                    self.makeVisible(self.stasAssociationVisObj)
                    self.displayStasAssociation(int(self.traceIndex))
                else:
                    self.makeInvisible(self.stasAssociationVisObj)
            else:
                self.makeInvisible(self.stasAssociationVisObj)
                globals.logger.warning(
                    "STA association can only be displayed if dataMode is set to preprocessed or set to online and --curves option is used")
        else:
            if self.guiDisplayStaAssociation:
                globals.logger.warning("STA association data not available when ns-3 mode is selected")
            self.makeInvisible(self.stasAssociationVisObj)
        self.forceRender()

    @on_trait_change('guiIterateSlsBftId')
    def iterateSlsBft(self):
        if not qdScenario.nsSlsResults.empty:
            traceBft = getNsSlsResultsBftId(int(self.guiTxNodeSelected), int(self.guiRxNodeSelected),
                                            self.guiIterateSlsBftId, qdScenario)
            if traceBft == -1:
                # No results available
                return
            self.traceIndex = traceBft
            self.forceRender()

    # Sensing Tab
    @on_trait_change('guiSensingTargetColor')
    def updateTargetColor(self):
        """Change Selected Target Color (Target, joints + MPCs)
        """
        if self.guiTargetSelected != "All":
            colorPickedRgb = self.guiSensingTargetColor.getRgb()
            # We udpate the selected target RGB color in the list holding the target color
            self.colorTargetsRgb[int(self.guiTargetSelected)] = [
                colorPickedRgb[0],
                colorPickedRgb[1],
                colorPickedRgb[2],
                255]


            # Selected target color change
            # We need to convert the color from RGB to float (0,1) colors to assign the color to the selected target
            colorPickedFloat = (colorPickedRgb[0] / 255, colorPickedRgb[1] / 255, colorPickedRgb[2] / 255)
            # Assign the new selected color to the selected target
            self.targetJointsVisObj[int(self.guiTargetSelected)].actor.property.color = colorPickedFloat
            self.targetJointsConnectionsVisObj[int(self.guiTargetSelected)].actor.property.color = colorPickedFloat

            # MPCs individual target
            for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                self.mpcNodesTargetsReflections[int(self.guiTxNodeSelected)][int(self.guiTargetSelected)][
                    reflectionOrder].actor.property.color = colorPickedFloat
                self.mpcNodesTargetsReflections[int(self.guiRxNodeSelected)][int(self.guiTargetSelected)][
                    reflectionOrder].actor.property.color = colorPickedFloat

            # Change the color of the selected target in ALL targets representation  (stored in the last element)
            xTargetCoordinates, yTargetCoordinates, zTargetCoordinates = qdScenario.targetPosition[-1][0, ::, ::]
            # To apply the color to the selected target, we are going to use scalar values and fill it with the new colorTargetRgb
            # We need to color all the joints of each target according to the color sets to each individual target
            s = np.arange(xTargetCoordinates.shape[0])
            lut = np.zeros(
                (xTargetCoordinates.shape[0], 4))  # Colormap containing only the color assigned to each target
            nbJointsAllTargets = 0
            for targetId in range(qdScenario.nbTargets):
                # Construct the colormap with the colors assigned to each individual target
                nbJointsTarget = qdScenario.targetPosition[targetId][0, ::, ::][0].shape[0]
                lut[nbJointsAllTargets:nbJointsAllTargets + nbJointsTarget] = np.full((nbJointsTarget, 4),
                                                                                      self.colorTargetsRgb[targetId])
                nbJointsAllTargets += nbJointsTarget
            self.targetJointsVisObj[-1].mlab_source.trait_set(scalars=s)
            self.targetJointsVisObj[-1].module_manager.scalar_lut_manager.lut.number_of_colors = len(s)
            self.targetJointsVisObj[-1].module_manager.scalar_lut_manager.lut.table = lut
            self.targetJointsConnectionsVisObj[-1].module_manager.scalar_lut_manager.lut.table = lut

            # Update the selected Target MPCs with the newly selected colors for ALL targets representation
            for nodeId in range(qdScenario.nbNodes):
                for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                    xMpcCoordinate, yMpcCoordinate, zMpcCoordinate, connections = qdRealization.getTargetAllMpcCoordinates(
                        nodeId, reflectionOrder, self.traceIndex)
                    s = np.arange(xMpcCoordinate.shape[0])
                    lut = np.zeros((xMpcCoordinate.shape[0], 4))
                    totalMPCs = 0
                    for targetId in range(qdScenario.nbTargets):
                        nbMPCsCurrentTarget = \
                            qdRealization.sizeTrcsNdsRlfsTgtsJts[self.traceIndex][nodeId][reflectionOrder][
                                targetId]
                        # The MPCs boundaries to color are given by the number of MPCs for the current target and the total number of MPCs so far
                        lut[totalMPCs:totalMPCs + nbMPCsCurrentTarget] = np.full((nbMPCsCurrentTarget, 4),
                                                                                 self.colorTargetsRgb[targetId])
                        totalMPCs += nbMPCsCurrentTarget

                    # Udpate color for MPCs from Tx to Target
                    self.mpcNodesAllTargetsReflections[int(self.guiTxNodeSelected)][
                        reflectionOrder].module_manager.scalar_lut_manager.lut.number_of_colors = len(s)
                    self.mpcNodesAllTargetsReflections[int(self.guiTxNodeSelected)][
                        reflectionOrder].module_manager.scalar_lut_manager.lut.table = lut
                    # Udpate color for MPCs from Rx to Target
                    self.mpcNodesAllTargetsReflections[int(self.guiRxNodeSelected)][
                        reflectionOrder].module_manager.scalar_lut_manager.lut.number_of_colors = len(s)
                    self.mpcNodesAllTargetsReflections[int(self.guiRxNodeSelected)][
                        reflectionOrder].module_manager.scalar_lut_manager.lut.table = lut

            self.forceRender()

    @on_trait_change('guiDisplayTxRxMpcs')
    def updateTxRxCommunicationMPCsVisibility(self):
        """Update the visibility of the MPCs between the Tx and Rx communication nodes
        """
        txNode = int(self.guiTxNodeSelected)
        rxNode = int(self.guiRxNodeSelected)

        for reflectionOrder in range(0, maxReflectionOrder + 1):
            self.mpcEdgesDicVisObj[txNode, rxNode][reflectionOrder].actor.actor.visibility = self.guiDisplayTxRxMpcs
            self.mpcReflectionsProperties[reflectionOrder].hidden = not (self.guiDisplayTxRxMpcs)
        self.forceRender()

    @on_trait_change('guiDisplayTargetMpcs')
    def updateTargetMPCsVisibility(self):
        """Update the visibility of the MPCs between the Tx, Target, and Rx
        """
        if self.guiTargetSelected == "All":
            targetSelected = -1
        else:
            targetSelected = int(self.guiTargetSelected)

        if (self.guiDisplayTargetMpcs):
            # Make Visible the MPCs from the Tx Node and Rx Node to the target
            for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                if self.guiTargetSelected == "All":
                    self.makeVisible(self.mpcNodesAllTargetsReflections[int(self.guiTxNodeSelected)][reflectionOrder])
                    self.makeVisible(self.mpcNodesAllTargetsReflections[int(self.guiRxNodeSelected)][reflectionOrder])
                else:
                    self.makeVisible(
                        self.mpcNodesTargetsReflections[int(self.guiTxNodeSelected)][targetSelected][
                            reflectionOrder])
                    self.makeVisible(
                        self.mpcNodesTargetsReflections[int(self.guiRxNodeSelected)][targetSelected][
                            reflectionOrder])

            self.targetsVisualizationProperties.mpcsNodesTargetHidden = False
        else:
            # Make Invisible the MPCs from the Tx Node and Rx Node to the target
            for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                if self.guiTargetSelected == "All":
                    self.makeInvisible(self.mpcNodesAllTargetsReflections[int(self.guiTxNodeSelected)][reflectionOrder])
                    self.makeInvisible(self.mpcNodesAllTargetsReflections[int(self.guiRxNodeSelected)][reflectionOrder])
                else:
                    self.makeInvisible(
                        self.mpcNodesTargetsReflections[int(self.guiTxNodeSelected)][targetSelected][
                            reflectionOrder])
                    self.makeInvisible(
                        self.mpcNodesTargetsReflections[int(self.guiRxNodeSelected)][targetSelected][
                            reflectionOrder])
            self.targetsVisualizationProperties.mpcsNodesTargetHidden = True
        self.forceRender()

    @on_trait_change('guiButtonSaveSensingConfig')
    def saveSensingConfig(self):
        """Save the parameters configured for the sensing mode
        """
        saveFile = os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder, globals.sensingConfigFile)
        pickleObject = self.colorTargetsRgb
        pickle.dump(pickleObject, open(saveFile, "wb"), protocol=pickle.HIGHEST_PROTOCOL)
        print("Sensing Config Saved Successfully to:", saveFile)

    @on_trait_change('guiMimoStream')
    def selectMimoStream(self):
        if self.guiDisplayMimo:
            if qdScenario.qdInterpreterConfig.mimo != "beamTracking":
                # BeamTracking don't use the notion of PAA yet
                self.guiMimoTxStreamIdentifier = self.bestreamPaaIdCombination[self.guiMimoStream][0]
                self.guiMimoRxStreamIdentifier = self.bestreamPaaIdCombination[self.guiMimoStream][1]

            if self.guiDisplayMimo:
                self.guiMimoTxSector = self.bestSectorsCombination[0][self.guiMimoStream]
                self.guiMimoRxSector = self.bestSectorsCombination[1][self.guiMimoStream]


                # Update the GUI
                self.guiMimoStreamSize = self.mimoStreamPatternSize[self.guiMimoStream]
                self.guiMimoStreamColor = (self.mimoStreamProperties[self.guiMimoStream].color[0] * 255,
                                             self.mimoStreamProperties[self.guiMimoStream].color[1] * 255,
                                             self.mimoStreamProperties[self.guiMimoStream].color[2] * 255)

                self.guiMimoStreamMpcSize = self.mimoStreamProperties[self.guiMimoStream].width
                self.guiMimoEdgesSize = self.mimoStreamEdgeSize[self.guiMimoStream]

    @on_trait_change('guiMimoStreamOpacity')
    def changeStreamOpacity(self):
        if self.mimoStreamPatterns:
            for pattern in self.mimoStreamPatterns[self.guiMimoStream]:
                pattern.actor.property.opacity = self.guiMimoStreamOpacity

    @on_trait_change('guiMimoStreamSize')
    def changeMimoStreamSize(self):
        if self.mimoStreamPatterns:
            if qdScenario.qdInterpreterConfig.mimo != "beamTracking":
                # SU or MU MIMO
                for pattern in self.mimoStreamPatterns[self.guiMimoStream]:
                    pattern.actor.actor.scale = (
                        self.guiMimoStreamSize, self.guiMimoStreamSize,
                        self.guiMimoStreamSize)
            else:
                # Beamtracking MIMO
                if ("Analog", self.guiMimoStream) in self.mimoStreamPatterns:
                    for pattern in self.mimoStreamPatterns["Analog", self.guiMimoStream]:
                        pattern.actor.actor.scale = (
                            self.guiMimoStreamSize, self.guiMimoStreamSize,
                            self.guiMimoStreamSize)
                if ("Hybrid", self.guiMimoStream) in self.mimoStreamPatterns:
                    for pattern in self.mimoStreamPatterns["Hybrid", self.guiMimoStream]:
                        pattern.actor.actor.scale = (
                            self.guiMimoStreamSize, self.guiMimoStreamSize,
                            self.guiMimoStreamSize)
            # Keep the new selected stream size
            self.mimoStreamPatternSize[self.guiMimoStream] = self.guiMimoStreamSize

    @on_trait_change('guiMimoStreamColor')
    def updateMimoStreamColor(self):
        # Change Stream Color
        if self.mimoStreamPatterns:
            colorPicked = self.guiMimoStreamColor.getRgb()
            colorConverted = (colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)
            if qdScenario.qdInterpreterConfig.mimo != "beamTracking":
                for pattern in self.mimoStreamPatterns[self.guiMimoStream]:
                    # Update edge color as we want MPCs to be the same color as the stream
                    pattern.actor.property.edge_color = colorConverted
                    pattern.actor.property.color = (
                        colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)
            else:
                if ("Analog", self.guiMimoStream) in self.mimoStreamPatterns:
                    for pattern in self.mimoStreamPatterns["Analog", self.guiMimoStream]:
                        pattern.actor.property.edge_color = colorConverted

                        pattern.actor.property.color = (
                            colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)
                if ("Hybrid", self.guiMimoStream) in self.mimoStreamPatterns:
                    for pattern in self.mimoStreamPatterns["Hybrid", self.guiMimoStream]:
                        pattern.actor.property.edge_color = colorConverted
                        pattern.actor.property.color = (
                            colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)


            # Update MPC color as we want MPCs to be the same color as the stream
            for reflectionOrder in range(0, maxReflectionOrder + 1):
                self.mimoTubeMesh[self.guiMimoStream][reflectionOrder].actor.property.color = colorConverted

            # Keep the new selected color
            self.mimoStreamProperties[self.guiMimoStream].color = colorConverted

            self.forceRender()

    @on_trait_change('guiMimoEdgesSize')
    def updateMimoEdgesStreamSize(self):
        if self.mimoStreamPatterns:
            if qdScenario.qdInterpreterConfig.mimo != "beamTracking":
                for pattern in self.mimoStreamPatterns[self.guiMimoStream]:
                    pattern.actor.property.line_width = self.guiMimoEdgesSize
            else:
                # BeamTracking
                if ("Analog", self.guiMimoStream) in  self.mimoStreamPatterns:
                    for pattern in  self.mimoStreamPatterns["Analog", self.guiMimoStream]:
                        pattern.actor.property.line_width = self.guiMimoEdgesSize
                if ("Hybrid", self.guiMimoStream) in  self.mimoStreamPatterns:
                    for pattern in  self.mimoStreamPatterns["Hybrid", self.guiMimoStream]:
                        pattern.actor.property.line_width = self.guiMimoEdgesSize
            # Keep the new selected edge size
            self.mimoStreamEdgeSize[self.guiMimoStream] = self.guiMimoEdgesSize

    @on_trait_change('guiMimoStreamMpcSize')
    def updateMimoMpcsStreamSize(self):
        if self.mimoStreamPatterns:
            self.mimoStreamProperties[self.guiMimoStream].width = self.guiMimoStreamMpcSize
            for reflectionOrder in range(0, maxReflectionOrder + 1):
                self.mimoTubeObjects[self.guiMimoStream][reflectionOrder].filter.radius = self.guiMimoStreamMpcSize

    # Environment Tweak Tab
    @on_trait_change('guiEdgeVisibility')
    def updateViewEdgeVisibility(self):
        """Update the view edge visibility
        """
        if currentPicker == pickerView1:
            viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            if self.guiEdgeVisibility != self.scenesProperties[self.view1.mayavi_scene].edgeVisibility:
                # Update edge visibility for view1 internal representation
                self.scenesProperties[self.view1.mayavi_scene].edgeVisibility = self.guiEdgeVisibility
        else:
            viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            if self.guiTextureMaterial != self.scenesProperties[self.view2.mayavi_scene].edgeVisibility:
                # Update edge visibility for view2 internal representation
                self.scenesProperties[self.view2.mayavi_scene].edgeVisibility = self.guiEdgeVisibility

        for i in range(len(viewObjects)):
            # Apply to each object the edge visibility selected in the GUI
            viewObjects[
                i].mesh.actor.property.edge_visibility = self.guiEdgeVisibility
        self.forceRender()

    @on_trait_change('guiTextureMaterial')
    def switchViewTextureMaterial(self):
        """Update the view either to display material or texture
        """
        if currentPicker == pickerView1:
            viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            if self.guiTextureMaterial != self.scenesProperties[self.view1.mayavi_scene].representation:
                self.scenesProperties[self.view1.mayavi_scene].representation = self.guiTextureMaterial
        else:
            viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            if self.guiTextureMaterial != self.scenesProperties[self.view2.mayavi_scene].representation:
                self.scenesProperties[self.view2.mayavi_scene].representation = self.guiTextureMaterial

        if self.guiTextureMaterial == 'Texture':
            # User chooses the textured view
            for i in range(len(viewObjects)):
                # Iterate through all the objects of the view to texture them
                self.assignMaterialTexture(viewObjects[i])
        else:
            # User choose the Material view
            for i in range(len(viewObjects)):
                viewObjects[i].mesh.actor.enable_texture = False
                self.assignMaterialColor(viewObjects[i])

        self.forceRender()

    @on_trait_change('guiHideObject')
    def updateObjectVisibility(self):
        """Update the selected object visibility status
        """
        if currentSelectedObject != -1:
            if currentPicker == pickerView1:
                viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            else:
                viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            viewObjects[currentSelectedObject].mesh.actor.actor.visibility = not (self.guiHideObject)
            viewObjects[currentSelectedObject].hidden = self.guiHideObject
            viewObjects[currentSelectedObject].mesh.actor.mapper.scalar_visibility = False

            self.forceRender()

    @on_trait_change('guiFrontFaceCulling')
    def updateObjectFrontFaceCulling(self):
        """Update the selected object front face culling status
        """
        if currentSelectedObject != -1:
            if currentPicker == pickerView1:
                viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            else:
                viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            # Update if the front face of the object must be hidden depending on the viewing angle of the camera
            viewObjects[
                currentSelectedObject].mesh.actor.actor.property.frontface_culling = self.guiFrontFaceCulling
            viewObjects[currentSelectedObject].frontFaceCulling = self.guiFrontFaceCulling
            viewObjects[currentSelectedObject].mesh.actor.mapper.scalar_visibility = False


            viewObjects[
                currentSelectedObject].mesh.actor.actor.property.frontface_culling = self.guiFrontFaceCulling
            viewObjects[currentSelectedObject].frontFaceCulling = self.guiFrontFaceCulling
            viewObjects[currentSelectedObject].mesh.actor.mapper.scalar_visibility = False
            self.forceRender()

    @on_trait_change('guiBackFaceCulling')
    def updateObjectBackFaceCulling(self):
        """Update the selected object back face culling status
        """
        if currentSelectedObject != -1:
            if currentPicker == pickerView1:
                viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            else:
                viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            # Update if the back face of the object must be hidden depending on the viewing angle of the camera
            viewObjects[
                currentSelectedObject].mesh.actor.actor.property.backface_culling = self.guiBackFaceCulling
            viewObjects[currentSelectedObject].backFaceCulling = self.guiBackFaceCulling
            viewObjects[currentSelectedObject].mesh.actor.mapper.scalar_visibility = False


            viewObjects[
                currentSelectedObject].mesh.actor.actor.property.backface_culling = self.guiBackFaceCulling
            viewObjects[currentSelectedObject].backFaceCulling = self.guiBackFaceCulling
            viewObjects[currentSelectedObject].mesh.actor.mapper.scalar_visibility = False
            self.forceRender()

    @on_trait_change('guiObjectOpacity')
    def updateObjectOpacity(self):
        """Update the object opacity
        """
        if currentSelectedObject != -1:
            if currentPicker == pickerView1:
                viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            else:
                viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            viewObjects[currentSelectedObject].mesh.actor.property.opacity = self.guiObjectOpacity
            viewObjects[currentSelectedObject].opacity = self.guiObjectOpacity
            viewObjects[currentSelectedObject].mesh.actor.mapper.scalar_visibility = False

            self.forceRender()

    @on_trait_change('guiObjectColor')
    def applyCustomColor(self):
        """Update the selected object color with the color selected
        """
        if currentSelectedObject != -1:
            if currentPicker == pickerView1:
                viewObjects = self.environmentObjects[self.view1.mayavi_scene]
            else:
                viewObjects = self.environmentObjects[self.view2.mayavi_scene]
            colorPicked = self.guiObjectColor.getRgb()
            viewObjects[currentSelectedObject].mesh.actor.property.color = (
                colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)
            viewObjects[currentSelectedObject].colorChanged = True
            viewObjects[currentSelectedObject].customColor = (
                colorPicked[0] / 255, colorPicked[1] / 255, colorPicked[2] / 255)

            self.forceRender()

    @on_trait_change('guiButtonSaveEnvironment')
    def saveVisualizationConfig(self):
        """Save the parameters configured by the user for the visualization (textures, objects visibility, etc.)
        """

        # Save View1 configuration
        saveFileView1 = os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder, globals.view1ConfigFile)

        pickleView1 = SceneVisualizerConfig(self.scenesProperties[self.view1.mayavi_scene],
                                            self.environmentObjects[self.view1.mayavi_scene])
        pickle.dump(pickleView1,
                    open(saveFileView1, "wb"),
                    protocol=pickle.HIGHEST_PROTOCOL)

        print("Visualization Config for View1 Saved Successfully to:", saveFileView1)
        # Save View2 configuration
        saveFileView2 = os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder, globals.view2ConfigFile)
        pickleView2 = SceneVisualizerConfig(self.scenesProperties[self.view2.mayavi_scene],
                                            self.environmentObjects[self.view2.mayavi_scene])
        pickle.dump(pickleView2,
                    open(saveFileView2, "wb"),
                    protocol=pickle.HIGHEST_PROTOCOL)
        print("Visualization Config for View2 Saved Successfully to:", saveFileView2)


    # Codebook Tab
    @on_trait_change('guiIterateTxSectors,guiTxRefineAwvSelected')
    def txSelectedSectorAntennaPattern(self):
        """Display the selected sector guiIterateTxSectors antenna patterns for the transmitter
        """
        # Hide every other TX Antenna Pattern (role == 0)
        role = 0
        for paaId in range(codebooks.getNbPaaPerAp()):
            for sectorId in range(codebooks.getNbSectorPerApAntenna()):
                self.makeInvisible(self.txSectorsAntennaPatternVisObj[globals.NodeType.AP.value, paaId, sectorId, role])
        for paaId in range(codebooks.getNbPaaPerSta()):
            for sectorId in range(codebooks.getNbSectorPerStaAntenna()):
                self.makeInvisible(
                    self.txSectorsAntennaPatternVisObj[globals.NodeType.STA.value, paaId, sectorId, role])
        if self.refinedAwvTxPattern != 0:
            self.makeInvisible(self.refinedAwvTxPattern)
        if self.guiTxRefineAwvSelected == "None":
            # No Refine AWV configuration
            # Just display the selected Sectors antenna pattern on the transmitter
            role = 0
            self.displayTxss(int(self.guiTxNodeSelected), int(self.guiTxPaaSelected), int(self.guiIterateTxSectors),
                             self.traceIndex, role)
        else:
            # Custom AWV selected - Compute the radiation pattern corresponding to the refine AWV
            # Not activated because of the way the custom AWV are created won't work for any codebook
            # TODO fix it if needed
            txNode = int(self.guiTxNodeSelected)
            txSector = int(self.guiIterateTxSectors)
            rxNode = int(self.guiRxNodeSelected)
            refinedAwvId = int(self.guiTxRefineAwvSelected)
            azimuth, elevation = codebooks.getRefinedAwvAzimuthElevation(txSector, refinedAwvId,
                                                                         qdScenario.getNodeType(txNode))
            # Create the directivity pattern for the given azimuth and elevation
            xAntennaPattern, yAntennaPattern, zAntennaPattern, colorAntennaPattern = codebooks.getRefinedAwvRadiationPatternDic(
                azimuth, elevation, qdScenario.getNodeType(txNode))
            # Display the corresponding antenna pattern

            if self.refinedAwvTxPattern == 0:
                # If never created, create the corresponding pattern
                self.refinedAwvTxPattern = (
                    mlab.mesh(xAntennaPattern, yAntennaPattern, zAntennaPattern, vmin=np.amin(colorAntennaPattern),
                              vmax=np.amax(colorAntennaPattern), figure=self.view2.mayavi_scene, reset_zoom=False,
                              scalars=colorAntennaPattern, tube_radius=0.025, ))
                self.refinedAwvTxPattern.actor.actor.position = qdScenario.getNodePosition(int(self.traceIndex),
                                                                              int(self.guiTxNodeSelected))
                self.refinedAwvTxPattern.actor.actor.orientation = (
                    self.computePaaRotationAngles(int(self.guiTxNodeSelected), int(self.guiTxPaaSelected),
                                                  int(self.traceIndex)))
            else:
                # If already created, update the pattern
                self.refinedAwvTxPattern.mlab_source.set(x=xAntennaPattern, y=yAntennaPattern, z=zAntennaPattern,
                                            scalars=colorAntennaPattern, vmin=np.amin(colorAntennaPattern),
                                            vmax=np.amax(colorAntennaPattern))
                self.refinedAwvTxPattern.module_manager.scalar_lut_manager.data_range = [
                    np.amin(colorAntennaPattern), np.amax(colorAntennaPattern)]
                self.refinedAwvTxPattern.actor.actor.position = qdScenario.getNodePosition(int(self.traceIndex),
                                                                              int(self.guiTxNodeSelected))
                self.refinedAwvTxPattern.actor.actor.orientation = (
                    self.computePaaRotationAngles(int(self.guiTxNodeSelected), int(self.guiTxPaaSelected),
                                                  int(self.traceIndex)))
            self.makeVisible(self.refinedAwvTxPattern) # In case the visibility was turned-off
            self.forceRender()

    @on_trait_change('guiIterateRxSectors')
    def rxSelectedSectorAntennaPattern(self):
        """Display the selected sector guiIterateRxSectors antenna patterns for the receiver
        """
        # Hide every other RX Antenna Pattern (role == 1)
        role = 1
        for paaId in range(codebooks.getNbPaaPerAp()):
            for sectorId in range(codebooks.getNbSectorPerApAntenna()):
                self.makeInvisible(self.txSectorsAntennaPatternVisObj[globals.NodeType.AP.value, paaId, sectorId, role])
        for paaId in range(codebooks.getNbPaaPerSta()):
            for sectorId in range(codebooks.getNbSectorPerStaAntenna()):
                self.makeInvisible(
                    self.txSectorsAntennaPatternVisObj[globals.NodeType.STA.value, paaId, sectorId, role])
        # The receiver is by default displaying the Quasi-Omni, hide it
        # self.makeInvisible(quasiOmniAntennaPatternVisObj[
        #                   qdScenario.getNodeType(int(self.guiRxNodeSelected)), int(self.guiRxPaaSelected)])
        # Display the selected Sectors antenna pattern on the receiver
        self.displayTxss(int(self.guiRxNodeSelected), int(self.guiRxPaaSelected), int(self.guiIterateRxSectors),
                         self.traceIndex, role)

    # MIMO Tab
    @on_trait_change('guiButtonSaveMimoConfig')
    def saveMimoConfig(self):
        """Save the parameters configured by the user for MIMO (MPCs, size of Antenna Patterns, etc.)
        """
        saveFile = os.path.join(globals.scenarioPath, globals.qdRealizationInputFolder, globals.mimoConfigFile)
        pickleObject = MimoVisualizationConfig(self.mimoStreamProperties, self.mimoStreamPatternSize,
                                               self.guiMimoStreamColor, self.guiMimoStreamOpacity,
                                               self.mimoStreamEdgeSize)

        pickle.dump(pickleObject, open(saveFile, "wb"), protocol=pickle.HIGHEST_PROTOCOL)
        print("Components Config Saved Successfully to:", saveFile)

        ################ BEAM TRACKING ########################
        activateCprofile = False
        if activateCprofile == True:
            pr = cProfile.Profile()
            pr.enable()

    ######################################################################################################
    ###########                  GENERIC FUNCTIONS FOR THE VISUALIZATION                      ############
    ######################################################################################################
    def updateVisibility(self, anObject, visibility):
        """Change the visibility of an object in the visualization based on visibility

        Parameters
        ----------
        anObject : Visualization Object
            The object to change visibility
        visibility: Bool
            The visibility status of the object
        """
        anObject.actor.actor.visibility = visibility

    def makeVisible(self, anObject):
        """Make a visualization object Visible

        Parameters
        ----------
        anObject : Visualization Object
            The object to be visible
        """
        anObject.actor.actor.visibility = True

    def makeInvisible(self, anObject):
        """Make a visualization object Visible

        Parameters
        ----------
        anObject : Visualization Object
            The object to be invisible
        """
        anObject.actor.actor.visibility = False

    def animateOneStep(self):
        """Handle the animation in the visualization depending on the action in the visualizer (increase or decrease trace)
        """
        if self.guiVisualizerInteractions == "play":
            # If the current action selected is play, iterate by object.guiTraceIncrement

            if (self.traceIndex + self.guiTraceIncrement <= qdScenario.nbTraces - 1):
                self.traceIndex = self.traceIndex + self.guiTraceIncrement
                self.animateOneStep()
            # else:
                # Code if we want to loop forever when play is pressed
                # self.traceIndex = 0
                # self.animateOneStep()
        elif self.guiVisualizerInteractions == "back":
            # If the current action selected is back, decrement by object.guiTraceIncrement
            if (self.traceIndex - self.guiTraceIncrement >= 0):
                self.traceIndex = self.traceIndex - self.guiTraceIncrement
                self.animateOneStep()

    def forceRender(self):
        """Force the render (inspired by https://python.hotexamples.com/examples/pyface.api/GUI/set_busy/python-gui-set_busy-method-examples.html)
        """
        _gui = GUI()
        _gui.process_events()
        self.view1.render()
        self.view2.render()

    ######################################################################################################
    ###########                  GENERIC FUNCTIONS FOR THE COMPUTATIONS                       ############
    ######################################################################################################
    def computeSls(self, txNode, paaTx, rxNode, paaRx, traceIndex, guiTraceIncrement):
        """Perform the SLS phase

        Parameters
        ----------
        txNode : Int
            The Tx Node ID
        paaTx : Int
            The PAA Tx ID
        rxNode : Int
            The Rx Node ID
        paaRx : Int
            The PAA Rx ID
        traceIndex : Int
            The trace Index
        guiTraceIncrement : Int
            The trace increment (the step of the animation)
        """

        bestSectorTxRx = {}
        bestPowerTxRx = {}
        global dicBestAPPerSta
        dicBestAPPerSta = {}

        if not qdScenario.qdInterpreterConfig.plotData and not self.guiShowSlsBestAp:
            # Visualizer configures to not display the curves OR not to show which AP would be the best for the STA to associate with
            # We can just compute the SLS for the nodes selected (it depends from the mode: online or preprocessed)
            if qdScenario.qdInterpreterConfig.dataMode == "online":
                # Online Mode - Perform the computation of the SLS phase
                bestRxPowerTxRx, bestSnrTxRx, psdBestSectorTxRx, bestTxssSectorTxRx, rxPowerSectorListTxRx = qdPropagationLoss.performSls(
                    (txNode, rxNode, paaTx, paaRx, traceIndex), qdScenario.qdChannel, txParam,
                    globals.nbSubBands, qdScenario,
                    codebooks)
                # Keep the best sector and best power received for the computed TX/RX/PAATX/PAARX tuple
                bestSectorTxRx[(txNode, rxNode, paaTx, paaRx)] = bestTxssSectorTxRx
                bestPowerTxRx[(txNode, rxNode, paaTx, paaRx)] = bestRxPowerTxRx
            elif qdScenario.qdInterpreterConfig.dataMode == "preprocessed":
                # Preprocessed Mode - Read the preprocessed results
                index = qdScenario.dataIndex[(txNode, rxNode, paaTx, paaRx, traceIndex)]
                bestSectorTxRx[(txNode, rxNode, paaTx, paaRx)] = qdScenario.preprocessedSlsData.bestSectorIdList[
                    index]
                bestPowerTxRx[(txNode, rxNode, paaTx, paaRx)] = \
                    qdScenario.preprocessedSlsData.bestSectorRxPowerList[index]
        else:
            # Visualizer configures to display the curves
            # Compute for all Tx/Rx/PaaTx/PaaRx combinations
            for idTx in range(qdScenario.nbNodes):
                # Iterate all the potential Tx nodes
                for idRx in range(qdScenario.nbNodes):
                    # Iterate all the potential Rx nodes
                    if idTx != idRx:
                        for idPaaTx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(idTx))):
                            # Iterate over all the Tx PAAs
                            for idPaaRx in range(codebooks.getNbPaaNode(qdScenario.getNodeType(idRx))):
                                # Iterate all the potential PAA_RX
                                if qdScenario.qdInterpreterConfig.dataMode == 'online':
                                    bestRxPowerTxRx, bestSnrTxRx, psdBestSectorTxRx, bestTxssSectorTxRx, rxPowerSectorListTxRx = qdPropagationLoss.performSls(
                                        (idTx, idRx, idPaaTx, idPaaRx, traceIndex), qdScenario.qdChannel, txParam,
                                        globals.nbSubBands, qdScenario,
                                        codebooks)
                                    if qdScenario.qdInterpreterConfig.plotData:
                                        self.updateSlsPlots(idTx, idRx, idPaaTx, idPaaRx, bestRxPowerTxRx,
                                                            psdBestSectorTxRx,
                                                            rxPowerSectorListTxRx, traceIndex, guiTraceIncrement)

                                    if qdScenario.isNodeAp(idTx) and qdScenario.isNodeSta(idRx):
                                        # Check which AP a STA will be associated to based on the received power
                                        if idRx not in dicBestAPPerSta:
                                            # No computation has been done previously - Just store the values computed for the AP idTx for the STA IdRx
                                            dicBestAPPerSta[idRx] = (bestRxPowerTxRx, idTx, bestTxssSectorTxRx)
                                        else:
                                            if dicBestAPPerSta[idRx][0] < bestRxPowerTxRx:
                                                # Update the AP to which a STA will associate if the power received is greater
                                                dicBestAPPerSta[idRx] = (bestRxPowerTxRx, idTx, bestTxssSectorTxRx)

                                    # Keep the best sector for every TX/RX/PAATX/PAARX combination
                                    bestSectorTxRx[(idTx, idRx, idPaaTx, idPaaRx)] = bestTxssSectorTxRx
                                    bestPowerTxRx[(idTx, idRx, idPaaTx, idPaaRx)] = bestRxPowerTxRx
                                else:
                                    # Use the preprocessed data
                                    index = qdScenario.dataIndex[(idTx, idRx, idPaaTx, idPaaRx, traceIndex)]
                                    # Keep the best sector for every TX/RX/PAATX/PAARX combination
                                    bestSectorTxRx[(idTx, idRx, idPaaTx, idPaaRx)] = \
                                        qdScenario.preprocessedSlsData.bestSectorIdList[
                                            index]
                                    bestPowerTxRx[(idTx, idRx, idPaaTx, idPaaRx)] = \
                                        qdScenario.preprocessedSlsData.bestSectorRxPowerList[index]
                                    rxPowerSectorListTxRx = qdScenario.preprocessedSlsData.powerPerSectorList[index]
                                    if qdScenario.qdInterpreterConfig.plotData:
                                        self.updateSlsPlots(idTx, idRx, idPaaTx, idPaaRx,
                                                            qdScenario.preprocessedSlsData.bestSectorRxPowerList[index],
                                                            0,
                                                            rxPowerSectorListTxRx, traceIndex, guiTraceIncrement)

        return bestSectorTxRx, bestPowerTxRx

    def computePaaRotationAngles(self, nodeId, paaId, traceIndex):
        """Compute the resulting rotation angles of successive rotations

        Parameters
        ----------
        nodeId : Int
            The node ID
        paaId : Int
            The PAA ID
        traceIndex : int
            The trace index

        Returns
        ----------
        rotationToApply : X,Y,Z vector
            The rotations to apply
        """
        # Get the PAA initial orientation
        paaInitialOrientation = qdScenario.getPaaInitialOrientation(nodeId, paaId)
        rotationList = []  # Store the successive rotations
        # Apply both the device rotations and the paa initial orientation rotation and use quaternions to get the right angle to apply
        rotationList.append(qdScenario.getNodeRotation(traceIndex, nodeId))
        rotationList.append([paaInitialOrientation.x, paaInitialOrientation.y, paaInitialOrientation.z])
        rotationList = np.deg2rad(np.asarray(rotationList))
        # The quaternion implemented works now only for Z,X,Y transformation
        # Transform the original orientation angles X,Y,Z to Z,X,Y
        rotationList[:, [0, 1, 2]] = rotationList[:, [2, 0, 1]]
        rotationToApply = quaternionUtils.coordinateRotation(0, 0, np.asarray(rotationList), 'point')
        # Retransform the final rotation angles from Z, X, Y to X, Y, Z (as expected by Mayavi)
        rotationToApply[..., [0, 1, 2]] = rotationToApply[..., [1, 2, 0]]
        return rotationToApply

    ######################################################################################################
    ###########                            GUI CREATION                                       ############
    ######################################################################################################

    # GUI Creation and organization
    codebookGroup = HGroup(
        VGroup(
            Item(name='guiCodebookLabel', label='PAA Properties', width=100, style='readonly'),
            Item(name='guiIterateTxSectors', label='Iterate Over Tx Sector',
                 editor=RangeEditor(low_name='guiTxMinSectorId',
                                    high_name='guiTxMaxSectorId',
                                    mode='spinner',
                                    )),
            # Item(name='guiTxRefineAwvSelected', width=100, editor=CheckListEditor(name='guiTxRefineAwvChoices'),
            #      label='Refine AWV', emphasized=True),
            Item(name='guiIterateRxSectors', label='Iterate Over Rx Sector',
                 editor=RangeEditor(low_name='guiRxMinSectorId',
                                    high_name='guiRxMaxSectorId',
                                    mode='spinner',
                                    )),
            label='Sectors',
            show_border=True),
        label='Codebook',
        show_border=True)

    resultsGUI = VGroup(
        VGroup(
            HGroup(
                Item(name='guiTxssTxRxTxId', width=1, label='From:', style='readonly'),
                Item(name='guiTxssTxRxTxType', width=1, show_label=False, style='readonly'),
                Item(name='guiTxssTxRxRxId', width=1, label='To:', style='readonly'),
                Item(name='guiTxssTxRxRxType', width=1, show_label=False, style='readonly'),
            ),
            HGroup(
                Item(name='guiTxssTxRxBestSector', label='Sector:', style='readonly', format_str='%02d'),
                Item(name='guiTxssTxRxRcvPower', label='Rx Power:', style='readonly', format_str='%.2f'),
            ),
            label='TXSS TX-RX',
            show_border=True),
        VGroup(
            HGroup(
                Item(name='guiTxssRxTxTxId', width=1, label='From:', style='readonly'),
                Item(name='guiTxssRxTxTxType', width=1, show_label=False, style='readonly'),
                Item(name='guiTxssRxTxRxId', width=1, label='To:', style='readonly'),
                Item(name='guiTxssRxTxRxType', width=1, show_label=False, style='readonly'),
            ),
            HGroup(
                Item(name='guiTxssRxTxBestSector', label='Sector:', style='readonly', format_str='%02d'),
                Item(name='guiTxssRxTxRcvPower', label='Rx Power:', style='readonly', format_str='%.2f'),
            ),

            label='TXSS RX-TX',
            show_border=True),
        label='SLS',
        show_border=True)

    slsGroup = HGroup(
        VGroup(
            Item('guiDisplaySls', label='Display SLS'),
            HGroup(
                Item('guiSlsMode', label='SLS from:'),
                Item(name='guiIterateSlsBftId', label='BFT Trace', visible_when='guiSlsMode == "ns-3"',
                     editor=RangeEditor(low_name='guiMinSlsBftId',
                                        high_name='guiMaxSlsBftId',
                                        mode='spinner',
                                        )),
            ),
            HGroup(
                VGroup(

                    Item(name='guiTxNodeSelected', width=100, editor=CheckListEditor(name='guiTxNodeSelectedChoices'),
                         label='TX Node'),

                    Item(name='guiTxPaaSelected', width=100, editor=CheckListEditor(name='guiTxPaaSelectedChoices'),
                         label='PAA TX'),
                ),
                VGroup(
                    Item(name='guiRxNodeSelected', width=100, editor=CheckListEditor(name='guiRxNodeSelectedChoices'),
                         label='Rx Node'),
                    Item(name='guiRxPaaSelected', width=100, editor=CheckListEditor(name='guiRxPaaSelectedChoices'),
                         label='PAA RX')
                ),
                Item(name='guiSwitchTxRxNode', height=-75, width=-50, show_label=False, label=' ',
                     editor=ButtonEditor(image=ImageResource('/Pictures/Interface/switch.png')), style='custom'),
            ),
            label='SLS Interaction',
            show_border=True),
        VGroup(
            Item(name='traceIndex', label='Trace',
                 editor=RangeEditor(low_name='guiMinTrace',
                                    high_name='guiMaxTrace',
                                    mode='spinner',
                                    )),
            Item('guiVisualizerInteractions', width=1, style='custom',show_label=False),

            Item(name='guiTraceIncrement', width=1, label='PlaySpeed (Trace per animation)'),
            label='Scenario Interaction',
            show_border=True),
        resultsGUI,
        VGroup(

            Item(name='guiDisplayStaAssociation', width=-200, label='Display STAs Association'),
            Item(name='guiShowSlsBestAp', label='Show Best AP for STA',
                 visible_when='guiTxssTxRxTxType == "(STA)" and guiTxssRxTxTxType == "(AP)" and guiSlsDataModePreprocessed == True'),
            label='Association properties',
            show_border=True),
        VGroup(
            HGroup(
                VGroup(
                    HGroup(
                        Item(name='guiMpcReflection', width=1, label='MPCs Reflection', style='custom'),
                        Item('guiMpcsHidden', label='MPC Hidden'),
                    ),
                    HGroup(
                        Item(name='guiMpcsMagnifier', width=1, label='MPCs Size'),
                        Item('guiMpcColor', editor=ColorEditor(), label='Color'),

                    ),

                ),
                label='MPCs properties',
                show_border=True),
            Item(name='guiButtonSaveTweak', label='Save Config', style='custom'),
        ),
    )

    visualizationTweakGroup = VGroup(
        HGroup(
            HGroup(
                VGroup(
                    Item(name='guiDisplayNodesObjects',  label='Display 3D Objects'),
                    HGroup(
                        Group(
                            Item(name='guiApsNodesSize',  label='Size'),
                            Item(name='guiApThreeDModeScale',  label='Model Size'),
                            label='APs',
                            show_border=True),
                        Group(
                            Item(name='guiStasNodesSize',  label='Size'),
                            Item(name='guiStaThreeDModeScale', label='Model Size'),

                            label='STAs',
                            show_border=True),
                    ),
                    label='Nodes Properties',
                    show_border=True),
                VGroup(
                    HGroup(
                        Group(
                            Item(name='guiApAntennaPatternMagnifier', label='Size'),
                            Item(name='guiApAntennaPatternOpacity', label='Opacity'),
                            label='APs',
                            show_border=True),
                        Group(
                            Item(name='guiStaAntennaPatternMagnifier', label='Size'),
                            Item(name='guiStaAntennaPatternOpacity', label='Opacity'),
                            label='STAs',
                            show_border=True),
                        label='Antenna Patterns Properties',
                        defined_when='guiDisplayGroupSls == "True"',
                        show_border=True),

                    HGroup(
                            Item(name='guiApPaaMagnifier', label='APs'),
                            Item(name='guiStaPaaMagnifier', label='STAs'),
                        label='PAA Size',
                        show_border=True),
                ),
                VGroup(
                    VGroup(
                        HGroup(
                            Item(name='guiNodesScene',  label='Nodes:'),
                            Item(name='guiNodesLabelsScene',  label='Nodes Labels:'),
                        ),
                        HGroup(
                            Item(name='guiPaasScene',  label='PAAs:'),
                            Item(name='guiBeamformingPatternsScene',  label='Antenna Patterns:'),
                        ),

                        label='Change objects scene',
                        show_border=True),
                    VGroup(
                        HGroup(
                            Item(name='guiApsLabels',  label='AP:'),
                            Item('guiApsLabelsColor', editor=ColorEditor(), label=' Color'),
                        ),
                        HGroup(
                            Item(name='guiStasLabels',  label='STA:'),
                            Item('guiStasLabelsColor', editor=ColorEditor(), label=' Color'),
                        ),
                        label='Labels',
                        show_border=True),
                ),
                VGroup(
                    HGroup(
                        VGroup(
                            HGroup(
                                Item(name='guiMpcReflection', label='MPCs Reflection', style='custom'),
                                Item('guiMpcsHidden', label='MPC Hidden'),
                            ),
                            HGroup(
                                Item(name='guiMpcsMagnifier',  label='MPCs Size'),
                                Item('guiMpcColor', editor=ColorEditor(), label='Color'),

                            ),

                        ),
                        label='MPCs properties',
                        show_border=True),
                    Item(name='guiButtonSaveTweak', show_label = False ,  label='Save Config', style='custom'),
                ),
            ),
        ),
    )

    curvesInteractionGroup = HGroup(
        VGroup(
            Item(name='traceIndex', label='Trace',
                 editor=RangeEditor(low_name='guiMinTrace',
                                    high_name='guiMaxTrace',
                                    mode='spinner',
                                    )),
            Item('guiVisualizerInteractions', width=1, style='custom',show_label=False),

            Item(name='guiTraceIncrement', width=1, label='PlaySpeed (Trace per animation)'),
            label='Scenario Interaction',
            show_border=True),
        Item(name='guiCurvesMenu',
             editor=tree_editor,
             show_label=False, width=-1, height=-1,
             label='Plots',
             ),
        resultsGUI,
        layout='tabbed',

    )

    environmentGroup = Group(
        HGroup(
            # Group used to inspect the different objects of the scenario
            HGroup(Group(
                Item(name='guiViewSelected', label='View Selected', style='readonly'),
                Item(name='guiTextureMaterial', label='Representation'),
                Item(name='guiEdgeVisibility', label='Edge Visibility'),
                label='View Properties',
                show_border=True),
            ),

            HGroup(Group(
                # Item(name='guiTextureMaterial', label='Surface/Wireframe'),
                Item(name='guiObjectId', label='ID', style='readonly'),
                Item(name='guiObjectName', label='Name', style='readonly'),
                Item(name='guiMaterialId', label='Material ID', style='readonly'),
                Item(name='guiMaterialName', label='Material Name', style='readonly'),

                label='Object Inspector',
                show_border=True),
            ),
            # Group used to edit the objects material
            HGroup(Group(
                HGroup(
                    VGroup(
                        Group(
                            Item(name='guiHideObject', label='Hide Object'),
                            HGroup(
                            Item(name='guiFrontFaceCulling', label='Front'),
                            Item(name='guiBackFaceCulling', label='Back'),
                            label='Face Culling',
                            show_border=True),
                            Item(name='guiObjectOpacity', label='Object Opacity'),
                        label='Visibility',
                        show_border=True),

                    ),
                    VGroup(
                        Item('guiObjectColor', editor=ColorEditor(),  label='Object Color'),
                        HGroup(
                            Item('guiVisualizerTextures', label='texture', style='simple'),
                            Item(name='guiTextureMode', label='Interpolation'),
                            label='Texture setting',
                            show_border=True),
                    ),

                    HGroup(
                        Item(name='guiButtonSaveEnvironment',  show_label = False ,
                             style='custom'),
                    ),

                ),

                label='Object Editor',
                show_border=True),
            ),
        ),

    )

    scenarioInteractionGroup = HGroup(
        HGroup(
            VGroup(

                Item(name='guiTxNodeSelected', width=100, editor=CheckListEditor(name='guiTxNodeSelectedChoices'),
                     label='TX Node', emphasized=True),

                Item(name='guiTxPaaSelected', width=100, editor=CheckListEditor(name='guiTxPaaSelectedChoices'),
                     label='PAA TX',
                     emphasized=True),
            ),
            VGroup(
                Item(name='guiRxNodeSelected', width=100, editor=CheckListEditor(name='guiRxNodeSelectedChoices'),
                     label='Rx Node', emphasized=True),
                Item(name='guiRxPaaSelected', width=100, editor=CheckListEditor(name='guiRxPaaSelectedChoices'),
                     label='PAA RX',
                     emphasized=True)
            ),
            Item(name='guiSwitchTxRxNode', height=-75, width=-50, show_label=False, label=' ',
                 editor=ButtonEditor(image=ImageResource('/Pictures/Interface/switch.png')), style='custom'),
            label='TX/RX Selection',
            show_border=True),
        VGroup(
            Item(name='traceIndex', label='Trace',
                 editor=RangeEditor(low_name='guiMinTrace',
                                    high_name='guiMaxTrace',
                                    mode='spinner',
                                    )),
            #  HGroup(
            Item('guiVisualizerInteractions', width=-200, style='custom',show_label=False),

            Item(name='guiTraceIncrement', width=-200, label='PlaySpeed (Trace per animation)'),
            label='Scenario Interaction',

            show_border=True),
    )

    mimoGroup = HGroup(
        # Group used to inspect the different objects of the scenario
        VGroup(
            Item(name='guiDisplayMimo', label='Display MIMO'),
            Item(name='guiMimoData', label='MIMO From:', style='custom', visible_when='guiDisplayBeamTrackingParameters == "False"'),
            Item(name='guiBeamtrackingType', label='BeamTracking Type', style='custom', visible_when='guiDisplayBeamTrackingParameters == "True"'),
            Item(name='guiMimoStream', label='Stream', style='custom'),
            HGroup(
                Item(name='guiMimoTxStreamIdentifier', label=guiMimoTxStreamIdentifierLabel, style='readonly'),
                Item(name='guiMimoRxStreamIdentifier', label=guiMimoRxStreamIdentifierLabel, style='readonly'),
            ),
            HGroup(
                Item(name='guiMimoTxSector', label='Tx Sector:', style='readonly'),
                Item(name='guiMimoRxSector', label='Rx Sector', style='readonly'),
            ),
            label='Streams Information',
            show_border=True),
        VGroup(
            Item(name='traceIndex', label='Trace',
                 editor=RangeEditor(low_name='guiMinTrace',
                                    high_name='guiMaxTrace',
                                    mode='spinner',
                                    )),
            Item('guiVisualizerInteractions',  style='custom',show_label=False),

            Item(name='guiTraceIncrement',  label='PlaySpeed (Trace per animation)'),
            label='Scenario Interaction',
            show_border=True),
        VGroup(
            Item(name='guiMimoStream', label='Stream', style='custom'),
            HGroup(
                Item(name='guiMimoStreamSize', label='Stream Size'),
                Item(name='guiMimoStreamMpcSize', label='Stream MPC Size'),
                Item(name='guiMimoEdgesSize', label='Edges Size'),
                Item(name='guiMimoStreamOpacity', label='Opacity'),
            ),

            Item('guiMimoStreamColor', editor=ColorEditor(), label='Stream Color'),
            Item('guiButtonSaveMimoConfig',show_label=False),

            label='Streams Visualization',
            show_border=True),

    )

    sensingGroup = HGroup(
        # Group used to inspect the different objects of the scenario
        VGroup(
            HGroup(
                Item(name='guiTxNodeSelected', width=100, editor=CheckListEditor(name='guiTxNodeSelectedChoices'),
                     label='TX Node', emphasized=True),
                Item(name='guiRxNodeSelected', width=100, editor=CheckListEditor(name='guiRxNodeSelectedChoices'),
                     label='RX Node', emphasized=True),
                Item(name='guiTargetSelected', label='Target', editor=CheckListEditor(name='guiTargetSelectedChoices')),
                label='Configure TX/RX/Target',
                show_border=True),
            HGroup(
                Item(name='guiDisplayTxRxMpcs', label='Display Tx/Rx MPCs'),
                Item(name='guiDisplayTargetMpcs', label='Display Target MPCs'),
                label='Configure MPCs',
                show_border=True),
            show_border=True),
        VGroup(
            Item(name='traceIndex', label='Trace',
                 editor=RangeEditor(low_name='guiMinTrace',
                                    high_name='guiMaxTrace',
                                    mode='spinner',
                                    )),
            Item('guiVisualizerInteractions', width=1, style='custom',show_label=False),

            Item(name='guiTraceIncrement', width=1, label='PlaySpeed (Trace per animation)'),
            label='Scenario Interaction',
            show_border=True),
        VGroup(
            Item('guiSensingTargetColor', editor=ColorEditor(), label='Target Color'),
            Item('guiButtonSaveSensingConfig', height=-35, width=-500, label='Save Configuration'),
            label='Tweak',
            show_border=True),

    )

    orientationGroup = HGroup(
        VGroup(
            Item(name='guiDisplayDeviceTxAxis', width=-300, label='Device Orientation'),
            Item(name='guiDisplayPaaTxAxis', label='Tx PAA Orientation'),
            label='Tx',
            show_border=True),
        VGroup(
            Item(name='guiDisplayDeviceRxAxis', width=-300, label='Device Orientation'),
            Item(name='guiDisplayPaaRxAxis', label='Rx PAA Orientation'),
            label='Rx',
            show_border=True),

    )

    if qdScenario.qdInterpreterConfig.sensing and qdRealization.sensingResults.available:
        viewToDisplay = HSplit(
            Item('view1', editor=SceneEditor(scene_class=MayaviScene),
                 show_label=False, resizable=True, width=480, height=480),
            Item('view2',
                 editor=SceneEditor(scene_class=MayaviScene), show_label=False, resizable=True, width=480, height=900),
            Item('view3',
                 editor=SceneEditor(scene_class=MayaviScene), show_label=False, resizable=True, width=480,
                 height=880),

        )
    else:
        viewToDisplay = HSplit(
            Item('view1', editor=SceneEditor(scene_class=MayaviScene),
                 show_label=False, resizable=True, width=480, height=900),
            Item('view2',
                 editor=SceneEditor(scene_class=MayaviScene), show_label=False, resizable=True, width=480, height=900),
        )

    view = View(
        VGroup(
            viewToDisplay,
            Group(
                Group(
                    scenarioInteractionGroup,
                    label="Scenario Interaction"),
                Group(
                    visualizationTweakGroup,
                    label="Visualization Tweak"),
                Group(
                    curvesInteractionGroup,
                    label="Curves Interaction", defined_when='guiDisplayGroupCurves == "True"'),
                Group(
                    environmentGroup,
                    label="Environment Interaction"),
                Group(
                    orientationGroup,
                    label="Orientation"),
                Group(
                    codebookGroup,
                    label="Codebook",defined_when='guiDisplayGroupCodebook == True'),
                Group(
                    slsGroup,
                    label="SLS", defined_when='guiDisplayGroupSls == "True"'),

                Group(
                    mimoGroup,
                    label=qdScenario.qdInterpreterConfig.mimo, defined_when='guiDisplayGroupMimo == "True"'),
                Group(
                    sensingGroup,
                    label="Sensing", defined_when='guiDisplayGroupSensing == "True"'),
                layout="tabbed"),

            layout="split"),
    )


################################################################################
# The QWidget containing the visualization, this is pure PyQt4 code.
class MayaviQWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # There is a bug apparently in Mayavi that has not been fixed yet
        # (See https://github.com/enthought/mayavi/issues/3)
        # These 3 lines just catch the warning displayed due to this bug
        # and avoid to output them - Mainly cause it's speeding-up the simulation
        output = vtk.vtkFileOutputWindow()
        output.SetFileName("log.txt")
        vtk.vtkOutputWindow().SetInstance(output)
        self.visualization = Visualization()

        # If you want to debug, beware that you need to remove the Qt
        # input hook.
        # QtCore.pyqtRemoveInputHook()
        # import pdb ; pdb.set_trace()
        # QtCore.pyqtRestoreInputHook()

        # The edit_traits call will generate the widget to embed.
        self.ui = self.visualization.edit_traits(parent=self,
                                                 kind='subpanel').control
        layout.addWidget(self.ui)
        self.ui.setParent(self)

        sys.setrecursionlimit(10 ** 9)


if __name__ == "__main__":
    freeze_support()
    # from multiprocessing import set_start_method
    #
    # set_start_method("spawn")
    # Don't create a new QApplication, it would unhook the Events
    # set by Traits on the existing QApplication. Simply use the
    # '.instance()' method to retrieve the existing one.
    app = QtGui.QApplication.instance()
    container = QtGui.QSplitter()
    splitter = QtGui.QSplitter(container)
    mayavi_widget = MayaviQWidget(container)

    # New code curve
    mayavi_widget.resize(800, 600)
    mayavi_widget.setMinimumWidth(400)
    splitter.addWidget(mayavi_widget)
    #

    if qdScenario.qdInterpreterConfig.plotData:
        # Create the widgets to display the graph only if the visualizer has been configured to to so
        global Y_CURVE_LEGEND
        Y_CURVE_LEGEND = {}  # Dictionary storing the legends for all the plots (the key is the name of the plot)

        # Handle Power Plots creation (Widget + PlotItem)
        pg.setConfigOption('background', (68, 68, 68))
        powerWidget = pg.PlotWidget()
        Y_CURVE_LEGEND["Power"] = pg.LegendItem(offset=(80, 30))
        Y_CURVE_LEGEND["Power"].setParentItem(powerWidget.graphicsItem())

        rxPowerPlotItem = powerWidget.plotItem
        labelStyle = {'color': '#FFF', 'font-size': '24px'}
        rxPowerPlotItem.setLabel('left', 'Power (dBm)', **labelStyle)
        rxPowerPlotItem.setLabel('bottom', 'Trace', **labelStyle)
        rxPowerPlotItem.getAxis('left').setPen((255, 255, 255))
        # rxPowerPlotItem.setYRange(-80, 0, padding=0)
        rxPowerPlotItem.showGrid(True, True)
        axisX = rxPowerPlotItem.getAxis('bottom')
        axisX.setTickSpacing(1000, 100)

        powerPerSectorWidget = pg.PlotWidget()
        Y_CURVE_LEGEND["Power Per Sector"] = powerPerSectorWidget.addLegend(offset=(80, 30))
        powerPerSectorPlotItem = powerPerSectorWidget.plotItem
        # powerPerSectorPlotItem.setYRange(-100, -40, padding=0)
        powerPerSectorPlotItem.setLabel('left', 'Power (dBm)', **labelStyle)
        powerPerSectorPlotItem.setLabel('bottom', 'Sector ID', **labelStyle)
        powerPerSectorPlotItem.showGrid(True, True)
        axisX = powerPerSectorPlotItem.getAxis('bottom')
        # Create the tick based on the codebook (AP or STA) with the max number of sectors
        tickX = np.arange(max(codebooks.getNbSectorPerApAntenna(), codebooks.getNbSectorPerStaAntenna()))
        axisX.setTicks([[(v, str(v)) for v in tickX]])
        font = QtGui.QFont()
        font.setPixelSize(10)
        axisX.tickFont = font

        if qdScenario.qdInterpreterConfig.dataMode == "online":
            # We can display the PSD only in online mode
            # Handle PSD Plots creation (Widget + PlotItem)
            psdWidget = pg.PlotWidget()
            Y_CURVE_LEGEND["PSD"] = psdWidget.addLegend(offset=(80, 30))
            psdPlotItem = psdWidget.plotItem
            # psdPlotItem.setYRange(-120, -60, padding=0)
            psdPlotItem.setLabel('left', 'Power (Db)', **labelStyle)
            psdPlotItem.setLabel('bottom', 'Subband', **labelStyle)
            psdPlotItem.showAxis('right')
            psdPlotItem.showGrid(True, True)
            axisX = psdPlotItem.getAxis('bottom')
            axisX.setTickSpacing(20, 5)

            # Handle Power Per Sector Plots creation (Widget + PlotItem)

        global CURVES_DIC
        CURVES_DIC = {}  # Dictionary holding all the curves objects - The key is made of the name of the curve and the Tx/Rx/PaaTx/PaaRx tuple

        global Y_CURVE_DATA_DIC
        Y_CURVE_DATA_DIC = {}  # Dictionary holding all the curves data - he key is made of the name of the curve and the Tx/Rx/PaaTx/PaaRx tuple
        combination = 0

        global Y_CURVE_FILTER  # Dictionary used to filter the curves to display - he key is made of the name of the curve and the Tx/Rx/PaaTx/PaaRx tuple
        Y_CURVE_FILTER = {}
        nbNodesPermutations = globals.nPr(qdScenario.nbNodes, 2)
        # Create the curves objects and curves data placeholders for each plot
        for tx in range(qdScenario.nbNodes):
            for rx in range(qdScenario.nbNodes):
                # Creation of Power plots
                if tx != rx:
                    for apPaaId in range(codebooks.getNbPaaPerAp()):
                        for staPaaId in range(codebooks.getNbPaaPerSta()):
                            # Power curves and data
                            CURVES_DIC[("Power", tx, rx, apPaaId, staPaaId)] = rxPowerPlotItem.plot()
                            CURVES_DIC[("Power", tx, rx, apPaaId, staPaaId)].setPen(
                                color=pg.intColor(combination, hues=nbNodesPermutations), width=3)

                            Y_CURVE_DATA_DIC[("Power", tx, rx, apPaaId, staPaaId)] = np.empty(100)
                            Y_CURVE_DATA_DIC[("Power", tx, rx, apPaaId, staPaaId)].fill(-math.inf)

                            # # Add the RX side
                            #
                            # CURVES_DIC[("Power", rx, staPaaId,tx, apPaaId)] = rxPowerPlotItem.plot(
                            #     pen=QPen(
                            #         pg.intColor(combination, hues=nbNodesPermutations),
                            #         0, 2, 2, 3))
                            # Y_CURVE_DATA_DIC[("Power", rx, tx, staPaaId,apPaaId)] = np.empty(100)
                            # Y_CURVE_DATA_DIC[("Power", rx, tx, staPaaId,apPaaId)].fill(-math.inf)

                            CURVES_DIC[
                                ("Power Per Sector", tx, rx, apPaaId, staPaaId)] = powerPerSectorPlotItem.plot()
                            CURVES_DIC[("Power Per Sector", tx, rx, apPaaId, staPaaId)].setPen(
                                color=pg.intColor(combination, hues=nbNodesPermutations), width=2)

                            Y_CURVE_DATA_DIC[("Power Per Sector", tx, rx, apPaaId, staPaaId)] = np.empty(
                                codebooks.getNbSectorsPerPaaNode(tx))
                            Y_CURVE_DATA_DIC[("Power Per Sector", tx, rx, apPaaId, staPaaId)].fill(-math.inf)
                            if qdScenario.qdInterpreterConfig.dataMode == "online":
                                # We can display the PSD only in online mode
                                # as these data are not stored in the preprocessed mode
                                CURVES_DIC[("PSD", tx, rx, apPaaId, staPaaId)] = psdPlotItem.plot(
                                    pen=QPen(pg.intColor(combination, hues=nbNodesPermutations), 0))
                                Y_CURVE_DATA_DIC[("PSD", tx, rx, apPaaId, staPaaId)] = np.empty(globals.nbSubBands)
                                Y_CURVE_DATA_DIC[("PSD", tx, rx, apPaaId, staPaaId)].fill(-math.inf)

                            combination = combination + 1

        qtabWidget = QtGui.QTabWidget(container)  # Create a QtTab widget for the plots to display
        qtabWidget.addTab(powerWidget, 'Power')
        qtabWidget.addTab(powerPerSectorWidget, 'PowerPerTxSector')
        if qdScenario.qdInterpreterConfig.dataMode == "online":
            # Add the power, PSD depending on the mode
            qtabWidget.addTab(psdWidget, 'PSD')

        splitter.addWidget(qtabWidget)

    window = QtGui.QMainWindow()
    window.setCentralWidget(container)
    window.setWindowTitle("Q-D Interpreter Visualizer")
    # The way the curves are managed impose to wait for all the curves to be initialized
    # before to call the interruption that triggers the method updateNewSelection
    # TODO Improve that
    mayavi_widget.visualization.guiTxNodeSelected = "0"

    window.show()
    app.exec_()
