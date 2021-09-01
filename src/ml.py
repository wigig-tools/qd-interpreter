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


import os
from enum import Enum

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

import globals as gb
import qdPropagationLoss
import qdRealization
from modelLib import Models

# initialize random seeds for reproducible results when comparing ML models
tf.random.set_seed(0)
np.random.seed(0)


def top_10_accuracy(y_true, y_pred):
    """Return the topk=10 accuracy
    """
    return tf.keras.metrics.top_k_categorical_accuracy(y_true, y_pred, k=10)


def top_50_accuracy(y_true, y_pred):
    """Return the topk=50 accuracy
    """
    return tf.keras.metrics.top_k_categorical_accuracy(y_true, y_pred, k=50)


class CommunicationMode(Enum):
    """Enumeration that contains the possible communication modes
    """
    STAS_TO_AP = "StaToAp"  # We want to check the SLS phase from ALL STAs to ONE AP
    AP_TO_STAS = "ApToSta"  # We want to check the SLS phase from ONE AP to ALL STAs
    STAS_TO_STA = "StaToSta"  # We want to check the SLS phase from ALL STAs minus 1 to ONE STA


class InputToUse(Enum):
    """Enumeration that describes the training input values
    """
    COORDINATES = "Coordinates"  # We use only the coordinates
    ROTATIONS = "Rotations"  # We use only the rotations
    COORDINATES_ROTATIONS = "CoordinatesAndRotations"  # We use both coordinates and rotations


def getInputValues(qdScenario, inputToUse):
    """Get the input data for the training depending on the input to use
    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    inputToUse : InputToUse Class
        The type of input values to use for the training (coordinates, rotations, or coordinates and rotations)

    Returns
    -------
    inputData : Numpy Array
        The input data to use for the training
    """
    # Load the STAs and APs coordinates and rotations information
    scenarioQdVisualizerFolder = os.path.join(gb.scenarioPath, gb.qdRealizationOutputFolder,
                                              gb.qdRealizationVisualizerFolder)
    qdRealization.readJSONNodesPositionFile(scenarioQdVisualizerFolder, gb.nodePositionJSON, qdScenario)
    # Transform the data for the ML framework
    if inputToUse == InputToUse.COORDINATES:
        # Use only Coordinates
        inputData = qdScenario.getAllSTAsAllPositions()  # Get the STAs coordinates
        inputData = np.transpose(inputData, (2, 0, 1))
        inputData = inputData.reshape(qdScenario.nbTraces * qdScenario.nbStas, 3)
    elif inputToUse == InputToUse.ROTATIONS:
        # Use only Rotations
        inputData = qdScenario.getAllSTAsAllRotations()  # Get the STAs rotations
        inputData = np.transpose(inputData, (2, 0, 1))
        inputData = inputData.reshape(qdScenario.nbTraces * qdScenario.nbStas, 3)
        inputData = np.deg2rad(inputData[:, :])  # Convert all the rotation angles from deg to rad
    elif inputToUse == InputToUse.COORDINATES_ROTATIONS:
        # Use Coordinates and Rotations
        inputData = np.concatenate((qdScenario.getAllSTAsAllPositions(), qdScenario.getAllSTAsAllRotations()),
                                   axis=1)  # Concatenate STAs positions and rotations
        inputData = np.transpose(inputData, (2, 0, 1))
        inputData = inputData.reshape(qdScenario.nbTraces * qdScenario.nbStas, 6)
        inputData[:, 3:6] = np.deg2rad(inputData[:, 3:6])  # Convert all the rotation angles from deg to rad
    return inputData


def getGroundTruthValues(qdScenario, codebooks, communicationMode, dataIndex, targetApId, targetStaId, slsRxPower):
    """Get the ground truth values (in our case, the power received in dBm for every sector and traces)

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    communicationMode : CommunicationMode Class Enum
        The communication mode used for the training (AP_TO_STAS, STAS_TO_AP, or STAS_TO_STA)
    dataIndex : Dic
        Used for the correct indexing of slsRxPower (preprocessed slsRxPower file can be pretty huge and we removed the indexing from the file to save some space so we reconstruct it at runtime)
    targetApId : int
        The AP to consider when AP_TO_STAS or STAS_TO_AP mode is used
    targetStaId : int
        The STA to consider when STAS_TO_STA communication mode is used
    slsRxPower : Numpy array
        The preprocessed data from the SLS phase (it contains the Rx Power for every transmission for all sectors tested in the SLS phase)
    """
    if communicationMode == CommunicationMode.AP_TO_STAS:
        #####################################################
        #    AP TO STAs                                     #
        #####################################################
        # We want to perform the training using the SLS data of one AP (targetApId) to all the STAs
        rowIndex = 0
        nbSectorsPerApAntenna = codebooks.getNbSectorPerApAntenna()
        y_all = np.zeros((qdScenario.nbTraces * qdScenario.nbStas, nbSectorsPerApAntenna))

        for staId in range(qdScenario.nbAps, qdScenario.nbNodes):
            # Iterate over all the STAs in the simulation
            for traceId in range(qdScenario.nbTraces):
                # Iterate over all the traces of the simulation
                # We get the power for every tx sector for a given trace for targetApId to staId transmission and convert it from dBm to W
                index = dataIndex[(targetApId, staId, 0, 0,
                                   traceId)]  # Get the index for the slsRxPower TODO The 0,0 should be the paaTx,paaRx (not a problem until we use MIMO)
                # Our default behavior is to return a power of -infinite when the communication between nodes is impossible
                # Replace the -infinite values with large negative values to allow the training
                slsRxPowerWithoutInfinite = np.nan_to_num(slsRxPower[index])
                y_all[traceId + rowIndex * qdScenario.nbTraces] = qdPropagationLoss.DbmtoW(slsRxPowerWithoutInfinite)
                # We transform the data to have the sum of all the power per sector of a given trace equal to 1
                y_all[traceId + rowIndex * qdScenario.nbTraces] = y_all[traceId + rowIndex * qdScenario.nbTraces] / sum(
                    y_all[traceId + rowIndex * qdScenario.nbTraces])
            rowIndex += 1
    elif communicationMode == CommunicationMode.STAS_TO_AP:
        ######################################################
        #     STAs TO AP                                      #
        ######################################################
        # We want to perform the training using the SLS data from all STAs to one AP (apTargetId)
        rowIndex = 0
        nbSectorsPerStaAntenna = codebooks.getNbSectorPerStaAntenna()
        y_all = np.zeros((qdScenario.nbTraces * qdScenario.nbStas, nbSectorsPerStaAntenna))
        for staId in range(qdScenario.nbAps, qdScenario.nbNodes):
            # Iterate over all the STAs in the simulation
            for traceId in range(qdScenario.nbTraces):
                # Iterate over all the traces of the simulation
                # We get the power for every tx sector for a given trace for staId to targetApId transmission and convert it from dBm to W
                index = dataIndex[(staId, targetApId, 0, 0,
                                   traceId)]  # Get the index for the slsRxPower TODO The 0,0 should be the paaTx,paaRx (not a problem as we are not in MIMO case)

                # Our default behavior is to return a power of -infinite when the communication between nodes is impossible
                # Replace the -infinite values with negative large values to allow the training
                slsRxPowerWithoutInfinite = np.nan_to_num(slsRxPower[index])
                y_all[traceId + rowIndex * qdScenario.nbTraces] = qdPropagationLoss.DbmtoW(slsRxPowerWithoutInfinite)
                # We transform the data to have the sum of all the power per sector of a given trace equal to 1
                y_all[traceId + rowIndex * qdScenario.nbTraces] = y_all[traceId + rowIndex * qdScenario.nbTraces] / sum(
                    y_all[traceId + rowIndex * qdScenario.nbTraces])
            rowIndex += 1
    elif communicationMode == CommunicationMode.STAS_TO_STA:
        ######################################################
        #     STAs TO STA                                    #
        ######################################################
        # We want to perform the training using the SLS data of ALL STAs (minus one, the targetStaId) to one STA (targetStaId)
        # Get all the power received for all STAs to targetStaId transmissions and this for every tx sector of the STAs
        rowIndex = 0
        nbSectorsPerStaAntenna = codebooks.getNbSectorPerStaAntenna()
        y_all = np.zeros((qdScenario.nbTraces * qdScenario.nbStas, nbSectorsPerStaAntenna))
        for staId in range(qdScenario.nbAps, qdScenario.nbNodes):
            for traceId in range(qdScenario.nbTraces):
                # Go over every traces
                if targetStaId == staId:
                    # We don't want to add the targetStaId to targetStaId data
                    break
                index = dataIndex[(staId, targetStaId, 0, 0,
                                   traceId)]  # Get the index for the slsRxPower TODO The 0,0 should be the paaTx,paaRx (not a problem as we are not in MIMO case)
                # Our default behavior is to return a power of -infinite when the communication between nodes is impossible
                # Replace the -infinite values with negative large values to allow the training
                slsRxPowerWithoutInfinite = np.nan_to_num(slsRxPower[index])
                y_all[traceId + rowIndex * qdScenario.nbTraces] = qdPropagationLoss.DbmtoW(slsRxPowerWithoutInfinite)
                if sum(y_all[traceId + rowIndex * qdScenario.nbTraces]) != 0:
                    y_all[traceId + rowIndex * qdScenario.nbTraces] = y_all[
                                                                          traceId + rowIndex * qdScenario.nbTraces] / sum(
                        y_all[traceId + rowIndex * qdScenario.nbTraces])
            rowIndex += 1
    return y_all


def topKSls(qdScenario, codebooks, slsRxPower, dataIndex, communicationMode=CommunicationMode.AP_TO_STAS,
            inputToUse=InputToUse.COORDINATES_ROTATIONS, targetApId=0, targetStaId=0, nbEpochs=100,
            modelType='Baseline'):
    """Compute the Top-K for the SLS phase

    Parameters
    ----------
    qdScenario: QdScenario class
        Scenario parameters (number of nodes, APs, STAs, trace numbers, etc.)
    slsRxPower : Numpy array
        The preprocessed data from the SLS phase (it contains the Rx Power for every transmission for all sectors tested in the SLS phase)
    dataIndex : Dic
        Used for the correct indexing of slsRxPower (preprocessed slsRxPower file can be pretty huge and we removed the indexing from the file to save some space so we reconstruct it at runtime)
    communicationMode : Enum
        The communication mode used for the training (AP_TO_STAS, STAS_TO_AP, or STAS_TO_STA)
    inputToUse : InputToUse Class
        The training input for the training (either coordinates, rotations, or rotations and coordinates)
    targetApId : int
        The AP to consider when AP_TO_STAS or STAS_TO_AP mode is used (optional and default set to 0)
    targetStaId : int
        The STA to consider when STAS_TO_STA communication mode is used (optional and default set to 0)
    nbEpochs : int
        The number of epochs used for the training
    modelType : string
        The name of the model to use ('baseline' (default), 'CoordinatesAndRotationsSplit')
    """

    x_all = getInputValues(qdScenario, inputToUse)
    y_all = getGroundTruthValues(qdScenario, codebooks, communicationMode, dataIndex, targetApId, targetStaId,
                                 slsRxPower)

    # We need to handle differently the STAS_TO_STA case as it's not using all the STAs as an input
    if communicationMode != CommunicationMode.STAS_TO_STA:
        # AP_TO_STAS or STAS_TO_AP Case
        # We will use all the STAs as an input of the ML
        totalNumberOfInput = qdScenario.nbTraces * qdScenario.nbStas
    else:
        # For STAS to STA communication, we want to add to the already created input data
        # the characteristics of the targetStaId (coordinates and rotations)
        targetStaCoordinatesRotations = x_all[(targetStaId - qdScenario.nbAps) * (
            qdScenario.nbTraces):]  # Get the targetStaId coordinates and rotations
        # Construct an array repeating targetStaId coordinates and rotations to use it as an input of the ML
        targetStaCoordinatesRotationsTiled = np.tile(targetStaCoordinatesRotations, (qdScenario.nbStas - 1,
                                                                                     1))
        # Here, we could have filtered the coordinates, or the rotations, we decided to use both
        # targetStaCoordinatesRotationsTiled = targetStaCoordinatesRotationsTiled[:,3:6]

        # Filter to remove the SLS results of the targetStaId as we don't want them (full of 0 anyway as not computed)
        y_all = y_all[:(
                               targetStaId - qdScenario.nbAps) * qdScenario.nbTraces]
        x_all = x_all[:(targetStaId - qdScenario.nbAps) * (
            qdScenario.nbTraces)]  # Filter to remove the coordinates and rotations of targetStaId as we don't want them
        x_all = np.concatenate([x_all, targetStaCoordinatesRotationsTiled],
                               axis=1)  # Add the coordinates and rotations of targetStaId to the input data for the training
        totalNumberOfInput = qdScenario.nbTraces * (qdScenario.nbStas - 1)

    # Split the data into training, validation and testing data
    percentForTraining = 0.5
    percentForValidation = 0.2
    percentForTesting = 0.3

    # Compute the indexing of the training, validation and testing dataset
    beginTraceTraining = 0
    endTraceTraining = round(totalNumberOfInput * percentForTraining)

    beginTraceValidation = endTraceTraining + 1
    endTraceValidation = endTraceTraining + round(totalNumberOfInput * percentForValidation)

    beginTraceTesting = endTraceValidation + 1
    endTraceTesting = endTraceValidation + round(totalNumberOfInput * percentForTesting)

    print("Start Data Training:", beginTraceTraining)
    print("End Data Training:", endTraceTraining)
    print("Start Data Validation:", beginTraceValidation)
    print("End Data Validation:", endTraceValidation)
    print("Start Data Testing:", beginTraceTesting)
    print("End Data Testing:", endTraceTesting)

    # Randomize the data
    N = y_all.shape[0]
    randIndex = np.arange(N)
    np.random.shuffle(randIndex)
    x_all = x_all[randIndex]
    y_all = y_all[randIndex]

    # Create the datasets for the training
    X_coord_train = x_all[:endTraceTraining, :]
    X_coord_validation = x_all[beginTraceValidation:endTraceValidation, :]
    X_coord_testing = x_all[beginTraceTesting:endTraceTesting, :]

    y_train = y_all[:endTraceTraining, :]
    y_validation = y_all[beginTraceValidation:endTraceValidation, :]
    y_testing = y_all[beginTraceTesting:endTraceTesting, :]

    ################################################################
    #                   Machine-Learning Part                      #
    ################################################################
    batch_size = 32
    thisModel = Models()
    opt = tf.keras.optimizers.Adam()

    # The number of classes just depends from the codebook number of sectors
    if communicationMode == CommunicationMode.AP_TO_STAS:
        num_classes = codebooks.getNbSectorPerApAntenna()
    elif CommunicationMode.STAS_TO_AP:
        num_classes = codebooks.getNbSectorPerStaAntenna()
    elif communicationMode == CommunicationMode.STAS_TO_STA:
        num_classes = codebooks.getNbSectorPerStaAntenna()

    model = thisModel.createModel(modelType, num_classes, (x_all.shape[1],))

    model.compile(loss=tf.keras.losses.categorical_crossentropy,
                  optimizer=opt,
                  metrics=[tf.keras.metrics.categorical_accuracy,
                           tf.keras.metrics.top_k_categorical_accuracy, top_10_accuracy,
                           top_50_accuracy, tf.keras.metrics.mean_squared_error])

    model.summary()


    # from tensorflow.keras.utils import plot_model
    # plot_model(model, to_file='model.pdf')

    hist = model.fit(X_coord_train, y_train,
                     validation_data=(X_coord_validation, y_validation), epochs=nbEpochs, batch_size=batch_size,
                     verbose=0)
    # verbose 0 = silent, 1 = progress bar, 2 = one line per epoch

    print("============================================================================================")
    print("Evaluate on test data for model:", modelType, " , input data type:", inputToUse.value,
          "and communication mode:", communicationMode.value)
    results = model.evaluate(X_coord_testing, y_testing, batch_size=batch_size)
    print("Test loss, Test accuracy, Test topk5, Test top10, Test topk50, Test MSE:", results)
    print("============================================================================================")
    # Plot and save the graphs
    acc = hist.history['top_k_categorical_accuracy']
    val_acc = hist.history['val_top_k_categorical_accuracy']

    loss = hist.history['loss']
    val_loss = hist.history['val_loss']
    epochs = range(1, len(acc) + 1)

    fig, (ax1, ax2) = plt.subplots(1, 2)
    ax1.set_xlabel('Epochs')
    ax1.set_ylabel('Accuracy')
    ax1.plot(epochs, acc, 'b--', label='accuracy')
    ax1.plot(epochs, val_acc, 'g-', label='validation accuracy')
    ax1.legend()
    ax2.set_xlabel('Epochs')
    ax2.set_ylabel('Loss')
    ax2.plot(epochs, loss, 'b--', label='loss')
    ax2.plot(epochs, val_loss, 'g--', label='validation loss' )
    ax2.legend()

    destinationPath = os.path.join(gb.scenarioPath, gb.graphFolder, gb.mlFolder, gb.slsFolder, inputToUse.value)
    if not os.path.exists(destinationPath):
        os.makedirs(destinationPath)
    fileToSave = os.path.join(destinationPath, modelType+communicationMode.value + inputToUse.value + ".pdf")
    # Save the data
    f = open(os.path.join(destinationPath, modelType+communicationMode.value + inputToUse.value + ".csv"), "w")
    f.write("Loss,Categorical Accuracy, topK=5 Accuracy,top k=10 Accuracy, topk=50 accuracy, Mean Square Error\n")
    f.write(str(results))
    plt.savefig(fileToSave)
    plt.clf()
