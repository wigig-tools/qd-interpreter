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
"""Module that implements the Power computation for transmissions
"""

import math

import numpy as np
from numba import jit
import globals


class Frequencies:
    """
    A class that represents the Operating Frequency of the subbands


   Attributes
   ----------
   lowerFrequencies : Numpy array
       The list of lower frequencies of each subband

   centerFrequencies :  Numpy array
       The list of center frequencies of each subband

   higherFrequencies :  Numpy array
       The list of higher frequencies of each subband
   """

    def __init__(self, lowerFrequencies, centerFrequencies, higherFrequencies):
        self.lowerFrequencies = lowerFrequencies
        self.centerFrequencies = centerFrequencies
        self.higherFrequencies = higherFrequencies

    def getLowerFrequencies(self):
        """Get the lower frequencies
        """
        return self.lowerFrequencies

    def getCenterFrequencies(self):
        """Get the center frequencies
        """
        return self.centerFrequencies

    def getHigherFrequencies(self):
        """Get the higher frequencies
        """
        return self.higherFrequencies

    def getLowerFrequencySubband(self, subband):
        """Get the lower frequency for a subband

        Parameters
        ----------
        subband : int
            ID of the subband
        """
        return self.lowerFrequencies[subband]

    def getCenterFrequencySubband(self, subband):
        """Get the center frequency for a subband

        Parameters
        ----------
        subband : int
            ID of the subband
        """
        return self.centerFrequencies[subband]

    def getHigherFrequencySubband(self, subband):
        """Get the higher frequency for a subband

        Parameters
        ----------
        subband : int
            ID of the subband
        """
        return self.higherFrequencies[subband]


class TxParam:
    """
    A class to represent the txParam Computation


    Attributes
    ----------
    frequencies : int
        The ID of the node

    txPowerPerSubBandWHz : Enum value TODO
        family name of the person

    noise : int
        Number of PAA for the node

    nbSectorPerPaa: int
        Number of sectors per PAA

    paaInitialOrientation: Dict
        Store the PAA initial orientation
        The Dict key is int:paaId

    paaPositions: Dict
        Store the PAA (x,y,z) positions
        The Dict key is int:paaId

    nodePositions: Dict
        Store the node (x,y,z) position
        The Dict key is TODO
    """

    def setFrequencies(self, frequencies):
        """Set the frequencies (lower, center and higher)
        """
        self.frequencies = frequencies

    def getFrequencies(self):
        """Get the frequencies (lower, center and higher) for all subbands
        """
        return self.frequencies

    def getLowerFrequencies(self):
        """Get the lower frequencies for all subbands
        """
        return self.getFrequencies().getLowerFrequencies()

    def getCenterFrequencies(self):
        """Get the center frequencies for all subbands
        """
        return self.getFrequencies().getCenterFrequencies()

    def getHigherFrequencies(self):
        """Get the higher frequencies for all subbands
        """
        return self.getFrequencies().getHigherFrequencies()

    def allocateFrequencies(self, centerFrequency, channelWidth,
                            bandBandwidth, guardBandwidth):
        """Allocate the subbands frequencies (lower, center and higher)

        Parameters
        ----------
        centerFrequency : float
            Center Frequency of the band (in MHz)
        channelWidth : float
            Channel Width (in MHz)
        bandBandwidth : float
            Subband width (in Hz)
        guardBandwidth : float
            Guard band width (in Hz)
        """
        lowerFrequenciesList = []
        centerFrequenciesList = []
        higherFrequenciesList = []
        centerFrequencyHz = centerFrequency * 1e6
        bandwidth = (channelWidth - 329.53) * 1e6
        numBands = int(bandwidth / bandBandwidth)
        # lay down numBands/2 bands symmetrically around center frequency
        # and place an additional band at center frequency
        # The computation of the center frequencies is done as in ns-3 (i.e, numBands is an int TODO Check if not a problem when dividing by 2)
        startingFrequencyHz = centerFrequencyHz - (int(numBands / 2) * bandBandwidth) - float(bandBandwidth) / 2
        for i in range(numBands):
            f = startingFrequencyHz + (i * bandBandwidth)
            fl = f
            f += bandBandwidth / 2

            fc = f

            f += bandBandwidth / 2
            fh = f

            # Get the lower, center, and higher Frequencies for a subband (needed to compute the power received)
            lowerFrequenciesList.append(fl)
            centerFrequenciesList.append(fc)
            higherFrequenciesList.append(fh)

        lowerFrequenciesList = np.asarray(lowerFrequenciesList)
        centerFrequenciesList = np.asarray(centerFrequenciesList)
        higherFrequenciesList = np.asarray(higherFrequenciesList)
        self.setFrequencies(Frequencies(lowerFrequenciesList, centerFrequenciesList, higherFrequenciesList))

    def allocateTxPowerPerSubband(self, txPowerW, mode, frequencies, nbSubBands):
        """Allocate the TX power per subband

        Parameters
        ----------
        txPowerW : float
            Total Tx Power allocated to one PAA (in W) #TODO Discuss if the power needs to be normalized
        mode : int
            Not used yet but should select the transmission mode (Control Mode, Single Carrier or ODFM) #TODO Probably revisit how it's done in ns-3
        """
        # TODO Mode is not yet used as we focused only on BT but the allocated power is different for ODFM for example
        txPowerPerSubBandW = txPowerW / nbSubBands  # Get the power per subband
        txPowerPerSubBandWHz = []
        # Compute the Power
        for i in range(nbSubBands):
            txPowerPerSubBandWHz.append(
                txPowerPerSubBandW / (
                        frequencies.getHigherFrequencySubband(i) - frequencies.getLowerFrequencySubband(i)))

        txPowerPerSubBandWHz = np.asarray(txPowerPerSubBandWHz)
        self.txPowerPerSubBandWHz = txPowerPerSubBandWHz

    def getTxPowerPerSubBandWHz(self):
        """Get the Tx Power per subband
        """
        return self.txPowerPerSubBandWHz

    def computeNoise(self):
        """Compute the noise power
        """
        BOLTZMANN = 1.3803e-23
        nT = BOLTZMANN * 290 * globals.channelWidth * 1e6;
        noiseFloor = globals.noiseFigure * nT
        noiseInterference = 0  # We don't consider any interference right now
        self.noise = noiseFloor + noiseInterference

    def getNoise(self):
        """Get the noise power
        """
        return self.noise


def DbmtoW(txPowerDbm):
    """Convert Dbm to W
    """
    return 10 ** ((txPowerDbm - 30) / 10)


# This function is used to speed-up the final gain computation
# Numba is used to accelerate the recursive sums
@jit(nopython=True)
def computeRx(nbMpcs, subBandGainAllSubbandSinglePath, txPowerPerSubBandWHz, lowerFrequenciesList,
              higherFrequenciesList, noise, nbSubBands):
    """Compute the reception

    Parameters
    ----------
    nbMpcs : int
        Number of MPCs

    subBandGainAllSubbandSinglePath : Numpy array
        Gain per subband for every MPC

    txPowerPerSubBandWHz : Numpy array
        The Transmit power allocated per subband (in W/Hz)

    lowerFrequenciesList : Numpy array
        Lower frequency for each subband

    higherFrequenciesList : Numpy array
        Higher frequencies for each subband

    noise : float
        The noise associated to the transmission

    nbSubBands : int
        The number of subbands

    Returns
    -------
    float : The total received Power (dB) for the entire bandwidth
    Numpy array : The power received per subband (dB)
    float: The SNR (dB) for the entire bandwidth
    """
    rxPowerPerSubBandWithGaindB = np.empty(nbSubBands)  # Store the received power per Subband
    totalRxPowerW = 0  # The Rx Power over the entire bandwidth
    # subBandGainAllSubbandSinglePath contains the gain per subband and per multipath
    # We need to obtain:
    # - The RX power received per-subband after applying the beamforming gain
    # - The total RX power, after applying the beamforming gain

    for i in range(nbSubBands):
        subsbandGain = 0  # Gain for a subbband, i.e., over all multipaths for a subband
        for j in range(nbMpcs):
            # For every multipath, compute the total gain
            subsbandGain = subsbandGain + subBandGainAllSubbandSinglePath[i, j]
        # Apply the gain to the power receive in the subband
        rxPowerSubBandWithGainWHz = txPowerPerSubBandWHz[i] * abs(subsbandGain) * abs(subsbandGain)
        # Integrate the signal to obtain the Power of the complete subband
        rxPowerSubBandWithGainW = rxPowerSubBandWithGainWHz * (higherFrequenciesList[i] - lowerFrequenciesList[i])
        # Convert in dB
        rxPowerSubBandWithGaindB = 10 * math.log10(rxPowerSubBandWithGainW) + 30
        # Hold the power received per subband to be able to get the PSD
        rxPowerPerSubBandWithGaindB[i] = rxPowerSubBandWithGaindB
        # Add the subband rx power to the total rx power
        totalRxPowerW = totalRxPowerW + rxPowerSubBandWithGainW
    # Compute the SNR
    snrdB = 10 * math.log10(totalRxPowerW / noise)
    return 10 * math.log10(totalRxPowerW) + 30, rxPowerPerSubBandWithGaindB, snrdB


def precomputeTxValues(txRx, qdProperties, centerFrequenciesList):
    """Compute the parameters used for a transmission that are independent of the applied beamforming, and thus from the sectors

    Parameters
    ----------
     txRx : Tuple
        ID of the transmitter, receiver, PAA transmitter, PAA receiver, and the trace Index

    qdProperties : QdProperties class
        MPCs characteristics

    centerFrequenciesList : Numpy array
        The center frequency of each subband

    Returns
    -------

    nbMpcs: float
        The Number of MPCs for the given trace
    azimuthTxAngle: Numpy array
        The azimuth angle for the transmitter for each MPC (degrees)
    elevationTxAngle: Numpy array
        The elevation angle for the transmitter for each MPC (degrees)
    azimuthRxAngle: Numpy array
        The azimuth angle for the receiver for each MPC (degrees)
    elevationRxAngle: Numpy array
        The elevation angle for the receiver for each MPC (degrees)
    smallScaleFading: Numpy array
        Small-Scale fading for each MPC
    """
    # Get the number of MPCs
    nbMpcs = qdProperties.DicNbMultipathTxRx[txRx]
    doppler = complex(1, 0)
    if (nbMpcs > 0):
        # Compute complex delay
        temp_delay = -2 * np.pi * np.outer(centerFrequenciesList, qdProperties.DicDelayTxRx[txRx])
        delay = np.cos(temp_delay) + 1j * np.sin(temp_delay)
        # Path Power Linear
        pathPowerLinear = pow(10.0, (qdProperties.DicPathLossTxRx[txRx] / 10.0))
        # Complex phase
        phase_numpy = qdProperties.DicPhaseTxRx[txRx]
        complexPhase = np.cos(phase_numpy) + 1j * np.sin(phase_numpy)
        # Small Scale Fading
        smallScaleFading = delay * np.sqrt(pathPowerLinear) * doppler * complexPhase

        # Get the MPCs angles of departure and arrival
        # We are rounding them as our steering vector granularity is 1 degree
        azimuthTxAngle = np.around(qdProperties.DicAodAzimuthTxRx[txRx]).astype(int)
        elevationTxAngle = np.around(qdProperties.DicAodElevationTxRx[txRx]).astype(int)
        azimuthRxAngle = np.around(qdProperties.DicAoaAzimuthTxRx[txRx]).astype(int)
        elevationRxAngle = np.around(qdProperties.DicAoaElevationTxRx[txRx]).astype(int)
        return nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading
    else:
        # No MPC for the given transmission
        return 0, 0, 0, 0, 0, 0

def computeSteeredRx(directivityTxAzimuthElevation,directivityRxAzimuthElevation, txParam, nbSubBands,qdScenario, codebooks,nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading):
    """Compute the RX Power when the PAA is steered in azimuth and elevation instead of using sectors
    """
    if nbMpcs == 0:
        # No MPC for the given traceIndex => Return infinite values
        return -math.inf, -math.inf, np.full(nbSubBands, -math.inf), -1, np.full(
            codebooks.getNbSectorsPerPaaNode(qdScenario.getNodeType(idTx)),
            -math.inf)  # TODO Define a constant for -1 i.e, no best sector


    txSum_numpy = directivityTxAzimuthElevation[[azimuthTxAngle], [elevationTxAngle]]
    rxSum_numpy = directivityRxAzimuthElevation[[azimuthRxAngle], [elevationRxAngle]]

    subBandGainAllSubbandSinglePath = rxSum_numpy * txSum_numpy * smallScaleFading

    rxPower, psd, snr = computeRx(nbMpcs, subBandGainAllSubbandSinglePath, txParam.getTxPowerPerSubBandWHz(),
              txParam.getLowerFrequencies(), txParam.getHigherFrequencies(),
              txParam.getNoise(), nbSubBands)
    return rxPower, psd

def performSls(txRx, qdProperties, txParam, nbSubBands, qdScenario, codebooks):
    """Perform the SLS phase for a given pair of transmitter,receiver, pair of transmitter and receiver PAA, and for a given trace

    Parameters
    ----------

    txRx : Tuple
        ID of the transmitter, receiver, PAA transmitter, PAA receiver, and the trace Index

    qdProperties : QdProperties class
        MPCs characteristics

    txParam : TxParam class
        The transmission parameters

    nbSubBands : int
        Number of subbands to use

     qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)

    codebooks : Codebooks class
        Directivity of the AP and STA nodes (sectors and quasi-omni directivity)

    Returns
    -------
    maxRxPower: float
        The power received for the best sector (dB)
    snrBestSector: float
        The SNR observed for the best sector (dB)
    psdBestSector: Numpy arrray
        The PSD of the best sector (power received per subband in dB)
    bestSector: int
        ID of the best Sector
    rxPowerPerSector: Numpy array
        Received power for all the tested sectors (dB)
    """
    maxRxPower = -math.inf
    bestSector = 0
    snrBestSector = 0
    psdBestSector = []
    rxPowerPerSector = []
    # Compute only once the TX values that are common to every sector
    nbMpcs, azimuthTxAngle, elevationTxAngle, azimuthRxAngle, elevationRxAngle, smallScaleFading = precomputeTxValues(
        txRx, qdProperties, txParam.getCenterFrequencies())

    idTx = txRx[0]
    idPaaRx = txRx[3]
    if qdScenario.isNodeAp(idTx):
        sectorDirectivityToUse = codebooks.getApSectorsDirectivity() # TODO Should take into account PAA Id - Fine as for now as we are using symmetric multi PAA codebook
        quasiOmniDirectivityToUse = codebooks.getStaQuasiOmniDirectivity()  # TODO Should take into account PAA - Fine as for now as we are using symmetric multi PAA codebook
    else:
        sectorDirectivityToUse = codebooks.getStaSectorsDirectivity() # TODO Should take into account PAA - Fine as for now as we are using symmetric multi PAA codebook
        # quasiOmniDirectivityToUse = codebooks.getStaQuasiOmniDirectivity()  # TODO Should take into account PAA - Fine as for now as we are using symmetric multi PAA codebook
        quasiOmniDirectivityToUse = codebooks.getApQuasiOmniDirectivity()  # TODO Should take into account PAA - Fine as for now as we are using symmetric multi PAA codebook
    if nbMpcs == 0:
        # No MPC for the given traceIndex => Return infinite values
        return -math.inf, -math.inf, np.full(nbSubBands, -math.inf), -1, np.full(
            codebooks.getNbSectorsPerPaaNode(qdScenario.getNodeType(idTx)), -math.inf)  # TODO Define a constant for -1 i.e, no best sector

    for sectorID in range(codebooks.getNbSectorsPerPaaNode(qdScenario.getNodeType(idTx))):
        # getNbSectorsPerPaaNode
        # Iterate over the sector and get the Tx and RX directivity
        txSum_numpy = sectorDirectivityToUse[sectorID][
            [azimuthTxAngle], [elevationTxAngle]]  # Get the Tx Antenna Pattern for all MPCs
        rxSum_numpy = quasiOmniDirectivityToUse[idPaaRx][[azimuthRxAngle], [
            elevationRxAngle]]  # Get the Rx Antenna Pattern for all MPCs TODO Should take into account antenna
        # Compute the gain for all subband/MPCs
        subBandGainAllSubbandSinglePath = rxSum_numpy * txSum_numpy * smallScaleFading
        # Compute the reception
        rxPower, psd, snr = computeRx(nbMpcs, subBandGainAllSubbandSinglePath, txParam.getTxPowerPerSubBandWHz(),
                                      txParam.getLowerFrequencies(), txParam.getHigherFrequencies(),
                                      txParam.getNoise(), nbSubBands)

        rxPowerPerSector.append(rxPower)
        if rxPower > maxRxPower:
            # Keep the RxPower, the PSD values, and the sector giving the best results (as a TxSS would operate)
            maxRxPower = rxPower
            bestSector = sectorID
            psdBestSector = psd
            snrBestSector = snr
    if maxRxPower == -math.inf:
        # Handle the case where the best power computed is - inf

        bestSector = -1 # TODO Define a constant for this
    return maxRxPower, snrBestSector, psdBestSector, bestSector, rxPowerPerSector
