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

import globals
import ml
import scheduler
import numpy as np
import os

if __name__ == "__main__":
    qdScenario, txParam, codebooks, environmentFile, maxReflectionOrder = globals.initializeOracle()

    # Machine-Learning Beamforming-Training
    # Use coordinates and rotations
    # uses default modelType='Baseline'
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.AP_TO_STAS, ml.InputToUse.COORDINATES_ROTATIONS)
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.STAS_TO_AP, ml.InputToUse.COORDINATES_ROTATIONS)
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.STAS_TO_STA, ml.InputToUse.COORDINATES_ROTATIONS,
               targetStaId=qdScenario.nbNodes - 1)  # For all STAs to STA case, we use the last STA as a target
    #
    # # Use only rotations
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.AP_TO_STAS, ml.InputToUse.ROTATIONS)
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.STAS_TO_AP, ml.InputToUse.ROTATIONS)
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.STAS_TO_STA, ml.InputToUse.ROTATIONS,
               targetStaId=qdScenario.nbNodes - 1)  # For all STAs to STA case, we use the last STA as a target

    # # Use only coordinates
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.AP_TO_STAS, ml.InputToUse.COORDINATES)
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.STAS_TO_AP, ml.InputToUse.COORDINATES)
    ml.topKSls(qdScenario, codebooks, qdScenario.preprocessedSlsData.powerPerSectorList, qdScenario.dataIndex,
               ml.CommunicationMode.STAS_TO_STA, ml.InputToUse.COORDINATES,
               targetStaId=qdScenario.nbNodes - 1)  # For all STAs to STA case, we use the last STA as a target
