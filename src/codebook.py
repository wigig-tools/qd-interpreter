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

import cmath
import queue
import threading
import numpy as np
import pandas as pd
import globals
import os


# TODO Probably Move Somewhere else
# Vectorize complex management
def vComplex(arr1, arr2):
    return np.vectorize(np.complex)(arr1, arr2)

class Codebooks:
    """
    A class to represent the STAs and APs codebook


    Attributes
    ----------
    nbPaaPerAp : int
        The number of PAAs per AP

    nbPaaPerSta : int
        The number of PAAs per STA

    nbSectorPerApAntenna : int
        The number of sectors per AP PAA

    nbSectorPerStaAntenna: int
        The number of sectors per STA PAA

    elementPositionsAp: Numpy array
        The position of the AP PAAs antenna elements

    elementPositionsSta: Numpy array
        The position of the AP PAAs antenna elements

    patternsAp: Numpy array
        The AP directivity antenna patterns for all sectors (used for visualization)
    
    patternsSta: Numpy array
        The STA directivity antenna patterns for all sectors (used for visualization)

    apSectorsDirectivity: Numpy array
        The AP directivity for all sectors (used for computation)

    staSectorsDirectivity: Numpy array
        The STA directivity for all sectors (used for computation)

    apQuasiOmniDirectivity: Numpy array
        The AP quasi-omni directivity antenna patterns (used for visualization)

    staQuasiOmniDirectivity: Numpy array
        The STA quasi-omni directivity antenna patterns (used for visualization)

    apSingleElementDirectivity: Numpy array
        Single element directivity of the AP PAA elements

    staSingleElementDirectivity: Numpy array
        Single element directivity of the STA PAA elements

    apSteeringVector: Numpy array
        The steering vector of the AP PAA

    staSteeringVector: Numpy array
        The steering vector of the STA PAA
    """

    def __init__(self):
        # What is done below (attributes set to None) is not really the best practice and can be dangerous
        # as the creation of the instance contains non-initialized attributes
        # The reason to do so is that I want the user to at least know the existence of these attributes
        # Creational pattern could be used but I switched to class very-last minute so let's improve that later
        self.nbPaaPerAp = None
        self.nbPaaPerSta = None
        self.nbSectorPerApAntenna = None
        self.nbSectorPerStaAntenna = None
        self.elementPositionsAp = None
        self.elementPositionsSta = None
        self.patternsAp = None
        self.patternsSta = None
        self.apSectorsDirectivity = None
        self.staSectorsDirectivity = None
        self.apQuasiOmniDirectivity = None
        self.staSectorsDirectivity = None
        self.QuasiPatternsAp = None
        self.QuasiPatternsSta= None
        self.apSingleElementDirectivity = None
        self.staSingleElementDirectivity = None
        self.apSteeringVector = None
        self.staSteeringVector = None
        self.apRefinedAwvsDic = None
        self.staRefinedAwvsDic = None
        self.apRefinedAwvsDirectivityDic = None
        self.staRefinedAwvsDirectivityDic = None
        self.apRefinedAwvsRadiationPatternDic = None
        self.staRefinedAwvsRadiationPatternDic = None
        self.staElementsWeights = None
        self.apElementsWeights = None

    def setNbPaaPerAp(self,nbPaa):
        """Set the number of PAA for the AP Codebook
        """
        self.nbPaaPerAp = nbPaa

    def setNbPaaPerSta(self,nbPaa):
        """Set the number of PAA for the STA Codebook
        """
        self.nbPaaPerSta = nbPaa

    def getNbPaaPerAp(self):
        """Get the number of PAA for the AP Codebook
        """
        return self.nbPaaPerAp

    def getNbPaaPerSta(self):
        """Get the number of PAA for the STA Codebook
        """
        return self.nbPaaPerSta

    def getNbPaaNode(self,nodeType):
        """Get the number of PAA for the nodeType Codebook
        """
        if nodeType == globals.NodeType.AP:
            return self.getNbPaaPerAp()
        else:
            return self.getNbPaaPerSta()

    def setNbElementsPaaAp(self, nbElements):
        """Set the number of elements per AP PAA
        """
        self.nbElementsPaaAp = nbElements

    def setNbElementsPaaSta(self, nbElements):
        """Set the number of elements per STA PAA
        """
        self.nbElementsPaaSta = nbElements

    def geNbElementsPerPaaNode(self, nodeType):
        """Get the number of elements per PAA for the Nodetype Codebook
        """
        if nodeType == globals.NodeType.AP:
            return self.nbElementsPaaAp
        else:
            return self.nbElementsPaaSta

    def setNbSectorPerApAntenna(self,nbSectors):
        """Set the number of sectors per PAA for the AP Codebook
        """
        self.nbSectorPerApAntenna = nbSectors

    def setNbSectorPerStaAntenna(self,nbSectors):
        """Set the number of sectors per PAA for the STA Codebook
        """
        self.nbSectorPerStaAntenna = nbSectors

    def getNbSectorPerApAntenna(self):
        """Get the number of sectors per PAA for the AP Codebook
        """
        return self.nbSectorPerApAntenna

    def getNbSectorPerStaAntenna(self):
        """Get the number of sectors per PAA for the STA Codebook
        """
        return self.nbSectorPerStaAntenna

    def getNbSectorsPerPaaNode(self,nodeType):
        """Get the number of sectors per PAA for the Nodetype Codebook
        """
        if nodeType == globals.NodeType.AP:
            return self.getNbSectorPerApAntenna()
        else:
            return self.getNbSectorPerStaAntenna()

    def setApPaaElementPositions(self,elementPositions):
        """Set the PAA antenna elements position for the AP codebook
        """
        self.elementPositionsAp = elementPositions

    def setStaPaaElementPositions(self,elementPositions):
        """Set the PAA antenna elements position for the STA codebook
        """
        self.elementPositionsSta = elementPositions

    def getApPaaElementPositions(self):
        """ Get the x, y and z coordinates of the PAA elements for the AP codebook (please note that the coordinates are in the global coordinates system)

        Returns
        -------
        elementPositionsAp : Numpy Array
            x,y and z of the AP codebook Antenna Elements
        """
        return self.elementPositionsAp

    def getStaPaaElementPositions(self):
        """ Get the x, y and z coordinates of the PAA elements for the STA codebook (please note that the coordinates are in the global coordinates system)

        Returns
        -------
        elementPositionsSta : Numpy Array
            x,y and z of the STA codebook Antenna Elements
        """
        return self.elementPositionsSta

    def setApSectorsPattern(self, patternsAp):
        """Set all sectors AP antenna pattern directivity for all the sectors
        """
        self.patternsAp = patternsAp

    def setStaSectorsPattern(self, patternsSta):
        """Set all sectors STA antenna pattern directivity for all the sectors
        """
        self.patternsSta = patternsSta

    def getApSectorsPattern(self):
        """Get all sectors AP antenna pattern directivity for all the sectors
        """
        return self.patternsAp

    def getStaSectorsPattern(self):
        """Get all sectors STA antenna pattern directivity for all the sectors
        """
        return self.patternsSta

    def getApSectorPattern(self,sectorId,paaId):
        """Get the AP sector pattern sectorId for the PAA paa ID
        """
        return self.patternsAp[sectorId + paaId * self.getNbSectorPerApAntenna()]

    def getStaSectorPattern(self,sectorId,paaId):
        """Get the STA sector pattern sectorId for the PAA paa ID
        """
        return self.patternsSta[sectorId + paaId * self.getNbSectorPerStaAntenna()]

    def getSectorPatternNode(self,nodeType,sectorId,paaId,streamId, filterPattern):
        """Get the node sector pattern sectorId for the PAA paa ID
        """
        if nodeType == globals.NodeType.AP:
            return self.getApSectorPattern(sectorId[streamId], paaId)
        else:
            return self.getStaSectorPattern(sectorId[streamId], paaId)

    def setApQuasiOmnisPattern(self,quasiPattern):
        """Set quasi-omni antenna pattern directivity for the AP
        """
        self.QuasiPatternsAp = quasiPattern

    def setStaQuasiOmnisPattern(self, quasiPattern):
        """Set quasi-omni antenna pattern directivity for the STA
        """
        self.QuasiPatternsSta = quasiPattern

    def getApQuasiOmniPattern(self,paaId):
        """Get the quasi-omni antenna pattern directivity for the PAA paaId of the AP
         """
        return self.QuasiPatternsAp[paaId]

    def getStaQuasiOmniPattern(self,paaId):
        """Get the quasi-omni antenna pattern directivity for the PAA paaId of the STA
        """
        return self.QuasiPatternsSta[paaId]

    def setApSectorsDirectivity(self, sectorDirectivityAP):
        """Set all sectors AP directivity for all the sectors
        """
        self.apSectorsDirectivity = sectorDirectivityAP

    def setApQuasiOmniDirectivity(self, quasiOmniPatternDirectivityAP):
        """Set quasi-omni AP directivity
        """
        self.apQuasiOmniDirectivity = quasiOmniPatternDirectivityAP

    def setStaSectorsDirectivity(self, sectorDirectivitySTA):
        """Set all sectors STA directivity for all the sectors
        """
        self.staSectorsDirectivity = sectorDirectivitySTA

    def setStaQuasiOmniDirectivity(self, quasiOmniPatternDirectivitySTA):
        """Set quasi-omni STA directivity
        """
        self.staQuasiOmniDirectivity = quasiOmniPatternDirectivitySTA

    def getApSectorsDirectivity(self):
        """Get all sectors AP directivity for all the sectors
        """
        return self.apSectorsDirectivity

    def getApQuasiOmniDirectivity(self):
        """Set quasi-omni AP directivity
        """
        return self.apQuasiOmniDirectivity

    def getStaSectorsDirectivity(self):
        """Get all sectors STA directivity for all the sectors
        """
        return self.staSectorsDirectivity

    def getStaQuasiOmniDirectivity(self):
        """Get quasi-omni STA directivity
        """
        return self.staQuasiOmniDirectivity

    def setApSingleElementDirectivity(self, singleElementDirectivity):
        """Set the single element directivity for the AP PAA
        """
        self.apSingleElementDirectivity = singleElementDirectivity

    def setStaSingleElementDirectivity(self, singleElementDirectivity):
        """Set the single element directivity for the STA PAA
        """
        self.staSingleElementDirectivity = singleElementDirectivity

    def getSingleElementDirectivityNode(self, nodeType):
        """Get the single element directivity of PAA for the nodeType
        """
        if nodeType == globals.NodeType.AP:
            return self.apSingleElementDirectivity
        else:
            return self.staSingleElementDirectivity

    def setApSteeringVector(self, steeringVector):
        """Set the steering vector for the AP PAA
        """
        self.apSteeringVector = steeringVector

    def setStaSteeringVector(self, steeringVector):
        """Set the steering vector for the STA PAA
        """
        self.staSteeringVector = steeringVector

    def getSteeringVectorNode(self, nodeType):
        """Get the single element directivity of PAA for the nodeType
        """
        if nodeType == globals.NodeType.AP:
            return self.apSteeringVector
        else:
            return self.staSteeringVector

    def setRefinedAwvDirectivityDic(self, refinedAwvsDirectivityDic, nodeType):
        """Set the refined Directivity dictionary (contains the directivity for an azimuth, elevation steering)
        """
        if nodeType == globals.NodeType.AP:
            self.apRefinedAwvsDirectivityDic = refinedAwvsDirectivityDic
        else:
            self.staRefinedAwvsDirectivityDic = refinedAwvsDirectivityDic

    def getRefinedAwvDirectivityAzEl(self, az, el, nodeType):
        """Get the refined Directivity dictionary
        """
        if nodeType == globals.NodeType.AP:
            return self.apRefinedAwvsDirectivityDic[az,el,nodeType]
        else:
            return self.staRefinedAwvsDirectivityDic[az,el,nodeType]

    def setRefinedAwvRadiationPatternDic(self, refinedAwvsRadiationPatternDic, nodeType):
        """Set the refined Radiation Pattern dictionary (contains the radiation for an azimuth, elevation steering)
        """
        if nodeType == globals.NodeType.AP:
            self.apRefinedAwvsRadiationPatternDic = refinedAwvsRadiationPatternDic
        else:
            self.staRefinedAwvsRadiationPatternDic = refinedAwvsRadiationPatternDic

    def getRefinedAwvRadiationPatternDic(self, az, el, nodeType):
        """Get the refined radiation pattern dic
        """
        if nodeType == globals.NodeType.AP:
            return self.apRefinedAwvsRadiationPatternDic[az, el, nodeType]
        else:
            return self.staRefinedAwvsRadiationPatternDic[az, el, nodeType]

    def setRefinedAwvDic(self, refinedAwvsDic, nodeType):
        """Set the refined AWV dictionary
        """
        if nodeType == globals.NodeType.AP:
            self.apRefinedAwvsDic = refinedAwvsDic
        else:
            self.staRefinedAwvsDic = refinedAwvsDic

    def getRefinedAwvAzimuthElevation(self, sectorId, refineAwvId, nodeType):
        """Return the refined AWV dic for a node of nodeType
        """
        if nodeType == globals.NodeType.AP:
            return self.apRefinedAwvsDic[sectorId, refineAwvId]
        else:
            return self.staRefinedAwvsDic[sectorId, refineAwvId]

    def geElementWeightsNode(self, nodeType, sectorId):
        """Get the AWV corresponding to a Sector
        """
        if nodeType == globals.NodeType.AP:
            return self.apElementsWeights[sectorId]
        else:
            return self.staElementsWeights[sectorId]


#########################################
######    Antenna Patterns        #######
#########################################
def loadCodebook(CodebookFolder,beamTracking, codebookMode, apFileName=None, staFileName=None, parallel=True):
    """Initiate the Computation of the AP and STA codebook

    Parameters
    ----------
    CodebookFolder : string
        Name of the folder containing the codebook to be loaded

    beamTracking: Bool
        Indicate if we use the beamtracking mode (the codebooks are different in this mode)

    codebookMode: str
        Indicate if we want the antenna pattern represented in dB or linear domain

    apFileName: string
        Name of the AP codebook

    staFileName: string
        Name of the STA codebook

    parallel: Bool
        Use two threads to perform in parallel the directivity and antenna patterns computation

    Returns
    ----------
    codebookObject : Codebooks class
        Class containing the directionality of the sectors and quasi-omni pattern for the STAs and APs
    """
    path = CodebookFolder
    codebookObject = Codebooks()
    if apFileName is not None:
        apdf = pd.read_csv(os.path.join(path,apFileName), sep='\t', header=None, names=['data'])
    if staFileName is not None:
        stadf = pd.read_csv(os.path.join(path,staFileName), sep='\t', header=None, names=['data'])

    if apFileName is not None and staFileName is not None:
        if apdf.equals(stadf):
            globals.logger.info("AP(s) and STA(s) codebook are identical")
            globals.logger.info("Load Codebook:" + path + staFileName)
            loadComputation(apdf, 'both',  codebookObject,beamTracking, codebookMode)
        else:
            if parallel:
                que = queue.Queue()  # queue
                thread1 = threading.Thread(target=lambda q, apdf,codebookObject,beamTracking,codebookMode: q.put(loadComputation(
                    df=apdf, dfType='ap', codebookObject=codebookObject,beamTracking=beamTracking, codebookMode = codebookMode)),
                                           args=(que, apdf, codebookObject,beamTracking, codebookMode))
                thread2 = threading.Thread(target=lambda q, stadf, codebookObject,beamTracking,codebookMode: q.put(loadComputation(
                    df=stadf, dfType='sta',  codebookObject=codebookObject,beamTracking=beamTracking,codebookMode = codebookMode)),
                                           args=(que, stadf,  codebookObject,beamTracking,codebookMode))
                thread1.start()
                thread2.start()
                thread1.join()
                thread2.join()

            else:
                globals.logger.info("AP(s) and STA(s) codebook are different")
                globals.logger.info("Load AP codebook:" + path + apFileName)
                loadComputation(apdf, 'ap', codebookObject,beamTracking,codebookMode)
                globals.logger.info("Load STA codebook:" + path + staFileName)
                loadComputation(stadf, 'sta', codebookObject,beamTracking,codebookMode)

    elif apFileName is not None:
        loadComputation(apdf, 'ap',codebookObject, beamTracking,codebookMode)
    elif staFileName is not None:
        loadComputation(stadf, 'sta',codebookObject, beamTracking,codebookMode)
    else:
        print('Warning: No AP or STA file input! Please check the input files.')
    return codebookObject

def loadComputation(df, dfType, codebookObject, beamTracking,codebookMode):
    """Read the Codebooks and compute the directivity of each sector and the associated antenna patterns

    Parameters
    ----------
    df : pandas dataframe
        Data from the codebook read

    dfType: string
        Value either, 'both', 'ap', or 'sta' depending if the APs and STAs codebook are identical or not

    codebookObject : Codebooks class
        Class containing the directionality of the sectors and quasi-omni pattern for the STAs and APs

    beamTracking: Bool
        Indicate if we use the beamtracking mode (the codebooks are different in this mode)

    codebookMode: str
        Indicate if we want the antenna pattern represented in dB or linear domain
    """
    globals.logger.info("Compute " + dfType + " directivity")
    # Initialize the coordinates of the radiation pattern
    radiusFactor = 0.011  # Decide the effective size of the pattern when visualizing it (can be changed when visualizing)
    azimuthAnglesWrapped = np.linspace(np.radians(0), np.radians(360), num=globals.azimuthCardinality)
    elevationAnglesWrapped = np.linspace(np.radians(0), np.radians(180), num=globals.elevationCardinality)
    X, Y = np.meshgrid(elevationAnglesWrapped, azimuthAnglesWrapped)
    tempX, tempY, tempZ = np.multiply(radiusFactor,
                                      (np.multiply(np.sin(X), np.cos(Y)), np.multiply(np.sin(X), np.sin(Y)), np.cos(X)))

    # Read the codebook
    # First line is the number of RF chain
    nbRfChain = df.iloc[0].values.astype(int)[0]
    # Second line determines the number of phased antenna arrays within the device
    nbPhasedAntennaArrayNumber = df.iloc[1].values.astype(int)[0]
    globals.logger.info("Number of PAA:" + str(nbPhasedAntennaArrayNumber))

    dfIndex = 2
    sectorPattern = []
    quasiOmniPattern = []
    sectorDirectivity = []
    quasiOmniPatternDirectivity = []
    sectorWeights = []
    for antennaIndex in range(nbPhasedAntennaArrayNumber):
        # Loop though all the PAA and compute quasi-omni directivity and patterns and sector directivity and patterns
        sixRows = df['data'].iloc[dfIndex:dfIndex + 5].values.astype(int)
        # Read phased antenna array ID
        antennaID = sixRows[0]

        rfChainID = sixRows[1]
        globals.logger.info("Antenna ID:" + str(antennaID))
        # Read phased antenna array azimuth orientation degree
        azimuthOrientationDegree = sixRows[2]
        # Read phased antenna array elevation orientation degree
        elevationOrientationDegree = sixRows[3]
        # Read the number of antenna elements
        nbElements = sixRows[4]
        # Read the antenna element position
        dfAntennaPosition = df.iloc[dfIndex + 5].str.split(',', expand=True).astype(np.float64).values[0]
        # Read the number of quantization bits for phase
        # phaseQuantizationBits = sixRows[4]
        # Read the number of quantization bits for amplitude */
        # amplitudeQuantizationBits = sixRows[5]
        dfResultIndex = dfIndex + globals.azimuthCardinality + 8
        # Read the directivity of a single antenna element
        singleElementDirectivity = df['data'].iloc[dfIndex + 8:dfResultIndex
                                   ].str.split(',', expand=True).astype(np.float64).values

        currentIndex = nbElements * globals.azimuthCardinality + dfResultIndex
        # Read the steering vector
        results = df['data'].iloc[dfResultIndex:currentIndex
                  ].str.split(',', expand=True).astype(np.float64).values
        amp, phaseDelay = results[:, ::2], results[:, 1::2]
        steeringVector = vComplex(np.multiply(amp, np.cos(phaseDelay)),
                                  np.multiply(amp, np.sin(phaseDelay)))
        steeringVector = steeringVector[None, ...].reshape((nbElements, globals.azimuthCardinality,
                                                            globals.elevationCardinality))

        # Read Quasi-omni antenna weights
        results = df.iloc[currentIndex].str.split(',', expand=True).astype(np.float64).values[0]
        amp, phaseDelay = results[::2], results[1::2]
        polarSteering = np.vectorize(cmath.polar)(vComplex(amp, phaseDelay))
        quasiOmniWeights = vComplex(polarSteering[0], polarSteering[1])

        # Compute Quasi-Omni Directivity
        # We need to decouple the visualized Antenna Pattern and the directivity computed
        globals.logger.debug("Compute Quasi-Omni directivity")
        directivity = steeringVector.copy()
        for n in range(len(quasiOmniWeights)):
            directivity[n, :, :] *= quasiOmniWeights[n]
        directivity = directivity.sum(axis=0)
        directivity[...] = np.multiply(directivity, singleElementDirectivity)
        # Store the quasi-omni directivity for a given PAA (used to obtain quasi-omni gain)
        quasiOmniPatternDirectivity.append(directivity.copy())
        # Compute the quasi-omni sectorPattern of a given PAA (use for visualization)
        # Directivity can have a zero value - Replace it with a small value instead to not yied any error when applying log10
        directivity[directivity == 0] = 0.0000001
        directivity = 10 * np.log10(np.abs(directivity) ** 2)
        hi, lo = 40, -40
        # Clip the gain values
        directivity = np.clip(directivity, lo, hi)
        # Adjust for negative values
        if (lo < 0):
            directivity -= lo
        tempResults = np.multiply((tempX, tempY, tempZ), directivity)
        quasiOmniPattern.append(np.vstack((tempResults, directivity[None, ...])))

        currentIndex += 1
        # Read the number of sectors within this antenna array
        nbSectorsPerAntenna = df.iloc[currentIndex].values.astype(int)[0]
        globals.logger.info("Number of Sectors:" + str(nbSectorsPerAntenna))

        currentIndex += 1
        for sector in range(nbSectorsPerAntenna):
            globals.logger.debug("Compute Sector:" + str(sector) + " directivity")
            # Compute sector directivity
            if not beamTracking:
                # Beamtracking not used
                results = df.iloc[currentIndex + 3].str.split(',',
                                                              expand=True).values.astype(np.float64)[0, :]
            else:
                # Beamtracking used
                # Beamtracking codebook format is slightly different as it includes two additional lines for the steering angles (not used in this software)
                results = df.iloc[currentIndex + 5].str.split(',',
                                                              expand=True).values.astype(np.float64)[0, :]
            # Read sector antenna weights vector
            amp, phaseDelay = results[::2], results[1::2]
            if not beamTracking:
                elementsWeights = vComplex(np.multiply(amp, np.cos(phaseDelay)),
                                           np.multiply(amp, np.sin(
                                               phaseDelay)))
            else:
                # When beamtracking is used, we need to normalize the antenna weights
                elementsWeights = vComplex(np.multiply(amp, np.cos(phaseDelay))/np.sqrt(nbElements),
                                           np.multiply(amp, np.sin(phaseDelay))/np.sqrt(nbElements))
            sectorWeights.append(elementsWeights)
            # Compute Sector Directivity
            directivity = steeringVector.copy()
            for n in range(len(elementsWeights)):
                directivity[n, :, :] *= elementsWeights[n]
            directivity = directivity.sum(axis=0)
            directivity[...] = np.multiply(directivity, singleElementDirectivity)
            sectorDirectivity.append(directivity.copy())

            # Compute sector pattern
            # Directivity can have a zero value - Replace it with a small value instead to not yied any error when applying log10
            directivity[directivity == 0] = 0.000001
            if codebookMode == 'linear':

                directivity = np.abs(directivity) ** 2
            else:
                directivity = 10 * np.log10(np.abs(directivity) ** 2)
                # TODO: Make it a dynamic parameter
                hi, lo = 40, -40
                # Clip the gain values
                directivity = np.clip(directivity, lo, hi)
                # Adjust for negative values
                if (lo < 0):
                    directivity -= lo

            tempResults = np.multiply((tempX, tempY, tempZ), directivity)
            sectorPattern.append(np.vstack((tempResults, directivity[None, ...])))
            if not beamTracking:
                # Beamtracking not used
                currentIndex += 4
            else:
                # Beamtracking used
                currentIndex += 6
        dfIndex = currentIndex

    dfTypeLower = dfType.lower()
    if dfTypeLower == 'both':
        print("************************************************")
        print("*             CODEBOOK SUMMARY                 *")
        print("************************************************")
        print("AP and STA codebooks are configured to be identical:")
        print("\tNb Phased Antenna Array:", nbPhasedAntennaArrayNumber)
        print("\tNb Sectors per Phased Antenna Array:", nbSectorsPerAntenna)
        codebookObject.setNbPaaPerAp(nbPhasedAntennaArrayNumber)
        codebookObject.setNbPaaPerSta(nbPhasedAntennaArrayNumber)

        codebookObject.setNbElementsPaaAp(nbElements)
        codebookObject.setNbElementsPaaSta(nbElements)

        codebookObject.setApPaaElementPositions(dfAntennaPosition)
        codebookObject.setStaPaaElementPositions(dfAntennaPosition)

        codebookObject.setNbSectorPerApAntenna(nbSectorsPerAntenna)
        codebookObject.setNbSectorPerStaAntenna(nbSectorsPerAntenna)

        codebookObject.setApSectorsPattern(sectorPattern)
        codebookObject.setStaSectorsPattern(sectorPattern)

        codebookObject.setApQuasiOmnisPattern(quasiOmniPattern)  # TODO Should take into account antenna
        codebookObject.setStaQuasiOmnisPattern(quasiOmniPattern)  # TODO Should take into account antenna

        codebookObject.setApSectorsDirectivity(sectorDirectivity)
        codebookObject.setStaSectorsDirectivity(sectorDirectivity)

        codebookObject.setApQuasiOmniDirectivity(quasiOmniPatternDirectivity)
        codebookObject.setStaQuasiOmniDirectivity(quasiOmniPatternDirectivity)

        codebookObject.setApSingleElementDirectivity(singleElementDirectivity)
        codebookObject.setStaSingleElementDirectivity(singleElementDirectivity)

        codebookObject.setApSteeringVector(steeringVector)
        codebookObject.setStaSteeringVector(steeringVector)
        if not beamTracking:

            AppendAwvsForSuMimoBFT_27(codebookObject,codebookMode, globals.NodeType.AP)
            AppendAwvsForSuMimoBFT_27(codebookObject,codebookMode, globals.NodeType.STA)
        else:
            codebookObject.staElementsWeights = sectorWeights
            codebookObject.apElementsWeights = sectorWeights
    elif dfTypeLower == 'ap':
        print("************************************************")
        print("*             CODEBOOK SUMMARY                 *")
        print("************************************************")
        print("AP codebook")
        print("\tNb Phased Antenna Array:", nbPhasedAntennaArrayNumber)
        print("\tNb Sectors per Phased Antenna Array:", nbSectorsPerAntenna)
        codebookObject.setNbPaaPerAp(nbPhasedAntennaArrayNumber)
        codebookObject.setNbElementsPaaAp(nbElements)
        codebookObject.setApPaaElementPositions(dfAntennaPosition)
        codebookObject.setNbSectorPerApAntenna(nbSectorsPerAntenna)
        codebookObject.setApSectorsPattern(sectorPattern)
        codebookObject.setApQuasiOmnisPattern(quasiOmniPattern)  # TODO Should take into account antenna
        codebookObject.setApSectorsDirectivity(sectorDirectivity)
        codebookObject.setApQuasiOmniDirectivity(quasiOmniPatternDirectivity)
        codebookObject.setApSingleElementDirectivity(singleElementDirectivity)
        codebookObject.setApSteeringVector(steeringVector)
        if not beamTracking:
            # Compute the refined AWV
            AppendAwvsForSuMimoBFT_27(codebookObject,codebookMode, globals.NodeType.AP)
        else:
            codebookObject.apElementsWeights = sectorWeights
    elif dfTypeLower == 'sta':
        print("************************************************")
        print("*             CODEBOOK SUMMARY                 *")
        print("************************************************")
        print("STA codebook")
        print("\tNb Phased Antenna Array:", nbPhasedAntennaArrayNumber)
        print("\tNb Sectors per Phased Antenna Array:", nbSectorsPerAntenna)
        print("\n")
        codebookObject.setNbPaaPerSta(nbPhasedAntennaArrayNumber)
        codebookObject.setNbElementsPaaSta(nbElements)
        codebookObject.setStaPaaElementPositions(dfAntennaPosition)
        codebookObject.setNbSectorPerStaAntenna(nbSectorsPerAntenna)
        codebookObject.setStaSectorsPattern(sectorPattern)
        codebookObject.setStaQuasiOmnisPattern(quasiOmniPattern)  # TODO Should take into account antenna
        codebookObject.setStaSectorsDirectivity(sectorDirectivity)
        codebookObject.setStaQuasiOmniDirectivity(quasiOmniPatternDirectivity)
        codebookObject.setStaSingleElementDirectivity(singleElementDirectivity)
        codebookObject.setStaSteeringVector(steeringVector)
        if not beamTracking:
            AppendAwvsForSuMimoBFT_27(codebookObject,codebookMode, globals.NodeType.STA)
        else:
            codebookObject.staElementsWeights = sectorWeights

def computeHybridPattern(codebooks,codebookMode, nodeType,elementsWeights,quality):
    """Compute hybrid antenna pattern

    Parameters
    ----------
    codebooks : Numpy array
        Contain all the nodes x,y,z positions

    codebookMode : str
        Are the antenna pattern displayer in Linear or dB

    codebookMode : Int
        Type of the node (AP or STA)

    elementsWeights : array
        The AVW to apply for the digital beamforming

    quality : Int
        The magnitude of reduction of the quality of the antenna pattern
    """

    # Handle the antenna pattern quality filter (speed up the computation and visualization)
    if quality == 1:
        qualitySize = 361
        qualitySizeElevation = 181
    else:
        qualitySize = 361 // quality + 1
        qualitySizeElevation = 181 // quality + 1

    azimuthAngles = np.linspace(np.radians(0), np.radians(360), num=qualitySize)
    elevationAngles = np.linspace(np.radians(0), np.radians(180), num=qualitySizeElevation)
    X, Y = np.meshgrid(elevationAngles, azimuthAngles)
    tempX, tempY, tempZ = np.multiply(0.011,
                                      (np.multiply(np.sin(X), np.cos(Y)), np.multiply(np.sin(X), np.sin(Y)), np.cos(X)))
    singleElementDirectivity = codebooks.getSingleElementDirectivityNode(nodeType),
    directivity = codebooks.getSteeringVectorNode(nodeType).copy()
    for n in range(len(elementsWeights)):
        directivity[n, :, :] *= elementsWeights[n]
    directivity = directivity.sum(axis=0)
    directivity[...] = np.multiply(directivity, singleElementDirectivity)

    if codebookMode == 'linear':
        # Compute the linear pattern
        directivity = np.abs(directivity) ** 2
    else:
        # Compute the dB pattern
        directivity = 10 * np.log10(np.abs(directivity) ** 2)
        # TODO: Make it a dynamic parameter
        hi, lo = 40, -40
        # Clip the gain values
        directivity = np.clip(directivity, lo, hi)
        # Adjust for negative values
        if (lo < 0):
            directivity -= lo

    radiationPatternFiltered = directivity[::quality,::quality]
    tempResults = np.multiply((tempX, tempY, tempZ), radiationPatternFiltered)
    pattern = [np.vstack((tempResults, radiationPatternFiltered[None, ...]))]
    xAntennaPattern = pattern[0][0]
    yAntennaPattern = pattern[0][1]
    zAntennaPattern = pattern[0][2]
    colorAntennaPattern = pattern[0][3]
    return xAntennaPattern, yAntennaPattern, zAntennaPattern, colorAntennaPattern

def AppendAwvsForSuMimoBFT_27(codebooks,codebookMode, nodeType):
    """Add the refined AWV associated to the sectors

    Parameters
    ----------
    df : pandas dataframe
        Data from the codebook read

    dfType: string
        Value either, 'both', 'ap', or 'sta' depending if the APs and STAs codebook are identical or not
    """
    # TODO This function is having limited functionalities as everything is hardcoded
    # It's just implemented as it is in ns-3 and should be revisited later on
    refinedAwvsDic = {}  # Use to retrieve azimuth and elevation steering for a [sectorId,refineAwvId]
    azAngle = 0
    elAngle = -45
    nbElevation = 3
    nbRefinedAwvs = 5
    directivityDic = {}
    radiationPatternDic = {}
    sectorId = 0
    for elevationId in range(nbElevation):
        for nbAzimuths in range(5):
            azAwvAngle = azAngle - 10
            for refinedAwvId in range(nbRefinedAwvs):
                refinedAwvsDic[sectorId, refinedAwvId] = (azAwvAngle, elAngle)
                xAntennaPattern, yAntennaPattern, zAntennaPattern, colorAntennaPattern, directivity = computeDirectivityAzimuthElevation(
                    azAwvAngle, elAngle, codebooks.getSingleElementDirectivityNode(nodeType),
                    codebooks.getSteeringVectorNode(nodeType),
                    codebooks.geNbElementsPerPaaNode(nodeType),codebookMode)
                directivityDic[azAwvAngle, elAngle, nodeType] = directivity
                radiationPatternDic[
                    azAwvAngle, elAngle, nodeType] = xAntennaPattern, yAntennaPattern, zAntennaPattern, colorAntennaPattern
                azAwvAngle += 5

            azAngle += 20
            sectorId += 1
        azAngle = 200
        for nbAzimuths in range(4):
            azAwvAngle = azAngle - 10
            for refinedAwvId in range(nbRefinedAwvs):
                refinedAwvsDic[sectorId, refinedAwvId] = (azAwvAngle, elAngle)
                xAntennaPattern, yAntennaPattern, zAntennaPattern, colorAntennaPattern, directivity = computeDirectivityAzimuthElevation(
                    azAwvAngle, elAngle,
                    codebooks.getSingleElementDirectivityNode(nodeType),
                    codebooks.getSteeringVectorNode(nodeType),
                    codebooks.geNbElementsPerPaaNode(nodeType),codebookMode)
                directivityDic[azAwvAngle, elAngle, nodeType] = directivity
                radiationPatternDic[
                    azAwvAngle, elAngle, nodeType] = xAntennaPattern, yAntennaPattern, zAntennaPattern, colorAntennaPattern
                azAwvAngle += 5
            azAngle += 20
            sectorId += 1
        azAngle = 0
        elAngle += 45
    codebooks.setRefinedAwvDic(refinedAwvsDic, nodeType)
    codebooks.setRefinedAwvDirectivityDic(directivityDic, nodeType)
    codebooks.setRefinedAwvRadiationPatternDic(radiationPatternDic, nodeType)


# Test function to steer the antenna in azimuth and elevation
# Please note that the azimuth and elevation has a resolution of one degree
def computeDirectivityAzimuthElevation(azimuth, elevation, singleElementDirectivity, steeringVector, nbElements,codebookMode):
    """ Steer the antenna in azimuth and elevation and return the resulting pattern
    """
    globals.logger.debug(
        "Compute Directivity when Steering => Azimuth:" + str(azimuth) + ",Elevation:" + str(elevation))

    # Create the reverse indexing
    # Create the Azimuth Angles Wrapped as they are obtained in the Q-D Codebook generator
    # As a reminder, the steering vector is indexed using azimuth angles wrapped in the range [0:180][-179:0]
    azimuthAnglesWrapped = np.concatenate((np.linspace(0, 180, num=181), np.linspace(-179, 0, num=180)))
    # Transform the azimuth angles to stay in the range [-180:180] TODO: Check if needed as normally, we should not use angles greater than 180
    if azimuth > 180:
        azimuth -= 360

    # Create the Elevation Angles Wrapped as they are obtained in the Q-D Codebook generator
    # As a reminder, the steering vector is indexed using elevation angles wrapped in the range [90][-90]
    elevationAnglesWrapped = np.linspace(90, -90, num=globals.elevationCardinality)
    # We know want to find the steering vector corresponding to the given azimuth
    # For this, we look for the index of the azimuth in the azimuth angle wrapped to then retrieve the right steering vector for the given azimuth
    azimuthIndex = np.where(azimuthAnglesWrapped == azimuth)
    # We know want to find the steering vector corresponding to the given elevation
    # For this, we look for the index of the elevation in the elevation angle wrapped to then retrieve the right steering vector for the given elevation
    elevationIndex = np.where(elevationAnglesWrapped == elevation)

    # Get the right index to retrieve the steering vector for azimuth,elevation
    realIndexAzimuth = azimuthIndex[0][0]
    realIndexElevation = elevationIndex[0][0]

    azimuthAngles = np.linspace(np.radians(0), np.radians(360), num=361)
    elevationAngles = np.linspace(np.radians(0), np.radians(180), num=globals.elevationCardinality)
    X, Y = np.meshgrid(elevationAngles, azimuthAngles)
    tempX, tempY, tempZ = np.multiply(0.011,
                                      (np.multiply(np.sin(X), np.cos(Y)), np.multiply(np.sin(X), np.sin(Y)), np.cos(X)))

    elementsWeights = []  # The element weights to steer to azimuth and elevation
    for i in range(nbElements):
        # Compute the element weights for azimuth and elevation steering
        elementsWeights.append(np.conj(steeringVector[i][realIndexAzimuth][realIndexElevation]))
    directivity = steeringVector.copy()
    for n in range(len(elementsWeights)):
        directivity[n, :, :] *= elementsWeights[n]
    directivity = directivity.sum(axis=0)
    directivity[...] = np.multiply(directivity, singleElementDirectivity)

    radiationPattern = directivity.copy()
    radiationPattern[radiationPattern == 0] = 0.0000001

    if codebookMode == 'linear':
        radiationPattern = np.abs(radiationPattern) ** 2
    else:
        radiationPattern = 10 * np.log10(np.abs(radiationPattern) ** 2)

        # TODO: Make it a dynamic parameter
        hi, lo = 40, -40
        # Clip the gain values
        radiationPattern = np.clip(radiationPattern, lo, hi)
        # Adjust for negative values
        if (lo < 0):
            radiationPattern -= lo

    tempResults = np.multiply((tempX, tempY, tempZ), radiationPattern)
    pattern = [np.vstack((tempResults, radiationPattern[None, ...]))]
    xAntennaPattern = pattern[0][0]
    yAntennaPattern = pattern[0][1]
    zAntennaPattern = pattern[0][2]
    colorAntennaPattern = pattern[0][3]
    return xAntennaPattern, yAntennaPattern, zAntennaPattern, colorAntennaPattern, directivity
