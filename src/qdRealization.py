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
import datetime
import json
import os
import time
import pickle
import numpy as np

import globals
sizeTrcsNdsRlfsTgtsJts = []
class InitialOrientation:
    """
    A class to represent the Initial Orientation

    Attributes
    ----------
    x : Float
        The x initial orientation

    y : Float
        The y initial orientation
    z: Float
        The z initial orientation
    """
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return "x:" + str(self.x) + " y:" + str(self.y) + "z:" + str(self.z)


class QdProperties():
    """
    A class to store the MPCs properties
    """
    DicNbMultipathTxRx = {}
    DicDelayTxRx = {}
    DicPathLossTxRx = {}
    DicPhaseTxRx = {}
    DicAodElevationTxRx = {}
    DicAodAzimuthTxRx = {}
    DicAoaElevationTxRx = {}
    DicAoaAzimuthTxRx = {}


class QdScenario:
    """
    A class to store the Q-D scenario parameters and results
    """
    def __init__(self, nbNodes, nbTraces, timeStep,qdInterpreterConfig):
        self.nbNodes = nbNodes
        self.nbTraces = nbTraces
        self.timeStep = timeStep
        self.qdInterpreterConfig = qdInterpreterConfig
        # What is done below (attributes set to None) is not really the best practice and can be dangerous
        # as the creation of the instance contains non-initialized attributes
        # The reason to do so is that I want the user to at least know the existence of these attributes
        # Creational pattern could be used instead
        self.nbAps = None
        self.nbStas = None
        self.nodesMobility = None
        self.nodesRotation = None
        self.paasInitialOrientation= None
        self.paasPosition = None
        self.nodesType = None
        self.targetPosition = None
        self.targetConnection = []
        self.nbTargets = None
        self.maxReflectionOrderTarget = None
        self.nsSlsResults = None
        self.beamTrackingResults = None
        self.maxSupportedStreams = 0
        self.nsSuMimoResults = None
        self.oracleSuMimoResults = None
        self.nsMuMimoResults = None
        self.oracleMuMimoResults = None
        self.preprocessedSlsData = None
        self.preprocessedAssociationData = None
        self.dataIndex = None
        self.qdProperties = None

    def getTxSectorAnalogBT(self, traceIndex):
        """
        Get the transmitter analog Beamforming Training sector for a given trace

        Parameters
        ----------
        nbAps : int
            traceIndex : The Q-D trace index
        """
        return self.beamTrackingResults.analogBeamTrackingResults[traceIndex].txSectorId

    def getRxSectorAnalogBT(self, traceIndex):
        """
        Get the receiver analog Beamforming Training sector for a given trace

        Parameters
        ----------
        nbAps : int
            traceIndex : The Q-D trace index
        """
        return self.beamTrackingResults.analogBeamTrackingResults[traceIndex].rxSectorId

    def getTxAwvAnalogBT(self, traceIndex):
        """
        Get the transmitter analog Beamforming Training AWV for a given trace

        Parameters
        ----------
        nbAps : int
            traceIndex : The Q-D trace index
        """
        return self.beamTrackingResults.analogBeamTrackingResults[traceIndex].txAwvId

    def getRxAwvAnalogBT(self, traceIndex):
        """
        Get the receiver analog Beamforming Training AWV for a given trace

        Parameters
        ----------
        nbAps : int
            traceIndex : The Q-D trace index
        """
        return self.beamTrackingResults.analogBeamTrackingResults[traceIndex].rxAwvId

    def getTxPaaAnalogBT(self, traceIndex):
        """
        Get the transmitter analog Beamforming Training PAA for a given trace

        Parameters
        ----------
        nbAps : int
            traceIndex : The Q-D trace index
        """
        return self.beamTrackingResults.analogBeamTrackingResults[traceIndex].txAntennaId

    def getRxPaaAnalogBT(self, traceIndex):
        """
        Get the receiver analog Beamforming Training PAA for a given trace

        Parameters
        ----------
        nbAps : int
            traceIndex : The Q-D trace index
        """
        return self.beamTrackingResults.analogBeamTrackingResults[traceIndex].rxAntennaId

    def setNodesConfiguration(self, nbAps, nbStas, nbNodes):
        """Set the number of APs, STAs, and total nodes

        Parameters
        ----------
        nbAps : int
            Number of APs
        nbStas: int
            Number of STAs
        nbNodes: int
            Total Number of Nodes
        """
        self.nbAps = nbAps
        self.nbStas = nbStas
        self.nbNodes = nbNodes

    def setNodesMobility(self, nodesMobility):
        """Set the nodes mobility (i.e., positions)

        Parameters
        ----------
        nodesMobility : Numpy array
            Contain all the nodes x,y,z positions
        """
        self.nodesMobility = nodesMobility

    def getAllNodesAllPositions(self):
        """Get all nodes coordinates for all the traces

        Returns
        -------
        npCoordinates: numpy array
            The x,y,z coordinates of all nodes for all traces
        """
        return self.nodesMobility

    def getAllNodesPosition(self,traceIndex):
        """Get all nodes coordinates for a given trace

        Parameters
        ----------
        traceIndex : int
            The trace identifier

        Returns
        -------
        npCoordinates: numpy array
            The x,y,z coordinates of all nodes for a given trace
        """
        return self.nodesMobility[traceIndex, :, :]

    def getAllAPsPosition(self,traceIndex):
        """Get all APs coordinates for a given trace

        Parameters
        ----------
        traceIndex : int
            The trace identifier

        Returns
        -------
        npCoordinates: numpy array
            The x,y,z coordinates of all the APs nodes for a given trace
        """
        return self.nodesMobility[traceIndex, ::, :self.nbAps]

    def getAllSTAsPosition(self,traceIndex):
        """Get all STAs coordinates for a given trace

        Parameters
        ----------
        traceIndex : int
            The trace identifier

        Returns
        -------
        npCoordinates: numpy array
            The x,y,z coordinates of all the STAs nodes for a given trace
        """
        return self.nodesMobility[traceIndex, ::, self.nbAps:self.nbNodes]

    def getAllSTAsAllPositions(self):
        """Get all STAs coordinates for all the traces

        Returns
        -------
        npCoordinates: numpy array
            The x,y,z coordinates of all the STAs nodes for all traces
        """
        return self.nodesMobility[::, ::, self.nbAps:self.nbNodes]

    def getNodePosition(self,traceIndex, nodeID):
        """Get a node coordinates for a given trace

        Parameters
        ----------
        traceIndex : int
            The trace identifier

        nodeID : int
            The Node Identifier

        Returns
        -------
        npCoordinates: numpy array
            The x,y,z coordinates of the node for a given trace
        """

        return self.nodesMobility[traceIndex, ::, nodeID]

    def getNodeAllPositions(self, nodeID):
        """Get a node coordinates for all Traces

        Parameters
        ----------
        nodeID : int
            The Node Identifier

        Returns
        -------
        npCoordinates: numpy array
            The x,y,z coordinates of the node for all traces
        """

        return self.nodesMobility[::, ::, nodeID]

    def setNodesRotation(self,nodesRotation):
        """Set the nodes rotations (i.e., devices rotations)

        Parameters
        ----------
        nodesMobility : Numpy array
            Contain all the nodes x,y,z rotations of the devices
        """
        self.nodesRotation = nodesRotation

    def getAllSTAsAllRotations(self):
        """Get the nodes rotations (i.e., devices rotations)

        Returns
        ----------
        nodesRotation : Numpy array
            Contain all the nodes x,y,z rotations of the devices
        """
        return self.nodesRotation[::, ::, self.nbAps:self.nbNodes]

    def getAllNodesRotation(self,traceIndex):
        """Get all nodes rotations for a given trace

        Parameters
        ----------
        traceIndex : int
            The trace identifier

        Returns
        -------
        npCoordinates: numpy array
            The rotation x,y,z coordinates of all nodes for a given trace (device rotation)
        """
        return self.nodesRotation[traceIndex, :, :]

    def getNodeRotation(self,traceIndex, nodeID):
        """Get a node rotation for a given trace

        Parameters
        ----------
        traceIndex : int
            The trace identifier

        nodeID : int
            The Node Identifier

        Returns
        -------
        npCoordinates: numpy array
            The x,y,z rotation of the node for a given trace
        """

        if self.nodesRotation[::, ::, nodeID].shape[0] == 1:
            # Nodes Rotations can either be made of:
            # - N rotations (N being the number of traces) when the node is rotating
            # - 1 rotation if the device does not rotate - We handle this case here
            traceIndex = 0


        return self.nodesRotation[traceIndex, ::, nodeID]

    def setPaasPosition(self,paasPosition):
        """Set the PAAs centroid positions

        Parameters
        ----------
        paasPosition : Numpy array
            Contain all the PAAs centroids x,y,z positions
        """
        self.paasPosition = paasPosition

    def getPaaPosition(self,node, paa, traceIndex):
        """Get the PAA centroid of the PAA paa of the Node node for the trace traceIndex

        Parameters
        ----------
        node : int
            The node ID
        paa : int array
            The PAA ID
        traceIndex : int
            The trace identifier
        Returns
        ----------
        x : Numpy array
            X positions of the PAA centroid
        y : Numpy array
            Y position of the PAA centroid
        z: Numpy array
            Z position of the PAA centroid
        """
        if self.paasPosition[node, paa].shape[1] == 1:
            # PAA positions can either be made of:
            # - N positions (N being the number of traces) when the node is moving
            # - 1 positions if the device does not move - We handle this case here
            traceIndex = 0

        x = self.paasPosition[node, paa][0, traceIndex]
        y = self.paasPosition[node, paa][1, traceIndex]
        z = self.paasPosition[node, paa][2, traceIndex]
        return x, y, z

    def setPaasInitialOrientation(self,paasInitialOrientation):
        """Set the PAAs Initial Orientation

        Parameters
        ----------
        paasInitialOrientation : Numpy array
            The Initial Orientations of all PAAs of all Nodes
        """
        self.paasInitialOrientation = paasInitialOrientation

    def getPaaInitialOrientation(self,nodeIndex, paaId):
        """Get the initial orientation of a node PAA

        Parameters
        ----------
        nodeIndex : int
            The node identifier

        paaId : int
            The PAA identifier

        Returns
        -------
        npCoordinates: numpy array
            The PAA initial orientation of the PAA paaId of the node nodeIndex
        """
        return self.paasInitialOrientation[(nodeIndex, paaId)]

    def setNodesType(self, nodesType):
        """Set the Nodes Type for all the nodes in the scenario

        Parameters
        ----------
        paasInitialOrientation : Numpy array
            The Initial Orientations of all PAAs of all Nodes
        """
        self.nodesType = nodesType

    def getNodeType(self,nodeId):
        """Return the node Type
        """
        return self.nodesType[nodeId].type

    def isNodeAp(self,nodeId):
        """Return True if the node nodeId is an AP

        Parameters
        ----------
        nodeId : int
            The Node ID
        """
        if self.getNodeType(nodeId) == globals.NodeType.AP:
            return True
        else:
            return False

    def isNodeSta(self,nodeId):
        """Return True if the node nodeId is a STA

        Parameters
        ----------
        nodeId : int
            The Node ID
        """
        if self.getNodeType(nodeId) == globals.NodeType.STA:
            return True
        else:
            return False

class BeamTrackingResults:
    """A class to store BeamTracking results
    """
    def __init__(self, analogBeamTrackingResults,maxSupportedStream,digitalCombinerWeights,digitalPrecoderWeights):
        self.analogBeamTrackingResults = analogBeamTrackingResults
        self.maxSupportedStream = maxSupportedStream
        self.digitalCombinerWeights = digitalCombinerWeights
        self.digitalPrecoderWeights = digitalPrecoderWeights

class SensingResults:
    """A class to store sensing results
    """
    def __init__(self, available,slowTime, fastTime, velocity, dopplerRange):
        self.available = available
        self.slowTime = slowTime
        self.fastTime = fastTime
        self.velocity = velocity
        self.dopplerRange = dopplerRange



def readQdConfiguration(qdRealizationInputFolder, qdConfigurationFile):
    """Read the config file used in the Q-D realization software

    Parameters
    ----------
    qdRealizationInputFolder : string
        Name of the folder containing the Input files used by the Q-D realization software to generate the channel

    qdConfigurationFile : string
        Name of the Q-D realization software configuration file

    qdJSONFile : string
        Name of the Q-D file to read

    Returns
    -------
    nbNodes : int
        Number of nodes in the Q-D realization software
    """

    globals.logger.info("Read Q-D realization configuration file")
    fileName = os.path.join(qdRealizationInputFolder, qdConfigurationFile)
    try:
        with open(fileName, newline='') as csvfile:
            readCSV = csv.reader(csvfile, delimiter='\t')  # TODO Not going to work if not separated by a tab
            for row in readCSV:
                if row[0] == 'numberOfTimeDivisions':
                    timeDivision = int(row[1])
                    globals.logger.info("Channel Realization Number of Time Divisions:" + str(timeDivision))
                elif row[0] == 'totalTimeDuration':
                    totalTime = float(row[1])
                    globals.logger.info("Total Time:" + str(totalTime))
                elif row[0] == 'environmentFileName':
                    environmentFile = row[1]
                    globals.logger.info("Environment File Name:" + str(environmentFile))
                elif row[0] == 'totalNumberOfReflections':
                    maxReflectionOrder = int(row[1])

        # Get the total number of nodes using NodePosition files
        index = 0
        while True:
            positionFile =  os.path.join(qdRealizationInputFolder, "NodePosition" + str(index) + ".dat")
            if os.path.exists(positionFile):
                index += 1
            else:
                nbNodes = index
                break
        print("************************************************")
        print("*  Q-D Realization software scenario           *")
        print("************************************************")
        print("Nb Nodes:", nbNodes)
        print("Nb Traces:", timeDivision)
        print("Total Simulated Time:", totalTime, "s")
        print("Timestep:", (totalTime / timeDivision) * 1e3, "ms")
        print("\n")
        return nbNodes, timeDivision, (totalTime / timeDivision), environmentFile, maxReflectionOrder
    except FileNotFoundError:
        globals.logger.critical("Q-D configuration file: " + fileName + " does not exist - Please check that the scenario you want to launch exists - Exiting Q-D Interpreter")
        exit()


def readJSONNodesPositionFile(visualizerFolder, nodesPositionsJSON,qdScenario):
    """Read the JSON file containing the Nodes Positions and rotations parameters

    Parameters
    ----------
    visualizerFolder : string
        Name of the folder containing the files exported by the Q-D realization software for the visualizer

    nodesPositionsJSON : string
        Name of the file to read

    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    """

    fileName = os.path.join(visualizerFolder, nodesPositionsJSON)
    globals.logger.info("Read APs and STAs positions and rotation:" + fileName)
    try:
        # The file exist - Load it
        data = [json.loads(line) for line in open(fileName, 'r')]
        nodesPositions = []
        nodesRotations = []  # Represent the node rotation

        for position in data:
            # Read all Position and Rotation information
            nodesPositions.append(np.asarray(position['Position']))
            nodesRotations.append(np.asarray(position['Rotation']))

        # Arrange the position the way they are expected in Mayavi
        # i.e, instead of having a [nbNodes,nbTraces,coordinates] array
        # have a [nbTraces,coordinates,nbNodes] array
        nodesPositions = np.asarray(nodesPositions)
        nodesPositions = np.transpose(nodesPositions, (1, 2, 0))
        qdScenario.setNodesMobility(nodesPositions) # Save the node mobility
        # Arrange the rotation the way they are expected in Mayavi
        nodesRotations = np.asarray(nodesRotations)
        nodesRotations = np.transpose(nodesRotations, (1, 2, 0))
        nodesRotations = np.rad2deg(nodesRotations)  # Mayavi expects the rotations in degrees
        # The traces provided by NJIT were in the format
        # YAW, PITCH and ROLL
        # Col[0],Col[1],col[2]
        # YAW was along the Y axis and PITCH along the X axis
        # In our visualizer, YAW, PITCH and ROLL are not along the same axes
        # YAW is along Z axis
        # PITCH is along Y axis
        # Roll is along X axis
        # So
        # rotationX = ROLL(Measurements)
        # rotationY = PITCH(Measurements)
        # rotationZ = YAW(Measurments)
        # In the Q-D realization software, they are transformed them into
        #  YAW,  ROLL,         PITCH,
        #  0,   1      ,  2
        # So
        # rotationX = ROLL = col[1]
        # rotationY = PITCH = col[2]
        # rotationZ = YAW = col[0]
        # We transform the rotations to take it into account
        nodesRotations[:, [0, 1, 2]] = nodesRotations[:,[1, 2, 0]]
        qdScenario.setNodesRotation(nodesRotations)  # Save the nodes rotations
    except FileNotFoundError:
        globals.logger.critical("JSON Node Position File: " + fileName + " does not exist - Exit")
        exit()


def readTargetJSONPositionFile(visualizerFolder, targetsPositionsJSON,qdScenario):
    """Read the JSON file containing the Target Positions and rotations parameters

    Parameters
    ----------
    visualizerFolder : string
        Name of the folder containing the files exported by the Q-D realization software for the visualizer

    targetsPositionsJSON : string
        Name of the file to read

    qdScenario: QdScenario class
        Scenario parameters (Use to store the target information in this case.)
    """
    fileName = os.path.join(visualizerFolder, targetsPositionsJSON)
    globals.logger.info("Read Targets positions and rotation:" + fileName)
    try:
        # The file exist - Load it
        data = [json.loads(line) for line in open(fileName, 'r')]
        targetsAllJointsPositions = []
        currentTargetId = 0 # We know we'll start with a Target Id equal to 0
        currentTargetJointsPositions = []
        indexFileEnd = 1
        for position in data:
            # Read Target Positions and Rotations line by line
            # Due to how is organized the JSON file (one target/Joint per line)
            # and the fact that we don't know how many joints a target is made of
            # We monitor the target read for the current line, and compare it with the current Target
            # to know if we are reading a new target
            lineTargetId = position['target'] # Get the Target ID for the current line
            # Check if we are still handling the same current target of it we read a new target
            if currentTargetId == lineTargetId:
                # Still reading the same target
                # Accumulate all the joints positions of a given target
                currentTargetJointsPositions.append(position['position'])
                if len(data) == indexFileEnd:
                    # Handle End of file case

                    # Arrange the position the way they are expected in Mayavi
                    # i.e, instead of having a [nbJoints,nbTraces,positions] array
                    # We must have a [nbTraces,positions,nbJoints] array
                    targetsAllJointsPositions.append(np.transpose(np.asarray(currentTargetJointsPositions), (1, 2, 0)))
            else:
                # The target we read is a new one
                currentTargetId = lineTargetId # Assign the newly read line target Id to the current Target
                # Arrange the position the way they are expected in Mayavi
                # i.e, instead of having a [nbJoints,nbTraces,positions] array
                # have a [nbTraces,positions,nbJoints] array
                # and keep the positions
                targetsAllJointsPositions.append(np.transpose(np.asarray(currentTargetJointsPositions), (1, 2, 0)))
                # Clear all the joints positions that belong to the former target
                currentTargetJointsPositions.clear()
                # Store the first joint positions of the newly read target
                currentTargetJointsPositions.append(position['position'])
            indexFileEnd+=1
        # We want to store in the last element the coordinates of all targets to speed up the visualization
        allPositions = np.vstack(np.transpose(np.asarray(targetsAllJointsPositions),(0,3,1,2)))
        allPositions = np.transpose(allPositions,(1,2,0))
        qdScenario.nbTargets = len(targetsAllJointsPositions)
        targetsAllJointsPositions.append(allPositions)
        qdScenario.targetPosition = targetsAllJointsPositions
        print("************************************************")
        print("*             Sensing Scenario                 *")
        print("************************************************")
        print("Nb Targets:", qdScenario.nbTargets)

    except FileNotFoundError:
        # Todo add disable sensing
        globals.logger.critical("JSON Targets Position File: " + fileName + " does not exist - Exit")
        exit()


def readTargetConnectionFile(scenarioQdVisualizerFolder, qdScenario):
    """Read the file containing the Target Joints connections

        Parameters
        ----------
        scenarioQdVisualizerFolder : string
            Name of the folder containing the files exported by the Q-D realization software for the visualizer

        qdScenario: QdScenario class
            Scenario parameters (Use to store the target information in this case.)
    """
    connectionFilePrefix = "TargetConnection"
    for i in range(qdScenario.nbTargets):
        filename = os.path.join(scenarioQdVisualizerFolder, connectionFilePrefix + str(i) + ".txt")
        try:
            with open (filename) as read_obj:
                # pass the file object to reader() to get the reader object
                from csv import reader
                csv_reader = reader(read_obj,quoting=csv.QUOTE_NONNUMERIC)
                connectionList = list(csv_reader)
                qdScenario.targetConnection.append(connectionList)
        except OSError as e:
            # If there is not target joints connection file, just create the simplest connection possible
            qdScenario.targetConnection.append([[0,0]])


def readJSONTargetMPCFile(visualizerFolder, mcpTargetJSON, qdScenario):
    """Read the JSON file containing the MPCs coordinates from each node to each target

    Parameters
    ----------
    visualizerFolder : string
        Name of the folder containing the files exported by the Q-D realization software for the visualizer

    mcpTargetJSON : string
        Name of the file to read

    qdScenario: QdScenario class
        Scenario parameters (Use to store the target information in this case.)
    """
    fileName = os.path.join(visualizerFolder, mcpTargetJSON)
    globals.logger.info("Read Target JSON MPCs Files:" + fileName)
    mpcsTargetsJsonDic = {}
    maxTargetReflectionOrder = 0
    # Parse the JSON MPCs file
    try:
        with open(fileName) as f:
            for line in f:
                from json.decoder import JSONDecodeError
                try:
                    data = json.loads(line)
                    mpcsTargetsJsonDic[
                        (data['node'], data['nodePaa'], data['target'], data['joint'], data['Rorder']
                         )] = np.asarray(data['MPC'],dtype=np.float)
                    if data['Rorder'] > maxTargetReflectionOrder:
                        maxTargetReflectionOrder = data['Rorder']
                except JSONDecodeError as e:
                    globals.logger.critical("Error: " + e + " Impossible to decode JSON Targets MPCs file - Exit")
                    exit()
    except FileNotFoundError:
        globals.logger.critical("JSON Targets MPCs File: " + fileName + " does not exist - Exit")
        exit()
    qdScenario.maxReflectionOrderTarget = maxTargetReflectionOrder

    # Reconstruct the data the way we want them TODO: First version - Could be optimized
    # We want first to store the MPCs from each node to each individual target
    # We will construct later the MPCs from each node to all targets (as it speeds up the visualization if we want to display the MPCs from one node to all targets)
    global mpcNdsTgtsRflsTrcsJts
    mpcNdsTgtsRflsTrcsJts = []
    for nodeId in range(2):
        # Iterate over all the nodes
        mpcTgtsRflsTrcsJts = []
        for targetId in range(qdScenario.nbTargets):
            # Iterate over all the targets
            mpcRflsTrcsJts = []
            # for target in range(2):
            for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                # Iterate over all Reflection Order
                mpcTrcsJts = []
                for traceIndex in range(qdScenario.nbTraces):
                    # Iterate over all the Traces
                    currentIndexConnection = 0
                    xJts = []
                    yJts = []
                    zJts = []
                    listConnection = tuple()
                    for jointId in range(qdScenario.targetPosition[targetId].shape[2]):
                        # Iterate over all the joints of a given trace, target, node and reflection order
                        # For the visualizer, the less objects we create, the faster it is
                        # We are thus accumulating all the joints MPCs coordinates of a given target

                        # Get the coordinates of a given joint from one node to one target for a trace and a given reflection order
                        xMpcCoordinate = mpcsTargetsJsonDic[nodeId, 0, targetId, jointId, reflectionOrder][...,
                                         0::3][traceIndex]
                        yMpcCoordinate = mpcsTargetsJsonDic[nodeId, 0, targetId, jointId, reflectionOrder][...,
                                         1::3][traceIndex]
                        zMpcCoordinate = mpcsTargetsJsonDic[nodeId, 0, targetId, jointId, reflectionOrder][...,
                                         2::3][traceIndex]


                        # Reshape the MPC coordinates to 1D as expected by the visualizer library
                        xMpcCoordinate = xMpcCoordinate.flatten()
                        yMpcCoordinate = yMpcCoordinate.flatten()
                        zMpcCoordinate = zMpcCoordinate.flatten()
                        # Accumulate the coordinates for all the joints
                        xJts.append(xMpcCoordinate)
                        yJts.append(yMpcCoordinate)
                        zJts.append(zMpcCoordinate)

                        # Create the MPCs vertices connections for a given joint
                        nbPathToConnect = xMpcCoordinate.size  # Get the total number of MPCs coordinates
                        connections = tuple()
                        for i in range(currentIndexConnection, currentIndexConnection+nbPathToConnect, 2 + reflectionOrder):
                            idConnection = 0
                            for j in range(reflectionOrder + 1):
                                connections = connections + ((i + idConnection, i + 1 + idConnection),)
                                idConnection = idConnection + 1
                        # Accumulate the MPCs connections for all joints
                        listConnection = listConnection + connections
                        currentIndexConnection+=nbPathToConnect
                    # Here, we aggregate all the joints MPCs info for a given trace and we add it for every trace
                    mpcTrcsJts.append([np.concatenate(xJts).flatten(),np.concatenate(yJts).flatten(),np.concatenate(zJts).flatten(),listConnection])
                # Here, we can add for all the joints the MPCs coordinates (for a given reflection)
                mpcRflsTrcsJts.append(mpcTrcsJts)
            # Here, we are adding for a given target all the MPCs of all reflections order all joints for a given target
            mpcTgtsRflsTrcsJts.append(mpcRflsTrcsJts)
        # Here, we are adding for all nodes all the targets MPCs
        mpcNdsTgtsRflsTrcsJts.append(mpcTgtsRflsTrcsJts)

    # To speed up the visualization, construct the MPCs for all targets accumulated
    # TODO Should be merged to the previous MPCs construction
    global mpcTrcsNdsRflsTgtsJts
    global sizeTrcsNdsRlfsTgtsJts
    mpcTrcsNdsRflsTgtsJts = []
    for traceIndex in range(qdScenario.nbTraces):
        # Iterate over all the traces
        mpcNdsRflsTgtsJts = []
        sizeNdsRlfsTgtsJts = []
        for nodeId in range(2):
            # Iterate over all the nodes
            mpcRflsTgtsJts = []
            sizeRlfsTgtsJts = []
            for reflectionOrder in range(0, qdScenario.maxReflectionOrderTarget + 1):
                # Iterate Over Reflection Order
                xTgtsJoints = []
                yTgtsJoints = []
                zTgtsJoints = []
                listConnection = tuple()
                currentIndexConnection = 0 # Use to keep track of the number of MPCs corresponding to each target when they are all aggregated
                sizeTgtsJts = []
                for targetId in range(qdScenario.nbTargets):
                # Iterate all the targets
                    sizeJts = 0 # We keep how many MPCs we have per target for a given trace, node and reflection
                    # Iterate Over the Traces
                    for jointId in range(qdScenario.targetPosition[targetId].shape[2]):
                        # Iterate over all the joints of a given trace, target, node and reflection
                        # Get the coordinates of the MPCs of a given joint from one node to one target for a given reflection order and trace
                        xMpcCoordinate = mpcsTargetsJsonDic[nodeId, 0, targetId, jointId, reflectionOrder][...,
                                         0::3][traceIndex]
                        yMpcCoordinate = mpcsTargetsJsonDic[nodeId, 0, targetId, jointId, reflectionOrder][...,
                                         1::3][traceIndex]
                        zMpcCoordinate = mpcsTargetsJsonDic[nodeId, 0, targetId, jointId, reflectionOrder][...,
                                         2::3][traceIndex]

                        nbPathToConnect = xMpcCoordinate.size  # Get the total number of MPCs coordinates

                        if nbPathToConnect!=0:
                            # Case where at least one MPC exists from the node to the joint
                            xMpcCoordinate = xMpcCoordinate.flatten()
                            yMpcCoordinate = yMpcCoordinate.flatten()
                            zMpcCoordinate = zMpcCoordinate.flatten()
                        else:
                            # Case where there is no MPC to the joint
                            # We choose to create a fake MPCs (0,0) as we are the one in charge of creating the
                            # vertices connection - It's easier to handle it if there is at least one MPC per joint
                            xMpcCoordinate = np.zeros(2)
                            yMpcCoordinate = np.zeros(2)
                            zMpcCoordinate = np.zeros(2)
                            nbPathToConnect = xMpcCoordinate.size

                        # We are going to accumulate all the MPCs coordinates from one node to all targets joints
                        xTgtsJoints.append(xMpcCoordinate)
                        yTgtsJoints.append(yMpcCoordinate)
                        zTgtsJoints.append(zMpcCoordinate)
                        connections = tuple()

                        # Create the MPCs vertices connections using an indexing common to all joints connecting a node
                        # to all the targets in the scenario
                        for i in range(currentIndexConnection, currentIndexConnection + nbPathToConnect,
                                       2 + reflectionOrder):
                            idConnection = 0
                            for j in range(reflectionOrder + 1):
                                connections = connections + ((i + idConnection, i + 1 + idConnection),)
                                idConnection = idConnection + 1
                        # Accumulate all the MPCs connections
                        listConnection = listConnection + connections
                        currentIndexConnection += nbPathToConnect
                        sizeJts += xMpcCoordinate.size
                    sizeTgtsJts.append(sizeJts)

                # Here, we accumulated all the targets joints MPCs of a given reflection order
                mpcRflsTgtsJts.append([np.concatenate(xTgtsJoints).flatten(),np.concatenate(yTgtsJoints).flatten(),np.concatenate(zTgtsJoints).flatten(),listConnection])
                sizeRlfsTgtsJts.append(sizeTgtsJts)
            # Add the MPCs for all the targets from one node to all targets all reflection order
            mpcNdsRflsTgtsJts.append(mpcRflsTgtsJts)
            sizeNdsRlfsTgtsJts.append(sizeRlfsTgtsJts)
        # Add the MPCs for each trace for all the targets from all node to all targets all reflection order
        mpcTrcsNdsRflsTgtsJts.append(mpcNdsRflsTgtsJts)
        sizeTrcsNdsRlfsTgtsJts.append(sizeNdsRlfsTgtsJts)
    mpcTrcsNdsRflsTgtsJts = np.asarray(mpcTrcsNdsRflsTgtsJts)
    sizeTrcsNdsRlfsTgtsJts = np.asarray(sizeTrcsNdsRlfsTgtsJts)

def getTargetMpcCoordinates(node,target,rOrder,traceIndex):
    """ Get the x, y and z coordinates and the connections for the MPCs of a given node to target reflection order and at a given traceIndex
    Parameters
    ----------
    node : int
        Identifier of the node

    target : int
        Identifier of the target

    rOrder : int
        Identifier of the reflection order

    traceIndex : int
        Identifier of the trace index

    Returns
    -------
    xMpcCoordinate : Numpy Array
        x coordinates of the MPCs points

    yMpcCoordinate : Numpy Array
        y coordinates of the MPCs points

    zMpcCoordinate : Numpy Array
        z coordinates of the MPCs points

    connection : Tuple
        The connectivity between the MPCs edges
    """
    return mpcNdsTgtsRflsTrcsJts[node][target][rOrder][traceIndex]

def getTargetAllMpcCoordinates(node,rOrder,traceIndex):
    """ Get the x, y and z coordinates for the MPCs of a given reflection order and at a given traceIndex for all targets
    Parameters
    ----------
    node : int
        Identifier of the node

    rOrder : int
        Identifier of the reflection order

    traceIndex : int
        Identifier of the trace index

    Returns
    -------
    xMpcCoordinate : Numpy Array
        x coordinates of the MPCs points

    yMpcCoordinate : Numpy Array
        y coordinates of the MPCs points

    zMpcCoordinate : Numpy Array
        z coordinates of the MPCs points

    connection : Tuple
        The connectivity between the MPCs edges
    """
    return mpcTrcsNdsRflsTgtsJts[traceIndex][node][rOrder]

def readDoppler(visualizerFolder,dopplerAxisFile,dopplerRangeFile):
    """Read the files containing the doppler range info for the sensing mode

    Parameters
    ----------
    visualizerFolder : string
        Name of the folder containing the files exported by the Q-D realization software for the visualizer

    targetsPositionsJSON : string
        Name of the file to read

    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    """
    global sensingResults
    fileName = os.path.join(visualizerFolder, dopplerAxisFile)
    try:
        with open(fileName, newline='',) as f:
            # Read the doppler axis file (give us when is performed the range estimation, and the velocity and delay range)
            reader = csv.reader(f,quoting=csv.QUOTE_NONNUMERIC)
            axisData = list(reader)
    except FileNotFoundError:
        globals.logger.warning("Doppler Axis File not found:" + fileName + " => Doppler Graph disabled")
        slowTime = None
        sensingResults = SensingResults(False, None, None, None,None)
        return

    from numpy import genfromtxt
    fileName = os.path.join(visualizerFolder, dopplerRangeFile)
    if os.path.exists(fileName):
        # Read the doppler range file (Dimension: size(Velocity):(size(fasttime)) * (size(Slow Time))
        rangeDopplerData = genfromtxt(fileName, delimiter=',')
    else:
        globals.logger.warning("Doppler Range File not found:" + fileName + " => Doppler Graph disabled")
        sensingResults = SensingResults(False, None, None, None, None)
        return

    slowTime = np.asarray(axisData[0])  # Slow Time (i.e, trace at which we can estimate the range)
    fastTime = np.asarray(axisData[1])  # Fast Time (delay bins of each MPCs)
    velocity = np.asarray(axisData[2])  # Velocity
    dopplerRange = rangeDopplerData

    sensingResults = SensingResults(True, slowTime, fastTime, velocity, dopplerRange)


def readJSONMPCFile(visualizerFolder, mcpJSON):
    """Read the JSON file containing the MPCs coordinates

    Parameters
    ----------
    visualizerFolder : string
        Name of the folder containing the files exported by the Q-D realization software for the visualizer

    mcpJSON : string
        Name of the file to read
    """
    fileName = os.path.join(visualizerFolder, mcpJSON)
    globals.logger.info("Read JSON MPCs Files:" + fileName)
    global MPC_DIC
    MPC_DIC = {}
    with open(fileName) as f:
        for line in f:
            from json.decoder import JSONDecodeError
            try:
                data = json.loads(line)
                MPC_DIC[
                    (data['TX'], data['PAA_TX'], data['RX'], data['PAA_RX'], data['Rorder']
                     )] = np.asarray(data['MPC'],dtype=np.float)
            except JSONDecodeError as e:
                globals.logger.critical("Error: " + e + " Impossible to decode MPCs file - Exit")
                exit()



def readJSONQdFile(nsFolder, qdFilesFolder, qdJSON,qdInterpreterConfig,qdNbNodes):
    """Read the JSON file containing the Q-D realization (MPCs properties) for the channel realized

    Parameters
    ----------
    nsFolder : string
        Name of the folder containing the files exported by the Q-D realization software for ns-3

    qdFilesFolder : string
        Name of the folder where Q-D files are exported

    qdJSONFile : string
        Name of the Q-D file to read

    qdNbNodes: int
        Total number of nodes in the scenario
    """
    nbNodesPermutations = globals.nPr(qdNbNodes, 2)
    permutationCount = 0
    globals.logger.info("Read APs and STAs MPCs characteristics from the JSON Q-D file")
    fileName = os.path.join(nsFolder, qdFilesFolder, qdJSON)
    serialize = False
    serializedFolder = os.path.join(nsFolder, qdFilesFolder, "CachedQd")
    if not os.path.exists(serializedFolder) or qdInterpreterConfig.regenerateCachedQdRealData:
        # The folder to cache the data does not exist - We need to serialize and to parse the Q-D file
        print("Cache the Q-D realization software Q-D MPCs output data")
        serialize = True

    if serialize == False:
        # The serialized data already exists - Use them
        qdproperties = QdProperties()
        qdproperties.DicNbMultipathTxRx = pickle.load(
            open(os.path.join(serializedFolder, "DicNbMultipathTxRx.p"), "rb"))
        qdproperties.DicDelayTxRx = pickle.load(open(os.path.join(serializedFolder, "DicDelayTxRx.p"), "rb"))
        qdproperties.DicPathLossTxRx = pickle.load(open(os.path.join(serializedFolder, "DicPathLossTxRx.p"), "rb"))
        qdproperties.DicPhaseTxRx = pickle.load(open(os.path.join(serializedFolder, "DicPhaseTxRx.p"), "rb"))
        qdproperties.DicAodElevationTxRx = pickle.load(
            open(os.path.join(serializedFolder, "DicAodElevationTxRx.p"), "rb"))
        qdproperties.DicAodAzimuthTxRx = pickle.load(open(os.path.join(serializedFolder, "DicAodAzimuthTxRx.p"), "rb"))
        qdproperties.DicAoaElevationTxRx = pickle.load(
            open(os.path.join(serializedFolder, "DicAoaElevationTxRx.p"), "rb"))
        qdproperties.DicAoaAzimuthTxRx = pickle.load(open(os.path.join(serializedFolder, "DicAoaAzimuthTxRx.p"), "rb"))
        return qdproperties

    # The serialized data does not exist - We need to parse the Q-D files
    try:
        # Please note that The JSON file generated by the Q-D realization software are
        # not de-facto valid JSON files. They are files made of valid JSON objects (one per line)
        lineNumber = 0
        totalTime = 0
        currentPair = (0, 0)
        DicNbMultipathTxRx = {}
        DicDelayTxRx = {}
        DicPathLossTxRx = {}
        DicPhaseTxRx = {}
        DicAodElevationTxRx = {}
        DicAodAzimuthTxRx = {}
        DicAoaElevationTxRx = {}
        DicAoaAzimuthTxRx = {}

        print("Parse JSON Q-D files - Can be time-consuming")
        globals.printProgressBar(0, nbNodesPermutations, 0, prefix='Progress:', suffix='Complete', length=50)
        with open(fileName) as f:
            for line in f:
                startProcess = time.time()
                lineNumber = lineNumber + 1
                from json.decoder import JSONDecodeError
                try:
                    data = json.loads(line)
                except JSONDecodeError as e:
                    globals.logger.critical("Error: " + e + " Impossible to decode Q-D channel JSON file - Exit")
                    exit()

                idTxidRxIdPaaTxPaaRx = (
                    int(data['TX']), int(data['RX']), int(data['PAA_TX']), int(data['PAA_RX']))

                traceIndex = 0
                for singleTraceDelay in data['Delay']:
                    DicDelayTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(singleTraceDelay)
                    # The number of MPCs is needed and not contained in the JSON File
                    # Use the delay shape to get the number of MPCs per timestep
                    DicNbMultipathTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = \
                        np.asarray(singleTraceDelay).shape[0]

                    traceIndex = traceIndex + 1

                # Process Gain
                traceIndex = 0
                for singleTraceGain in data['Gain']:
                    if traceIndex % 1 == 0:
                        DicPathLossTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(singleTraceGain)
                    traceIndex = traceIndex + 1

                # Process Phase
                traceIndex = 0
                for singleTracePhase in data['Phase']:
                    if traceIndex % 1 == 0:
                        DicPhaseTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(singleTracePhase)
                    traceIndex = traceIndex + 1

                # Process Angle of Departure Elevation
                traceIndex = 0
                for singleTraceAODEL in data['AODEL']:
                    if traceIndex % 1 == 0:
                        # DicAodElevationTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(
                        #     singleTraceAODEL,dtype=np.float16)
                        DicAodElevationTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(
                            singleTraceAODEL)
                    traceIndex = traceIndex + 1

                # Process Angle of Departure Azimuth
                traceIndex = 0
                for singleTraceAODAZ in data['AODAZ']:
                    if traceIndex % 1 == 0:
                        # DicAodAzimuthTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(
                        #     singleTraceAODAZ,dtype=np.float16)
                        DicAodAzimuthTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(
                            singleTraceAODAZ)
                    traceIndex = traceIndex + 1

                # Process Angle of Arrival Elevation
                traceIndex = 0
                for singleTraceAOAEL in data['AOAEL']:
                    if traceIndex % 1 == 0:
                        # DicAoaElevationTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(
                        #     singleTraceAOAEL,dtype=np.float16)
                        DicAoaElevationTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(
                            singleTraceAOAEL)
                    traceIndex = traceIndex + 1

                # Process Angle of Arrival Azimuth
                traceIndex = 0
                for singleTraceAOAAZ in data['AOAAZ']:
                    if traceIndex % 1 == 0:
                        # DicAoaAzimuthTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(
                        #     singleTraceAOAAZ,dtype=np.float16)
                        DicAoaAzimuthTxRx[idTxidRxIdPaaTxPaaRx + (traceIndex,)] = np.asarray(
                            singleTraceAOAAZ)
                    traceIndex = traceIndex + 1

                if (int(data['TX']), int(data['RX'])) != currentPair:
                    # For the progress bar, we just update the progress once we go to a new tx,rx (not taking into account the PAAs)
                    permutationCount += 1
                    totalTime += time.time() - startProcess
                    averageProcessTime = totalTime / permutationCount
                    remainingTime = round(averageProcessTime * (nbNodesPermutations - permutationCount))
                    globals.printProgressBar(permutationCount, nbNodesPermutations,
                                             datetime.timedelta(0, remainingTime),
                                             prefix='Progress:', suffix='Complete',
                                             length=50)
                    currentPair = (int(data['TX']), int(data['RX']))
            if serialize == True:
                # Serialize the data
                if not os.path.exists(serializedFolder):
                    os.makedirs(serializedFolder)

                # DicNbMultipathTxRx.asType(np.uint16)
                pickle.dump(DicNbMultipathTxRx, open(os.path.join(serializedFolder, "DicNbMultipathTxRx.p"), "wb"),
                            protocol=pickle.HIGHEST_PROTOCOL)
                pickle.dump(DicDelayTxRx, open(os.path.join(serializedFolder, "DicDelayTxRx.p"), "wb"),
                            protocol=pickle.HIGHEST_PROTOCOL)
                pickle.dump(DicPathLossTxRx, open(os.path.join(serializedFolder, "DicPathLossTxRx.p"), "wb"),
                            protocol=pickle.HIGHEST_PROTOCOL)
                pickle.dump(DicPhaseTxRx, open(os.path.join(serializedFolder, "DicPhaseTxRx.p"), "wb"),
                            protocol=pickle.HIGHEST_PROTOCOL)
                pickle.dump(DicAodElevationTxRx, open(os.path.join(serializedFolder, "DicAodElevationTxRx.p"), "wb"),
                            protocol=pickle.HIGHEST_PROTOCOL)
                pickle.dump(DicAodAzimuthTxRx, open(os.path.join(serializedFolder, "DicAodAzimuthTxRx.p"), "wb"),
                            protocol=pickle.HIGHEST_PROTOCOL)
                pickle.dump(DicAoaElevationTxRx, open(os.path.join(serializedFolder, "DicAoaElevationTxRx.p"), "wb"),
                            protocol=pickle.HIGHEST_PROTOCOL)
                pickle.dump(DicAoaAzimuthTxRx, open(os.path.join(serializedFolder, "DicAoaAzimuthTxRx.p"), "wb"),
                            protocol=pickle.HIGHEST_PROTOCOL)


                qdproperties = QdProperties()
                qdproperties.DicNbMultipathTxRx = DicNbMultipathTxRx
                qdproperties.DicDelayTxRx = DicDelayTxRx
                qdproperties.DicPathLossTxRx = DicPathLossTxRx
                qdproperties.DicPhaseTxRx = DicPhaseTxRx
                qdproperties.DicAodElevationTxRx = DicAodElevationTxRx
                qdproperties.DicAodAzimuthTxRx = DicAodAzimuthTxRx
                qdproperties.DicAoaElevationTxRx = DicAoaElevationTxRx
                qdproperties.DicAoaAzimuthTxRx = DicAoaAzimuthTxRx
                return qdproperties
    except FileNotFoundError:
        globals.logger.critical("JSON MPC File: " + fileName + " does not exist - Exit")
        exit()


def readJSONPAAPositionFile(visualizerFolder, paaPositionJSON,qdScenario):
    """Read the JSON file indicating the position of the PAA(s) in the channel realized

    Parameters
    ----------
    visualizerFolder : string
        Name of the folder containing the files exported by the Q-D realization software for the visualizer

    paaPositionJSON : string
        Name of the file to read
    """
    globals.logger.info("Read APs and STAs antenna positions")
    fileName = os.path.join(visualizerFolder, paaPositionJSON)  # TODO Not Hardcoded
    paaPosition = {}
    paaInitialOrientation = {}
    # Try first to see if a JSON file is present
    try:
        # A json file is present - just load it
        data = [json.loads(line) for line in open(fileName, 'r')]
        # paaPosition = []
        for node in data:
            # The orientation is given in the JSON file with the order of the Euler angles
            # The visualizer library operates only with Z,Y
            # We need to reorganize to have rotX,rotY,rotZ
            # http://davis.lbl.gov/Manuals/VTK-4.5/classvtkProp3D.html#a15
            # Sets the orientation of the Prop3D. Orientation is specified as X,Y and Z rotations in that order, but they are performed as RotateZ, RotateX, and finally RotateY.

            # The Q-D software provides the initial orientation angles in the order of the Euler angles
            # For example, if the Euler angles to apply is Z, X, and Y, the coordinates are given as Z,X,Y
            # We need to reorder them to align with our software expectation that needs the coordinates ordered in X,Y,Z

            initialOrientationRead = np.rad2deg(np.asarray(node['Orientation']))
            paaPosition[(node['Node'], node['PAA'])] =  np.asarray(node['Position']).transpose()
            paaInitialOrientation[(node['Node'], node['PAA'])] = InitialOrientation(
                initialOrientationRead[1], initialOrientationRead[2], initialOrientationRead[0])
        qdScenario.setPaasPosition(paaPosition)
        qdScenario.setPaasInitialOrientation(paaInitialOrientation)
    except FileNotFoundError:
        globals.logger.critical("JSON PAA position File: " + fileName + " does not exist - Exit")
        exit()


def getMpcCoordinates(transmitter, paaTx, receiver, paaRx, reflectionOrder, traceIndex):
    """ Get the x, y and z coordinates for the MPCs of a given reflection order and at a given traceIndex
    Parameters
    ----------
    transmitter : int
        Identifier of the transmitter

    paaTx : int
        Identifier of the transmitter PAA

    receiver : int
        Identifier of the receiver

    paaRx : int
        Identifier of the receiver PAA

    reflectionOrder : int
        Identifier of the reflection order

    traceIndex : int
        Identifier of the trace

    Returns
    -------
    xMpcCoordinate : Numpy Array
        x coordinates of the MPCs points

    yMpcCoordinate : Numpy Array
        y coordinates of the MPCs points

    zMpcCoordinate : Numpy Array
        z coordinates of the MPCs points
    """

    # nbTrace, numberOfMPCs, number of 3 coordinates to create the MPCs
    # The coordinates must be arranged the following way for 1st reflection order (so 3 points to connect)
    # [[xMPC1Point1,xMPC1Point2,xMPC1Point3] [xMPC2Point1,xMPC2Point2,xMPC2Point3]]
    # [[yMPC1Point1,yMPC1Point2,yMPC1Point3] [yMPC2Point1,yMPC2Point2,yMPC2Point3]]
    # [[zMPC1Point1,zMPC1Point2,zMPC1Point3] [zMPC2Point1,zMPC2Point2,zMPC2Point3]]

    # Originally, in the JSON, the coordinates are arranged the following way in one line
    # [
    # Trace 0
    #    [
    #       # MPC 1
    #       [xMPC1Point1Trace0,yMPC1Point1Trace0,zMPC1Point1Trace0,xMPC1Point2Trace0,yMPC1Point2Trace0,zMPC1Point2Trace0, xMPC1Point3Trace0,yMPC1Point3Trace0,zMPC1Point3Trace0],
    #       # MPC 2
    #       [xMPC2Point1Trace0,yMPC2Point1Trace0,zMPC2Point1Trace0,xMPC2Point2Trace0,yMPC2Point2Trace0,zMPC2Point2Trace0, xMPC2Point3Trace0,yMPC2Point3Trace0,zMPC2Point3Trace0]
    #    ]
    # Trace 1
    #    [
    #       # MPC 1
    #       [xMPC1Point1Trace1,yMPC1Point1Trace1,zMPC1Point1Trace1,xMPC1Point2Trace1,yMPC1Point2Trace1,zMPC1Point2Trace1, xMPC1Point3Trace1,yMPC1Point3Trace1,zMPC1Point3Trace1]
    #       # MPC 2
    #       [xMPC2Point1Trace1,yMPC2Point1Trace1,zMPC2Point1Trace1,xMPC2Point2Trace1,yMPC2Point2Trace1,zMPC2Point2Trace1, xMPC2Point3Trace1,yMPC2Point3Trace1,zMPC2Point3Trace1]
    #    ]

    # The ellipsis operator is used as line of sight MPC have a shape of (nbCoordinates triples / only one LoS)
    # and for 1st order reflection and higher, it has a shape (numberOfMPCs,nbCoordinatesTriplets)
    xMpcCoordinate = MPC_DIC[
                         (int(transmitter), paaTx, int(receiver), paaRx, int(reflectionOrder))][...,
                     0::3][traceIndex]
    yMpcCoordinate = MPC_DIC[
                         (int(transmitter), paaTx, int(receiver), paaRx, int(reflectionOrder))][...,
                     1::3][traceIndex]
    zMpcCoordinate = MPC_DIC[
                         (int(transmitter), paaTx, int(receiver), paaRx, int(reflectionOrder))][...,
                     2::3][traceIndex]
    return np.asarray(xMpcCoordinate), np.asarray(yMpcCoordinate), np.asarray(zMpcCoordinate)

def readEnvironmentCoordinates(visualizerFolder, roomCoordinatesFile):
    """Read the file containing the coordinates of the 3D environment

    Parameters
    ----------
    visualizerFolder : string
        Name of the folder containing the files exported by the Q-D realization software for the visualizer
    nodesPositionsJSON : string
        Name of the file to read
    """

    fileName = os.path.join(visualizerFolder, roomCoordinatesFile)
    globals.logger.info("Read Environment File:" + fileName)
    x = []
    y = []
    z = []

    with open(fileName) as csvfile:
        topology = csv.reader(csvfile, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
        for row in topology:
            x.append(row[::3])
            y.append(row[1::3])
            z.append(row[2::3])
    return x, y, z

def readAnalogBeamTrackingResult(beamTrackingResultsFolder, analogBeamTrackingFile):
    """Read the analog beamforming tracking results

        Parameters
        ----------
        beamTrackingResultsFolder : Str
            The folder that contains the beamtracking results

        analogBeamTrackingFile : Str
            The name of the file with the analog BT results

        Returns
        -------
        analogBeamTrackingResults: Dic
            Contain the analog beamforming training results
    """
    analogBeamTrackingResults = {}
    filename = os.path.join(beamTrackingResultsFolder,analogBeamTrackingFile)
    lineRead = 0
    try:
        with open(filename) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                if lineRead == 0:
                    # We don't know how many streams are supported before to read the file
                    # The number of columns of the file is made of Tx Ant Id/Sector/AWV)+ Rx Tx Ant Id/Sector/AWV)+(5 fixed fields)
                    # So the maximum number of streams can thus be obtained with (TotalNumber of Columns - 5)/(3*2)
                    maxSupportedStream = int((len(row)-5)/(3*2))
                    # Trace ID in the BeamTracking Results can use a different indexing than the one used in the
                    # Q-D Realization software output - Account for this
                    initialIndex = int(row['TRACE_IDX'])
                    lineRead += 1

                txAntennaId = [] # Contain the Tx streams Antennas ID
                txSectorId = []  # Contain the Tx streams Sectors ID
                txAwv = []  # Contain the TX Streams AWVs (Not used)
                rxAntennaId = []  # Contain the Rx streams Antennas ID
                rxSectorId = []  # Contain the RX streams Sectors ID
                rxAwv = []  # Contain the RX Streams AWVs (Not used)
                bestreamIdCombination = []
                for streamId in range(maxSupportedStream):
                    # Construct the results for every TX and RX streams
                    # The plus 1 is due to the fact that the name of the fields are indexed starting from 1
                    # The minus 1 is due to the fact that the beamtracking results are indexed starting from 1

                    # Tx Streams
                    txAntennaId.append(int(row['TX_ANTENNA_ID'+str(streamId+1)])-1)
                    txSectorId.append(int(row['TX_SECTOR_ID' + str(streamId+1)])-1)
                    txAwv.append(int(row['TX_AWV_ID' + str(streamId+1)])-1)

                    # Rx Streams
                    rxAntennaId.append(int(row['RX_ANTENNA_ID' + str(streamId + 1)]) - 1)
                    rxSectorId.append(int(row['RX_SECTOR_ID' + str(streamId + 1)]) - 1)
                    rxAwv.append(int(row['RX_AWV_ID' + str(streamId+1)])-1)
                    # BeamTracking is not yet managing SU MIMO - THe combination is thus just the SRC ID and DST ID repeated nb Streams
                    bestreamIdCombination.append([int(row['SRC_ID']) - 1,int(row['DST_ID']) - 1])

                # Remove the initial index to have a key index starting at 0
                analogBeamTrackingResults[int(row['TRACE_IDX']) - initialIndex] = globals.MimoBeamformingResults(
                    bestreamIdCombination,
                    int(row['TRACE_IDX']),
                    txAntennaId,
                    txSectorId,
                    txAwv,
                    rxAntennaId,
                    rxSectorId,
                    rxAwv
                    )
        # qdScenario.beamTrackingResults = BeamTrackingResults(analogBeamTrackingResults,maxSupportedStream-1)
        return [analogBeamTrackingResults,maxSupportedStream-1]
    except OSError as e:
        globals.logger.critical("No 802.11ay PHY Beamtracking MIMO Results - File:" + filename + " does not exist - Exit")
        exit()

def readDigitalPrecoder(beamTrackingResultsFolder,digitalPrecoderFile):
    """Read the digital precoder results

            Parameters
            ----------
            beamTrackingResultsFolder : Str
                The folder that contains the beamtracking results

            digitalPrecoderFile : Str
                The name of the file with the digital precoder results
    """
    fileName = os.path.join(beamTrackingResultsFolder,digitalPrecoderFile)
    try:
        with open(fileName) as f:
            for line in f:
                from json.decoder import JSONDecodeError
                try:
                    data = json.loads(line)
                    realPart = np.asarray(data['real'], dtype=np.float)
                    imaginaryPart = np.asarray(data['imag'], dtype=np.float)
                    digitalWeight = realPart + 1j * imaginaryPart
                    return digitalWeight
                except JSONDecodeError as e:
                    globals.logger.critical("Error: " + e + " Impossible to decode Digital Precoder file - Exit")
                    exit()
    except OSError as e:
        globals.logger.critical("No Digital Precoder - File:" + fileName + " does not exist - Exit")
        exit()


def readDigitalCombiner(beamTrackingResultsFolder,digitalCombinerFile):
    """Read the digital precoder results

    Parameters
    ----------
    beamTrackingResultsFolder : Str
        The folder that contains the beamtracking results

    digitalCombinerFile : Str
        The name of the file with the digital combiner results
    """
    fileName = os.path.join(beamTrackingResultsFolder,digitalCombinerFile)
    try:
        with open(fileName) as f:
            for line in f:
                from json.decoder import JSONDecodeError
                try:
                    data = json.loads(line)
                    realPart = np.asarray(data['real'], dtype=np.float)
                    imaginaryPart = np.asarray(data['imag'], dtype=np.float)
                    digitalWeight = realPart + 1j * imaginaryPart
                    return digitalWeight
                except JSONDecodeError as e:
                    globals.logger.critical("Error: " + e + " Impossible to decode Digital Combiner file - Exit")
                    exit()
    except OSError as e:
        globals.logger.critical("No Digital Combiner - File:" + fileName + " does not exist - Exit")
        exit()