import os
from os import path
from tvtk.api import tvtk
import math
from mayavi.modules.surface import Surface
import re
from matplotlib import cm
import xml.etree.ElementTree as ET
from mayavi import mlab

cachedSuffix = "_CACHED"


class SceneVisualizationProperties:
    """
    A class to represent the way the scene must be visualized

    Attributes
    ----------
    representation : String
       If the scene must be textured or not
    edgeVisibility: Bool
       If the edges must be visualized or not
    """

    def __init__(self, representation, edgeVisibility):
        self.representation = representation
        self.edgeVisibility = edgeVisibility


class MaterialProperties:
    """
    A class to represent the material library properties

    Attributes
    ----------
    materialNameDic : Dictionary
        Store the name of the material based on its ID as a key
    materialPathDic: Dictionary
        Store the path of the texture associated to the ID of the material
    """

    def __init__(self, materialNameDic, materialPathDic):
        self.materialNameDic = materialNameDic
        self.materialPathDic = materialPathDic


class EnvironmentObject:
    """
    A class to represent an Object of the environment

    Attributes
    ----------
    id : int
        The ID of the object

    name: str
        The name of the object

    mesh: Visualization object
        The mesh of the object

    materialId: Int
        The ID of the material of the object

    hidden: Bool
        Define if the object in hidden in the visualization

    frontFaceCulling: Bool
        Define if the front face must be culled

    BackFaceCulling: Bool
        Define if the back face must be culled

    opacity: Float
        Define the transparency level of the object

    colorChanged: Bool
        Define if the color of object has been changed by the user

    customColor: Tuple
        New color of the object selected by the user

    customTexture: String
        Path to the texture elected by the user

    textureMode: String
        Define the interpolation method used to map the texture to the object
    """

    def __init__(self, objectId, name, mesh, materialId, hidden, frontFaceCulling, backFaceCulling, opacity, textureMode):
        self.id = objectId
        self.name = name
        self.mesh = mesh
        self.materialId = materialId
        self.hidden = hidden
        self.frontFaceCulling = frontFaceCulling
        self.backFaceCulling = backFaceCulling
        self.opacity = opacity
        self.colorChanged = False
        self.customColor = (1, 0, 0)
        self.customTexture = ""
        self.textureMode = textureMode


def parseAmfEnvironment(environmentFile, scenesProperties,textureFolder):
    """Parse the 3D environment when the format used is AMF or XML and construct the visualization objects

    Parameters
    ----------
     environmentFile : String
        File containing the environment
     scenesProperties: Dictionary
        Dictionary storing the scenes properties
    textureFolder: String
        The Path to the texture folder

    Returns
    -------
    materialProperties: MaterialProperties Class
        Material properties (material names and textures paths)
    environmentObjects: Dictionary
        Dictionary storing the objects that make the environment
    """
    materialNameDic = {}  # Dictionary with the Material library names (Material ID is the key and value is the material Name)
    materialPathDic = {}  # Dictionary with the Material texture paths (Material ID is the key and value is the texture path)
    environmentObjects = {}  # Dictionary with the objects constructed
    amfFileToParse = environmentFile
    nbMaterialMtl = 0

    for currentScene in scenesProperties.keys():
        environmentObjects[currentScene] = []
    try:
        AMF_TREE = ET.parse(amfFileToParse)
    except OSError as e:
        print("Error:", e)
        exit()

    AMF_ROOT = AMF_TREE.getroot()
    objectsDict = {}
    # By default, we add a material with ID 0 that corresponds to the case where no material is assigned to a volume
    # Obviously, this choice imposes to use Material ID in the library with an ID greater than 0 TODO: Check if it's the case once we know how to manage the material library
    noMaterialID = "0"
    materialNameDic[noMaterialID] = "No Material"

    unit = "meter" # Default unit is set to meter
    conversionDivider = 1
    for tUnit in AMF_ROOT.iter('amf'):
        # We must get the unit of the AMF file to convert everything to meters (as done in the Q-D realization software)
        if 'unit' not in tUnit.attrib:
            unit = "meter"
        else:
            unit = tUnit.attrib['unit']

    if unit == "meter":
        conversionDivider = 1
    elif unit == "millimeter":
        conversionDivider = 1000
    elif unit == "inch":
        conversionDivider = 39.3701
    elif unit == "feet":
        conversionDivider = 3.28084
    elif unit == "micron":
        conversionDivider = 1000000
    else:
        print("ERROR: AMF Unit Not managed: " ,unit)
        exit()



    # Start by handling the material in the AMF file to build the material library
    for tMaterial in AMF_ROOT.iter('material'):
        # Iterate through all the material in the scenario
        materialId = tMaterial.attrib['id']
        for tName in tMaterial.iter('metadata'):
            materialName = tName.text  # Get the material Name
            materialNameDic[materialId] = materialName  # Add the material to the material dictionary

    for tObject in AMF_ROOT.iter('object'):
        # Iterate through all the objects in the AMF File
        coordinateX = []
        coordinateY = []
        coordinateZ = []
        duplicatedObject = False
        xmlObjectID = tObject.attrib['id']  # Get the Object ID
        for tName in tObject.iter('metadata'):
            xmlObjectName = tName.text  # Get the object Name
            # There is a bug in the way geodata scenario are generated
            # It includes twice every object so we handle that here
            # TODO: Fix the geodata scenarios generation and update the code accordingly
            if xmlObjectName in objectsDict:
                # If an object with the same name has already been parsed, flag it
                duplicatedObject = True
            else:
                # The object does not exist in the object dictionnary, just add it to the objects dictionary
                objectsDict[xmlObjectName] = True

        # Get the X, Y, Z coordinates corresponding to an object
        for tcoordinatesX in tObject.iter('x'):
            # Get x coordinates
            coordinateX.append(float(tcoordinatesX.text)/conversionDivider)
            # coordinateX.append(float(tcoordinatesX.text))
        for tcoordinatesY in tObject.iter('y'):
            # Get y coordinates
            coordinateY.append(float(tcoordinatesY.text)/conversionDivider)
            # coordinateY.append(float(tcoordinatesY.text))
        for tcoordinatesZ in tObject.iter('z'):
            # Get z coordinates
            coordinateZ.append(float(tcoordinatesZ.text)/conversionDivider)
            # coordinateZ.append(float(tcoordinatesZ.text))

        for tVolume in tObject.iter('volume'):
            # Iterate over the volume, i.e., the triangles connections and material
            # Please note that an object can be defined with more than one volume
            try:
                materialId = tVolume.attrib[
                    'materialid']  # Get the material ID associated to the triangles connections
                nbMaterialMtl += 1
            except KeyError:
                # It's possible that a volume is not having any material assigned - Handle it
                # print("Warning: Object :", xmlObjectName, " is not having any material associated to it") TODO Commented for now
                materialId = None

            v1 = []  # First vertex
            v2 = []  # Second vertex
            v3 = []  # Third vertex
            for tTriangles in tVolume.iter('triangle'):
                # Iterate over the triangles of a volume
                for tFirstPoint in tTriangles.iter('v1'):
                    # Get First vertex
                    v1.append(int(tFirstPoint.text))
                for tSecondPoint in tTriangles.iter('v2'):
                    # Get Second vertex
                    v2.append(int(tSecondPoint.text))
                for tThirdPoint in tTriangles.iter('v3'):
                    # Get Third vertex
                    v3.append(int(tThirdPoint.text))

            # Get the final triangles coordinates by connecting the vertices to their associated coordinates
            finalX = []
            finalY = []
            finalZ = []
            for index in range(len(v1)):
                finalX.append([coordinateX[v1[index]], coordinateX[v2[index]], coordinateX[v3[index]]])
                finalY.append([coordinateY[v1[index]], coordinateY[v2[index]], coordinateY[v3[index]]])
                finalZ.append([coordinateZ[v1[index]], coordinateZ[v2[index]], coordinateZ[v3[index]]])

            # Create the triangles connections
            triangles = [(i * 3, (i * 3) + 1, (i * 3) + 2) for i in range(0, len(finalX))]

            if materialId == None:
                # Assign the No Material ID in case no material was assigned to a volume
                materialId = noMaterialID

            if duplicatedObject == False:
                # Add the volume to the visualization only it it was not added previously
                # Create the volume to visualize
                for currentScene in scenesProperties.keys():
                    volume = mlab.triangular_mesh(finalX, finalY, finalZ, triangles,
                                                  representation='surface', name="volume:" + xmlObjectName,
                                                  figure=currentScene, reset_zoom=False)

                    texturePath = os.path.join(textureFolder, str(materialNameDic[str(materialId)]) + ".jpg")
                    if os.path.exists(texturePath) and scenesProperties[currentScene].representation == "Texture":
                        # We add texture only if a texture exists for the material and the scene was configured to be textured
                        # AMF format is not including any way to handle texture
                        # The logic here is that we try to open the file based on the material name
                        # As the texture images are stored in 'Pictures/Textures', the easiest way to texture an AMF scenario
                        # is to place jpg pictures in the 'Pictures/Textures' Folder
                        materialPathDic[materialNameDic[str(materialId)]] = texturePath
                        img = tvtk.JPEGReader()
                        img.file_name = texturePath
                        texture = tvtk.Texture(input_connection=img.output_port, interpolate=0)
                        volume.actor.enable_texture = True

                        volume.actor.tcoord_generator_mode = 'plane'
                        volume.actor.actor.texture = texture
                    else:
                        # No texture so add color depending on the material
                        viridis = cm.get_cmap('viridis', len(materialNameDic))
                        colorToAssign = viridis(int(materialId) / len(materialNameDic))
                        volume.actor.property.color = (
                            colorToAssign[0], colorToAssign[1], colorToAssign[2])

                    volume.actor.property.edge_visibility = scenesProperties[currentScene].edgeVisibility
                    volume.actor.mapper.scalar_visibility = False
                    # Create the object
                    currentObject = EnvironmentObject(xmlObjectID, xmlObjectName, volume, materialId, False, False,False, 1.0,
                                                      'plane')
                    environmentObjects[currentScene].append(currentObject)
    materialProperties = MaterialProperties(materialNameDic, materialPathDic)
    return materialProperties, environmentObjects


def parseObjEnvironment(environmentFile, engine, scenesProperties,textureFolder):
    """
    Parse the 3D environment when the format used is OBJ and construct the visualization objects

    Parameters
    ----------
     environmentFile : String
        File containing the environment
     scenesProperties: Dictionary
        Dictionary storing the scenes properties
     textureFolder: String
        The Path to the texture folder

    Returns
    -------
    materialProperties: MaterialProperties Class
        Material properties (material names and textures paths)
    environmentObjects: Dictionary
        Dictionary storing the objects that make the environment
    """
    materialNameDic = {}  # Dictionary with the Material library names (Material ID is the key and value is the material Name)
    materialPathDic = {}  # Dictionary with the Material texture paths (Material ID is the key and value is the texture path)
    environmentObjects = {}  # Dictionary with the objects constructed
    mltMaterialIdDic = {}  # Dictionary storing the material ID
    materialID = 0
    newObjectParsed = False
    objFileToWrite = 0

    for currentScene in scenesProperties.keys():
        environmentObjects[currentScene] = []

    objFileToParse = environmentFile
    fileName, file_extension = os.path.splitext(objFileToParse)
    scenarioCachedFolder = os.path.join(fileName + cachedSuffix)
    lastLineRead = 0
    # Handle OBJ file parsing
    if not os.path.exists(scenarioCachedFolder):  # Check if the scenario has already been cached
        # The scenario has not been cached already
        os.makedirs(scenarioCachedFolder)
        # We want to split the entire OBJ file into N OBJ files
        # N being the number of objects that made the original OBJ file
        # This is done mainly to construct N different objects in the fastest possible ways in the visualizer
        with open(objFileToParse) as fp:
            line = fp.readline()  # Read the first line
            while line:
                # Look for the objects that make the OBJ (The line will start with 'o')
                if re.match("^o ", line):
                    # An Object has been found - Get its name first
                    objectName = re.split('\s+', line)  # Split space and get the object name
                    objectName = objectName[1]
                    # Create the file what will store this object
                    objFileToWrite = open(os.path.join(scenarioCachedFolder, objectName + '.obj'), 'w')
                    newObjectParsed = True  # Indicate that we've just parsed a new object
                # Check for the vertices data (start with 'f')
                if re.match("^f ", line):
                    # Vertices data information found
                    # Vertices data can be made of 2 or 3 values:
                    # 3 Values: Geometric vertices, texture vertices, and vertex normals - In this case, the vertices data are separated with '/'
                    # 2 Values: Geometric and vertex normals

                    # Each of these types of vertices is numbered separately, starting with 1 (http://paulbourke.net/dataformats/obj/)
                    # As the vertices datas are indexed based on the total number of each vertices data in the OBJ file
                    # This information needs to be rewritten as we are going to split the OBJ file is several OBJ files
                    # We need to rewrite the vertices data to always start with 1 in every newly generated OBJ file
                    verticeData = re.split('\s+', line)
                    if len(verticeData[1].split('//')) == 2:
                        # No texture vertices
                        noTextureVertice = True
                        delimiter = "//"
                    else:
                        noTextureVertice = False
                        delimiter = "/"

                    # Get the Triplets that make the vertices Data
                    # In our case, we manage only 3 triplets as we want to handle geometry just made of triangles
                    # TODO: Add a check on verticeData length to quit if the line is not made of 3 triplets
                    if newObjectParsed:
                        # Beginning of the new object
                        positionObject = lastLineRead  # We keep the position just before we read the first 'f' parameter
                        newObjectParsed = False
                        absolutetoRemoveGeometrixVertex = math.inf
                        absolutetoRemoveNormVertex = math.inf
                        absolutetoRemoveTextureVertex = math.inf
                        # Here, we need to identify the minimal index for Geometric vertices, texture vertices, and vertex normals
                        # The only way to do that is to read all the 'f' properties and to get each minimal values
                        while re.match("^f ", line):
                            # Read all the object f properties
                            verticeData = re.split('\s+', line)
                            firstTriplet = re.split(delimiter, verticeData[1])
                            secondTriplet = re.split(delimiter, verticeData[2])
                            thirdTriplet = re.split(delimiter, verticeData[3])
                            if noTextureVertice:
                                # Get the minimum for the geometric vertex value
                                absolutetoRemoveGeometrixVertex = min(absolutetoRemoveGeometrixVertex,
                                                                      int(firstTriplet[0]) - 1,
                                                                      int(secondTriplet[0]) - 1, int(
                                        thirdTriplet[0]) - 1)
                                # Get the minimum for the normal vertex value
                                absolutetoRemoveNormVertex = min(absolutetoRemoveNormVertex,
                                                                 int(firstTriplet[1]) - 1,
                                                                 int(secondTriplet[1]) - 1, int(
                                        thirdTriplet[1]) - 1)
                            else:
                                # Get the minimum for the geometrix vertex value
                                absolutetoRemoveGeometrixVertex = min(absolutetoRemoveGeometrixVertex,
                                                                      int(firstTriplet[0]) - 1,
                                                                      int(secondTriplet[0]) - 1, int(
                                        thirdTriplet[0]) - 1)
                                # Get the minimum for the texture vertex value
                                absolutetoRemoveTextureVertex = min(absolutetoRemoveTextureVertex,
                                                                    int(firstTriplet[1]) - 1,
                                                                    int(secondTriplet[1]) - 1, int(
                                        thirdTriplet[1]) - 1)
                                # Get the minimum for the texture vertex value
                                absolutetoRemoveNormVertex = min(absolutetoRemoveNormVertex,
                                                                 int(firstTriplet[2]) - 1,
                                                                 int(secondTriplet[2]) - 1, int(
                                        thirdTriplet[2]) - 1)
                            line = fp.readline()  # Read another line

                        # We handle all the vertices data information and get the minimums
                        fp.seek(positionObject)  # Come back in the file to proceed to the writing on the new OBJ file
                        line = fp.readline()

                    # Handle the creation of the obj file corresponding to the object
                    # Get the vertices properties for the current line
                    verticeData = re.split('\s+', line)
                    firstTriplet = re.split(delimiter, verticeData[1])
                    secondTriplet = re.split(delimiter, verticeData[2])
                    thirdTriplet = re.split(delimiter, verticeData[3])

                    # Rewrite the vertices data to have them starting at 1
                    if noTextureVertice:
                        firstTripletToWrite = str(
                            int(firstTriplet[0]) - absolutetoRemoveGeometrixVertex) + "//" + str(
                            int(firstTriplet[1]) - absolutetoRemoveNormVertex) + " "
                        secondTripletToWrite = str(
                            int(secondTriplet[0]) - absolutetoRemoveGeometrixVertex) + "//" + str(
                            int(secondTriplet[1]) - absolutetoRemoveNormVertex) + " "
                        thirdTripletToWrite = str(
                            int(thirdTriplet[0]) - absolutetoRemoveGeometrixVertex) + "//" + str(
                            int(thirdTriplet[1]) - absolutetoRemoveNormVertex) + "\n"
                    else:
                        firstTripletToWrite = str(
                            int(firstTriplet[0]) - absolutetoRemoveGeometrixVertex) + "/" + str(
                            int(firstTriplet[1]) - absolutetoRemoveTextureVertex) + "/" + str(
                            int(firstTriplet[2]) - absolutetoRemoveNormVertex) + " "
                        secondTripletToWrite = str(
                            int(secondTriplet[0]) - absolutetoRemoveGeometrixVertex) + "/" + str(
                            int(secondTriplet[1]) - absolutetoRemoveTextureVertex) + "/" + str(
                            int(secondTriplet[2]) - absolutetoRemoveNormVertex) + " "
                        thirdTripletToWrite = str(
                            int(thirdTriplet[0]) - absolutetoRemoveGeometrixVertex) + "/" + str(
                            int(thirdTriplet[1]) - absolutetoRemoveTextureVertex) + "/" + str(
                            int(thirdTriplet[2]) - absolutetoRemoveNormVertex) + "\n"

                    # Write the new triplet with index starting at 1
                    objFileToWrite.write("f " + firstTripletToWrite + secondTripletToWrite + thirdTripletToWrite)
                else:
                    if objFileToWrite != 0:
                        # Just write the line as is
                        objFileToWrite.write(line)
                lastLineRead = fp.tell()  # Keep the position before to read the new line
                line = fp.readline()  # Read another line

        # In the previous step, when we parsed the entire obj file, we created N new OBJ object files
        # Now, we want to split every individual object into M OBJ objects where M is the number of different materials
        # that made an individual object. It must be done to allow to visualize the multiple materials of a given individual object in the visualizer
        # TODO: This could be probably be done in a one-step process and optimized as right now, we have duplicated vertices
        for objFileToWrite in os.listdir(scenarioCachedFolder):
            # Read all the obj files that are available in the cached folder
            with open(os.path.join(scenarioCachedFolder, objFileToWrite)) as fp:
                line = fp.readline()  # Read the first line
                objectName = ""
                nbMaterialObject = 0
                commonLineToWrite = ""
                materialLineToWrite = []
                materialExtension = []
                while line:
                    if re.match("^o ", line):
                        # The object line has been found
                        objectName = re.split('\s+', line)  # Split space and get the object name
                        objectName = objectName[1]
                        commonLineToWrite = commonLineToWrite + (line)
                    elif re.match("^usemtl ", line):  # Vertices coordinates (start with a 'v')
                        materialLineToWrite.append(line)
                        # We are going to add as a suffix of the newly OBJ file the name of the material
                        materialExtension.append(re.split('\s+', line)[1])
                        nbMaterialObject += 1
                    elif re.match("^f ", line):
                        materialLineToWrite[nbMaterialObject - 1] = materialLineToWrite[
                                                                        nbMaterialObject - 1] + line
                    else:
                        commonLineToWrite = commonLineToWrite + (line)
                    line = fp.readline()  # Read the first line

                for i in range(len(materialExtension)):
                    # Iterate over all the different materials of the individual OBJ object and create one new OBJ file per material
                    objFileToWrite = open(
                        os.path.join(scenarioCachedFolder, objectName + materialExtension[i] + '.obj'), 'w')
                    objFileToWrite.write(commonLineToWrite + materialLineToWrite[i])
                fp.close()
                if (path.exists(os.path.join(scenarioCachedFolder, objectName + '.obj'))):
                    # Remove the obj files not needed anymore
                    os.remove(os.path.join(scenarioCachedFolder, objectName + '.obj'))

    # MT file parsing
    nbElementRead = 0
    mtlFilePresent = False
    mtlFileToParse = fileName + ".mtl"
    nbMaterialMtl = 0
    try:
        with open(mtlFileToParse) as fp:
            mtlFilePresent = True
            line = fp.readline()
            currentMaterialName = ""
            # nbMaterialMtl = 0
            while line:
                if re.match("^newmtl ", line):
                    currentMaterialName = re.split('\s+', line)[1]
                    mltMaterialIdDic[currentMaterialName] = nbMaterialMtl
                    nbMaterialMtl += 1
                if re.match("^map_Kd ", line):
                    # Add the path of the texture and the material ID
                    materialPathDic[currentMaterialName] = line.split()[1].replace('\\\\', '\\')
                line = fp.readline()  # Read the first line
    except FileNotFoundError:
        print("Warning: Scenario config file: " + fileName + ".mtl does not exist")
        print("The material library will be auto-created")
        # As we don't have any mtl file, we must create the library
        # The number of material will be set to the number of different obj objects
        for i in os.listdir(scenarioCachedFolder):
            nbMaterialMtl += 1

    # Create the objects for the visualizer
    for objFileToWrite in os.listdir(scenarioCachedFolder):
        # Read all the obj files that are available in the cached folder
        materialFound = False
        objectNameFound = False
        with open(os.path.join(scenarioCachedFolder, objFileToWrite)) as fp:
            line = fp.readline()
            objectName = ""
            while line:
                if re.match("^o ", line):
                    # The object line has been found
                    objectName = re.split('\s+', line)  # Split space and get the object name
                    objectName = objectName[1]
                    objectNameFound = True
                if re.match("^usemtl ", line):  # Check for the material of the object
                    if not mtlFilePresent:
                        # If no MTL file is not present, we must manage the material ID on our own
                        # By default, for every material, we create a new material ID
                        materialID = nbElementRead
                        materialName = re.split('\s+', line)[1]
                        materialNameDic[str(materialID)] = materialName  # Add the material to the material dictionary
                        nbElementRead = nbElementRead + 1
                        materialFound = True
                    else:
                        # The mtl file was present, use the material information
                        materialName = re.split('\s+', line)[1]
                        materialID = mltMaterialIdDic[materialName]
                        materialNameDic[str(materialID)] = materialName
                        materialFound = True

                if objectNameFound == True and materialFound == True:
                    for currentScene in scenesProperties.keys():
                        # Add the object to every scene
                        poly_data_reader = engine.open(os.path.join(scenarioCachedFolder, objFileToWrite),
                                                       currentScene)

                        volume = Surface()
                        if mtlFilePresent:
                            img = tvtk.JPEGReader()
                            if materialNameDic[str(materialID)] in materialPathDic and scenesProperties[
                                currentScene].representation == "Texture":
                                # We add texture only if a texture exists for the material and the scene was configured to be textured
                                # Texture path is managed by OBJ and mtl file so we just have to open the texture files
                                img.file_name = str(materialPathDic[materialNameDic[str(materialID)]])
                                texture = tvtk.Texture(input_connection=img.output_port, interpolate=0)
                                volume.actor.enable_texture = True
                                volume.actor.property.edge_visibility = False
                                volume.actor.tcoord_generator_mode = 'none'
                                volume.actor.actor.texture = texture
                        engine.add_module(volume, poly_data_reader)
                        if scenesProperties[currentScene].representation == "Material":
                            # If the Scene is configured to display material, handle it
                            # We associate one different color per material
                            viridis = cm.get_cmap('viridis', nbMaterialMtl)
                            volume.actor.mapper.scalar_visibility = False
                            colorToAssign = viridis(materialID / nbMaterialMtl)

                            volume.actor.property.color = (
                                colorToAssign[0], colorToAssign[1], colorToAssign[2])

                        volume.actor.property.edge_visibility = scenesProperties[currentScene].edgeVisibility
                        currentObject = EnvironmentObject("1", objectName, volume, str(materialID), False, False,False, 1.0,
                                                          'none')
                        environmentObjects[currentScene].append(currentObject)
                    break

                line = fp.readline()
    materialProperties = MaterialProperties(materialNameDic, materialPathDic)
    return materialProperties, environmentObjects


def constructEnvironment(environmentFile, engine, scenesProperties, textureFolder):
    """Construct the 3D environment for the scenario

    Parameters
    ----------
     environmentFile: String
        File containing the environment
    engine: Mayavi Engine
        The engine storing the scenes
    scenesProperties: Dictionary
        Dictionary storing the scenes properties
    textureFolder: String
        The Path to the texture folder

    Returns
    -------
    objFile: Bool
        Stating if the environment is represented by an OBJ file or AMF/XML
    materialProperties: MaterialProperties Class
        Material properties (material names and textures paths)
    environmentObjects: Dictionary
        Dictionary storing the objects that make the environment
    """
    fileExtension = os.path.splitext(environmentFile)[1]
    if fileExtension == ".obj":
        # The environment is represented with an .obj file
        objFile = True
        materialProperties, environmentObjects = parseObjEnvironment(environmentFile, engine, scenesProperties,textureFolder)
    else:
        # The environment is represented with an .amf or .xml file
        objFile = False
        materialProperties, environmentObjects = parseAmfEnvironment(environmentFile, scenesProperties,textureFolder)
    return objFile, materialProperties, environmentObjects



