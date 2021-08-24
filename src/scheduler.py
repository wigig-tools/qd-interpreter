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


import math
import os
import random
from enum import Enum

import matplotlib.pyplot as plt
import numpy as np

import globals
import plots
import qdPropagationLoss


class StaAssociationMode(Enum):
    """A class to select how are associated the STAs
    """
    BEST_AP = "AssocBestAP"  # The STAs associate to the best AP (in term of Received Power)
    SAME_AP = "AssocSameAP"  # The STAs stay associated to the same AP (by default, the best AP from the first trace)


def createStasAssociation(qdScenario,associationMode, staIds, preprocessedAssociationData):
    """Create the association for the STAs depending on the mode

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)

    associationMode: Enum
        The association mode described in the class StaAssociationMode

    staIds: Numpy array
        The STA IDs to consider for the scheduling

    preprocessedAssociationData : Dic
        The preprocessed association Data

    Returns
    -------
    apConnectedStas: Dic
        Contains the ID of the STAs connected to an AP
    """
    apConnectedStas = {}
    print("Create STAs association to APs for all the traces")
    globals.printProgressBarWithoutETA(0, qdScenario.nbTraces, prefix='Progress:', suffix='Complete', length=50)
    for traceIndex in range(qdScenario.nbTraces):
        # Iterate over all the traces
        for i in staIds:
            # Iterate over all the STAs to get the AP to which they are associated
            if associationMode == StaAssociationMode.SAME_AP:
                # The STA will always stay associated to the AP they were associated at the first trace
                idApStaAssociated = preprocessedAssociationData[(i, 0)][1]  # Trace always 0
            else:
                # The STA associates with the AP yielding the highest received power for every trace
                idApStaAssociated = preprocessedAssociationData[(i, traceIndex)][1]
            if (idApStaAssociated, traceIndex) not in apConnectedStas:
                # It is the first STA associated to the AP for this trace
                apConnectedStas[(idApStaAssociated, traceIndex)] = []
                # Add the id of the STA to the dictionary holding the STA connected to each AP
                apConnectedStas[(idApStaAssociated, traceIndex)].append(i)
            else:
                # Add the id of the STA to the dictionary holding the STA connected to each AP
                apConnectedStas[(idApStaAssociated, traceIndex)].append(i)
        globals.printProgressBarWithoutETA(traceIndex + 1, qdScenario.nbTraces, prefix='Progress:', suffix='Complete',
                                           length=50)
    return apConnectedStas


def createDownlinkScheduling(qdScenario,apConnectedStas, folderPrefix):
    """Create the scheduling (and a plot for the scheduling) for downlink data transmission (from APs to STAs)
    The amount of time scheduled for a STA is set to the duration of a trace divided by the number of STAs associated to the AP

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    apConnectedStas : Dict
        Contains the ID of the STAs connected to an AP
    folderPrefix : string
        The folder prefix to save the figures

    Returns
    -------
    schedulingDic: Dic
        Contains each AP scheduling
    nbStasConnectedToAps: Numpy array
        Number of STA connected to a given AP for all the traces
    """
    # TODO Should include if we want to try with a subset of STA
    NO_TRANSMISSION = qdScenario.nbNodes  # By default, we set no transmission to the total number of nodes
    nbStasConnectedToAps = np.zeros((qdScenario.nbAps, qdScenario.nbTraces))
    fig, ax = plt.subplots(1, figsize=(8, 6))
    schedulingDic = {}
    # SchedulingDic is using AP ID as a key
    # It contains every allocation for the AP to STAs transmissions
    # Content: Beginning Allocation, ID of the STAs the AP is transmitting to

    # Iterate over all the APs and all the traces to:
    # - Determine the amount of time to allocate to a STA transmission for the STAs associated with a given AP for a given trace
    # - Order randomly the downlink transmission to every STA associated to a given AP for a given trace
    for idAp in range(qdScenario.nbAps):
        transmissionIntervals = []
        idApDownlink = [idAp, idAp + 1]
        idStaDownlink = []
        averageStaConnected = 0
        nbSample = 0
        traceList = []
        for traceIndex in range(qdScenario.nbTraces):
            if (idAp, traceIndex) in apConnectedStas:
                # There is at least one STA associated to the AP for a given trace
                nbStaConnectedToAp = len(apConnectedStas[idAp, traceIndex])
                nbStasConnectedToAps[idAp, traceIndex] = int(nbStaConnectedToAp)
                averageStaConnected += nbStaConnectedToAp
                nbSample += 1
                # Compute the duration of a transmission allocated to each STA
                timeStep = qdScenario.timeStep / nbStaConnectedToAp
                for allocationSta in range(nbStaConnectedToAp):
                    # For every STA, compute the beginning of the transmission
                    beginInterval = traceIndex * qdScenario.timeStep + timeStep * allocationSta
                    transmissionIntervals.append(beginInterval)
                    # Select randomly one of the STA to perform the transmission
                    idStaDownlink.append(apConnectedStas[(idAp, traceIndex)].pop(
                        random.randrange(len(apConnectedStas[(idAp, traceIndex)]))))
                    traceList.append(traceIndex)
            else:
                # No STA associated to the AP for the given trace
                beginInterval = traceIndex * qdScenario.timeStep
                transmissionIntervals.append(beginInterval)
                # Color the scheduling to white
                idStaDownlink.append(NO_TRANSMISSION)
                nbStasConnectedToAps[idAp, traceIndex] = 0
                nbSample += 1
                traceList.append(traceIndex)

        # We need to add a closing value as we are adding only the beginning interval values
        transmissionIntervals.append(qdScenario.nbTraces * qdScenario.timeStep)
        idStaDownlink.append(NO_TRANSMISSION)
        traceList.append(qdScenario.nbTraces)
        transmissionIntervals = np.asarray(transmissionIntervals)
        idApDownlink = np.asarray(idApDownlink)
        idStaDownlink = np.asarray(idStaDownlink)
        traceList = np.asarray(traceList)
        schedulingDic[idAp] = (transmissionIntervals, idStaDownlink, traceList)
        idStaDownlink = idStaDownlink.reshape(len(idApDownlink) - 1, len(transmissionIntervals))
        c = ax.pcolormesh(transmissionIntervals, idApDownlink, idStaDownlink, cmap='gnuplot2', vmin=qdScenario.nbAps,
                          vmax=qdScenario.nbNodes)

    # Create a visualization for the downlink scheduling (svg format)
    bounds = np.arange(qdScenario.nbAps, qdScenario.nbNodes + 1)
    bounds = bounds.astype(np.str)
    bounds[-1] = "No transmission"
    bounds = bounds.astype(np.str)
    # TODO Discretize the colorbar
    cbar = plt.colorbar(c, ax=ax)
    cbar.ax.locator_params(nbins=qdScenario.nbStas + 1)
    cbar.ax.set_yticklabels(bounds)
    cbar.set_label('ID of the STA')
    plt.xlabel("Time (s)")
    plt.ylabel("AP ID")
    # Center the Y Tick label
    tick_limit = qdScenario.nbAps
    ax.yaxis.set_ticks([0, tick_limit])
    # offset all ticks between limits
    myticklabels = np.arange(qdScenario.nbAps)
    offset = 1
    ax.yaxis.set(ticks=np.arange(offset / 2., tick_limit, offset), ticklabels=myticklabels)
    plt.title("Downlink Transmission Scheduling")
    destinationPath = os.path.join(globals.scenarioPath, globals.graphFolder, folderPrefix, globals.schedulingFolder)
    if not os.path.exists(destinationPath):
        os.makedirs(destinationPath)

    figureFile = "Scheduling"
    fileToSave = os.path.join(destinationPath, figureFile + ".svg", )
    plt.savefig(fileToSave)
    plt.cla()
    plt.close(plt.gcf())

    # Create a visualization for the evolution of the number of STAs connected to the AP
    for idAp in range(qdScenario.nbAps):
        xValues = np.arange(qdScenario.nbTraces)
        yValues = nbStasConnectedToAps[idAp]
        xLegend = "Trace"
        yLegend = "Number of STAs connected"
        titleGraph = "Number of STAs connected to AP:" + str(idAp)
        fileToSave = "ConnectivityAP" + str(idAp)
        destFolder = os.path.join(folderPrefix, globals.associationFolder)
        nbStaConnectedToApPlot = plots.OraclePlot(xValues, yValues,
                                                  destFolder,
                                                  fileToSave, titleGraph, xLegend,
                                                  yLegend)
        plots.plotOneMetric(nbStaConnectedToApPlot, qdScenario.nbTraces)

    return schedulingDic, nbStasConnectedToAps


def transmitData(qdScenario,schedulingDic, nbStasConnectedToAps, associationMode, folderPrefix, preprocessedSlsData, txParam,
                 dataIndex):
    """Proceed to the data transmission according to the scheduling

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    schedulingDic: Dic
        Contains each AP scheduling
    nbStasConnectedToAps: Numpy array
        Number of STA connected to a given AP for all the traces
    associationMode: Enum
        The association mode described in the class StaAssociationMode
    folderPrefix : string
        The folder prefix to save the figures
    preprocessedSlsData : SlsResults class
        The preprocessed data for the SLS Phase
    txParam: TxParam class
        Parameters associated to the transmissions
    dataIndex: Dic
        Used to reconstruct the index of the preprocessed data
    """
    NO_TRANSMISSION = qdScenario.nbNodes  # TODO Two time in the code - To remove
    ###################################
    #     INTERFERENCE COMPUTATION     #
    ###################################
    for apId in range(qdScenario.nbAps):
        # Iterate over each AP to compute the SNR and SINR of its downlink transmissions (taking into account other potential interfering AP transmissions)
        snrDownlinkTx = []
        timeSnrSinr = []
        sinrDownlinkTx = []
        timeCapacity = []
        capacityDownlinkTx = []
        sumDownlinkCapacity = 0
        nbDownlinkCapacity = 0

        currentIndexApInterfer = {new_list: 0 for new_list in range(qdScenario.nbAps)}
        currentInterfererEndTransmissions = {}
        currentInterfererReceivers = {}
        apTransmissionsTimeSteps = schedulingDic[apId][0]
        apTransmissionsReceivers = schedulingDic[apId][1]
        apTransmissionsTraces = schedulingDic[apId][2]

        destinationPath = os.path.join(globals.scenarioPath, globals.dataFolder, folderPrefix, globals.capacityFolder)
        if not os.path.exists(destinationPath):
            os.makedirs(destinationPath)

        # Create file to save the capacity for the current AP
        f = open(os.path.join(destinationPath, "AP" + str(apId) + ".csv"), "w")
        f.write("TRACE,AP,STA,SINR(dB),Capacity(Mbps),NBSTAFORAP,TRANSMISSIONTIMESTEP\n")
        globals.printProgressBarWithoutETA(0, len(apTransmissionsTimeSteps) - 1, prefix='Progress:', suffix='Complete',
                                           length=50)
        for indexTimeStep in range(len(apTransmissionsTimeSteps) - 1):
            # Go over every downlink allocations allocated for a given transmitting AP
            currentTransmissionTrace = apTransmissionsTraces[
                indexTimeStep]  # Get the trace corresponding to the timestep
            currentTransmissionReceiver = apTransmissionsReceivers[
                indexTimeStep]  # Get the receiver corresponding to the transmission
            # Look for all the potential AP interferers for this specific timestep and for this specific transmitting AP
            currentTransmissionNbInterferer = 0  # Number of AP interfering with the current transmission
            for apInterferer in range(qdScenario.nbAps):
                # Iterate over the potential AP interferers
                if apId != apInterferer:  # If the interferer is not the AP itself
                    currentInterfererEndTransmissions[apInterferer] = []
                    # Get the timestep of the interferer AP
                    apInterfererTimeSteps = schedulingDic[apInterferer][0]
                    for indexTimeStepInterferer in range(currentIndexApInterfer[apInterferer],
                                                         len(apInterfererTimeSteps) - 1):
                        # Iterate over the timestep interfer list
                        if apTransmissionsTimeSteps[indexTimeStep] < apInterfererTimeSteps[
                            indexTimeStepInterferer + 1] and apInterfererTimeSteps[indexTimeStepInterferer] < \
                                apTransmissionsTimeSteps[indexTimeStep + 1]:
                            currentInterfererReceiver = schedulingDic[apInterferer][1][indexTimeStepInterferer]
                            if currentInterfererReceiver != NO_TRANSMISSION:  # Check if the interfering AP if transmitting
                                # The interfering AP is having a transmission that will interfere with the current AP transmission
                                currentInterfererReceiver = schedulingDic[apInterferer][1][indexTimeStepInterferer]
                                currentTransmissionNbInterferer += 1
                                # Keep the upper bound of the interfering transmission
                                currentInterfererEndTransmissions[apInterferer].append(
                                    apInterfererTimeSteps[indexTimeStepInterferer + 1])
                                # Keep the receiver of the interfering transmission
                                currentInterfererReceivers[(apInterferer, apInterfererTimeSteps[
                                    indexTimeStepInterferer + 1])] = currentInterfererReceiver
                        else:
                            # All the interferer timestep with the current transmission have been computed
                            if apInterfererTimeSteps[indexTimeStepInterferer] > apTransmissionsTimeSteps[
                                indexTimeStep + 1]:
                                # If the upper boundary of an interfer transmission is greater than the end of the current transmission, it means it may interfer later on
                                # so we need to go one timestep back
                                currentIndexApInterfer[apInterferer] = indexTimeStepInterferer - 1
                            else:
                                currentIndexApInterfer[apInterferer] = indexTimeStepInterferer
                            break  # Go to the next interfering AP

            # At that point, we know for a current transmission which are the timesteps of the interferers and which are the interferers
            # The total number of interferences corresponds to the total number of interferences to take into account
            # We must now compute the SNR and SINR (taking into account the interference of the interferers if any)
            nbInterferenceTreated = 0
            rxPowerTransmission = -math.inf  # Initialize the received power
            if currentTransmissionReceiver != NO_TRANSMISSION:
                # Get the current downlink transmission received power
                rxPowerTransmission = preprocessedSlsData.bestSectorRxPowerList[
                    dataIndex[(apId, currentTransmissionReceiver, 0, 0, currentTransmissionTrace)]]
            if rxPowerTransmission == -math.inf:
                #################################################
                #     CASE1: Transmission but no power received #
                #################################################
                # This case happened if no MPC exists between the transmitter and the receiver
                timeSnrSinr.append(apTransmissionsTimeSteps[indexTimeStep])
                snrDownlinkTx.append(np.nan)
                sinrDownlinkTx.append(np.nan)
                timeCapacity.append(apTransmissionsTimeSteps[indexTimeStep])
                capacityDownlinkTx.append(np.nan)
            elif currentTransmissionReceiver == NO_TRANSMISSION:
                ###################################
                #     CASE2: No Transmission    #
                ###################################
                # This case happens when you iterate through a transmission allocation where no transmission was scheduled
                timeSnrSinr.append(apTransmissionsTimeSteps[indexTimeStep])
                snrDownlinkTx.append(np.nan)
                sinrDownlinkTx.append(np.nan)
                timeCapacity.append(apTransmissionsTimeSteps[indexTimeStep])
                capacityDownlinkTx.append(np.nan)
            elif currentTransmissionNbInterferer == 0:
                ###############################################
                #     CASE3: Transmission and No Interferer   #
                ###############################################
                # This case happens when no interference occurred for the current transmission
                # Compute SNR and SINR
                snrdB = 10 * math.log10(qdPropagationLoss.DbmtoW(rxPowerTransmission) / (
                    txParam.getNoise()))
                sinrdB = snrdB  # No interferer so SINR = SNR
                timeSnrSinr.append(apTransmissionsTimeSteps[indexTimeStep])  # Keep the time
                snrDownlinkTx.append(snrdB)  # Keep the SNR
                sinrDownlinkTx.append(sinrdB)  # Keep the SINR

                # Compute Capacity using Shannon - Hartley
                # We divide the obtained capacity by the number of users scheduled in the transmitting timestep
                capacity = 2.16 * 1e9 * (np.log2(1 + 10 ** ((sinrdB) / 10))) / nbStasConnectedToAps[
                    apId, int(currentTransmissionTrace)]
                timeCapacity.append(apTransmissionsTimeSteps[indexTimeStep])
                capacityDownlinkTx.append(capacity / 1e6)
                sumDownlinkCapacity += capacity / 1e6  # Use to compute the average capacity
                nbDownlinkCapacity += 1  # Use to compute the average capacity
                # Write the capacity data
                f.write(str(currentTransmissionTrace) + "," + str(apId) + "," + str(
                    currentTransmissionReceiver) + "," + str(sinrdB) + "," + str(capacity / 1e6) + "," + str(
                    nbStasConnectedToAps[
                        apId, int(currentTransmissionTrace)]) + "," + str(
                    apTransmissionsTimeSteps[indexTimeStep]) + "-" + str(
                    apTransmissionsTimeSteps[indexTimeStep + 1]) + "\n")
            else:
                ###############################################
                #     CASE4: Transmission and Interferer(s)   #
                ###############################################
                # This case happens when the current transmission is experiencing interferences
                # We will divide the transmissions into chunk to compute correctly the interference
                nbChunk = 0
                interferenceChunkStartTime = apTransmissionsTimeSteps[indexTimeStep]
                chunkSinr = []
                while currentTransmissionNbInterferer - nbInterferenceTreated > 0:
                    # Iterate over all the interference timesteps occuring for the current transmission allocation
                    # We know how many interferences occured - Iterate while we still have interference
                    interferenceChunkEndTime = math.inf
                    interfererEndingCurrentChunk = []
                    # Find the chunk ending Time
                    for apIdInChunk in range(qdScenario.nbAps):
                        if apIdInChunk != apId:
                            # Iterate over all the potential AP interferers and find the minimum upper boundaries of the interfering transmissions
                            if currentInterfererEndTransmissions[
                                apIdInChunk]:  # Need to test if there was an interference
                                if min(currentInterfererEndTransmissions[apIdInChunk]) < interferenceChunkEndTime:
                                    interferenceChunkEndTime = min(currentInterfererEndTransmissions[apIdInChunk])

                    # We found the Chunk Ending Time
                    interferingApCurrentChunk = []
                    for apIdInChunk in range(qdScenario.nbAps):
                        if apIdInChunk != apId:
                            if currentInterfererEndTransmissions[
                                apIdInChunk]:
                                if min(currentInterfererEndTransmissions[apIdInChunk]) == interferenceChunkEndTime:
                                    # Every Interfering transmission ending at the end of the current chunk end time must be removed - Store Them
                                    interfererEndingCurrentChunk.append(
                                        apIdInChunk)

                                if min(currentInterfererEndTransmissions[apIdInChunk]) >= interferenceChunkEndTime:
                                    # Each interfering transmission ending after the end of the current chunk will continue interfering for the next chunk
                                    interferingApCurrentChunk.append(
                                        apIdInChunk)  # List of the APs that will interfere in the chunk
                    sumInterfererPower = 0
                    for apIdInChunk in interferingApCurrentChunk:
                        # Take into account the interferers for a given chunk
                        # Get the interfering transmission receiver and the sector used to compute the interference it generates with the current downlink transmission
                        interferReceiver = currentInterfererReceivers[
                            (apIdInChunk, currentInterfererEndTransmissions[apIdInChunk][0])]
                        interfererSectorUsed = preprocessedSlsData.bestSectorIdList[
                            dataIndex[
                                (apIdInChunk, interferReceiver, 0, 0,
                                 currentTransmissionTrace)]] # TODO should have PAA tx and PAA rx instead of 0,0
                        if interfererSectorUsed != -1:
                            # A downlink transmission occured
                            index = dataIndex[
                                (apIdInChunk, currentTransmissionReceiver, 0, 0,
                                 currentTransmissionTrace)] # TODO should have PAA tx and PAA rx instead of 0,0
                            # Compute the received power from the interfering transmission
                            rwPowerFromInterferer = preprocessedSlsData.powerPerSectorList[
                                index, interfererSectorUsed]
                        else:
                            # There was no downlink transmission from the AP interfering
                            rwPowerFromInterferer = -math.inf
                        if rwPowerFromInterferer != -math.inf:
                            # Add the interering downlink transmission to the total received power from the interferers
                            sumInterfererPower += qdPropagationLoss.DbmtoW(rwPowerFromInterferer)

                    # Compute the SNR for the current downlink transmission
                    snrdB = 10 * math.log10(qdPropagationLoss.DbmtoW(rxPowerTransmission) / (
                        txParam.getNoise()))

                    if associationMode == StaAssociationMode.SAME_AP:
                        # The SINR is equivalent to the SNR if the STA are associated to the same AP (we consider different channel per AP)
                        sinrdB = snrdB
                    else:
                        # Compute the SINR using the other interfering downlink transmissiond
                        sinrdB = 10 * math.log10(qdPropagationLoss.DbmtoW(rxPowerTransmission) / (
                                txParam.getNoise() + sumInterfererPower))
                    timeSnrSinr.append(interferenceChunkStartTime)
                    snrDownlinkTx.append(snrdB)
                    sinrDownlinkTx.append(sinrdB)
                    chunkSinr.append(sinrdB)
                    for apIdInChunk in interfererEndingCurrentChunk:
                        # Remove from the list of interference the AP with the upper boundaries equal to the absolute minimum
                        currentInterfererEndTransmissions[apIdInChunk].pop(0)
                    interferenceChunkStartTime = interferenceChunkEndTime
                    nbInterferenceTreated += len(interfererEndingCurrentChunk)
                    nbChunk += 1
                # We computed the entire current downlink transmission
                # We can obtain the capacity thanks to Shannon-Hartley relationship
                # It requires us to first compute the average SINR in the linear domain
                # and then to divide by the number of users scheduled in the current transmission
                sumSinrLinear = 0
                for i in chunkSinr:
                    sumSinrLinear += 10 ** (i / 10)
                averageSinrLinear = sumSinrLinear / nbChunk
                capacity = 2.16 * 1e9 * (np.log2(1 + averageSinrLinear)) / nbStasConnectedToAps[
                    apId, int(currentTransmissionTrace)]
                timeCapacity.append(interferenceChunkStartTime)
                capacityDownlinkTx.append(capacity / 1e6)
                sumDownlinkCapacity += capacity / 1e6
                nbDownlinkCapacity += 1

                # Write the capacity computed
                f.write(str(currentTransmissionTrace) + "," + str(apId) + "," + str(
                    currentTransmissionReceiver) + "," + str(averageSinrLinear) + "," + str(capacity / 1e6) + "," + str(
                    nbStasConnectedToAps[
                        apId, int(currentTransmissionTrace)]) + "," + str(
                    apTransmissionsTimeSteps[indexTimeStep]) + "-" + str(
                    apTransmissionsTimeSteps[indexTimeStep + 1]) + "\n")
            globals.printProgressBarWithoutETA(indexTimeStep + 1, len(apTransmissionsTimeSteps) - 1,
                                               prefix='Progress:', suffix='Complete',
                                               length=50)
        # Plot for a given downlink AP transmission
        ##########################
        #    SNR SINR PLOT       #
        ##########################
        figureFile = "AP" + str(apId)
        # Initialise the figure and axes.
        fig, ax = plt.subplots(1, figsize=(8, 6))

        # Set the title for the figure
        fig.suptitle('SNR SINR AP:' + str(apId), fontsize=15)

        # Draw all the lines in the same plot, assigning a label for each one to be
        # shown in the legend.
        ax.plot(timeSnrSinr, snrDownlinkTx, color="red", label="SNR")
        ax.plot(timeSnrSinr, sinrDownlinkTx, color="green", label="SINR")
        ax.set_xlim(0, qdScenario.timeStep * qdScenario.nbTraces)

        plt.legend(loc="lower right", frameon=True)
        plt.xlabel("Time (s)")
        plt.ylabel("SNR/SINR (dB)")
        destinationPath = os.path.join(globals.scenarioPath, globals.graphFolder, folderPrefix, globals.snrSinrFolder)
        if not os.path.exists(destinationPath):
            os.makedirs(destinationPath)
        fileToSave = os.path.join(destinationPath, figureFile + ".png", )
        plt.savefig(fileToSave)
        plt.cla()
        plt.close(plt.gcf())

        ##########################
        #    CAPACITY PLOT       #
        ##########################
        # Create the throughput Curve
        # Initialise the figure and axes.
        fig, ax = plt.subplots(1, figsize=(8, 6))

        # Set the title for the figure
        fig.suptitle('Capacity AP:' + str(apId), fontsize=15)
        figureFile = "CapacityAP" + str(apId)

        # Draw all the lines in the same plot, assigning a label for each one to be
        # shown in the legend.
        ax.plot(timeCapacity, capacityDownlinkTx, color="green", label="Capacity")
        ax.set_xlim(0, qdScenario.timeStep * qdScenario.nbTraces)
        if nbDownlinkCapacity != 0:
            plt.axhline(y=sumDownlinkCapacity / nbDownlinkCapacity, color='r', linestyle='-', label="Average Capacity")
        plt.legend(loc="lower right", frameon=True)
        plt.xlabel("Time (s)")
        plt.ylabel("Capacity (Mbps)")
        destinationPath = os.path.join(globals.scenarioPath, globals.graphFolder, folderPrefix, globals.capacityFolder)
        if not os.path.exists(destinationPath):
            os.makedirs(destinationPath)
        fileToSave = os.path.join(destinationPath, figureFile + ".png", )
        plt.savefig(fileToSave)
        plt.cla()
        plt.close(plt.gcf())


def computeDataTransmission(qdScenario,associationMode, staIds, folderPrefix, preprocessedSlsData,
                            preprocessedAssociationData, txParam, dataIndex):
    """Compute the data transmission (and its scheduling) according to the association Mode
    Parameters
    ----------
    associationMode: Enum
        The association mode described in the class StaAssociationMode

    staIds: Numpy array
        The STA IDs to consider for the scheduling

    folderPrefix : string
        The folder prefix to save the figures

    preprocessedSlsData : SlsResults class
        The preprocessed data for the SLS Phase

    preprocessedAssociationData : Dic
        The preprocessed association Data
  
    txParam: TxParam class
        Parameters associated to the transmissions
    dataIndex: Dic
        Used to reconstruct the index of the preprocessed data
    """
    apConnectedStas = createStasAssociation(qdScenario,associationMode, staIds, preprocessedAssociationData)
    print("************************************************")
    print("*      ASSOCIATION CONFIGURATION SUMMARY       *")
    print("************************************************")
    schedulingDic, nbStasConnectedToAps = createDownlinkScheduling(qdScenario,apConnectedStas,
                                                                   folderPrefix)  # Define the transmission (Works only for downlink, i.e, AP to STA)
    transmitData(qdScenario,schedulingDic, nbStasConnectedToAps, associationMode, folderPrefix, preprocessedSlsData, txParam,
                 dataIndex)

