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
import scheduler
import numpy as np
import os

# Initialize the oracle
qdScenario, txParam, codebooks, environmentFile, maxReflectionOrder = globals.initializeOracle()

# Setup the association mode
allAssociationModes = [scheduler.StaAssociationMode.BEST_AP, scheduler.StaAssociationMode.SAME_AP]
for associationMode in allAssociationModes:
    from itertools import combinations
    # Get the list of all STAs ID
    staIdsList = np.arange(qdScenario.nbAps, qdScenario.nbNodes)
    for nbSample in range(qdScenario.nbStas, qdScenario.nbStas + 1):
        allCombinations = list(
            combinations(staIdsList, nbSample))  # Find all the STA ID combinations nCr for nbSample sample
        for staIdToConsider in allCombinations:
            if nbSample == qdScenario.nbStas:
                folderPrefix = os.path.join(associationMode.value, "AllSTAs")
                if not os.path.exists(folderPrefix):
                    os.makedirs(folderPrefix)
            else:
                folderPrefix = str(nbSample) + "STAs"
                for name in staIdToConsider:
                    folderPrefix += ("_" + str(name))
                folderPrefix = os.path.join(associationMode.value, folderPrefix)
                if not os.path.exists(folderPrefix):
                    os.makedirs(folderPrefix)
            # Compute the downlink data transmission for all AP for one association mode
            scheduler.computeDataTransmission(qdScenario, associationMode, staIdToConsider, folderPrefix,
                                              qdScenario.preprocessedSlsData, qdScenario.preprocessedAssociationData,
                                              txParam, qdScenario.dataIndex)
