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
import datetime
import os
import pickle
import time
import itertools
import numpy as np
import pandas as pd
import qdPropagationLoss
import globals
import math
from qdPropagationLoss import performSls
from heapq import heappush, heappushpop


class SlsResults:
    """
    Class used for the SLS preprocessed data

    Attributes
    ----------
    bestSectorIdList : Numpy array
        Contains the best sector ID

    powerPerSectorList : Numpy array
        Contains all the power received per sector

    bestSectorRxPowerList : Numpy array
        Contains the Rx Power for the best sector
    """

    def __init__(self, bestSectorIdList, powerPerSectorList, bestSectorRxPowerList):
        self.bestSectorIdList = bestSectorIdList
        self.powerPerSectorList = powerPerSectorList
        self.bestSectorRxPowerList = bestSectorRxPowerList


def getSuMimoAllValidStreamCombinations(nbPaaTx, nbPaaRx):
    """
    Get the list of all possible individual SU-MIMO stream combinations
    A stream is connecting a MIMO initiator PAAs to a responder PAAs
    A stream is identified with a tuple (idTxPaa,idRxPaa)

    Attributes
    ----------
    nbPaaTx : Int
        Number of PAAs of the Initiator

    nbPaaRx : Int
        Number of PAAs of the Responder
    """
    allIndividualStreamList = list(itertools.product(np.arange(nbPaaTx), np.arange(nbPaaRx)))
    ############################################################
    #            ALL POSSIBLE STREAMS COMBINATIONS             #
    ############################################################
    # Not every individual stream combination is possible. Indeed, a MIMO initiator single PAA cannot transmit to more
    # than one responder PAA
    # We need to obtain the list of all individual streams combination achievable
    # A combination is made of nb PAA MIMO Initiator Nb PAA responder
    if len(np.arange(nbPaaTx)) != len(np.arange(nbPaaRx)):
        print("The number of PAA of the MIMO Initiator must be equal to the number of PAAs of the receiver")
        exit()  # TODO Not exit
    mimoTxStreamCombinationsTxtoRx = []
    duplicates = {}
    for initialTxStream in allIndividualStreamList:
        # Iterate over all individual streams (e.g, MIMO Initator: PAA0 => MIMO Responder: PAA0)
        # to find all the possible MIMO Tx Combinations
        # initialTxStream represents the stream for whom we are looking at the possible configuration
        setToEvaluate = allIndividualStreamList  # The entire list of possible Tx Streams
        possibleStreamsConfiguration = [initialTxStream]  # Store a possible stream configuration
        setOfTx = []  # Used to check the MIMO Initiator Tx PAA streams already added
        setOfRx = []  # Used to check the Responder Rx ID streams already added
        setOfTx.append(initialTxStream[0])  # Add the MIMO Initiator PAA ID of the initialTxStream
        setOfRx.append(initialTxStream[1])  # Add the Responder Rx ID of the initialTxStream
        for combinationTry in setToEvaluate:
            # Iterate over all individual streams to check if it can be added to a possible stream configuration
            if combinationTry[0] in setOfTx or combinationTry[1] in setOfRx:
                # The combination is impossible
                # We discard the combination that are impossible i.e.:
                # - Reusing the same MIMO initiator PAA
                # - Reusing the same responder ID
                pass
            else:
                # The combination is possible - Add it
                setOfTx.append(combinationTry[0])
                setOfRx.append(combinationTry[1])
                possibleStreamsConfiguration.append(combinationTry)
        txStreamCombinationToAdd = []
        # The algorithm will yield duplicated possible stream configurations
        # However, they will be ordered differently so we need to order the stream configuration in order to avoid duplicate
        # For this, we iterate over the possible stream configuration and reorder it
        for i in range(len(possibleStreamsConfiguration)):
            txStreamCombinationToAdd.append(
                possibleStreamsConfiguration.pop(possibleStreamsConfiguration.index(min(possibleStreamsConfiguration))))
        # Keep the possible Tx Stream Combinations without any duplicates
        if tuple(txStreamCombinationToAdd) in duplicates:
            duplicates[tuple(txStreamCombinationToAdd)]
        else:
            duplicates[tuple(txStreamCombinationToAdd)] = len(mimoTxStreamCombinationsTxtoRx)
            mimoTxStreamCombinationsTxtoRx.append(tuple(txStreamCombinationToAdd))
    return mimoTxStreamCombinationsTxtoRx


def getMuMimoAllValidStreamCombinations(elementsInitiator, elementsResponder):
    """
    Get the list of all possible individual MU-MIMO stream combinations

    Attributes
    ----------
    elementsInitiator : Int
        Elements of the Initiator Stream

    elementsResponder : Int
        Elements of the Responder Stream
    """
    # For MU-MIMO, depending who is the initiator or the responder, the initiator elements and responder has different meaning
    # If the initiator is the AP, then, the initiator elements are PAAs IDs (cardinality = number of AP PAAs) of the AP and the elements for the responders
    # are the STAs IDs
    # The opposite is that the STAs are the initators and the AP the responder. In this case, the elements of the initator
    # are the STA IDs and the elements of the responder is the number of AP elements
    # Update the variable name accordingly
    allIndividualStreamList = list(itertools.product(elementsInitiator, elementsResponder))

    mimoTxStreamCombinationsItoR = {}
    for initialTxStream in allIndividualStreamList:
        # Iterate over all individual streams (for example, MIMO Initator: PAA0 => Responder: STA1 PAA0)
        # to find all the possible MIMO Tx Combinations
        # initialTxStream represents the stream for whom we are looking at the possible configuration
        setToEvaluate = allIndividualStreamList  # The entire list of possible Tx Streams
        possibleStreamsConfiguration = [initialTxStream]  # Store a possible stream configuration
        setOfTx = []  # Used to check the MIMO Initiator Tx PAA streams already added
        setOfRx = []  # Used to check the Responder Rx ID streams already added
        setOfTx.append(initialTxStream[0])  # Add the MIMO Initiator PAA ID of the initialTxStream
        setOfRx.append(initialTxStream[1])  # Add the Responder Rx ID of the initialTxStream
        for combinationTry in setToEvaluate:
            # Iterate over all individual streams to check if it can be added to a possible stream configuration
            if combinationTry[0] in setOfTx or combinationTry[1] in setOfRx:
                # The combination is impossible
                # We discard the combination that are impossible i.e.:
                # - Reusing the same MIMO initiator PAA
                # - Reusing the same responder ID
                pass
            else:
                # The combination is possible - Add it
                setOfTx.append(combinationTry[0])
                setOfRx.append(combinationTry[1])
                possibleStreamsConfiguration.append(combinationTry)
        txStreamCombinationToAdd = []
        # The algorithm will yield duplicated possible stream configurations
        # However, they will be ordered differently so we need to order the stream configuration in order to avoid duplicate
        # For this, we iterate over the possible stream configuration and reorder it
        for i in range(len(possibleStreamsConfiguration)):
            txStreamCombinationToAdd.append(
                possibleStreamsConfiguration.pop(possibleStreamsConfiguration.index(min(possibleStreamsConfiguration))))
        # We store the possible Tx Stream Combinations in a hashmap to get rid of duplucate
        mimoTxStreamCombinationsItoR[tuple(txStreamCombinationToAdd)] = 1
    return mimoTxStreamCombinationsItoR

def performSuMimoSisoPhase(txId, rxId, nbPaaTx, nbPaaRx, traceIndex, qdProperties, txParam,
                         nbSubBands,
                         qdScenario, codebooks):
    """
    Perform the SISO Phase for SU-MIMO

    Attributes
    ----------
    txId : Int
        ID of the transmitter

    rxId : Int
        ID of the receiver

    nbPaaTx: Int
        Number of PAA of the transmitter

    nbPaaRx: Int
        Number of PAA of the receiver

    traceIndex: int
        Q-D trace ID

    qdProperties: Class
        Contains the Multiplath Properties

    txParam: Class
        Contain the transmission parameters

    nbSubBands: Int
        Total number of subbands

    qdScenario : Class
        Contain the parameters and results for the Q-D scenario used

    codebooks : Class
        Represents the codebook class
    """
    mimoSisoResults = {}
    for mimoTxAntennaId in range(nbPaaTx):
        # Iterate over the Tx Antennas
        for mimoRxAntennaId in range(nbPaaRx):
            # Iterate over the Rx Antennas
            rxPower, snr, psdBestSector, txssSector, rxPowerSectorList = performSls(
                (txId, rxId, mimoTxAntennaId, mimoRxAntennaId, traceIndex), qdProperties, txParam,
                nbSubBands,
                qdScenario, codebooks)
            rxPowerSectorList = np.asarray(rxPowerSectorList)
            snrList = 10 * np.log10(qdPropagationLoss.DbmtoW(rxPowerSectorList) / txParam.getNoise())
            mimoSisoResults[mimoTxAntennaId, mimoRxAntennaId] = (rxPowerSectorList,
                                                                 snrList)
    # mimoSisoResults is a dictionary that contains the SISO received power and SNR
    # The key is Tx PAA ID, Rx PAA ID
    # The values are a tuple made of [nb Tx sector Rx Power, nb Tx sector SNR values]
    return mimoSisoResults

def performMuMimoSisoPhase(mode,mimoInitiatorId,nbPaaMimoInitiator, mimoResponderIds, traceIndex, qdProperties, txParam,
                         nbSubBands,
                         qdScenario, codebooks):
    """
    Perform the SISO Phase for MU-MIMO

    Attributes
    ----------
    mode : str
        Either Initiator or Responder

    mimoInitiatorId : Int
        ID of the MIMO Initiator

    nbPaaMimoInitiator: Int
        Number of PAA of the Initiator

    mimoResponderIds : Int
        ID of the receiver

    traceIndex: int
        Q-D trace ID

    qdProperties: Class
        Contains the Multiplath Properties

    txParam: Class
        Contain the transmission parameters

    nbSubBands: Int
        Total number of subbands

    qdScenario : Class
        Contain the parameters and results for the Q-D scenario used

    codebooks : Class
        Represents the codebook class
    """
    mimoSisoResults = {}
    for mimoTxAntennaId in range(nbPaaMimoInitiator):
        for rxNode in mimoResponderIds:
            if mode == "initiator":
                # Initiator case - The results are computed from AP to STAs
                rxPowerITXSS, snrITXSS, psdBestSectorITXSS, txssSectorITXSS, rxPowerSectorListITXSS = performSls(
                    (mimoInitiatorId, rxNode, mimoTxAntennaId, 0, traceIndex), qdProperties, txParam, nbSubBands,
                    qdScenario, codebooks)  # 0 should be rx antenna id and traceId
                rxPowerSectorListITXSS = np.asarray(rxPowerSectorListITXSS)
                snrListITXSS = 10 * np.log10(qdPropagationLoss.DbmtoW(rxPowerSectorListITXSS) / txParam.getNoise())

                mimoSisoResults[mimoTxAntennaId, rxNode] = (rxPowerSectorListITXSS, snrListITXSS)
            else:
                # We are in the initiator case - The results are computed from STAs to AP
                rxPowerRTXSS, snrRTXSS, psdBestSectorRTXSS, txssSectorRTXSS, rxPowerSectorListRTXSS = performSls(
                            (rxNode, mimoInitiatorId, 0, mimoTxAntennaId, traceIndex), qdProperties, txParam, nbSubBands,
                            qdScenario, codebooks)  # 0 should be rx antenna id and traceId
                rxPowerSectorListRTXSS = np.asarray(rxPowerSectorListRTXSS)
                snrListITXSS = 10 * np.log10(qdPropagationLoss.DbmtoW(rxPowerSectorListRTXSS) / txParam.getNoise())
                mimoSisoResults[rxNode, mimoTxAntennaId] = (rxPowerSectorListRTXSS, snrListITXSS)
    return mimoSisoResults

def getSuMimoTopKSnr(txId, nbPaaTx, mimoTxStreamCombinationsTxtoRx, mimoSisoResults, qdScenario, codebooks, topK):
    """
        Compute the top-k for SU-MIMO

        Attributes
        ----------
        txId : Int
            ID of the transmitter

        mimoTxStreamCombinationsTxtoRx: Dic
            All possible individual stream combinations

        mimoSisoResults: Dic
            Contain the SISO results for every transmitter to receiver pair

        qdScenario : Class
            Contain the parameters and results for the Q-D scenario used

        codebooks : Class
            Represents the codebook class

        topK : Int
            Top K value to use
        """
    ############################################################
    # TOP K FROM INITIATOR TO RESPONDER              #
    ############################################################
    # Here, we have all the SNR for every individual stream

    # Compute the Top-K SNR for all the possible Tx sector combinations of the possible MIMO Tx Stream Combination
    # For that, we use joint-snr sum

    # Create all the possible TX sector combinations
    # It depends from the number of Tx Sector of the MIMO initiator PAA and its number of PAA
    nbSectorsPerPaaMimoTx = codebooks.getNbSectorsPerPaaNode(qdScenario.getNodeType(txId))
    txNbSectorId = np.arange(nbSectorsPerPaaMimoTx)
    argProduct = []  # Argument to pass to obtain the right product iterator
    txTopKCandidatesTxtoRx = {}
    rxTopKCandidatesTxtoRx = {}
    txTopKCandidatesTxtoRxTable = []
    streamCombinationTested = 0
    for i in range(nbPaaTx):
        argProduct.append(txNbSectorId)

    allTxSectorsCombinations = list(itertools.product(*argProduct))
    for aStreamCombination in mimoTxStreamCombinationsTxtoRx:
        txCandidates = []  # Change one line
        # Iterate over all the streams combination to compute the joint-SNR sum
        # A stream combination is for example (Tx PAA:0, Rx PAA:0)(Tx PAA:1, Rx PAA:1)
        for aTxSectorCombination in allTxSectorsCombinations:
            # Iterate over all the possible Tx sector combinations for Tx PAAs for a given stream combination
            sumSinrLinear = 0
            indexSector = 0

            for indidualStream in aStreamCombination:
                # Iterate over each stream of the combination to compute the sum of the joint-SNR (we use linear scale to sum them)
                # mimoSisoResults[indidualStream][1] contains the SNR for one of the stream
                sumSinrLinear += 10 ** (mimoSisoResults[indidualStream][1][aTxSectorCombination[indexSector]] / 10)
                indexSector += 1
            sumSinrDb = 10 * np.log10(1 + sumSinrLinear)  # Convert back the sum to the dB scale
            # Keep the top-K combination, i.e, the top Tx sector combinations that yield the highest joint-SNR
            if len(txCandidates) < topK:
                heappush(txCandidates, [sumSinrDb, aTxSectorCombination])
            else:
                heappushpop(txCandidates, [sumSinrDb, aTxSectorCombination])
        # Store the top K candidates for a stream combination
        txTopKCandidatesTxtoRx[aStreamCombination] = sorted(txCandidates, reverse=True)
        rxTopKCandidatesTxtoRx[aStreamCombination] = sorted(txCandidates, reverse=True)
        bufferToStore = []
        for i in sorted(txCandidates, reverse=True):
            bufferToStore.append(i[1])

        txTopKCandidatesTxtoRxTable.append(bufferToStore)
        streamCombinationTested += 1
    return txTopKCandidatesTxtoRx, txTopKCandidatesTxtoRxTable

def getMuMimoTopKSnr(mode, mimoInitiatorId, nbPaaMimoInitiator,nbSectorsPerPaaMimoInitiator, mimoTxStreamCombinationsItoR, sisoInitiatorToResponderList, topK):
    """
        Compute the top-k for MU-MIMO

        Attributes
        ----------
        mode : str
            Either Initiator or Responder

        mimoInitiatorId : Int
            ID of the Initiator

        nbPaaMimoInitiator: Int
            Number of PAA of the Initiator

        nbSectorsPerPaaMimoInitiator: Int
            Number of sectors of the Initiator

        mimoTxStreamCombinationsItoR: Dic
            All possible individual stream combinations

        sisoInitiatorToResponderList : Dic
            Contain the SISO results for every transmitter to receiver pair

        topK : Int
            Top K value to use
    """
    # Here, we have all the SNR for every individual stream

    # Compute the Top-K SNR for all the possible Tx sector combinations of the possible MIMO Tx Stream Combination
    # For that, we use joint-snr sum

    # Create all the possible TX sector combinations
    # It depends from the number of Tx Sector of the MIMO initiator PAA and its number of PAA
    txNbSectorId = np.arange(nbSectorsPerPaaMimoInitiator)
    argProduct = []  # Argument to pass to obtain the right product iterator
    txTopKCandidatesItoR = {}
    rxTopKCandidatesItoR = {}
    txTopKCandidatesItoRTable = []
    streamIdItoRTable = []

    if mode == "initiator":
        for i in range(nbPaaMimoInitiator):
            argProduct.append(txNbSectorId)
    else:
        for i in range(len(mimoInitiatorId)):
            argProduct.append(txNbSectorId)

    allTxSectorsCombinations = list(itertools.product(*argProduct))
    txCandidates = []
    for aStreamCombination in mimoTxStreamCombinationsItoR.keys():
        # Iterate over all the streams combination to compute the joint-SNR sum
        for aTxSectorCombination in allTxSectorsCombinations:
            # Iterate over all the possible Tx sector combinations
            sumSinrLinear = 0
            indexSector = 0
            for i in aStreamCombination:
                # Iterate over the each stream of the combination to compute the sum of the joint-SNR (we use linear scale to sum them)
                sumSinrLinear += 10 ** (sisoInitiatorToResponderList[i][1][aTxSectorCombination[indexSector]] / 10)
                indexSector += 1
            sumSinrDb = 10 * np.log10(1 + sumSinrLinear)  # Convert back the sum to the dB scale

            # Keep the top-K combination, i.e, the 5 Tx sector combinations that yield the highest joint-SNR
            if len(txCandidates) < topK:
                heappush(txCandidates, [sumSinrDb, aTxSectorCombination])
            else:
                heappushpop(txCandidates, [sumSinrDb, aTxSectorCombination])
        # Store the top K candidates for a stream combination
        txTopKCandidatesItoR[aStreamCombination] = sorted(txCandidates, reverse=True)
        rxTopKCandidatesItoR[aStreamCombination] = sorted(txCandidates, reverse=True)
        bufferToStore = []
        for i in sorted(txCandidates, reverse=True):
            bufferToStore.append(i[1])

        txTopKCandidatesItoRTable.append(bufferToStore)
        streamIdItoRTable.append(aStreamCombination)
    return txTopKCandidatesItoR,txTopKCandidatesItoRTable,streamIdItoRTable


def getDirectivity(nodeId, qdScenario, codebooks):
    """
    Get all the directivity and angles corresponding to all the sectors/AWVs combinations
    The directivity and angles are stored in a list to speed up the MIMO computation

    Attributes
    ----------
    nodeId : Int
        The node ID

    qdScenario : Class
        Contain the parameters and results for the Q-D scenario used

    codebooks : Class
        Represents the codebook class
    """
    angles = []
    directivityList = []
    index = 0
    for sectorId in range(codebooks.getNbSectorsPerPaaNode(qdScenario.getNodeType(nodeId))):
        for awvId in range(5):
            # Get the azimuth and elevation angle corresponding to a sector/AWV
            azimuthAwv, elevationAwv = codebooks.getRefinedAwvAzimuthElevation(
                sectorId,
                awvId, qdScenario.getNodeType(nodeId))
            angles.append([azimuthAwv, elevationAwv])
            # Get the directivity for the sector/AWV azimuth and elevation angle
            directivity = codebooks.getRefinedAwvDirectivityAzEl(azimuthAwv,
                                                                 elevationAwv,
                                                                 qdScenario.getNodeType(
                                                                     nodeId))
            directivityList.append(directivity)
            index += 1
    return directivityList, angles



def performSuMimoBft(traceIndex, mimoInitiatorId, anglesInitiator, directivityInitiator, mimoResponderId, anglesResponder,
                   directivityResponder, nbPaaMimoInitiator, mimoTxStreamCombinationsItoR, txTopKCandidatesItoRTable,
                   rxTopKCandidatesRtoITable, qdProperties, qdScenario, txParam, nbSubBands, codebooks):
    """
       Perform SU-MIMO MIMO beamforming training phase between an initiator and a responder for a given trace

       Attributes
       ----------
       traceIndex : Int
           The Q-D trace index

       mimoInitiatorId : Int
           ID of the Initiator

       anglesInitiator: Dic
           List of all the Initiator angles (azimuth, elevation) for the custom AWV

       directivityInitiator: Dic
           List of all the Initiator directivity for the custom AWV

       mimoResponderId : Int
           ID of the Responder

       anglesResponder: Dic
           List of all the Responder angles (azimuth, elevation) for the custom AWV

       directivityResponder: Dic
           List of all the Responder directivity for the custom AWV

       nbPaaMimoInitiator : Int
            Number of PAA of the initiator

       mimoTxStreamCombinationsItoR : Dic
            All possible individual stream combinations

       txTopKCandidatesItoRTable : Dic
            Top K tx sector for all possible stream combinations from Initiator to Responder

       rxTopKCandidatesRtoITable: Dic
            Top K tx sector for all possible stream combinations from Responder to Initiator

       qdProperties: Class
        Contains the Multiplath Properties

       qdScenario : Class
            Contain the parameters and results for the Q-D scenario used

       txParam: Class
        Contain the transmission parameters

        nbSubBands: Int
            Total number of subbands

        codebooks : Class
            Represents the codebook class
    """
    bestSinrCombination = np.full(nbPaaMimoInitiator,
                                  -math.inf)  # Store the best SINR combination (largest mimimum SINR)
    bestreamIdCombination = 0
    bestSectorsCombination = 0
    bestAwvCombination = 0
    precomputedValue = {}
    testStoredPower = {}

    for streamCombinationId in range(len(mimoTxStreamCombinationsItoR)):
        # Test one of the stream combination, i.e, for example
        # Stream 0: (0, 0) format: (PAA_TX, PAA_RX)
        # Stream 1: (1, 1) format: (PAA_TX, PAA_RX)
        # Stream 2: (2, 2) format: (PAA_TX, PAA_RX)
        # print("Test Stream Combination:", streamCombinationId)
        # for j in range(len(mimoTxStreamCombinationsItoR[streamCombinationId])):
        #     print("\tStream:", j, " PAA Tx:", mimoTxStreamCombinationsItoR[streamCombinationId][j][0], " PAA Rx:",
        #           mimoTxStreamCombinationsItoR[streamCombinationId][j][1])

        # Create the entire Tx/Rx sectors combinations for the top K Tx and Rx sectors computed
        allSectorsCombinations = list(
            itertools.product(txTopKCandidatesItoRTable[streamCombinationId],
                              rxTopKCandidatesRtoITable[streamCombinationId]))

        totalNb = 0
        for completeSectorsStreamConfiguration in allSectorsCombinations:
            # Test one of TX/RX sector combination
            # awvList = np.arange(5) # TODO ns-3 is not yet computing MIMO with refined AWV - If we were to use the 5 custom AWV, that's the code to use
            # Here, we configure the AWV to be set to 2 as 2 corresponds by design to the sector itself
            awvList = [2]
            # Create the refined AWVs TX and Rx combinations
            argProduct = []
            for i in range(nbPaaMimoInitiator):
                argProduct.append(awvList)
            allTxAWVCombination = list(itertools.product(*argProduct))
            allRxAWVCombination = list(itertools.product(*argProduct))
            txSectorIdList = completeSectorsStreamConfiguration[0]  # Contain the Tx sector for each stream
            rxSectorIdList = completeSectorsStreamConfiguration[1]  # Contain the Rx sector for each stream
            for txAwvs in allTxAWVCombination:
                for rxAwvs in allRxAWVCombination:
                    # Test one of TX/RX AWV combination for a given Tx/Rx sector combination
                    aStreamCombination = []
                    for streamId in range(nbPaaMimoInitiator):
                        # Configure the individual streams that makes the stream combination
                        aStreamCombination.append(
                            [mimoTxStreamCombinationsItoR[streamCombinationId][streamId][0],
                             txSectorIdList[streamId],
                             mimoTxStreamCombinationsItoR[streamCombinationId][streamId][1], rxSectorIdList[streamId],
                             txAwvs[streamId],
                             rxAwvs[streamId]])
                    sinrCombination = []  # Store the SINR for each stream of a stream combination
                    powerPair = []
                    for intentedTransmission in aStreamCombination:
                        # For each individual stream, compute the Reception Power of the intended transmission
                        intendedTxPaa = intentedTransmission[0]
                        intendedTxSector = intentedTransmission[1]
                        intendedTxRefinedAwv = intentedTransmission[4]
                        intendedRxId = mimoResponderId
                        intendedRxPaa = intentedTransmission[2]
                        intendedRxSector = intentedTransmission[3]
                        intendedRxRefinedAwv = intentedTransmission[5]

                        # Here, we want to compute the power received for the intended transmission
                        # For that, we need to obtain the directivity of the Tx and Rx
                        intendedDirectivityTx = directivityInitiator[(intendedTxSector * 5) + intendedTxRefinedAwv]
                        intendedTxAzimuthAwv, intendedTxElevationAwv = anglesInitiator[
                            (intendedTxSector * 5) + intendedTxRefinedAwv]

                        # # ADD
                        # intendedDirectivityTx = codebooks.getApSectorsDirectivity()
                        # intendedDirectivityTx= intendedDirectivityTx[intendedTxSector]
                        # # NO ADD

                        intendedDirectivityRx = directivityResponder[(intendedRxSector * 5) + intendedRxRefinedAwv]
                        intendedRxAzimuthAwv, intendedRxElevationAwv = anglesResponder[
                            (intendedRxSector * 5) + intendedRxRefinedAwv]

                        # ADD
                        # intendedDirectivityRx = codebooks.getStaSectorsDirectivity()
                        # intendedDirectivityRx = intendedDirectivityRx[intendedRxSector]
                        # NO ADD
                        txRx = (mimoInitiatorId, intendedRxId, intendedTxPaa, intendedRxPaa,
                                traceIndex)
                        # As we will perform the same computations many time, store the results to avoid to recompute
                        if (txRx, intendedTxAzimuthAwv, intendedTxElevationAwv, intendedRxAzimuthAwv,
                            intendedRxElevationAwv) not in testStoredPower:
                            # The Received Power computation has never been performed
                            # Check if we already computed the propagation loss precomputed value
                            if (txRx) not in precomputedValue:
                                # The computation has never been done
                                nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = qdPropagationLoss.precomputeTxValues(
                                    txRx, qdProperties, txParam.getCenterFrequencies())
                                precomputedValue[(
                                    txRx)] = nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading
                            else:
                                # The computation has been done - Get the precomputed values
                                nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = \
                                    precomputedValue[(txRx)]

                            # Compute the received power for the intended transmission
                            intendedRxPower, intendedRxpsd = qdPropagationLoss.computeSteeredRx(
                                intendedDirectivityTx, intendedDirectivityRx, txParam, nbSubBands,
                                qdScenario, codebooks, nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle,
                                elevationRxAngle, smallScaleFading)
                            testStoredPower[(txRx, intendedTxAzimuthAwv, intendedTxElevationAwv, intendedRxAzimuthAwv,
                                             intendedRxElevationAwv)] = intendedRxPower, intendedRxpsd
                        else:
                            # The computation has already been performed - Just get the results
                            intendedRxPower, intendedRxpsd = testStoredPower[(
                                txRx, intendedTxAzimuthAwv, intendedTxElevationAwv, intendedRxAzimuthAwv,
                                intendedRxElevationAwv)]

                        sumInterference = 0
                        for interferingTransmission in aStreamCombination:
                            # For each individual stream, compute the interference due to the other streams transmissions (interfering streams)
                            if interferingTransmission == intentedTransmission:
                                # Do not computed as a stream is not interfering with itself
                                pass
                            else:
                                # Compute the interference generated by every individual streams that is not the intended transmission itself
                                interferingTxPaa = interferingTransmission[0]
                                interferingTxSector = interferingTransmission[1]
                                interferingTxRefinedAwv = interferingTransmission[4]

                                # Here, we are interested to compute the interference created by the transmission - Thus, we don't care about the RX configuration of the interfering transmission
                                # But just the RX configuration of the intended transmission
                                interferingDirectivityTx = directivityInitiator[
                                    (interferingTxSector * 5) + interferingTxRefinedAwv]
                                interferingTxAzimuthAwv, interferingTxElevationAwv = anglesInitiator[
                                    (interferingTxSector * 5) + interferingTxRefinedAwv]

                                # ADD
                                # interferingDirectivityTx = codebooks.getApSectorsDirectivity()
                                # interferingDirectivityTx = interferingDirectivityTx[interferingTxSector]
                                # NO ADD

                                # The directivity Rx must be computed with the intended receiver
                                txRx = (mimoInitiatorId, intendedRxId, interferingTxPaa,
                                        intendedRxPaa, traceIndex)  # 0 is PAA RX
                                # Here, we have the power received for:
                                # MimoInitiatorId(mimoTxAntennaId,txSectorId,txRefinedAwvId) => rxNode(paaRxNode,rxSectorId, rxRefinedAwvId)
                                # We are interested about the interfer transmission to the intended receiver - The awv azimuth and elevation corresponds to the intended one
                                if (txRx, interferingTxAzimuthAwv, interferingTxElevationAwv, intendedRxAzimuthAwv,
                                    intendedRxElevationAwv) not in testStoredPower:
                                    if (txRx) not in precomputedValue:
                                        nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = qdPropagationLoss.precomputeTxValues(
                                            txRx, qdProperties, txParam.getCenterFrequencies())
                                        precomputedValue[(
                                            txRx)] = nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading
                                    else:
                                        nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = \
                                            precomputedValue[(txRx)]

                                    interferingRxPower, interferingRxpsd = qdPropagationLoss.computeSteeredRx(
                                         interferingDirectivityTx,
                                        intendedDirectivityRx, txParam,
                                        nbSubBands,
                                        qdScenario, codebooks, nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle,
                                        elevationRxAngle, smallScaleFading)
                                    testStoredPower[(
                                        txRx, interferingTxAzimuthAwv, interferingTxElevationAwv, intendedRxAzimuthAwv,
                                        intendedRxElevationAwv)] = interferingRxPower, interferingRxpsd
                                else:
                                    interferingRxPower, interferingRxpsd = testStoredPower[
                                        (txRx, interferingTxAzimuthAwv, interferingTxElevationAwv, intendedRxAzimuthAwv,
                                         intendedRxElevationAwv)]
                                sumInterference += qdPropagationLoss.DbmtoW(interferingRxPower)
                                powerPair.append([intendedRxPower, interferingRxPower])
                        # Compute the SINR
                        sinr = 10 * math.log10(
                            qdPropagationLoss.DbmtoW(intendedRxPower) / (txParam.getNoise() + sumInterference))
                        sinrCombination.append(sinr)

                    if min(sinrCombination) > min(bestSinrCombination):
                        # The best stream combination is the one resulting in the highest minimum SINR
                        bestSinrCombination = sinrCombination
                        # for i in range(len(completeSectorsStreamConfiguration[0])):
                        #     print("\t\t\tStream:", i, " Tx Sector(AWV): ", completeSectorsStreamConfiguration[0][i],
                        #           "(",
                        #           txAwvs[i], ") Rx Sector(AWV): ", completeSectorsStreamConfiguration[1][i], "(",
                        #           rxAwvs[i],
                        #           ")", " SNR: ", bestSinrCombination[i], sep='')
                        bestreamIdCombination = mimoTxStreamCombinationsItoR[streamCombinationId]
                        bestSectorsCombination = completeSectorsStreamConfiguration
                        bestAwvCombination = (txAwvs, rxAwvs)
                        bestPowerCombination = powerPair
                    totalNb += 1

        # print("Total Combinations Tested:", totalNb)

    return globals.MimoBeamformingResults(bestreamIdCombination,
                                          traceIndex,
                                          bestreamIdCombination[0],
                                          bestSectorsCombination[0],
                                          bestAwvCombination[0],
                                          bestreamIdCombination[1],
                                          bestSectorsCombination[1],
                                          bestAwvCombination[1]
                                          )


def performMuMimoBft(traceIndex,mimoInitiatorId,anglesInitiator, directivityInitiator,nbPaaMimoInitiator,streamIdItoRTable,txTopKCandidatesItoRTable,mimoResponderId,rxTopKCandidatesRtoITable,anglesResponder,
                   directivityResponder, qdProperties, qdScenario, txParam, nbSubBands, codebooks):
    """
       Perform MU-MIMO MIMO beamforming training phase between an initiator and a responder for a given trace

       Attributes
       ----------
       traceIndex : Int
           The Q-D trace index

       mimoInitiatorId : Int
           ID of the Initiator

       anglesInitiator: Dic
           List of all the Initiator angles (azimuth, elevation) for the custom AWV

       directivityInitiator: Dic
           List of all the Initiator directivity for the custom AWV

       nbPaaMimoInitiator : Int
            Number of PAA of the initiator

       streamIdItoRTable : Dic
            All possible individual stream combinations

       txTopKCandidatesItoRTable : Dic
            Top K tx sector for all possible stream combinations from Initiator to Responder

       rxTopKCandidatesRtoITable: Dic
            Top K tx sector for all possible stream combinations from Responder to Initiator

       mimoResponderId : Int
           ID of the Responder

       anglesResponder: Dic
           List of all the Responder angles (azimuth, elevation) for the custom AWV

       directivityResponder: Dic
           List of all the Responder directivity for the custom AWV

       qdProperties: Class
        Contains the Multiplath Properties

       qdScenario : Class
            Contain the parameters and results for the Q-D scenario used

       txParam: Class
        Contain the transmission parameters

        nbSubBands: Int
            Total number of subbands

        codebooks : Class
            Represents the codebook class
    """
    bestSinrCombination = [-math.inf, -math.inf]
    precomputedValue = {}
    testStoredPower = {}
    for streamCombinationId in range(nbPaaMimoInitiator):
        # Test one of the stream combination, i.e, for example
        # Stream: (0, 0) format: (PAA_TX, RX1_ID)
        # Stream: (1, 1) format: (PAA_TX, RX2_ID)
        # Stream: (2, 2) format: (PAA_TX, RX3_ID)

        # Create the entire Tx/Rx sectors combinations for the top K Tx and Rx sectors computed
        allTxSectorsCombinations = list(
            itertools.product(txTopKCandidatesItoRTable[streamCombinationId], rxTopKCandidatesRtoITable[streamCombinationId]))
        totalNb = 0
        for completeSectorsStreamConfiguration in allTxSectorsCombinations:
            # Test one of TX/RXs sector combination
            # awvList = np.arange(5) # TODO ns-3 is not yet computing MIMO with refined AWV - If we were to use the 5 custom AWV, that's the code to use
            # Here, we configure the AWV to be set to 2 as 2 corresponds by design to the sector itself
            awvList = [2]
            allTxAWVCombination = list(itertools.product(awvList, awvList))
            allRxAWVCombination = list(itertools.product(awvList, awvList))
            txSectorIdList = completeSectorsStreamConfiguration[0]
            rxSectorIdList = completeSectorsStreamConfiguration[1]
            for txAwvs in allTxAWVCombination:
                for rxAwvs in allRxAWVCombination:
                    # Test one of TX/RXs AWVs combination for a given Tx/Rxs sector combination
                    aStreamCombination = []
                    for streamId in range(nbPaaMimoInitiator):
                        # Configure the individual streams that makes the stream combination
                        aStreamCombination.append(
                            [streamIdItoRTable[streamCombinationId][streamId][0], txSectorIdList[streamId],
                             streamIdItoRTable[streamCombinationId][streamId][1], rxSectorIdList[streamId], txAwvs[streamId],
                             rxAwvs[streamId]])
                    sinrCombination = []  # Store the SINR for each stream of a stream combination
                    powerPair = []
                    for intentedTransmission in aStreamCombination:
                        # For each individual stream, compute the Reception Power of the intended transmission
                        intendedTxPaa = intentedTransmission[0]
                        intendedTxSector = intentedTransmission[1]
                        intendedTxRefinedAwv = intentedTransmission[4]
                        intendedRxId = intentedTransmission[2]
                        intendedRxSector = intentedTransmission[3]
                        intendedRxRefinedAwv = intentedTransmission[5]
                        # Here, we want to compute the power received for the intended transmission
                        # For that, we need to obtain the directivity of the Tx and Rx
                        intendedDirectivityTx = directivityInitiator[(intendedTxSector * 5) + intendedTxRefinedAwv]
                        intendedTxAzimuthAwv, intendedTxElevationAwv = anglesInitiator[
                            (intendedTxSector * 5) + intendedTxRefinedAwv]

                        intendedDirectivityRx = directivityResponder[(intendedRxSector * 5) + intendedRxRefinedAwv]
                        intendedRxAzimuthAwv, intendedRxElevationAwv = anglesResponder[
                            (intendedRxSector * 5) + intendedRxRefinedAwv]
                        txRx = (mimoInitiatorId, intendedRxId, intendedTxPaa,
                                0, traceIndex)  # 0 is PAA RX
                        # As we will perform the same computations many time, store the results to avoid to recompute
                        if (txRx, intendedTxAzimuthAwv, intendedTxElevationAwv, intendedRxAzimuthAwv,
                            intendedRxElevationAwv) not in testStoredPower:
                            # The Received Power computation has never been performed
                            # Check if we already computed the propagation loss precomputed value
                            if (txRx) not in precomputedValue:
                                # The computation has never been done
                                nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = qdPropagationLoss.precomputeTxValues(
                                    txRx, qdProperties, txParam.getCenterFrequencies())
                                precomputedValue[(
                                    txRx)] = nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading
                            else:
                                # The computation has been done - Get the precomputed values
                                nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = \
                                    precomputedValue[(txRx)]

                            # Compute the received power for the intended transmission
                            intendedRxPower, intendedRxpsd = qdPropagationLoss.computeSteeredRx(
                                intendedDirectivityTx, intendedDirectivityRx, txParam, nbSubBands,
                                qdScenario, codebooks, nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle,
                                elevationRxAngle, smallScaleFading)
                            testStoredPower[(txRx, intendedTxAzimuthAwv, intendedTxElevationAwv, intendedRxAzimuthAwv,
                                             intendedRxElevationAwv)] = intendedRxPower, intendedRxpsd
                        else:
                            # The computation has already been performed - Just get the results
                            intendedRxPower, intendedRxpsd = testStoredPower[(
                                txRx, intendedTxAzimuthAwv, intendedTxElevationAwv, intendedRxAzimuthAwv,
                                intendedRxElevationAwv)]

                        for interferingTransmission in aStreamCombination:
                            # For each individual stream, compute the interference due to the other streams transmissions (interfering streams)
                            if interferingTransmission == intentedTransmission:
                                # Do not computed as a stream is not interfering with itself
                                pass
                            else:
                                # Compute the interference generated by every individual streams that is not the intended transmission itself
                                interferingTxPaa = interferingTransmission[0]
                                interferingTxSector = interferingTransmission[1]
                                interferingTxRefinedAwv = interferingTransmission[4]
                                # Here, we are interested to compute the interference created by the transmission - Thus, we don't care about the RX configuration of the interfering transmission
                                # But just the RX configuration of the intended transmission
                                interferingDirectivityTx = directivityInitiator[
                                    (interferingTxSector * 5) + interferingTxRefinedAwv]
                                interferingTxAzimuthAwv, interferingTxElevationAwv = anglesInitiator[
                                    (interferingTxSector * 5) + interferingTxRefinedAwv]
                                # The directivity Rx must be computed with the intended receiver
                                txRx = (mimoInitiatorId, intendedRxId, interferingTxPaa,
                                        0, traceIndex)  # 0 is PAA RX
                                # Here, we have the power received for:
                                # MimoInitiatorId(mimoTxAntennaId,txSectorId,txRefinedAwvId) => rxNode(paaRxNode,rxSectorId, rxRefinedAwvId)
                                # We are interested about the interfer transmission to the intended receiver - The awv azimuth and elevation corresponds to the intented one
                                if (txRx, interferingTxAzimuthAwv, interferingTxElevationAwv, intendedRxAzimuthAwv,
                                    intendedRxElevationAwv) not in testStoredPower:
                                    if (txRx) not in precomputedValue:
                                        nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = qdPropagationLoss.precomputeTxValues(
                                            txRx, qdProperties, txParam.getCenterFrequencies())
                                        precomputedValue[(
                                            txRx)] = nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading
                                    else:
                                        nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = \
                                            precomputedValue[(txRx)]

                                    interferingRxPower, interferingRxpsd = qdPropagationLoss.computeSteeredRx(
                                        interferingDirectivityTx,
                                        intendedDirectivityRx, txParam,
                                        nbSubBands,
                                        qdScenario, codebooks, nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle,
                                        elevationRxAngle, smallScaleFading)
                                    testStoredPower[(
                                        txRx, interferingTxAzimuthAwv, interferingTxElevationAwv, intendedRxAzimuthAwv,
                                        intendedRxElevationAwv)] = interferingRxPower, interferingRxpsd
                                else:
                                    interferingRxPower, interferingRxpsd = testStoredPower[
                                        (txRx, interferingTxAzimuthAwv, interferingTxElevationAwv, intendedRxAzimuthAwv,
                                         intendedRxElevationAwv)]
                                sinr = 10 * math.log10(qdPropagationLoss.DbmtoW(intendedRxPower) / (
                                        txParam.getNoise() + qdPropagationLoss.DbmtoW(interferingRxPower)))
                                sinrCombination.append(sinr)
                                powerPair.append([intendedRxPower, interferingRxPower])
                    if min(sinrCombination) > min(bestSinrCombination):
                        bestSinrCombination = sinrCombination
                        bestreamIdCombination = streamIdItoRTable[streamCombinationId]

                        bestSectorsCombination = completeSectorsStreamConfiguration
                        bestAwvCombination = (txAwvs, rxAwvs)
                        # print("best Stream ID:", bestreamIdCombination)
                        # for i in range(len(completeSectorsStreamConfiguration[0])):
                        #     print("\t\t\tStream:", i, " Tx Sector(AWV): ", completeSectorsStreamConfiguration[0][i],
                        #           "(",
                        #           txAwvs[i], ") Rx Sector(AWV): ", completeSectorsStreamConfiguration[1][i], "(",
                        #           rxAwvs[i],
                        #           ")", " SNR: ", bestSinrCombination[i], sep='')
                    totalNb += 1

        # print("Total Nb:", totalNb)


    return globals.MimoBeamformingResults(bestreamIdCombination,
                                   traceIndex,
                                   bestreamIdCombination[0],
                                   bestSectorsCombination[0],
                                   bestAwvCombination[0],
                                   bestreamIdCombination[1],
                                   bestSectorsCombination[1],
                                   bestAwvCombination[1]
                                   )

def computeSuMimoBft(mimoInitiatorId, mimoResponderId, traceIndex, qdScenario, qdProperties, txParam, nbSubBands,
                     codebooks, topK=20):
    """
       Compute SU-MIMO results between an initiator and a responder for a given trace

       Attributes
       ----------
       mimoInitiatorId : Int
           ID of the Initiator

       mimoResponderId : Int
           ID of the Responder

       traceIndex : Int
           The Q-D trace index

       qdScenario : Class
            Contain the parameters and results for the Q-D scenario used

       qdProperties: Class
        Contains the Multiplath Properties

       txParam: Class
        Contain the transmission parameters

        nbSubBands: Int
            Total number of subbands

        codebooks : Class
            Represents the codebook class
    """
    nbPaaMimoInitiator = codebooks.getNbPaaNode(qdScenario.getNodeType(mimoInitiatorId))
    nbPaaMimoResponder = codebooks.getNbPaaNode(qdScenario.getNodeType(mimoResponderId))

    directivityInitiator, anglesInitiator = getDirectivity(mimoInitiatorId, qdScenario, codebooks)
    directivityResponder, anglesResponder = getDirectivity(mimoResponderId, qdScenario, codebooks)

    mimoTxStreamCombinationsItoR = getSuMimoAllValidStreamCombinations(nbPaaMimoInitiator, nbPaaMimoResponder)
    ############################################################
    # MIMO SISO PHASE FROM INITIATOR TO RESPONDER              #
    ############################################################
    # Compute the SISO phase from the initiator to the responder
    mimoSisoResultsItoR = performSuMimoSisoPhase(mimoInitiatorId, mimoResponderId, nbPaaMimoInitiator, nbPaaMimoResponder,
                                               traceIndex, qdProperties, txParam,
                                               nbSubBands,
                                               qdScenario, codebooks)
    # txTopKCandidatesItoR contains the top K candidates for all possible stream combination
    # The key is made of the stream combinations, e.g, Combination 1: Stream1 [(PAA TX: 0,PAA RX:0), Stream2 (PAA TX: 1,PAA RX:1)]
    # The values are a list made of top K join SNR and Tx sector combination values, e.g,  [[joint SNR Combination 1, (Tx Sector Stream 1, Tx Sector Stream 2)]
    # txTopKCandidatesItoRTable is a list containing the top K tx sector for all possible stream combinations
    # e.g, Combination 1 [(Tx Sector Combination 1: (9, 9),Tx Sector Combination 2: (0, 9), Tx Sector Combination K: (12, 9))], Combination 2
    txTopKCandidatesItoR, txTopKCandidatesItoRTable = getSuMimoTopKSnr(mimoInitiatorId, nbPaaMimoInitiator,
                                                                 mimoTxStreamCombinationsItoR,
                                                                 mimoSisoResultsItoR,
                                                                 qdScenario, codebooks,topK)

    # ############################################################
    # # ALL POSSIBLE INDIVIDUAL STREAM RESPONDER TO INITIATOR    #
    # ############################################################
    mimoTxStreamCombinationsRtoI = getSuMimoAllValidStreamCombinations(nbPaaMimoResponder, nbPaaMimoInitiator)
    ############################################################
    # MIMO SISO PHASE FROM RESPONDER TO INITIATOR              #
    ############################################################
    # Compute the SISO phase from the initiator to the responder
    mimoSisoResultsRtoI = performSuMimoSisoPhase(mimoResponderId, mimoInitiatorId, nbPaaMimoResponder, nbPaaMimoInitiator,
                                               traceIndex, qdProperties, txParam,
                                               nbSubBands,
                                               qdScenario, codebooks)

    ##################################################
    # TOP K FROM RESPONDER TO INITIATOR              #
    ##################################################
    txTopKCandidatesRtoI, rxTopKCandidatesRtoITable = getSuMimoTopKSnr(mimoResponderId,
                                                                 nbPaaMimoResponder,
                                                                 mimoTxStreamCombinationsRtoI,
                                                                 mimoSisoResultsRtoI,
                                                                 qdScenario, codebooks, topK)



    results = performSuMimoBft(traceIndex, mimoInitiatorId, anglesInitiator, directivityInitiator, mimoResponderId, anglesResponder,
                   directivityResponder, nbPaaMimoInitiator, mimoTxStreamCombinationsItoR, txTopKCandidatesItoRTable,
                   rxTopKCandidatesRtoITable, qdProperties, qdScenario, txParam, nbSubBands, codebooks)

    return results

def preprocessCompleteSuMimo(mimoInitiatorId, mimoResponderId, qdChannel, qdScenario, txParam,
                             nbSubBands, codebooks,suMimoPickledFile):
    """Precompute all the SU MIMO results between mimoInitiatorId and mimoResponderId

        Parameters
        ----------
        mimoInitiatorId : int
            The ID of the MIMO initiator

        mimoResponderId : int
            The ID of the MIMO responder

        qdChannel : Class
            Contains all the Q-D values for the channel

        qdScenario : Class
            Contain the parameters and results for the Q-D scenario used

        txParam : TxParam class
            The transmission parameters

        nbSubBands : int
            Number of subbands to use

        codebooks : Codebooks class
            Directivity of the AP and STA nodes (sectors and quasi-omni directivity)

        suMimoPickledFile : str
            The name of the file that will contain the pickled SU-MIMO results
    """
    print("The oracle will now compute all the SU-MIMO results for the pair Mimo Initiator:",mimoInitiatorId,"=> Mimo Responder:",mimoResponderId," - This process can be long")
    suMimoResults = {}
    topK=200 # We set the top K to a higher value when preprocessed
    for traceIndex in range(qdScenario.nbTraces):
        print("Trace:",traceIndex, " SU-MIMO BF computed - ", qdScenario.nbTraces-traceIndex, "traces remaining")
        # Iterate over all the traces for the pair and compute SU-MIMO results
        results = computeSuMimoBft(mimoInitiatorId, mimoResponderId,traceIndex,
             qdScenario, qdChannel, txParam, nbSubBands, codebooks, topK)
        suMimoResults[traceIndex,mimoInitiatorId,mimoResponderId] = results

    # Pickle the results
    pickle.dump(suMimoResults, open(suMimoPickledFile, "wb"),
                 protocol=pickle.HIGHEST_PROTOCOL)
    return suMimoResults

def computeMuMimoBft(mimoInitiatorId,mimoResponderIds,traceIndex,qdScenario, qdProperties, txParam, nbSubBands, codebooks, topK=20):
    """
       Compute MU-MIMO results between an initiator and responders for a given trace

       Attributes
       ----------
       mimoInitiatorId : Int
           ID of the Initiator

       mimoResponderId : Int
           ID of the Responder

       traceIndex : Int
           The Q-D trace index

       qdScenario : Class
            Contain the parameters and results for the Q-D scenario used

       qdProperties: Class
        Contains the Multiplath Properties

       txParam: Class
        Contain the transmission parameters

        nbSubBands: Int
            Total number of subbands

        codebooks : Class
            Represents the codebook class
    """
    directivityInitiator, anglesInitiator = getDirectivity(mimoInitiatorId, qdScenario, codebooks)
    directivityResponder, anglesResponder = getDirectivity(mimoResponderIds[0], qdScenario, codebooks) # We assume all nodes to be the same type

    nbPaaMimoInitiator = codebooks.getNbPaaNode(qdScenario.getNodeType(mimoInitiatorId))
    nbSectorsPerPaaMimoInitiator = codebooks.getNbSectorsPerPaaNode(qdScenario.getNodeType(mimoInitiatorId))
    nbSectorsPerPaaMimoResponder = codebooks.getNbSectorsPerPaaNode(qdScenario.getNodeType(1))  # TODO Should be automatic
    if len(np.arange(nbPaaMimoInitiator)) != len(mimoResponderIds):
        print("The number of PAA of the MIMO Initiator must be equal to the number of receivers")
        exit()

    ############################################################
    #                               INITIATOR PART             #
    ############################################################
    # Get all possible streams combination from initiator to responder
    mimoTxStreamCombinationsItoR = getMuMimoAllValidStreamCombinations(np.arange(nbPaaMimoInitiator), mimoResponderIds)
    # Perform the SISO phase of MU-MIMO from initiator to responder
    sisoInitiatorToResponderList = performMuMimoSisoPhase("initiator",mimoInitiatorId,nbPaaMimoInitiator, mimoResponderIds, traceIndex, qdProperties, txParam,nbSubBands,qdScenario, codebooks)
    # Get the top-K from initiator to responder
    txTopKCandidatesItoR,txTopKCandidatesItoRTable, streamIdItoRTable = getMuMimoTopKSnr("initiator", mimoInitiatorId, nbPaaMimoInitiator,nbSectorsPerPaaMimoInitiator, mimoTxStreamCombinationsItoR, sisoInitiatorToResponderList, topK)

    ############################################################
    #                    RESPONDER PART                        #
    ############################################################
    # Get all possible streams combination from responder to initiator
    mimoTxStreamCombinationsRtoI = getMuMimoAllValidStreamCombinations(mimoResponderIds,np.arange(nbPaaMimoInitiator))
    # Perform the SISO phase of MU-MIMO from responder to initiator
    sisoResponderToInitiatorList = performMuMimoSisoPhase("responder", mimoInitiatorId, nbPaaMimoInitiator,
                                                          mimoResponderIds, traceIndex, qdProperties, txParam,
                                                          nbSubBands, qdScenario, codebooks)
    # Get the top-K from responder to initiator
    rxTopKCandidatesRtoI, rxTopKCandidatesRtoITable, streamIdRtoITable = getMuMimoTopKSnr("responder", mimoResponderIds,
                                                                                          nbPaaMimoInitiator,
                                                                                          nbSectorsPerPaaMimoResponder,
                                                                                          mimoTxStreamCombinationsRtoI,
                                                                                          sisoResponderToInitiatorList, topK)
    results = performMuMimoBft(traceIndex,mimoInitiatorId,anglesInitiator,directivityInitiator, nbPaaMimoInitiator,streamIdItoRTable,txTopKCandidatesItoRTable,mimoResponderIds,rxTopKCandidatesRtoITable,anglesResponder,
                   directivityResponder, qdProperties, qdScenario, txParam, nbSubBands, codebooks)

    return results

def preprocessCompleteMuMimo(mimoInitiatorId, mimoGroupId, qdChannel, qdScenario, txParam,
                             nbSubBands, codebooks,muMimoPickledFile):
    """Precompute all the SU MIMO results between mimoInitiatorId and mimoResponderId

        Parameters
        ----------
        mimoInitiatorId : int
            The ID of the MIMO initiator

        mimoGroupId : int
            The ID of the MIMO Group

        qdChannel : Class
            Contains all the Q-D values for the channel

        qdScenario : Class
            Contain the parameters and results for the Q-D scenario used

        txParam : TxParam class
            The transmission parameters

        nbSubBands : int
            Number of subbands to use

        codebooks : Codebooks class
            Directivity of the AP and STA nodes (sectors and quasi-omni directivity)

        muMimoPickledFile : str
            The name of the file that will contain the pickled MU-MIMO results
    """
    print("The oracle will now compute all the MU-MIMO results for the Mimo Initiator:",mimoInitiatorId,"=> MIMO Group",mimoGroupId," - This process can be long")
    muMimoResults = {}
    # For now, we hardcode the MIMO Initiator and MIMO Responders
    mimoInitiatorId = 0
    mimoResponderIds = [1, 2]
    topK = 200
    for traceIndex in range(qdScenario.nbTraces):
        print("Trace:", traceIndex, " SU-MIMO BF computed - ", qdScenario.nbTraces - traceIndex, "traces remaining")
        results = computeMuMimoBft(mimoInitiatorId,mimoResponderIds,traceIndex,qdScenario, qdScenario.qdChannel, txParam, 355, codebooks, topK)
        muMimoResults[traceIndex,mimoGroupId] = results

    pickle.dump(muMimoResults, open(muMimoPickledFile, "wb"),
                 protocol=pickle.HIGHEST_PROTOCOL)

    return muMimoResults


def preprocessData(qdScenario, qdProperties, txParam, nbSubBands, codebooks):
    """Generate the SLS data (Best Sector, best Rx Power, and Rx power per sector) and STA association data

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    qdProperties : QdProperties class
        MPCs characteristics

    txParam : TxParam class
        The transmission parameters

    nbSubBands : int
        Number of subbands to use

    codebooks : Codebooks class
        Directivity of the AP and STA nodes (sectors and quasi-omni directivity)

    Returns
    -------
    preprocessedSlsData : SlsResults class
        The preprocessed data for the SLS Phase
    staAssociationDic : Dic
        The preprocessed association Data
    dataIndex: Dic
        Used to reconstruct the index of the preprocessed data
    """
    print("The oracle will now compute all the data for every pair of nodes and PAAs - This process can be long")
    nbNodesPermutations = globals.nPr(qdScenario.nbNodes,
                                      2)  # Total number of nodes permutations (used for progress bar)
    startProcess = time.time()
    globals.printProgressBar(0, nbNodesPermutations, 0, prefix='Progress:', suffix='Complete', length=50)
    staAssociationDic = {}
    numberOfPair = 0
    dataPath = os.path.join(globals.scenarioPath, globals.dataFolder)
    if not os.path.exists(dataPath):
        os.makedirs(dataPath)
    dataRxPowerPath = os.path.join(dataPath, globals.slsFolder, globals.rxPowerItxssFolder)
    if not os.path.exists(dataRxPowerPath):
        os.makedirs(dataRxPowerPath)
    bestItxssPath = os.path.join(dataPath, globals.slsFolder, globals.bestSectorItxssFolder)
    if not os.path.exists(bestItxssPath):
        os.makedirs(bestItxssPath)
    bestSectorIdList = []
    powerPerSectorList = []
    bestSectorRxPowerList = []
    for txId in range(qdScenario.nbNodes):
        # Iterate all the Tx nodes
        for rxId in range(qdScenario.nbNodes):
            # Iterate all the Rx nodes
            if txId != rxId:
                for txAntennaID in range(codebooks.getNbPaaNode(qdScenario.getNodeType(txId))):
                    # Iterate over all the Tx PAAs
                    for rxAntennaID in range(codebooks.getNbPaaNode(qdScenario.getNodeType(rxId))):
                        # Iterate over all the Rx PAAs
                        rxPowerITXSSList = []
                        snrITXSSList = []
                        bestSectorITXSSList = []
                        numberOfPair += 1
                        startSLSTime = time.time()

                        print("Compute for:", txId, rxId, txAntennaID, rxAntennaID)
                        for traceIndex in range(qdScenario.nbTraces):
                            rxPowerITXSS, snrITXSS, psdBestSectorITXSS, txssSectorITXSS, rxPowerSectorListITXSS = performSls(
                                (txId, rxId, txAntennaID, rxAntennaID, traceIndex), qdProperties, txParam, nbSubBands,
                                qdScenario, codebooks)
                            rxPowerITXSSList.append(rxPowerITXSS)
                            snrITXSSList.append(snrITXSS)
                            bestSectorITXSSList.append(txssSectorITXSS)
                            bestSectorIdList.append(txssSectorITXSS)
                            powerPerSectorList.append(rxPowerSectorListITXSS)
                            bestSectorRxPowerList.append(rxPowerITXSS)
                            # Determine to which AP is a STA associated for a given trace (we are using the received power)
                            if qdScenario.isNodeAp(txId) and qdScenario.isNodeSta(rxId):
                                if (rxId, traceIndex) not in staAssociationDic:
                                    # No computation has been done previously - Just store the values computed for the AP idTx for the STA IdRx
                                    staAssociationDic[(rxId, traceIndex)] = (rxPowerITXSS, txId, txssSectorITXSS)
                                else:
                                    if staAssociationDic[(rxId, traceIndex)][0] < rxPowerITXSS:
                                        # Update the AP to which a STA will associate if the power received is greater
                                        staAssociationDic[(rxId, traceIndex)] = (
                                            rxPowerITXSS, txId, txssSectorITXSS)

                        rxPowerData = {'traceIndex': np.arange(qdScenario.nbTraces),
                                       'rxPower': rxPowerITXSSList,
                                       'beginTrace(s)': np.arange(qdScenario.nbTraces) * qdScenario.timeStep,
                                       'endTrace(s)': np.arange(1, qdScenario.nbTraces + 1) * qdScenario.timeStep
                                       }
                        rxPowerDataFrame = pd.DataFrame(rxPowerData, columns=['traceIndex', 'rxPower', 'beginTrace(s)',
                                                                              'endTrace(s)'])
                        rxPowerFileName = "RxPower" + "Node" + str(txId) + "Node" + str(rxId) + "PAATx" + str(
                            txAntennaID) + "PAARx" + str(rxAntennaID) + ".csv"
                        globals.saveData(rxPowerDataFrame, dataRxPowerPath, rxPowerFileName)

                        bestItxssSectorData = {'traceIndex': np.arange(qdScenario.nbTraces),
                                               'sector': bestSectorITXSSList,
                                               'beginTrace(s)': np.arange(qdScenario.nbTraces) * qdScenario.timeStep,
                                               'endTrace(s)': np.arange(1,
                                                                        qdScenario.nbTraces + 1) * qdScenario.timeStep
                                               }
                        bestItxssSectorDataFrame = pd.DataFrame(bestItxssSectorData,
                                                                columns=['traceIndex', 'sector', 'beginTrace(s)',
                                                                         'endTrace(s)'])

                        bestItxssFileName = "BestSector" + "Node" + str(txId) + "Node" + str(rxId) + "PAATx" + str(
                            txAntennaID) + "PAARx" + str(rxAntennaID) + ".csv"
                        globals.saveData(bestItxssSectorDataFrame, bestItxssPath, bestItxssFileName)
                        totalTime = time.time() - startProcess

                        averageProcessTime = totalTime / numberOfPair
                        remainingTime = round(averageProcessTime * (nbNodesPermutations - numberOfPair))

                        globals.printProgressBar(numberOfPair, nbNodesPermutations,
                                                 datetime.timedelta(0, remainingTime), prefix='Progress:',
                                                 suffix='Complete',
                                                 length=50)
                        endSLSTime = time.time()

    # Code to downcast the values to save some space when we write them if needed TODO Remove or add the option
    bestSectorIdList = np.asarray(bestSectorIdList, dtype=np.int16)

    # We want to save numpy array only and the number of sectors can be different between STA and AP (ragged arrays)
    # Pad the Numpy array to avoid ragged arrays
    n = len(powerPerSectorList)
    m = max([len(x) for x in powerPerSectorList])

    A = np.zeros((n, m))
    for i in range(n):
        A[i, :len(powerPerSectorList[i])] = powerPerSectorList[i]
    # Code to downcast the values to save some space when we write them if needed TODO Remove or add the option
    # powerPerSectorList = np.asarray(A, dtype=np.float16)
    powerPerSectorList = np.asarray(A)
    # Code to downcast the values to save some space when we write them if needed TODO Remove or add the option
    # bestSectorRxPowerList = np.asarray(bestSectorRxPowerList, dtype=np.float16)
    bestSectorRxPowerList = np.asarray(bestSectorRxPowerList)

    # Store SLS preprocessed data
    slsPath = os.path.join(globals.scenarioPath, globals.preprocessedFolder, globals.slsFolder)
    if not os.path.exists(slsPath):
        os.makedirs(slsPath)
    np.savez(open(os.path.join(slsPath, "allSlsResultsNumpy.npy"), "wb"), bestSector=bestSectorIdList,
             allPower=powerPerSectorList,
             bestPower=bestSectorRxPowerList)
    # Store association data
    associationPath = os.path.join(globals.scenarioPath, globals.preprocessedFolder, globals.associationFolder)
    if not os.path.exists(associationPath):
        os.makedirs(associationPath)
    pickle.dump(staAssociationDic, open(os.path.join(associationPath, "associationResults.p"), "wb"),
                protocol=pickle.HIGHEST_PROTOCOL)

    preprocessedSlsData = SlsResults(bestSectorIdList, powerPerSectorList, bestSectorRxPowerList)
    dataIndex = constructIndex(qdScenario, codebooks)
    return preprocessedSlsData, staAssociationDic, dataIndex


def loadPreprocessedData(qdScenario, codebooks):
    """Load the precomputed SLS data (Best Sector, best Rx Power, and Rx power per sector) and association data

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    codebooks : Codebooks class
        Directivity of the AP and STA nodes (sectors and quasi-omni directivity)

    Returns
    -------
    preprocessedSlsData : SlsResults class
        The preprocessed data for the SLS Phase
    staAssociationDic : Dic
        The preprocessed association Data
    dataIndex: Dic
        Used to reconstruct the index of the preprocessed data
    """
    slsPath = os.path.join(globals.scenarioPath, globals.preprocessedFolder, globals.slsFolder)
    associationPath = os.path.join(globals.scenarioPath, globals.preprocessedFolder, globals.associationFolder)
    staAssociationDic = pickle.load(open(os.path.join(associationPath, "associationResults.p"), "rb"))

    allSlsResultsDicNpy = np.load(os.path.join(slsPath, "allSlsResultsNumpy.npy"))
    bestSectorIdList = allSlsResultsDicNpy['bestSector']
    powerPerSectorList = allSlsResultsDicNpy['allPower']
    bestSectorRxPowerList = allSlsResultsDicNpy['bestPower']
    preprocessedSlsData = SlsResults(bestSectorIdList, powerPerSectorList, bestSectorRxPowerList)
    dataIndex = constructIndex(qdScenario, codebooks)
    return preprocessedSlsData, staAssociationDic, dataIndex


def constructIndex(qdScenario, codebooks):
    """Construct the dictionary containing the indexing mapping between (IdTx,IdRx,IdPaaTx,IdPaaRx,traceIndex) tuple and preprocessed numpy row

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    codebooks : Codebooks class
        Directivity of the AP and STA nodes (sectors and quasi-omni directivity)

    Returns
    -------
    dataIndex: Dic
        Used to reconstruct the index of the preprocessed data
    """
    nbIndex = 0
    dataIndex = {}
    for txId in range(qdScenario.nbNodes):
        # Iterate all the Tx nodes
        for rxId in range(qdScenario.nbNodes):
            # Iterate all the Rx nodes
            if txId != rxId:
                for txAntennaID in range(codebooks.getNbPaaNode(qdScenario.getNodeType(txId))):
                    # Iterate over all the Tx PAAs
                    for rxAntennaID in range(codebooks.getNbPaaNode(qdScenario.getNodeType(rxId))):
                        # Iterate over all the Rx PAAs
                        for traceIndex in range(qdScenario.nbTraces):
                            # Iterate over all the Tx PAAs
                            dataIndex[(txId, rxId, txAntennaID, rxAntennaID, traceIndex)] = nbIndex
                            nbIndex += 1
    return dataIndex


def getIndex(tuple):
    """Get the numpy row index for prepocessed data for a given (IdTx,IdRx,IdPaaTx,IdPaaRx,traceIndex) tuple

    Parameters
    ----------
    tuple : tuple
        (IdTx,IdRx,IdPaaTx,IdPaaRx,traceIndex) tuple

    Returns
    -------
    index: Int
        The numpy row to use for a (IdTx,IdRx,IdPaaTx,IdPaaRx,traceIndex) tuple
    """
    index = globals.dicIndexToRemove[tuple]
    return index
