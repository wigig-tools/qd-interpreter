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
    qdScenario, preprocessedSlsData, preprocessedAssociationData, txParam, dataIndex, qdProperties, codebooks, environmentFile, maxReflectionOrder,suMimoResults, maxSupportedStreams, mimoResults = globals.initializeOracle()  # We don't want to use the visualizer

    # To uncomment if interested into computing scheduling and capacity
    # allAssociationModes = [scheduler.StaAssociationMode.BEST_AP,scheduler.StaAssociationMode.SAME_AP]
    # for associationMode in allAssociationModes:
    #     from itertools import combinations
    #     # Get the list of all STAs ID
    #     staIdsList = np.arange(qdScenario.nbAps, qdScenario.nbNodes)
    #     for nbSample in range(qdScenario.nbStas, qdScenario.nbStas + 1):
    #         allCombinations = list(
    #             combinations(staIdsList, nbSample))  # Find all the STA ID combinations nCr for nbSample sample
    #         for staIdToConsider in allCombinations:
    #             if nbSample == qdScenario.nbStas:
    #                 folderPrefix = os.path.join(associationMode.value, "AllSTAs")
    #                 if not os.path.exists(folderPrefix):
    #                     os.makedirs(folderPrefix)
    #             else:
    #                 folderPrefix = str(nbSample) + "STAs"
    #                 for name in staIdToConsider:
    #                     folderPrefix += ("_" + str(name))
    #                 folderPrefix = os.path.join(associationMode.value, folderPrefix)
    #                 if not os.path.exists(folderPrefix):
    #                     os.makedirs(folderPrefix)
    #             scheduler.computeDataTransmission(qdScenario,associationMode,staIdToConsider,folderPrefix,preprocessedSlsData,preprocessedAssociationData,txParam,dataIndex)

    # Machine-Learning Beamforming-Training
    # Use coordinates and rotations
    # ml.topKSls(qdScenario, codebooks, preprocessedSlsData.powerPerSectorList, dataIndex,
    #            ml.CommunicationMode.AP_TO_STAS, ml.InputToUse.COORDINATES_ROTATIONS,
    #            modelType='CoordinatesAndRotationsSplit')
    ml.topKSls(qdScenario, codebooks, preprocessedSlsData.powerPerSectorList, dataIndex,
               ml.CommunicationMode.STAS_TO_AP, ml.InputToUse.COORDINATES_ROTATIONS,
               modelType='CoordinatesAndRotationsSplit')
    # ml.topKSls(qdScenario, codebooks, preprocessedSlsData.powerPerSectorList, dataIndex,
    #            ml.CommunicationMode.STAS_TO_STA, ml.InputToUse.COORDINATES_ROTATIONS,
    #            targetStaId=qdScenario.nbNodes - 1, modelType='CoordinatesAndRotationsSplit')  # For all STAs to STA case, we use the last STA as a target