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
import csv
import globals as gb
import os
import numpy as np


def readNs3SuMimoResults(nsResultsFolder, suMimoFilePrefix, qdScenario):
    """Read and store the ns-3 SU-MIMO results

        Parameters
        ----------
        nsResultsFolder : str
            Folder that contains the ns-3 SU-MIMO results

        suMimoFilePrefix : str
            Prefix of the SU-MIMO result file

        qdScenario: Class
            Store the Q-D scenario parameters and results
    """
    suMimoResults = {}

    for initiator in range(qdScenario.nbNodes):
        for responder in range(qdScenario.nbNodes):
            if initiator != responder:
                # Read all the MIMO files (if they exist)
                # By default, we assume that MIMO has to occur between any node in the simulation
                # If only partial nodes in the simulation have MIMO results, MIMO will be disabled
                # TODO: Once ns-3 is able to generate MIMO results for more than a SU-MIMO pair, change this behavior
                try:
                    filename = os.path.join(nsResultsFolder, suMimoFilePrefix + str(initiator) + "_" + str(responder) + "_1.csv")
                    with open(filename) as f:
                        reader = csv.DictReader(f, delimiter=',')
                        lineRead = 0
                        for row in reader:
                            if lineRead == 0:
                                # We don't know how many streams are supported before to read the file
                                # The number of columns of the file is made of Total Columns = 6*nbStreams+2*nbStreams+7
                                # 6 as for a single stream, you have Tx Sector/Paa/AWV Rx Sector/Paa/AWV
                                # 2 as for a single stream, you have SINR Paa Tx/Paa Rx SINR PAA Rx/Paa Tx
                                # 7 as you have 7 fixed fields
                                # So the maximum number of streams can thus be obtained with (TotalColumns-7)/(8)
                                maxSupportedStream = int((len(row)-7)/8)

                                # Trace ID in the BeamTracking Results can use a different indexing than the one used in the
                                # Q-D Realization software output - Account for this
                                initialIndex = int(row['TRACE_ID'])
                                lineRead += 1

                            txAntennaId = [] # Contain the Tx streams Antennas ID
                            txSectorId = []  # Contain the Tx streams Sectors ID
                            txAwv = []  # Contain the TX Streams AWVs (Not used)

                            rxAntennaId = np.zeros(maxSupportedStream, dtype=int) # Contain the Rx streams Antennas ID
                            rxSectorId = np.zeros(maxSupportedStream, dtype=int) # Contain the RX streams Sectors ID
                            rxAwv = np.zeros(maxSupportedStream, dtype=int)  # Contain the RX Streams AWVs (Not used)
                            bestreamIdCombination = []

                            for streamId in range(maxSupportedStream):
                                # Construct the results for every TX and RX streams

                                # Tx Streams
                                txAntennaId.append(int(row['TX_ANTENNA_ID'+str(streamId+1)]))
                                txSectorId.append(int(row['TX_SECTOR_ID' + str(streamId+1)]))
                                txAwv.append(int(row['TX_AWV_ID' + str(streamId+1)]))


                                # Rx Streams
                                # We need to associate the correct RX PAA to the TX stream
                                # It is done using the PEER_RX_ID header value which contains the PAA associated to a TX Stream
                                bestreamIdCombination.append([int(row['TX_ANTENNA_ID' + str(streamId + 1)]),
                                                              int(row['PEER_RX_ID' + str(streamId + 1)])])
                                rxAntennaId[int(row['PEER_RX_ID' + str(streamId + 1)])] = int(row['RX_ANTENNA_ID' + str(streamId + 1)])
                                rxSectorId[int(row['PEER_RX_ID' + str(streamId + 1)])] = int(row['RX_SECTOR_ID' + str(streamId + 1)])
                                rxAwv[int(row['PEER_RX_ID' + str(streamId + 1)])] = int(row['RX_AWV_ID' + str(streamId+1)])

                            # Remove the initial index to have a key index starting at 0
                            suMimoResults[int(row['TRACE_ID']) - initialIndex,int(row['SRC_ID']),int(row['DST_ID']) ] = gb.MimoBeamformingResults(
                                bestreamIdCombination,
                                    int(row['TRACE_ID']),
                                txAntennaId,
                                txSectorId,
                                txAwv,
                                rxAntennaId,
                                rxSectorId,
                                rxAwv
                            )
                except OSError as e:
                    gb.logger.warning("SU-MIMO file"+ filename + " missing - SU-MIMO from ns-3 will be disabled")
                    return None
    return suMimoResults


def readNs3MuMimoResults(nsResultsFolder, muMimoInitiatorPrefix, muMimoResponderPrefix, qdScenario):
    """Read and store the ns-3 MU-MIMO results

    Parameters
    ----------
    nsResultsFolder : str
        Folder that contains the ns-3 results


    suMimoFilePrefix : str
        Prefix of the SU-MIMO result file

    qdScenario: Class
        Store the Q-D scenario parameters and results

    """

    mimoGroup = 1
    rxConfigurationSinrValues = {}
    commentFileSuffix = "_1.csv"
    mimoInitiator = 0
    # mimoResponder = [1,2]
    muMimoResults = {}

    for mimoInitiator in range(qdScenario.nbNodes):
        # Iterate for every nodes in the scenario
        # We assume that all nodes in the scenario can be MIMO initiator
        for mimoGroup in range(1,qdScenario.nbNodes):
            # Iterate for every MIMO group in the scenario
            # We assume that we can't have a MIMO group ID larger than the number of nodes (TODO: Check this)
            mimoInitiatorFilePrefix = muMimoInitiatorPrefix + str(mimoInitiator) + "_" + str(mimoGroup)
            mimoInitiatorFileName = os.path.join(nsResultsFolder,mimoInitiatorFilePrefix + commentFileSuffix)
            try:
                with open(mimoInitiatorFileName) as f:
                    # Open the initiator MU-MIMO file
                    reader = csv.DictReader(f, delimiter=',')
                    lineInitiatorRead = 0
                    for row in reader:
                        if lineInitiatorRead == 0:
                            # We don't know how many streams are supported before to read the file
                            # The number of columns of the file is made of Total Columns = 4*nbStreams+6
                            # 4 as for a single stream, you have RESPONDER_ID,ANTENNA_ID,SECTOR_ID,AWV_ID
                            # 6 as you have 7 fixed fields
                            # So the maximum number of streams can thus be obtained with (TotalColumns-6)/(4)
                            maxSupportedStream = int((len(row) - 6) / 4)
                            # Trace ID in the BeamTracking Results can use a different indexing than the one used in the
                            # Q-D Realization software output - Account for this
                            initialIndex = int(row['TRACE_ID'])
                        lineInitiatorRead += 1


                        txAntennaId = []  # Contain the Tx streams Antennas ID
                        txSectorId = []  # Contain the Tx streams Sectors ID
                        txAwv = []  # Contain the TX Streams AWVs (Not used)
                        rxAntennaId = []  # Contain the Rx streams Antennas ID
                        rxSectorId = []  # Contain the RX streams Sectors ID
                        rxAwv = []  # Contain the RX Streams AWVs (Not used)
                        readerResponderList = []
                        mimoResponder = []
                        mimoResponderFileNames = []
                        bestreamIdCombination = []
                        for streamId in range(maxSupportedStream):

                            # Construct the results for every TX and RX streams
                            ############## Tx Streams ################
                            txAntennaId.append(int(row['ANTENNA_ID' + str(streamId + 1)]))
                            txSectorId.append(int(row['SECTOR_ID' + str(streamId + 1)]))
                            txAwv.append(int(row['AWV_ID' + str(streamId + 1)]))
                            # We need to know to which responder each stream is connected to
                            mimoResponder.append(int(row['RESPONDER_ID' + str(streamId + 1)]))
                            # Construct the fileNames for the responders
                            mimoResponderFilePrefix = muMimoResponderPrefix + str(mimoResponder[-1]) + "_" + str(mimoGroup) + commentFileSuffix
                            mimoResponderFileName = os.path.join(nsResultsFolder, mimoResponderFilePrefix)
                            mimoResponderFileNames.append(mimoResponderFileName)
                            # Store the best stream combination
                            # For MU-MIMO, the format is Stream Id Tx PAA Rx IDs
                            bestreamIdCombination.append([txAntennaId[-1],mimoResponder[-1]])
                            try:
                                with open(mimoResponderFileNames[streamId]) as f2:
                                    # Open and handle the responder MIMO results files
                                    nbLineResponderRead = 0
                                    readerResponderList.append(csv.DictReader(f2, delimiter=','))
                                    for rowResponder in readerResponderList[streamId]:
                                        ############## Rx Streams ################
                                        nbLineResponderRead += 1

                                        if (nbLineResponderRead == lineInitiatorRead):
                                            rxAntennaId.append(int(rowResponder['ANTENNA_ID1']))
                                            rxSectorId.append(int(rowResponder['SECTOR_ID1']))
                                            rxAwv.append(int(rowResponder['AWV_ID1']))


                                        if (nbLineResponderRead == lineInitiatorRead):
                                            break
                            except OSError as e:
                                print(
                                    "No ns-3 MU-MIMO Results file - MU-MIMO Disabled")
                                return None

                            # srcId, dstId, traceId, txAntennaId, txSectorId, txAwvId, rxAntennaId, rxSectorId, rxAwvId)

                            muMimoResults[int(row['TRACE_ID']) - initialIndex,mimoGroup] = gb.MimoBeamformingResults(
                                            bestreamIdCombination,
                                            int(row['TRACE_ID']) - initialIndex,
                                            txAntennaId,
                                            txSectorId,
                                            txAwv,
                                            rxAntennaId,
                                            rxSectorId,
                                            rxAwv
                                        )
            except OSError as e:
                break
    return muMimoResults


# Read the configuration used in ns-3 to know which node is an AP and which node is a STA
def readNs3Configuration(scenarioFolder, nodesConfigurationFile, qdScenario):
    """Read the config file used in ns-3 to generate system-level performance results
    
    Parameters
    ----------
    scenarioFolder : string
        Name of the folder containing the scenario
             
    nodesConfigurationFile : string
        Name of the config file used in ns-3 to simulate the scenario
    """

    nodesDic = {} # Dictionary containing all the nodes (AP + STA)
    fileName = os.path.join(scenarioFolder, nodesConfigurationFile)

    print("************************************************")
    print("*          ns-3 Scenario Configuration         *")
    print("************************************************")

    try:
        f = open(fileName)
        print("ns-3 configuration file in the scenario folder - Filter the nodes")
    except OSError as e:
        print(
            "No ns-3 configuration file - Default Node Allocation (First node is an AP, all the others are STAs)")
        # In case no ns-3 configuration files are provided, the strategy used is to:
        # - Allocate the first node as an AP
        # - Allocate all the other nodes as STA
        for nodeId in range(qdScenario.nbNodes):
            if nodeId == 0:
                # First node is assigned the AP role
                nodesDic[nodeId] = gb.Node(nodeId, gb.NodeType.AP)
            else:
                # Other nodes are STAs
                nodesDic[nodeId] = gb.Node(nodeId, gb.NodeType.STA)
        nbActiveAps = 1
        nbActiveStas = qdScenario.nbNodes - 1
        qdScenario.setNodesConfiguration(nbActiveAps, nbActiveStas, nbActiveAps + nbActiveStas)
        print("Nb APs:",nbActiveAps)
        print("Nb STAs:", nbActiveStas)
        print("Number of Nodes:", nbActiveAps+nbActiveStas)
        qdScenario.setNodesType(nodesDic)
        return nodesDic

    # The first line determines the number of AP active in the ns-3 simulation
    nbActiveAps = int(f.readline())
    nbActiveStas = 0
    for indexAp in range(nbActiveAps):
        # Get the active STAs for each AP
        apID = int(f.readline().strip())  # Read the AP ID

        nodesDic[apID] = gb.Node(apID, gb.NodeType.AP)
        gb.logger.debug("AP:" + str(apID))
        nbAssociatedSTAs = int(f.readline().strip())  # Read the number of STAs associated to the AP
        nbActiveStas += nbAssociatedSTAs
        if nbAssociatedSTAs > 0:
            gb.logger.debug("\tnbAssociatedSTAs:" + str(nbAssociatedSTAs))
            staAssociated = f.readline().strip()  # Read the STAs IDs
            gb.logger.debug("\tstaAssociated:" + str(staAssociated))
            if staAssociated.find(',') != -1:
                # Parse the line separated by ','
                staListAsAList = [int(x) for x in staAssociated.split(',')]  # TODO Last Minute Bug - Ugly Fix
                # for i in range(len(staListAsAList)):
                for i in range(len(staListAsAList)):
                    nodesDic[staListAsAList[i]] = gb.Node(staListAsAList[i], gb.NodeType.STA)
            elif staAssociated.find(':') != -1:
                # Parse the line separated by ':'
                index = staAssociated.split(':')
                for i in range(nbAssociatedSTAs):
                    nodesDic[int(index[0]) + i] = gb.Node(int(index[0]) + i, gb.NodeType.STA)
            else:
                # Parse the line without any separator, i.e., only one STA
                nodesDic[int(staAssociated)] = gb.Node(int(staAssociated), gb.NodeType.STA)
    qdScenario.setNodesConfiguration(nbActiveAps,nbActiveStas,nbActiveAps+nbActiveStas)
    print("Nb APs:", nbActiveAps)
    print("Nb STAs:", nbActiveStas)
    print("Number of Nodes:", nbActiveAps+nbActiveStas)
    qdScenario.setNodesType(nodesDic)

def readNsSlsResults(scenarioFolder, slsFile, qdScenario):
    """Read the ns-3 results file for SLS

    Parameters
    ----------
    scenarioFolder : string
        Name of the folder containing the scenario

    slsFile : string
        Name of the file used in ns-3 to store the SLS results
    """
    import pandas as pd
    nodesConfigurationFile = "sls_1.csv"
    fileName = os.path.join(scenarioFolder, nodesConfigurationFile)
    try:
        qdScenario.nsSlsResults = pd.read_csv(fileName)
    except OSError as e:
        gb.logger.warning("SLS Activated and no ns-3 results file found: " + fileName)
        qdScenario.nsSlsResults = pd.DataFrame()


def getNsSlsResultsTxRxTrace(txNode,rxNode, traceId,qdScenario):
    """Get the SLS results for the TXSS between Tx Node/Rx Node for a given trace

    Parameters
    ----------
    txNode : int
        ID of the tx Node


    rxNode : int
        ID of the tx node

    traceId: int
        Trace to get the results for


    """
    # As we don't have the results for every trace, we must find the last time an SLS was performed
    txToRxDf = qdScenario.nsSlsResults.loc[(qdScenario.nsSlsResults["SRC_ID"] == txNode) & (qdScenario.nsSlsResults["DST_ID"] == rxNode)]
    if txToRxDf.empty:
        # No results available for the pair txNode rxNode
        return None,None
    txToRxDfTrace = txToRxDf.loc[(txToRxDf["TRACE_ID"] <= traceId)]
    index = txToRxDfTrace['TRACE_ID'].sub(traceId).abs().idxmin()
    paaTx = qdScenario.nsSlsResults["ANTENNA_ID"].iloc[index]
    bestSectorTxRx = qdScenario.nsSlsResults["SECTOR_ID"].iloc[index]
    return paaTx,bestSectorTxRx

def getNsSlsResultsBftId(txNode,rxNode, bftId,qdScenario):
    """Get the SLS results for the TXSS between Tx Node/Rx Node for a BFT ID

        Parameters
        ----------
        txNode : int
            ID of the tx Node


        rxNode : int
            ID of the tx node

        bftId: int
            The Beamforming Training ID

        qdScenario: Class
            Store the Q-D scenario parameters and results
    """
    txToRxDf = qdScenario.nsSlsResults.loc[
        (qdScenario.nsSlsResults["SRC_ID"] == txNode) & (qdScenario.nsSlsResults["DST_ID"] == rxNode) & (qdScenario.nsSlsResults["BFT_ID"] == bftId)]
    if txToRxDf.empty:
        # No results availablew
        return -1
    traceId = txToRxDf["TRACE_ID"]
    return traceId.values[0]

def getNumberOfBft(txNode,rxNode, qdScenario):
    """Get the number of Beamforming Training performed between a pair of device
    """
    if not qdScenario.nsSlsResults.empty:
        txToRxDf = qdScenario.nsSlsResults.loc[
            (qdScenario.nsSlsResults["SRC_ID"] == txNode) & (qdScenario.nsSlsResults["DST_ID"] == rxNode)]
        if txToRxDf.empty:
            # No result found
            return 1
    else:
        # No result available
        return 1
    return txToRxDf['TIME'].size
