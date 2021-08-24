# The NIST Q-D Interpreter Software

The NIST Q-D Interpreter software has been developed to help visualizing Beamforming Training (BT) results using 3D visualization. This software is part of the [NIST Q-D Framework](https://github.com/wigig-tools) and at such is using input for both the [NIST Q-D Channel Realization software](https://github.com/wigig-tools/qd-realization) and [ns-3 802.11ad/ay implementation](https://github.com/wigig-tools/wigig-module).

The NIST Q-D Interpreter software is developed in Python and uses the [Mayavi](https://docs.enthought.com/mayavi/mayavi/) library. 
It provides a flexible, scalable 3D visualizer to analyze BT results and more particularly:
* Sector-Level-Sweep (SLS) BT
* MIMO BT
* Beamtracking results

Recently, sensing visualizations were added to allow:
* Visualization of human targets moving and their associated Multi-Paths Components (MPCs)
* Visualization of the doppler range map

It is worth mentioning that the The NIST Q-D Interpreter software comes with its own implementation of the Q-D propagation model which allows to visualize the BT results without having to use system-level simulations.

This wiki is organized as follows:
* Section [Installation](#installation) describes how to install the NIST Q-D Interpreter software
* Section [First Steps](#first-steps) helps to user to get familiar with the visualizer. In particular, it shows how to launch the visualizer and configure the different visualization options to customize the visualizer appearance
* how to visualize \gls{SLS} \gls{BT} results

# Installation

# First Steps

## First time launch

To launch the visualizer, the scenario name must be specified using the `--s` option. The command below displays the command to execute a scenario named `scenarioName`.
 
`$ python qdVisualizer.py --s scenarioName`

For the purpose of this document, we will use the _Raw Spatial Sharing _scenario as an example scenario. It gives us the following command:

```$ python qdVisualizer.py --s RawSpatialSharing```

The first time a scenario is launched, it just reads the input from the NIST Q-D channel realization software and ns-3 and nothing is configured for the visualization itself. Once the visualizer is launched, you should obtain the visualization displayed on the figure below.


<img src="docs/img/RawSSFirstLaunch.png" alt="drawing">

We can observe that the visualizer is made of two main windows that we will refer to as `Left View` and `Right view`. 
The first time that a scenario is launched, all the faces of the 3D geometry of the environment are set to be opaque. 
The first thing to do is to configure the visualization correctly to display what we want to visualize. 


## Configuring the 3D environment appearance 
For an indoor scenario such as the Raw Spatial Sharing scenario, we must select the faces to hide in order to visualize the indoor environment. 
To do so, click on the `Environment Interaction` tab in the GUI. 
Then, select the top face of the left view. 
It should be now colored in red to state that it's currently selected as displayed in the figure below.

<img src="docs/img/RawSSFrontFaceCulling.png" alt="drawing">

Finally, click on the option `Front` that appears in the `Face Culling` box. 
The top face of the room should now be hidden. `Front face culling` must be used to hide a face whose normal is facing the camera while back face culling is doing the opposite. 

You should now have a view of the inside of the room on the `left view` as displayed on the picture below. 

<img src="docs/img/RawSSFrontFaceCulled.png" alt="drawing">

Try to apply front face culling to the side facea in order to reveal more of the inside of the room on both the `left` `right` view. 
The video below summarizes all the steps we perform to obtain a view that can be usable for visualization. 

The video below summarizes the steps performed.

<img src="docs/gif/RawSSCompleteEnvironmentConf.gif" alt="drawing">

If you want to keep the visualization configuration created for the scenario, just hit the `Save Environment` button highlighted in the picture below and the configuration will be loaded the text type you launch the scenario. 

<img src="docs/img/RawSSHighlightsSave.png" alt="drawing">

## Tweaking nodes, antenna arrays and MPCs appearance
When the visualizer is launched for the first time for a scenario, it's using default values for:
* nodes size
* nodes labels  
* Phased Antenna Arrays (PAAs) size
* MPCs size and colors
* On wich views to display nodes, nodes 3D Models, nodes labels and PAAs

After the configuration done in Section XXX, the `Raw Spatial Sharing` scenario is as depicted on the figure below. 

<img src="docs/img/RawSSBeforeConfigure.png" alt="drawing">

We can see that the MPCs different reflections order are hard to distinguish, that the nodes representations hide the nodes PAAs.  

The NIST Q-D interpreter can be used for a wide variety of scenario (indoor, outdoors, all variable in size) and thus, it's needed to configure the nodes, PAAs and MPCs visualization when first launching a scenario. 

To do so, one must select the `Visualization Tweak` tab in the GUI.

Each node is represented by a 3D sphere. Set the STAs and APs size to '0.4' as displayed below. 

<img src="docs/img/RawSSSetNodesSize.png" alt="drawing">

Each node PAA element is represented with cubes. Set the PAA size to '2' as displayed below. 

<img src="docs/img/RawSSSetPAAsSize.png" alt="drawing">

By default, MPCs all have the same width and LoS MPC is colored in blue, 2nd order reflection in red, and third order in green. Set the LoS reflection thickness to `0.1` by selecting `MPCs reflection` 0 in the list and set 'MPCs size' to 0.1 as displayed below.

<img src="docs/img/RawSSSetMPCsSize.png" alt="drawing">

Proceed the same way to set the 1st order reflection to `0.05` and 2nd order reflection to `0.01`.

The visualization of the scenario should now look like the picture displayed below and we can clearly see the devices, the PAAs, and distinghish the MPCs corresponding to each reflection order. 

<img src="docs/img/RawSSConfigurationDone.png" alt="drawing">


If you want to save the configuration, just click on `Save Config` as displayed below.

<img src="docs/img/RawSSSaveConfig.png" alt="drawing">

The next time the visualizer will be launched for this scenario, the configuration done will be used to display Nodes, PAAs, and MPCs. 


Each node can also use a 3D models. For this, click on the `Display 3D Objects` as displayed below.

<img src="docs/img/RawSSWithModels.png" alt="drawing">

There are two defaults models in the repository (one for the STAs and one for the APs).
The AP model is displayed below. 


<img src="docs/img/apDefaultModel.png" alt="drawing" width=300>

The STAs model is displayed below.

<img src="docs/img/staDefaultModel.png" alt="drawing" width=150>

Please note that these 3D models are pretty simple. One can still import any 3D models in the visualizer. To do so, please refer to Section XXX.  

## Interacting with a scenario

The `Raw Spatial Sharing` scenario is made of 1 AP (AP0) and 3 STAs (STA1, STA2, STA3). The scenario is made of 100 traces and STA3 is the only node moving along the y-axis. To interact with the scenario, select the `Scenario Interaction` tab in the GUI. 

To go to a specific trace, just enter the traces you want to visualize in the `Trace` GUI as displayed below. 
To iterate over the traces, the toolbar displayed below is provided. 

<img src="docs/img/iterationIcons.png" alt="drawing">


One can either going forward (play icon), backward (rewind icon), pause (pause icon), or go back to trace 0 (stop icon). It is worth mentionning that the trace iteration is set by default to `1` and can be changed using the `Playspeed (Trace per Animation)` value.

The video below shows the iteration over all the traces.

<img src="docs/gif/RawSSNode0to1.gif" alt="drawing">

On this video, we can observe STA3 moving along the y axis as expected. However, the right view remains static. It is as expected as by default, the visualizer displays the MPCs for a transmitter set to node 0 (AP0) and node 1 (STA1). Both of these nodes are static so the MPCs remaing the same all along the scenario.

To change the transmitter or receiver node, just change the value of `TX Nodes` and `Rx Nodes` in the GUI as displayed below in the video. 

<img src="docs/gif/RawSSNode0to3.gif" alt="drawing">

Now, we can see that when the transmitting node is set to 0 and the receiving node is set to 3, the MPCs are updated each trace. 

# SLS Visualization

There are two ways to visualize the SLS BT:
* Using the Oracle mode
* Using ns-3 results

In order to enable the SLS visualization, the option `--sls` must be used. 

## SLS Visualization with the Oracle mode

The oracle mode allows to visualize SLS results without running the scenario in ns-3. The Q-D propagation model developped in ns-3 has been reimplemented in Python to obtain the results.

To visualize SLS Oracle results, two modes are available:
* online: The SLS results are computed while visualizing. This method allows to load the scenario faster but is slower to display the SLS results
* preprocessed: The entire SLS results between every pair of nodes are computed the first time that the scenario is launched, and saved for next time the scenario will be visualized. This method is slower to launch the first time, but faster to display the SLS results when visualizing

It is worth mentionning that the configuration of this mode requires to add the option `dataMode`. By default, the `dataMode` is set to `none` and the oracle SLS results are not available. 

### Oracle SLS Online Mode

To launch the `LROOM` scenario with the Oracle SLS activated and set to `online`, execute the following command.

`python qdVisualizer.py --s LRoom --sls --dataMode online`

Then, just iterate through the traces using the `Play` button. 

<img src="docs/gif/LROOMSLSOnline.gif" alt="drawing">

We can see that the Tx and Rx antenna patterns are updated based on the MPCs availability. 

### Oracle SLS Preprocessed Mode

To launch the `LROOM` scenario with the Oracle SLS activated and set to `preprocessed`, execute the following command.

`python qdVisualizer.py --s LRoom --sls --dataMode preprocessed`


<img src="docs/gif/LROOMSLSPreprocessed.gif" alt="drawing">

We can observe that the SLS is slighly faster to visualize than in the `online` mode even if the overhead generated by the video capture is decreasing the difference in speed for both mode in real utilization.

## SLS Visualization with ns-3 Results

For this mode, the scenario must have been executed in ns-3 to obtain the SLS results file (please check ns-3 802.11ad/ay documentation to see how to proceed).
For the `LRoom` scenario available in this repository, the ns-3 results file is already included. It is located in `\LRoom\Output\Ns3\Results\SLS`. The SLS file is named `sls_1.csv`.
If you want to import new results, just replace this file. 

To enable the visualization of the ns-3 SLS results, select the `SLS` tab and switch the value from the GUI field `SLS from` to ns-3. The video below displays the SLS results obtained with ns-3.

<img src="docs/gif/SLSns3CompleteTraces.gif" alt="drawing">

Please note that you can also iterate the ns-3 results based on their BT ID. ns-3 won't perform a beamforming every trace (oracle mode does) and thus, you can iterate for every transmitter/receiver pair whenever a BT has been performed. To do so, change the value in the GUI of the `BFT trace` field as displayed in the video below. 

<img src="docs/gif/SLSns3IteratePerTraces.gif" alt="drawing">


## MISC
TODO
* Change Antenna Pattern properties
* Display STA association

# Q-D Interpreter
This repository contains the Q-D Interpreter implementation. The Q-D Interpreter can be used in two ways:
1. With visualizer (mainly to check Beamforming Training Results and the correctness of the scenario). The python script to use is: qdVisualizer.py. **NEERAJ**
1. Without visualizer (mainly to perform Capacity computations and Machine-Learning tasks). The python script to use is: qdSchedulingMlExample.py **RAIED**

## Features:
1. This application allows to visualizer the beamforming training evolution, and in particular, the SLS TxSS phase. Each beamforming training is visualized thanks to the directivity of the antenna pattern resulting of the beamforming training SLS phase.
1. The Multi-Paths components between a pair of transmitter/receiver are displayed.
1. The system level performance (Capacity/Power Receiver per Sector, etc.) can be visualized
1. Perform Machine-Learning Beamforming-Training 
1. Compute capacity

The Q-D Interpreter comes with a test Scenario _(ScenarioAsilomar6ap6sta)_ that helps the user to get familiarize with the framework. To access more complex scenario, please send an email to tanguy.ropitault@nist.gov.


Here is a sample snapshot for our Q-D visualizer:

![Snapshot for our Codebook Generator App](qdSnapshot.png)

# Download Information:
Just clone or download the repository.

# Installation
1. If you want to use the Q-D Interpreter with visualizer, please refer to *"InstallVisualizer.md"* document in the *"docs"* folder or click directly [here](https://gitlab.nist.gov/gitlab/tnr1/qdInterpreter/-/blob/master/docs/InstallVisualizer.md). **NEERAJ**
1. If you want to use the Q-D Interpreter without visualizer, please refer to *"InstallWithoutVisualizer.md"* document in the *"docs"* folder or click directly [here](https://gitlab.nist.gov/gitlab/tnr1/qdInterpreter/-/blob/master/docs/InstallWithoutVisualizer.md). **RAIED**

# Usage 
1. If you want to use the Q-D Interpreter with visualizer, please refer to *"ReadmeVisualizer.md"* document in the *"docs"* folder or click directly [here](https://gitlab.nist.gov/gitlab/tnr1/qdInterpreter/-/blob/master/docs/ReadmeVisualizer.md). **NEERAJ**
1. If you want to use the Q-D Interpreter without visualizer, please refer to *"ReadmeWithoutVisualizer.md"* document in the *"docs"* folder or click directly [here](https://gitlab.nist.gov/gitlab/tnr1/qdInterpreter/-/blob/master/docs/ReadmeWithoutVisualizer.md). **RAIED**


# Author Information:
The Q-D Interpreter is developed and maintained by [Tanguy Ropitault](https://www.nist.gov/people/tanguy-ropitault).

# Author Information:
The Q-D Interpreter is developed and maintained by [Tanguy Ropitault](https://www.nist.gov/people/tanguy-ropitault).