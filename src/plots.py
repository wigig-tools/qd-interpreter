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
"""Module used to plot the preprocessed data
"""
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm
from matplotlib.colors import ListedColormap
from matplotlib.font_manager import FontProperties

import globals
import qdRealization

class OraclePlot:
    """A class to facilitate the creation of simple plots.

   Attributes
   ----------
   xValues : numerical
       The x plot values

   yValues : numerical
       The y plot values

   destFolder : string
       The folder where to save the plot

   fileName: string
       The filename of the plot to save

   title: string
       The title to use for the plot

   xLegend: string
       The legend to use for x axis

   yLegend: string
       The legend to use for y axis
    """

    def __init__(self, xValues, yValues, destFolder, fileName, title, xLegend, yLegend):
        self.xValues = xValues
        self.yValues = yValues
        self.destFolder = destFolder
        self.fileName = fileName
        self.title = title
        self.xLegend = xLegend
        self.yLegend = yLegend


def plotOneMetric(anOraclePlot, maxX):
    """Plot and save the curve associated to anOraclePlot plot object

   Parameters
   ----------
   anOraclePlot : Class OraclePlot
       The object containing the data to plot as well as extra-information as the legend, title, and destination
   maxX : float
       The x limit of the plot to create
   """
    plt.plot(anOraclePlot.xValues, anOraclePlot.yValues)
    plt.xlabel(anOraclePlot.xLegend)
    plt.ylabel(anOraclePlot.yLegend)
    plt.title(anOraclePlot.title)
    plt.grid(True)
    plt.xlim(0, maxX)  # TODO Put a default value and apply the limit just if maxX is not the default value
    destinationPath = os.path.join(globals.scenarioPath, globals.graphFolder, anOraclePlot.destFolder)
    if not os.path.exists(destinationPath):
        os.makedirs(destinationPath)

    fileToSave = os.path.join(destinationPath, anOraclePlot.fileName + ".png", )
    plt.savefig(fileToSave)
    plt.clf()


def plotSlsMetrics(qdScenario,codebooks):
    """Generate the SLS plots (Best Sectors and Rx Power for best sector for every Tx/rx/PaaTx/PaaRx tuples)

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    codebooks : Codebooks class
        Class containing the directionality of the sectors and quasi-omni pattern for the STAs and APs
    """
    dataPath = os.path.join(globals.scenarioPath, globals.dataFolder)

    nbNodesPermutations = globals.nPr(qdScenario.nbNodes,
                                      2)  # Total number of nodes permutations (used for progress bar)
    numberOfPair = 0
    globals.printProgressBarWithoutETA(0, nbNodesPermutations, prefix='Progress:', suffix='Complete', length=50)
    for txId in range(qdScenario.nbNodes):
        # Iterate all the Tx nodes
        for rxId in range(qdScenario.nbNodes):
            # Iterate all the Rx nodes
            if txId != rxId:
                for txAntennaID in range(codebooks.getNbPaaNode(qdScenario.getNodeType(txId))):
                    # Iterate over all the Tx PAAs
                    for rxAntennaID in range(codebooks.getNbPaaNode(qdScenario.getNodeType(rxId))):
                        # Iterate over all the Rx PAAs

                        # Plot Rx Power curves for I-Txss
                        rxPowerItxssFile = "RxPower" + "Node" + str(txId) + "Node" + str(rxId) + "PAATx" + str(
                            txAntennaID) + "PAARx" + str(rxAntennaID) + ".csv"
                        fileName = os.path.join(dataPath, os.path.join(globals.slsFolder, globals.rxPowerItxssFolder),
                                                rxPowerItxssFile)
                        data = pd.read_csv(fileName)
                        # Just get the column of interest
                        df = pd.DataFrame(data, columns=['traceIndex', 'rxPower'])
                        # Plot received power from the best sector
                        xValues = df['traceIndex']
                        yValues = df['rxPower']
                        xLegend = "Trace Index"
                        yLegend = "Received Power (dBm)"
                        titleGraph = "Node:" + str(txId) + " => Node:" + str(rxId) + " PAA Tx:" + str(
                            txAntennaID) + " PAA Rx:" + str(rxAntennaID)

                        rxItxssPlot = OraclePlot(xValues, yValues,
                                                 os.path.join(globals.slsFolder, globals.rxPowerItxssFolder),
                                                 rxPowerItxssFile, titleGraph, xLegend, yLegend)
                        plotOneMetric(rxItxssPlot, qdScenario.nbTraces)

                        # Plot Best I-TXSS Sector
                        bestItxssSectorFile = "BestSector" + "Node" + str(txId) + "Node" + str(rxId) + "PAATx" + str(
                            txAntennaID) + "PAARx" + str(rxAntennaID) + ".csv"
                        fileName = os.path.join(dataPath,
                                                os.path.join(globals.slsFolder, globals.bestSectorItxssFolder),
                                                bestItxssSectorFile)
                        data = pd.read_csv(fileName)
                        df = pd.DataFrame(data, columns=['traceIndex', 'sector'])
                        xValues = df['traceIndex']
                        yValues = df['sector']
                        xLegend = "Trace Index"
                        yLegend = "Best Sector"
                        titleGraph = "Node:" + str(txId) + " => Node:" + str(rxId) + " PAA Tx:" + str(
                            txAntennaID) + " PAA Rx:" + str(rxAntennaID)
                        bestItxssSectorPlot = OraclePlot(xValues, yValues,
                                                         os.path.join(globals.slsFolder, globals.bestSectorItxssFolder),
                                                         bestItxssSectorFile, titleGraph, xLegend,
                                                         yLegend)
                        plotOneMetric(bestItxssSectorPlot, qdScenario.nbTraces)
                        numberOfPair += 1
                        globals.printProgressBarWithoutETA(numberOfPair, nbNodesPermutations, prefix='Progress:',
                                                           suffix='Complete',
                                                           length=50)


def plotMobilityMetrics(qdScenario):
    """Plot the STAs trajectories as well as the heatmap (using hexbin) of the mobility of the STAs

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    """
    scenarioQdVisualizerFolder = os.path.join(globals.scenarioPath, globals.qdRealizationOutputFolder,
                                              globals.qdRealizationVisualizerFolder)
    qdRealization.readJSONNodesPositionFile(scenarioQdVisualizerFolder, globals.nodePositionJSON,qdScenario)

    destinationPath = os.path.join(globals.scenarioPath, globals.graphFolder, "Mobility")
    if not os.path.exists(destinationPath):
        os.makedirs(destinationPath)

    ################################
    #  Plot STA Trajectory         #
    ################################
    fig, ax = plt.subplots(1, figsize=(8, 6))

    # Set the title for the figure
    color = ['b', 'g', 'r', 'c', 'm', 'y', 'b', 'g', 'r', 'c', 'm', 'y']
    style = ['solid', 'solid', 'solid', 'solid', 'solid', 'solid', 'dashed', 'dashed', 'dashed', 'dashed', 'dashed',
             'dashed']

    # Get AP coordinates
    for apId in range(qdScenario.nbAps):
        # We consider that the APs do not move so we get only the coordinate of the first trace
        apCoordinate = np.transpose(qdScenario.getNodePosition(0,apId))
        ax.plot(apCoordinate[0], apCoordinate[1], 'k*', markersize=10)
        plt.text(apCoordinate[0], apCoordinate[1], 'AP' + str(apId), horizontalalignment='center')

    for staId in range(qdScenario.nbAps, qdScenario.nbNodes):
        # Display Sta Trajectory
        staCoordinates = np.transpose(qdScenario.getNodeAllPositions(staId))

        ax.plot(staCoordinates[0], staCoordinates[1], color[staId - qdScenario.nbAps], linewidth=0.5,
                linestyle=style[staId - qdScenario.nbAps],
                label="STA" + str(staId))

        # Display the STA starting Point
        ax.plot(staCoordinates[0, 0], staCoordinates[1, 0], 'r*', markersize=10)
        plt.text(staCoordinates[0, 0], staCoordinates[1, 0], 'Start', horizontalalignment='center')

        # Display the STA End Point
        ax.plot(staCoordinates[0, -1], staCoordinates[1, -1], 'r*', markersize=10)
        plt.text(staCoordinates[0, -1], staCoordinates[1, -1], 'End', horizontalalignment='center')

    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    fontP = FontProperties()
    fontP.set_size('xx-small')
    plt.legend(bbox_to_anchor=(1.04, 1), loc='upper left', prop=fontP)
    fileToSave = os.path.join(destinationPath, "STAsMobility.pdf")
    plt.savefig(fileToSave)
    plt.cla()
    plt.close(plt.gcf())

    ################################
    #  Plot STA location heatmap   #
    ################################
    # Get all STA coordinates
    staCoordinates = qdScenario.getAllSTAsAllPositions()
    staCoordinates = np.transpose(staCoordinates, (1, 0, 2))

    # Prepare the data as expected by hexbin
    xOrig = staCoordinates[0].flatten()
    yOrig = staCoordinates[1].flatten()
    fig, ax = plt.subplots()
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")

    # Create a custom colorbar to have white color in the first position
    viridis = cm.get_cmap('jet', 256)
    newcolors = viridis(np.linspace(0, 1, 256))
    white = np.array([1, 1, 1, 1])
    newcolors[:1, :] = white
    customCm = ListedColormap(newcolors)

    # Draw the hexbin representation
    img = plt.hexbin(xOrig, yOrig, gridsize=10, cmap=customCm, edgecolors='k')

    nbDiscreteValuesCm = 20
    dataHexBin = img.get_array()  # Get the data of the hexbin to create a discret colormap based on the maximum hexbin value
    # define the bins and normalize
    bounds = np.linspace(1, max(dataHexBin), nbDiscreteValuesCm)
    bounds = np.append([0], bounds, axis=0)

    norm = mpl.colors.BoundaryNorm(bounds, customCm.N)
    # Create the corresponding colorbar
    cbar = plt.colorbar(img, ax=ax,
                        spacing='uniform', ticks=bounds, boundaries=bounds, format='%1i')
    cbar.set_label('Number of STAs in one hexbin')

    # Add the APs to the figure
    for apId in range(qdScenario.nbAps):
        # We consider that the APs do not move so we get only the coordinate of the first trace
        apCoordinates = np.transpose(qdScenario.getNodePosition(0, apId))
        ax.plot(apCoordinates[0], apCoordinates[1], 'k*', markersize=10)
        plt.text(apCoordinates[0], apCoordinates[1], 'AP' + str(apId), horizontalalignment='center')
    fileToSave = os.path.join(destinationPath, "AllStasHexBinHeatmap.pdf")
    plt.savefig(fileToSave)


def plotAssociationMetrics(qdScenario,preprocessedAssociationData):
    """Plot the STAs associated per AP trajectory and heatmap

   Parameters
   ----------
   qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
   preprocessedAssociationData : Dict
       The dictionary containing the AP to which a STA is associated (also the power and the best sector) for a given trace (key: (staId,traceIndex)
    """
    destinationPath = os.path.join(globals.scenarioPath, globals.graphFolder, "Association")
    if not os.path.exists(destinationPath):
        os.makedirs(destinationPath)

    # Get all Nodes X and Y coordinates
    nodesCoordinates = qdScenario.getAllNodesAllPositions()
    nodesCoordinates = np.transpose(nodesCoordinates, (1, 0, 2))
    xNodes = np.asarray(nodesCoordinates[0])
    yNodes = np.asarray(nodesCoordinates[1])
    # dicCoordinatesX and dicCoordinatesY will contain the coordinates of the STA connected to a given AP (key of the dict)
    dicCoordinatesX = {new_list: [] for new_list in range(qdScenario.nbAps)}
    dicCoordinatesY = {new_list: [] for new_list in range(qdScenario.nbAps)}

    nbTotalStaConnectedToAp = {}
    for i in range(qdScenario.nbAps):
        nbTotalStaConnectedToAp[i] = 0

    # Get the coordinates and the number of STAs connected to an AP
    for staId in range(qdScenario.nbAps, qdScenario.nbNodes):
        for traceIndex in range(qdScenario.nbTraces):
            apConnectedTo = preprocessedAssociationData[staId, traceIndex][1]
            nbTotalStaConnectedToAp[apConnectedTo] += 1
            dicCoordinatesX[apConnectedTo].append(xNodes[traceIndex][staId])
            dicCoordinatesY[apConnectedTo].append(yNodes[traceIndex][staId])

    sigmas = [0, 15]
    for i in range(qdScenario.nbAps):
        fig, axs = plt.subplots(2)
        for ax, s in zip(axs.flatten(), sigmas):
            if s == 0:
                ax.plot(dicCoordinatesX[i], dicCoordinatesY[i], 'k.', markersize=0.1)
                for apId in range(qdScenario.nbAps):
                    apCoordinates = np.transpose(qdScenario.getNodePosition(0, apId))
                    ax.plot(apCoordinates[0], apCoordinates[1], 'k*', markersize=1)
                    ax.text(apCoordinates[0], apCoordinates[1], 'AP' + str(apId), horizontalalignment='center')
                    ax.tick_params(labelsize=5)  # Reduce tick size
                ax.set_title("Location of STAs associated to AP:" + str(i),fontsize=9)
            else:
                xOrig = np.asarray(dicCoordinatesX[i]).flatten()
                yOrig = np.asarray(dicCoordinatesY[i]).flatten()
                for apId in range(qdScenario.nbAps):
                    apCoordinates = np.transpose(qdScenario.getNodePosition(0, apId))
                    ax.plot(apCoordinates[0], apCoordinates[1], 'k*', markersize=1)
                    ax.text(apCoordinates[0], apCoordinates[1], 'AP' + str(apId), horizontalalignment='center')
                viridis = cm.get_cmap('jet', 256)
                newcolors = viridis(np.linspace(0, 1, 256))
                white = np.array([1, 1, 1, 1])
                newcolors[:1, :] = white
                customCm = ListedColormap(newcolors)

                # Draw the hexbin representation
                img = plt.hexbin(xOrig, yOrig, gridsize=10, cmap=customCm, edgecolors='k', linewidths=0.1)

                nbDiscreteValuesCm = 20
                dataHexBin = img.get_array()  # Get the data of the hexbin to create a discret colormap based on the maximum hexbin value
                bounds = np.linspace(1, max(dataHexBin), nbDiscreteValuesCm)
                bounds = np.append([0], bounds, axis=0)

                norm = mpl.colors.BoundaryNorm(bounds, customCm.N)
                # Create the corresponding colorbar
                cbar = plt.colorbar(img, ax=ax, norm=norm,
                                    spacing='uniform', ticks=bounds, boundaries=bounds, format='%1i')
                cbar.set_label('Number of STAs in one hexbin')
                cbar.set_label('Number of STAs in one hexbin')
                cbar.ax.tick_params(labelsize=5)  # Reduce tick size
                ax.tick_params(labelsize=5)  # Reduce tick size
                ax.set_title("Heatmap of STAs associated to AP:" + str(i),fontsize=9)

        fileToSave = os.path.join(destinationPath, "StaConnectedToAP" + str(i) + ".pdf")
        plt.savefig(fileToSave)


def plotPreprocessedData(qdScenario,preprocessedAssociationData,codebooks):
    """Plot the preprocessed data (SLS, Mobility, and association)

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    preprocessedAssociationData : Dic
       The dictionary containing the AP to which a STA is associated (also the power and the best sector) for a given trace (key: (staId,traceIndex)
    codebooks : Codebooks class
        Class containing the directionality of the sectors and quasi-omni pattern for the STAs and APs
    """
    print("Plot the preprocessed data")
    plotSlsMetrics(qdScenario,codebooks)
    plotMobilityMetrics(qdScenario)
    plotAssociationMetrics(qdScenario,preprocessedAssociationData)
