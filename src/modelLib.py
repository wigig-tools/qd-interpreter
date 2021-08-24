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

import tensorflow as tf

class Models:
    """Class to create the training model
    """
    def createModel(self,modelType,numClasses,inputshape):    
        modelList=['Baseline','CoordinatesAndRotationsSplit','CoordinatesAndRotationsSplitExperimental',]
        assert modelType in modelList, "modelType error: set modelType to one of the following:"+str(modelList)

        if(modelType == 'Baseline'):

            model = tf.keras.models.Sequential()
            model.add(tf.keras.Input(inputshape))
            model.add(tf.keras.layers.Dense(4))
            model.add(tf.keras.layers.Activation('relu'))
            model.add(tf.keras.layers.Dense(16))
            model.add(tf.keras.layers.Activation('relu'))
            model.add(tf.keras.layers.Dense(64))
            model.add(tf.keras.layers.Activation('relu'))
            model.add(tf.keras.layers.Dense(numClasses))
            model.add(tf.keras.layers.Activation('softmax'))
        elif(modelType == 'CoordinatesAndRotationsSplit'):
            inputs = tf.keras.Input(inputshape)

            leftInput=inputs[:,0:3]
            left = tf.keras.layers.Dense(4, activation='relu')(leftInput)
            left = tf.keras.layers.Dense(16, activation='relu')(left)
            left = tf.keras.layers.Dense(32,activation='relu')(left)
            left=tf.keras.layers.Dense(numClasses, activation='relu')(left)
            left=tf.keras.layers.LayerNormalization(axis=1)(left)
            
            rightInput=inputs[:,3:6]
            right = tf.keras.layers.Dense(4,activation='relu')(rightInput)
            right = tf.keras.layers.Dense(16, activation='relu')(right)
            right = tf.keras.layers.Dense(32,activation='relu')(right)
            right=tf.keras.layers.Dense(numClasses, activation='relu')(right)           
            right=tf.keras.layers.LayerNormalization(axis=1)(right)


            concatenated = tf.keras.layers.concatenate([left, right])
            out = tf.keras.layers.Dense(numClasses, activation='softmax')(concatenated)
            model = tf.keras.models.Model(inputs, out)
        elif(modelType == 'CoordinatesAndRotationsSplitExperimental'):
            inputs = tf.keras.Input(inputshape)
            leftInput=inputs[:,0:3]#split[0]#
            left = tf.keras.layers.Dense(4, activation='relu')(leftInput)
            left = tf.keras.layers.Dense(16, activation='relu')(left)
            left = tf.keras.layers.Dense(32,activation='relu')(left)
            left=tf.keras.layers.Dense(numClasses, activation='relu')(left)
            left=tf.keras.layers.LayerNormalization(axis=1)(left)

            rightInput=inputs[:,3:6]#split[1]#
            right = tf.keras.layers.Dense(4,activation='relu')(rightInput)
            right = tf.keras.layers.Dense(16, activation='relu')(right)
            right = tf.keras.layers.Dense(32,activation='relu')(right)
            right=tf.keras.layers.Dense(numClasses, activation='relu')(right)
            right=tf.keras.layers.LayerNormalization(axis=1)(right)

            concatenated = tf.keras.layers.concatenate([left, right])
            out = tf.keras.layers.Dense(numClasses, activation='softmax')(concatenated)
            model = tf.keras.models.Model(inputs, out)
        return model
