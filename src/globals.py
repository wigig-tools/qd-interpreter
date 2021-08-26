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

import argparse
import logging
import math
import os
import pickle
from enum import Enum
import nsInput
from plots import plotPreprocessedData
import qdPropagationLoss
import qdRealization
from qdPropagationLoss import TxParam
from preprocessData import preprocessData
from preprocessData import loadPreprocessedData
from codebook import loadCodebook
import csv
from qdRealization import BeamTrackingResults
from preprocessData import preprocessCompleteSuMimo
from preprocessData import  preprocessCompleteMuMimo

# Subband parameters (TODO: Use a class)
centerFrequency = 60480
channelWidth = 2160
bandBandwidth = 5156250
guardBandwidth = 2160
nbSubBands = 355

# Power characteristics
deviceTxPowerDbm = 10  # Power used by the device to transmit (TODO: Different power for STAs and APs)

# SNR
noiseFigure = 5.01187

# Codebook variables
azimuthCardinality = 361
elevationCardinality = 181

# Files and Folder variables
scenarioFolder = ""  # The folder containing all the files needed to display a given scenario
scenarioPath = ""
configFile = "config.csv"  # The file containing the parameters of the scenario
nodePositionFolder = "NodePositions/"  # The folder containing the nodes positions
mpcFolder = "MpcCoordinates/"  # Folder that contains the MPC coordinates files
qdRealizationOutputFolder = "Output"
qdRealizationInputFolder = "Input"
qdRealizationVisualizerFolder = "Visualizer"  # Folder exported by the Q-D realization software to store visualizer files
qdRealizationNsFolder = "Ns3"  # Folder exported by the Q-D realization software to store ns-3 files
topologyFolder = "RoomCoordinates/"  # The folder containing the file defining the environment geometry
topologyFilename = "RoomCoordinates.csv"  # The environment geometry file
resultsFolder = "Results"  # Folder containing the results files (Throughput, SLS, etc.)
beamTrackingFolder = "BeamTracking"
slsFolder = "SLS"
pickleFolder = "pickle"
preprocessedFolder = "Preprocessed"
associationFolder = "Association"
slsResultsFile = "slsDMG_MCS1.csv"  # The file containing the SLS phase results # TODO Update FileName
snrFile = "snrDMG_MCS1.csv"  # The SNR file f(L-ROOM scenario only)
CodebookFolder = "Codebook/"  # Folder containing the different codebook files
graphFolder = "Graph"
schedulingFolder = "Scheduling"
mlFolder = "MachineLearning"
dataFolder = "Data"
bestSectorItxssFolder = "BestSectorITXSS"
rxPowerItxssFolder = "RxPowerITXSS"
capacityFolder = "Capacity"
snrSinrFolder = "SNR_SINR"
componentsConfigFile = "componentsVisConfig.conf"
mimoConfigFile = "mimoVisConfig.p"
sensingConfigFile = "sensingVisConfig.conf"
view1ConfigFile = "view1VisConfig.conf"
view2ConfigFile = "view2VisConfig.conf"
dopplerAxisFile = "axis.txt"
dopplerRangeFile = "rangeDoppler.txt"

defaultApCodebook = "ura_28x_siso_37sectors.txt"  # Default Codebook used by the APs
defaultStaCodebook = "ura_28x_siso_37sectors.txt"  # Default Codebook used by the STAs

qdFilesFolder = "QdFiles"  # The Folder containing the Q-D files
positionPrefix = "NodePositionsTrc"  # The folder containing the nodes mobility parameter
nodePositionJSON = "NodePositions.json"
targetPositionJSON = "TargetBasePositions.json"
targetMpcJSON = "targetMpc.json"

mpcJSON = "Mpc.json"
qdJSON = "qdOutput.json"
paaPositionJSON = "PAAPosition.json"
modelFolder ="3DObjects"
textureFolder = "Pictures/Textures/"
qdConfigurationFile = "paraCfgCurrent.txt"
suMimoFilePrefix = "SuMimo_"
muMimoInitiatorPrefix = "MuMimo_I_"
muMimoResponderPRefix = "MuMimo_R_"

class QdInterpreterConfig:
    """
    A class to represent the configurations of the software (command line parameters)

    Attributes
    ----------
    scenarioName : String
        Name of the scenario

    type : NodeType class
            Type of the node (AP or STA)
    """
    def __init__(self, scenarioName, slsEnabled,dataMode, plotData, regenerateCachedQdRealData, forceSlsDataRegeneration, forcePlotsRegeneration, sensing,
                 mimo,mimoDataMode,codebookMode, patternQuality,filterVelocity,codebookTabEnabled):
        self.scenarioName = scenarioName
        self.slsEnabled = slsEnabled
        self.plotData = plotData
        self.dataMode = dataMode
        self.regenerateCachedQdRealData = regenerateCachedQdRealData
        self.forceSlsDataRegeneration = forceSlsDataRegeneration
        self.forcePlotsRegeneration = forcePlotsRegeneration
        self.sensing = sensing
        self.mimo = mimo
        self.mimoDataMode = mimoDataMode
        self.codebookMode = codebookMode
        self.patternQuality = patternQuality
        self.filterVelocity = filterVelocity
        self.codebookTabEnabled = codebookTabEnabled


class NodeType(Enum):
    AP = 0
    STA = 1

class MimoBeamformingResults:
    # def __init__(self, srcId, dstId, traceId, txAntennaId, txSectorId, txAwvId, rxAntennaId,rxSectorId, rxAwvId):
    def __init__(self, bestreamIdCombination, traceId, txAntennaId, txSectorId, txAwvId, rxAntennaId, rxSectorId, rxAwvId):
        # self.srcId = srcId
        # self.dstId = dstId
        self.bestreamIdCombination = bestreamIdCombination
        self.traceId = traceId
        self.txAntennaId = txAntennaId
        self.txSectorId = txSectorId
        self.txAwvId = txAwvId
        self.rxAntennaId = rxAntennaId
        self.rxSectorId = rxSectorId
        self.rxAwvId = rxAwvId

class Node:
    """
    A class to represent a node in the simulation and its type.
    TODO: This class is not really needed anymore - Could be removed

    Attributes
    ----------
    id : int
        The ID of the node

    type : NodeType class
            Type of the node (AP or STA)
    """

    def __init__(self, id, type):
        """
        Constructor

        Parameters
        ----------
        id : int
            Node ID

        type : NodeType class
            Type of the node (AP or STA)
        """
        self.id = id
        self.type = type


def nPr(n, r):
    """Compute the number of permutations

        Parameters
        ----------
        n : int
            Number of Objects
        r : int
            Number of Samples
    """
    f = math.factorial
    return f(n) // f(n - r)


def printProgressBarWithoutETA(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """

    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix},', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


def printProgressBar(iteration, total, eta, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """

    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix} ETA:{eta},', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


# Logging
logger = 0
DEBUG_LEVELS = {'debug': logging.DEBUG,
                'info': logging.INFO,
                'warning': logging.WARNING,
                'error': logging.ERROR,
                'critical': logging.CRITICAL}


def initializeOracle(useVisualizer=False):
    """Initialize the Q-D Oracle (Load input files, precompute data, etc.)

    Parameters
    ----------
    useVisualizer : bool
        Use the Q-D oracle with visualizer or not

    Returns
    -------
    preprocessedSlsData : SlsResults class
        The preprocessed data for the SLS Phase
    preprocessedAssociationData : Dic
        The preprocessed association Data
    txParam: TxParam class
        Parameters associated to the transmissions
    dataIndex: Dic
        Used to reconstruct the index of the preprocessed data
    qdChannel: qdChannel class
        The parameters of each MPC
    codebooks : Codebooks class
        Directivity of the AP and STA nodes (sectors and quasi-omni directivity)
    """
    global logger
    global scenarioPath

    # Handle the command line-parsing
    parser = argparse.ArgumentParser()
    # By default, we force the user to provide a scenario folder
    parser.add_argument('--s', action='store', dest='scenarioName',
                        help='The scenario folder')

    parser.add_argument('-d', nargs='?', action='store', dest='debugLevel',
                        help='The Desired Quality level of debug ("debug", "info", "warning", "error", or "critical")',
                        default='warning')

    parser.add_argument('--dataMode', nargs='?', action='store', dest='dataMode', choices=['preprocessed', 'online', 'none'],
                        help='The mode to handle the input data',
                        default='none')

    parser.add_argument('-recacheQdRealizationOutput', nargs='?', action='store', dest='regenerateCachedQdRealData',
                        help='Force the regeneration of Q-D Realization software cached data',
                        type=int, default=0)

    parser.add_argument('-forceSlsDataRegeneration', nargs='?', action='store', dest='forceSlsDataRegeneration',
                        help='Force the regeneration of the SLS phase results',
                        type=int, default=0)

    parser.add_argument('-forcePlotsRegeneration', nargs='?', action='store', dest='forcePlotsRegeneration',
                        help='Force the regeneration of the SLS phase results',
                        type=int, default=0)

    parser.add_argument('--curves', dest='displayPlotWidget', action='store_true')
    parser.add_argument('--no-curves', dest='displayPlotWidget', action='store_false')
    parser.set_defaults(displayPlotWidget=False)

    parser.add_argument('--patternQuality', nargs='?', action='store', dest='patternQuality',
                        help='Granularity of the antenna patterns displayed',
                        type=int, default=4)

    parser.add_argument('--filterVelocity', nargs=2,action='store', dest='filterVelocity', type=float, default=[-math.inf,math.inf])
    # Visualization Features
    parser.add_argument('--sls', dest='slsEnabled', action='store_true')
    parser.add_argument('--no-sls', dest='slsEnabled', action='store_false')
    parser.set_defaults(slsEnabled=False)

    parser.add_argument('--sensing', dest='sensing', action='store_true')
    parser.add_argument('--no-sensing', dest='sensing', action='store_false')
    parser.set_defaults(sensing=False)


    parser.add_argument('--mimo', nargs='?', action='store', dest='mimo',
                        choices=['none', 'suMimo', 'muMimo', 'beamTracking'],
                        help='The MIMO Mode',
                        default='none')

    parser.add_argument('--mimoDataMode', nargs='?', action='store', dest='mimoDataMode',
                        choices=['none', 'online', 'preprocessed'],
                        help='The MIMO Mode',
                        default='none')

    parser.add_argument('--codebook', dest='codebookTabEnabled', action='store_true')
    parser.add_argument('--no-codebook', dest='codebookTabEnabled', action='store_false')
    parser.set_defaults(sensing=False)

    parser.add_argument('--codebookMode', nargs='?', action='store', dest='codebookMode', choices=['dB', 'linear'],
                        help='Is the antenna pattern represented in dB or linear',
                        default='dB')



    argument = parser.parse_args()

    if argument.patternQuality == 0:
        # We are slicing antenna pattern so 0 cannot be used
        argument.patternQuality = 1

    qdInterpreterConfig = QdInterpreterConfig(argument.scenarioName, argument.slsEnabled,argument.dataMode,argument.displayPlotWidget, argument.regenerateCachedQdRealData,
                                                          argument.forceSlsDataRegeneration,
                                                          argument.forcePlotsRegeneration, argument.sensing,
                                                          argument.mimo,argument.mimoDataMode, argument.codebookMode, argument.patternQuality,argument.filterVelocity,argument.codebookTabEnabled)

    print("************************************************")
    print("*      ORACLE CONFIGURATION SUMMARY            *")
    print("************************************************")
    print("Scenario:", qdInterpreterConfig.scenarioName)
    print("SLS Enabled:", qdInterpreterConfig.slsEnabled)
    print("Data Mode:", qdInterpreterConfig.dataMode)
    print("Sensing Enabled:", qdInterpreterConfig.sensing)
    print("MIMO:", qdInterpreterConfig.mimo)
    print("Codebook:", qdInterpreterConfig.codebookMode)
    print("Pattern Quality:", qdInterpreterConfig.patternQuality)


    # print("Regenerate Cached Data:", qdInterpreterConfig.regenerateCachedQdRealData)
    # print("Force SLS data regeneration:", qdInterpreterConfig.forceSlsDataRegeneration)
    # print("Force Plots regeneration:", qdInterpreterConfig.forcePlotsRegeneration)
    print("Use Q-D Oracle Visualizer:", useVisualizer)

    # Create the logger
    logger = logging.getLogger("Q-D Oracle")
    logger.setLevel(DEBUG_LEVELS.get(argument.debugLevel, logging.NOTSET))
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(DEBUG_LEVELS.get(argument.debugLevel, logging.NOTSET))
    formatter = logging.Formatter("%(levelname)s: %(message)s \t(%(module)s:%(funcName)s())")
    ch.setFormatter(formatter)
    logger.addHandler(ch)


    # Create transmission parameters (frequencies, power per subband, noise)
    txParam = TxParam()
    txParam.allocateFrequencies(centerFrequency, channelWidth, bandBandwidth, guardBandwidth)
    txParam.allocateTxPowerPerSubband(qdPropagationLoss.DbmtoW(deviceTxPowerDbm), False, txParam.getFrequencies(),
                                      nbSubBands)
    txParam.computeNoise()

    scenarioPath = os.path.join(scenarioFolder, qdInterpreterConfig.scenarioName)

    # Load codebook
    print("************************************************")
    print("*      CODEBOOK CONFIGURATION SUMMARY          *")
    print("************************************************")
    codebookApName, codebookStaName = loadCodebookConfiguration(os.path.join(scenarioFolder, qdInterpreterConfig.scenarioName))
    codebookPickledName = codebookApName + codebookStaName + qdInterpreterConfig.codebookMode
    cachedCodebooksFile = os.path.join(CodebookFolder,pickleFolder, codebookPickledName + ".p")
    if os.path.exists(cachedCodebooksFile):
        # The codebooks combination has already been pickled - Just load the pickled file
        print("The codebook combination has been already computed previously - Just load it")
        codebooks = pickle.load(
            open(cachedCodebooksFile, "rb"))
    else:
        # The Codebooks combination was never loaded - Load the codebooks first and then save the pickled codebooks
        print("The codebook combination has never been computed - Perform the computation")
        beamTrackingCodebook = False
        # Beamtracking codebooks files have a different format
        if qdInterpreterConfig.mimo == "beamTracking":
            beamTrackingCodebook = True
        codebooks = loadCodebook(CodebookFolder, beamTrackingCodebook, qdInterpreterConfig.codebookMode, codebookApName, codebookStaName)
        pickle.dump(codebooks, open(cachedCodebooksFile, "wb"), protocol=pickle.HIGHEST_PROTOCOL)


    print("Codebook AP")
    print("\tNb PAAs:",codebooks.getNbPaaPerAp())
    print("\tNb Sectors:",codebooks.getNbSectorPerApAntenna())
    print("Codebook STA")
    print("\tNb PAAs:", codebooks.getNbPaaPerSta())
    print("\tNb Sectors:", codebooks.getNbSectorPerStaAntenna())

    scenarioQdInputFolder = os.path.join(scenarioPath, qdRealizationInputFolder)
    qdNbNodes, nbTraces, timeStep, environmentFile, maxReflectionOrder = qdRealization.readQdConfiguration(
        scenarioQdInputFolder, qdConfigurationFile)

    environmentFile = os.path.join(scenarioPath, qdRealizationInputFolder, environmentFile)
    qdScenario = qdRealization.QdScenario(qdNbNodes, nbTraces, timeStep,qdInterpreterConfig)
    nsInput.readNs3Configuration(scenarioPath, "nodesConfiguration.txt", qdScenario)
    nsFolder = os.path.join(scenarioPath, qdRealizationOutputFolder, qdRealizationNsFolder)
    nsResultsFolder = os.path.join(nsFolder, resultsFolder)

    if qdInterpreterConfig.dataMode == 'online' or qdInterpreterConfig.mimoDataMode == "online" or qdInterpreterConfig.mimoDataMode == "preprocessed":
        # If dataMode or mimoDataMode is online (and mimoDataMode preprocessed), we need to load the Q-D channel
        qdChannel = qdRealization.readJSONQdFile(nsFolder, qdFilesFolder, qdJSON, qdInterpreterConfig, qdScenario.nbNodes)
        qdScenario.qdChannel = qdChannel


    if qdInterpreterConfig.slsEnabled:
        slsResultsPath = os.path.join(nsResultsFolder,slsFolder)
        nsInput.readNsSlsResults(slsResultsPath, "nodesConfiguration.txt", qdScenario)
        if qdInterpreterConfig.dataMode == 'preprocessed':
            # User wants to use preprocessed mode - The Oracle precomputes all the SLS results if needed
            slsPath = os.path.join(scenarioPath, preprocessedFolder, slsFolder)
            if os.path.exists(slsPath) and qdInterpreterConfig.forceSlsDataRegeneration == 0:
                print("The preprocessed SLS data have already been generated - Just import them")
                # Read the preprocessed data
                preprocessedSlsData, preprocessedAssociationData, dataIndex = loadPreprocessedData(qdScenario, codebooks)

                if qdInterpreterConfig.forcePlotsRegeneration == 1:
                    # User wants to regenerate the plots
                    plotPreprocessedData(qdScenario, preprocessedAssociationData, codebooks)
                qdChannel = None
            else:
                if not os.path.exists(slsPath):
                    # Data have not been previously preprocessed
                    print("The preprocessed SLS data do not exist - Generate them")
                    os.makedirs(slsPath)
                else:
                    # The user forced the preprocessing of the data
                    print("Regenerate the SLS preprocessed data")

                # We need to load the Q-D files to generate the data
                qdChannel = qdRealization.readJSONQdFile(nsFolder, qdFilesFolder, qdJSON, qdInterpreterConfig,qdScenario.nbNodes)
                preprocessedSlsData, preprocessedAssociationData, dataIndex = preprocessData(qdScenario, qdChannel,
                                                                                             txParam, nbSubBands, codebooks)
                # We force to generate the plots in this case as the data might have change
                plotPreprocessedData(qdScenario, preprocessedAssociationData, codebooks)
        elif qdInterpreterConfig.dataMode == 'online':
            print("Online Mode")
            # Online mode
            # User wants to use Online mode - The Oracle will compute the SLS results on the fly
            # This mode can be enabled only when the visualizer is used
            if not useVisualizer:
                logger.critical(
                    "Online Mode Activated but visualizer not used - Please change the mode used or activate the visualizer ")
                exit()
            preprocessedSlsData = None
            preprocessedAssociationData = None
            dataIndex = None
        elif qdInterpreterConfig.dataMode == 'none':
            # User does not want to deal with SLS data (mainly just to check the output of the Q-D realization software)
            preprocessedSlsData = None
            preprocessedAssociationData = None
            dataIndex = None
            qdChannel = None
            pass
        qdScenario.preprocessedSlsData = preprocessedSlsData
        qdScenario.preprocessedAssociationData = preprocessedAssociationData
        qdScenario.dataIndex = dataIndex


    if qdInterpreterConfig.mimo != "none":
        # MIMO is enabled
        # Try to load the results and compute the results depending on the type of MIMO and MIMO data mode
        # Type of MIMO can be: Beamtracking, SU-MIMO or MU-MIMO
        # MIMO data mode can be:
        # - preprocessed: The results are precomputed by the Oracle Mode
        # - online: The results will be computed on-the-fly by the Oracle Mode
        print("************************************************")
        print("*                   MIMO                       *")
        print("************************************************")
        if qdInterpreterConfig.mimo == "beamTracking":
            # Load the beamTracking results provided by the NIST IEEE 802.11ay PHY software
            beamTrackingResultsFolder = os.path.join(scenarioPath, qdRealizationOutputFolder,resultsFolder,beamTrackingFolder)
            analogBeamTrackingFile = "analogBT.csv"
            digitalCombinerFile = "digitalCombiner.json"
            digitalPrecoderFile = "digitalPrecoder.json"
            analogBeamTrackingMimoResults, qdScenario.maxSupportedStreams = qdRealization.readAnalogBeamTrackingResult(beamTrackingResultsFolder, analogBeamTrackingFile)
            digitalCombinerWeights = qdRealization.readDigitalCombiner(beamTrackingResultsFolder,digitalCombinerFile)
            digitalPrecoderWeights = qdRealization.readDigitalPrecoder(beamTrackingResultsFolder,digitalPrecoderFile)
            qdScenario.beamTrackingResults = BeamTrackingResults(analogBeamTrackingMimoResults,qdScenario.maxSupportedStreams,digitalCombinerWeights,digitalPrecoderWeights)
            print("Beamtracking results: Available")
        elif qdInterpreterConfig.mimo == "suMimo":
            # For now, codebook is only usable with one codebook combination due to how it is currently implemented in ns-3
            # The SU-MIMO could work with any codebook with minimal effort
            # This is due to the fact that the SU-MIMO implementation was done in parallel in ns-3 and in the Q-D interpreter
            # Initially, refined AWV were supposed to be used for the MIMO training and it was not achieved this way in ns-3
            # The check condition could be less harsh as it could work theoriticaly with any number of antennas
            # TODO Implement generic behavior if requested
            if codebookApName == "ura_28x_mimo_2x2_27sectors.txt" and codebookStaName == "ura_28x_mimo_2x2_27sectors.txt":
                pass
            else:
                logger.critical(
                    "Right now, SU-MIMO can work only with codebooks set as CODEBOOK_URA_AP_28x_AzEl_MIMO_2x2_27 for AP and CODEBOOK_URA_AP_28x_AzEl_MIMO_2x2_27 for STA ")
                exit()

            # The maximum number of streams depends from the maximum number of PAAs
            qdScenario.maxSupportedStreams = max(codebooks.getNbPaaPerAp(),
                                      codebooks.getNbPaaPerSta()) - 1
            # Try to read the results from ns-3
            qdScenario.nsSuMimoResults = nsInput.readNs3SuMimoResults(nsResultsFolder, suMimoFilePrefix, qdScenario)
            if qdScenario.nsSuMimoResults!= None:
                print("ns-3 SU-MIMO Results: Available")
            else:
                print("ns-3 SU-MIMO Results: Not Available")
            if qdInterpreterConfig.mimoDataMode == "preprocessed":
                suMimoPickledFile = os.path.join(nsResultsFolder,"suMimoResults.p")
                if os.path.exists(suMimoPickledFile):
                    # Try to load the preprocessed SU-MIMO results
                    print("SU-MIMO preprocessed data already generated - Just load them")
                    qdScenario.oracleSuMimoResults = pickle.load(open(suMimoPickledFile, "rb"))
                else:
                    print("SU-MIMO preprocessed data do not exist - Generate them")
                    # We are right now precomputing the SU-MIMO results just for one pair with
                    # the MIMO initiator ID set to 0 and the MIMO responder set to 1
                    # TODO change this behavior if needed
                    fakeInitiatorId = 0
                    fakeResponderId = 1
                    qdScenario.oracleSuMimoResults = preprocessCompleteSuMimo(fakeInitiatorId, fakeResponderId, qdChannel,
                    qdScenario, txParam,
                    nbSubBands, codebooks,suMimoPickledFile)
        elif qdInterpreterConfig.mimo == "muMimo":
            # For now, codebook is only usable with one codebook combination due to how it is currently implemented in ns-3
            # The MU-MIMO could work with any codebook with minimal effort
            # This is due to the fact that the MU-MIMO implementation was done in parallel in ns-3 and in the Q-D interpreter
            # Initially, refined AWV were supposed to be used for the MIMO training and it was not achieved this way in ns-3
            # The check condition could be less harsh as it could work theoretically with any number of antennas
            # TODO Implement generic behavior if requested
            if codebookApName == "ura_28x_mimo_2x2_27sectors.txt" and codebookStaName == "ura_28x_siso_27sectors.txt":
                pass
            else:
                logger.critical(
                    "Right now, MU-MIMO can work only with codebooks set as ura_28x_mimo_2x2_27sectors for AP and ura_28x_siso_27sectors for STA ")
                exit()

            # The maximum number of streams depends from the maximum number of PAAs
            qdScenario.maxSupportedStreams = max(codebooks.getNbPaaPerAp(),
                                      codebooks.getNbPaaPerSta()) - 1  # We get the maximum number of supported streams
            qdScenario.nsMuMimoResults = nsInput.readNs3MuMimoResults(nsResultsFolder, muMimoInitiatorPrefix, muMimoResponderPRefix,
                                                          qdScenario)
            if qdScenario.nsMuMimoResults != None:
                print("ns-3 MU-MIMO Results: Available")
            else:
                print("ns-3 MU-MIMO Results: Not Available")
            if qdInterpreterConfig.mimoDataMode == "preprocessed":
                # Try to load the preprocessed MU-MIMO results
                muMimoPickledFile = os.path.join(nsResultsFolder, "muMimoResults.p")
                if os.path.exists(muMimoPickledFile):
                    print("MU-MIMO preprocessed data already generated - Just load them")
                    qdScenario.oracleMuMimoResults = pickle.load(open(muMimoPickledFile, "rb"))
                else:
                    print("MU-MIMO preprocessed data do not exist - Generate them")
                    # We are right now precomputing the MU-MIMO results just for one MIMO initiator
                    # and with a MIMO group set to 1
                    # TODO change this behavior if needed
                    fakeInitiatorId = 0
                    fakeGroupId = 1
                    qdScenario.oracleMuMimoResults = preprocessCompleteMuMimo(fakeInitiatorId, fakeGroupId, qdChannel,
                                                                              qdScenario, txParam,
                                                                              nbSubBands, codebooks,muMimoPickledFile)
    else:
        # MIMO Not Enabled
        qdScenario.maxSupportedStreams = 0

    if useVisualizer:
        # Process the files used by the visualizer
        scenarioQdVisualizerFolder = os.path.join(scenarioPath, qdRealizationOutputFolder,
                                                  qdRealizationVisualizerFolder)
        nbJsonFileToLoad = 3
        fileLoaded = 0
        print("Load JSON files needed for the visualization configuration")
        printProgressBarWithoutETA(fileLoaded, nbJsonFileToLoad, prefix='',
                                   suffix='Complete', length=50)
        qdRealization.readJSONPAAPositionFile(scenarioQdVisualizerFolder, paaPositionJSON,
                                              qdScenario)  # TODO See if it needs to be pickled
        fileLoaded += 1
        printProgressBarWithoutETA(fileLoaded, nbJsonFileToLoad,
                                   prefix='', suffix='Complete',
                                   length=50)
        qdRealization.readJSONMPCFile(scenarioQdVisualizerFolder, mpcJSON)  # TODO See if it needs to be pickled
        fileLoaded += 1
        printProgressBarWithoutETA(fileLoaded, nbJsonFileToLoad,
                                   prefix='', suffix='Complete',
                                   length=50)
        qdRealization.readJSONNodesPositionFile(scenarioQdVisualizerFolder, nodePositionJSON, qdScenario)
        fileLoaded += 1
        printProgressBarWithoutETA(fileLoaded, nbJsonFileToLoad,
                                   prefix='', suffix='Complete',
                                   length=50)

        # Sensing
        if qdInterpreterConfig.sensing:
            # Sensing is enabled - Read the targets positions and MPCs and doppler range if available
            qdRealization.readTargetJSONPositionFile(scenarioQdVisualizerFolder, targetPositionJSON, qdScenario)
            qdRealization.readTargetConnectionFile(scenarioQdVisualizerFolder, qdScenario)
            qdRealization.readJSONTargetMPCFile(scenarioQdVisualizerFolder, targetMpcJSON, qdScenario)
            qdRealization.readDoppler(scenarioQdVisualizerFolder,dopplerAxisFile,dopplerRangeFile)


    return qdScenario, txParam, codebooks, environmentFile, maxReflectionOrder

def loadCodebookConfiguration(scenarioFolder):
    """Read the codebook configuration file if it exists

    Parameters
    ----------
    scenarioFolder : string
        The Scenario folder

    Returns
    -------
    codebookApFile: string
        Filename for the AP codebook
    codebookStaFile: string
        FileName for the STA codebook
    """
    filename = os.path.join(scenarioFolder, "codebookConfiguration.csv")
    if os.path.exists(filename):
        with open(filename) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                codebookApName = row['CODEBOOK_AP']
                codebookStaName = row['CODEBOOK_STA']
                print("Codebook Configuration File Found")
                print("\tCodebook AP:", codebookApName)
                print("\tCodebook STA:", codebookStaName)
                return codebookApName, codebookStaName

    else:
        print("No Codebook Configuration File - Set it to default codebook")
        print("\tCodebook AP:", defaultApCodebook)
        print("\tCodebook STA:", defaultStaCodebook)
        codebookApName = defaultApCodebook
        codebookStaName = defaultStaCodebook
        return codebookApName, codebookStaName

def saveData(dataFrame, dataPath, dataFile):
    fileToSave = os.path.join(dataPath, dataFile)
    dataFrame.to_csv(fileToSave, index=False, header=True)

