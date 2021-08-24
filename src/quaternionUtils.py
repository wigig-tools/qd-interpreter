
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

import quaternion
import numpy as np

#TODO Update with the latest implementation in the Q-D realization software and comment
# For now, it's just a mimimal implementation copied-pasted from the matlab code
def qtrnFeul(euclidian,axisOrder):
    """Obtain the quaternion corresponding to the Euler rotation
    """
    euclidian = euclidian/2
    a = euclidian[...,0]
    b = euclidian[...,1]
    c = euclidian[...,2]
    qa = np.cos(a)*np.cos(b)*np.cos(c) - np.sin(a)*np.sin(b)*np.sin(c)
    qb = np.cos(a)*np.cos(c)*np.sin(b) - np.cos(b)*np.sin(a)*np.sin(c)
    qc = np.cos(a)*np.cos(b)*np.sin(c) + np.cos(c)*np.sin(a)*np.sin(b)
    qd = np.cos(b)*np.cos(c)*np.sin(a) + np.cos(a)*np.sin(b)*np.sin(c)
    quaternionResult = qa,qb,qc,qd
    return quaternion.as_quat_array(np.transpose(quaternionResult))

def eulFqtrn(q,mode):
    """Obtain the quaternion corresponding to the Euler rotation
    """
    # Obtain the Euler angles corresponding to a quaternion rotation
    quaternionAsFloat = quaternion.as_float_array(q)
    qa = quaternionAsFloat[...,0]
    qb = quaternionAsFloat[...,1]
    qc = quaternionAsFloat[...,2]
    qd = quaternionAsFloat[...,3]
    the1 = np.ones(qa.shape)
    the2 = 2*the1
    tmp = qa*qb*the2 + qc*qd*the2
    if tmp > 1:
        tmp = 1
    if tmp < -1:
        tmp = -1

    # Compute the three rotation angles
    a = np.arctan2((qa*qd*the2 - qb*qc*the2),(qa**2*the2 - the1 + qc**2*the2))
    b = np.arcsin(tmp)
    c = np.arctan2((qa*qc*the2 - qb*qd*the2),(qa**2*the2 - the1 + qd**2*the2))
    return [a,b,c]

def coordinateRotation(P, C, euler, rotationType):
    """Apply rotation using quaternion
    """
    Q = []
    for element in euler:
        Q.append(qtrnFeul(element , 'ZXY'))

    totalQuaternionRotation =  Q[0] * Q[1]
    return np.rad2deg(eulFqtrn(totalQuaternionRotation,'ZXY'))