import bpy
import os.path
import mathutils
bl_info = {
    "name": "Portal Multi-Pass/Texture",
    "author": "dklug",
    "version": (0, 0, 1),
    "blender": (2, 90, 0),
    "location": "Ctrl Shift P",
    "description": "Portal Hotkey: Ctrl Shift P",
    "doc_url": "github.com/dklug",
    "category": "Object",
}


def apply_portal_materials(scn):
    if (scn.objects.get('BluePortal') and scn.objects.get('OrangePortal')):
        print('Applying portal image texture for frame', scn.frame_current)
        # Get needed variables
        portalBlue = scn.objects['BluePortal']
        portalBlue_material = portalBlue.active_material
        portalBlue_texImage = portalBlue_material.node_tree.nodes['Image Texture']
        portalOrange = scn.objects['OrangePortal']
        portalOrange_material = portalOrange.active_material
        portalOrange_texImage = portalOrange_material.node_tree.nodes['Image Texture']

        # check the current frame and a few frames back to get a recent image for the portal
        frameToCheck = scn.frame_current
        frameMinimum = scn.frame_current - scn.frame_step - 1
        while frameToCheck > frameMinimum:
            orangePath = str(scn.render.filepath) + \
                str.zfill(str(frameToCheck), 4)+'_Blue.png'
            bluePath = str(scn.render.filepath) + \
                str.zfill(str(frameToCheck), 4)+'_Orange.png'
            if os.path.isfile(orangePath):
                portalOrange_texImage.image = bpy.data.images.load(orangePath)
                print('orange image found for frame', frameToCheck)
                break
            if os.path.isfile(bluePath):
                portalBlue_texImage.image = bpy.data.images.load(bluePath)
                print('blue image found for frame', frameToCheck)
                break
            frameToCheck -= 1


def apply_camera_transformations(scn):
    if (scn.objects.get('BluePortal') and scn.objects.get('OrangePortal')):
        # print('---------apply camera transformations--------')
        # The angle from the A to the portal should be the same angle from the camera to B
        # We should use the 'mirrored' location of the main camera to find where the opposite camera should face
        # Variables
        # Portals
        portalBlue = bpy.data.objects['BluePortal']
        portalBlue_normal = portalBlue.data.polygons[0].normal
        portalBlue_normalEuler = portalBlue_normal.to_track_quat(
            '-Z', 'Y').to_euler()
        portalOrange = bpy.data.objects['OrangePortal']
        # make a new copy of the data by using normalized()
        portalOrange_normal = portalOrange.data.polygons[0].normal.normalized()
        # print('portalBlue_normal: ', portalBlue_normal)
        # print('portalBlue_normalEuler: ', portalBlue_normalEuler)

        targetBlue = bpy.data.objects['targetBlue']
        targetOrange = bpy.data.objects['targetOrange']

        # Cameras
        camBlue_ob = bpy.data.objects["Camera_Blue"]
        camOrange_ob = bpy.data.objects["Camera_Orange"]
        camMain_ob = bpy.data.objects["Camera_Main"]

        ####################################################################################

        # Assuming the blue and orange portal are front to back,
        mainToBlueRotation = (
            portalBlue.location-camMain_ob.location).to_track_quat('-Z', 'Y').to_euler()
        mainToOrangeRotation = (
            portalOrange.location-camMain_ob.location).to_track_quat('-Z', 'Y').to_euler()

        camOrange_ob.rotation_euler = mainToBlueRotation
        camBlue_ob.rotation_euler = mainToOrangeRotation
        # Rotate by the rotation difference between portal normals
        # Bodge for weird issue that only happens when both normals are the same
        if portalOrange_normal == portalBlue_normal:
            portalOrange_normal.z += .01
        # In all cases we want to flip this rotation, so use the opposite of one of the normals
        portalOrange_normal *= -1

        blueRotation = portalOrange_normal.rotation_difference(portalBlue_normal)
        orangeRotation = portalBlue_normal.rotation_difference(portalOrange_normal)

        camBlue_ob.rotation_euler.rotate(blueRotation)
        camOrange_ob.rotation_euler.rotate(orangeRotation)

        # cameras may be upside down, but facing the correct direction
        # We can make a point in the correct direction and then use to_track_quat again to make them not upside down
        blueDistance = (camMain_ob.location - portalBlue.location).length
        orangeDistance = (camMain_ob.location - portalOrange.location).length

        # Use the empties for the camera to face at rotate and then translate on local axes
        targetOrange.rotation_euler = camOrange_ob.rotation_euler
        orangeTargetTranslation = mathutils.Vector((.0, .0, orangeDistance))
        invertedOrangeRotation = targetOrange.rotation_euler.to_matrix()
        invertedOrangeRotation.invert()
        # project vector to world using rotation matrix
        orangeTargetTranslationRotated = orangeTargetTranslation @ invertedOrangeRotation
        targetOrange.location = portalOrange.location - orangeTargetTranslationRotated

        targetBlue.rotation_euler = camBlue_ob.rotation_euler
        blueTargetTranslation = mathutils.Vector((.0, .0, blueDistance))
        invertedBlueRotation = targetBlue.rotation_euler.to_matrix()
        invertedBlueRotation.invert()
        blueTargetTranslationRotated = blueTargetTranslation @ invertedBlueRotation
        targetBlue.location = portalBlue.location - blueTargetTranslationRotated

        camOrange_ob.rotation_euler = (portalOrange.location - targetOrange.location).to_track_quat(
            'Z', 'Y').to_euler()
        camBlue_ob.rotation_euler = (portalBlue.location - targetBlue.location).to_track_quat(
            'Z', 'Y').to_euler()

        # Now the cameras are not upside down, and they are pointing in the correct direction
        # Next it's time to move the cameras backwards similar to the way we moved the empties forwards

        camBlue_ob.location = blueTargetTranslationRotated
        camOrange_ob.location = orangeTargetTranslationRotated


def newNodeLoc(loc, xtra=0):
    return loc + 200 + xtra


def initialize_portal_material(portal, portalOpposite, name):
    # initialize material for  portal
    portal_material = bpy.data.materials.new(name=name)
    portal_material.use_nodes = True

    # Nodes from left to right
    portal_texCoord = portal_material.node_tree.nodes.new(
        'ShaderNodeTexCoord')
    portal_texCoord.object = portalOpposite
    portal_texImage = portal_material.node_tree.nodes.new(
        'ShaderNodeTexImage')
    portal_bsdf = portal_material.node_tree.nodes["Principled BSDF"]
    portal_bsdfTransparent = portal_material.node_tree.nodes.new(
        'ShaderNodeBsdfTransparent')
    portal_newGeometry = portal_material.node_tree.nodes.new(
        'ShaderNodeNewGeometry')
    portal_mixShader = portal_material.node_tree.nodes.new(
        'ShaderNodeMixShader')
    portal_matOutput = portal_material.node_tree.nodes["Material Output"]

    # Make the node locations readable for users
    loc = -600
    portal_texCoord.location = (loc, 0)
    loc = newNodeLoc(loc)
    portal_texImage.location = (loc, 0)
    loc = newNodeLoc(loc, 100)
    portal_bsdf.location = (loc, 0)
    loc = newNodeLoc(loc, 100)
    portal_bsdfTransparent.location = (loc, -200)
    portal_newGeometry.location = (loc, 200)
    loc = newNodeLoc(loc)
    portal_mixShader.location = (loc, 0)
    loc = newNodeLoc(loc)
    portal_matOutput.location = (loc, 0)

    # Links from left to right
    # Link Window texture coordinates to the vector of the image texture
    portal_material.node_tree.links.new(
        portal_texImage.inputs['Vector'], portal_texCoord.outputs['Window'])
    # Link image texture to base color and emission of the Principled BSDF
    portal_material.node_tree.links.new(
        portal_bsdf.inputs['Base Color'], portal_texImage.outputs['Color'])
    portal_material.node_tree.links.new(
        portal_bsdf.inputs['Emission'], portal_texImage.outputs['Color'])
    # Connect geometry backfacing to fac of mix shader (the back face of the portal should be transparent)
    portal_material.node_tree.links.new(
        portal_mixShader.inputs['Fac'], portal_newGeometry.outputs['Backfacing'])
    # Connect the bsdf and the transparent shader to the mixer
    portal_material.node_tree.links.new(
        portal_mixShader.inputs[1], portal_bsdf.outputs['BSDF'])
    portal_material.node_tree.links.new(
        portal_mixShader.inputs[2], portal_bsdfTransparent.outputs['BSDF'])
    # Connect mix to output
    portal_material.node_tree.links.new(
        portal_matOutput.inputs['Surface'], portal_mixShader.outputs['Shader'])
    # Use a texture coordinates node to display only the part of the render that should

    # Assign it to object
    if portal.data.materials:
        portal.data.materials[0] = portal_material
    else:
        portal.data.materials.append(portal_material)


class CreatePortal(bpy.types.Operator):
    """Portal Script"""      # Use this as a tooltip for menu items and buttons.
    bl_idname = "portal.create_portal"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Create Portal"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    # execute() is called when running the operator.
    def execute(self, context):

        scn = bpy.context.scene
        obj_array = []
        selected_obj = bpy.context.selected_objects
        # null check selected objects
        if (len(selected_obj) != 2):
            self.report({'INFO'}, 'Select two objects and try again')
            return {'FINISHED'}
        # get names of selected objects
        for obj in selected_obj:
            obj_array.append(obj.name)

        # initialize blue and orange portal
        portalBlue = bpy.data.objects[obj_array[0]]
        portalBlue.name = 'BluePortal'
        portalBlue_Normal = portalBlue.data.polygons[0].normal
        portalOrange = bpy.data.objects[obj_array[1]]
        portalOrange.name = 'OrangePortal'
        portalOrange_Normal = portalOrange.data.polygons[0].normal

        initialize_portal_material(
            portalBlue, portalOrange, 'BluePortalMaterial')
        initialize_portal_material(
            portalOrange, portalBlue, 'OrangePortalMaterial')

        apply_portal_materials(scn)

        # set up cameras
        camBlue = bpy.data.cameras.new("Camera_Blue")  # camera data
        camBlue_ob = bpy.data.objects.new(
            "Camera_Blue", camBlue)  # camera object
        camBlue_ob.parent = portalBlue
        camBlue_ob.rotation_euler = portalBlue_Normal.to_track_quat(
            '-Z', 'Y').to_euler()
        scn.collection.objects.link(camBlue_ob)

        camOrange = bpy.data.cameras.new("Camera_Orange")  # camera data
        camOrange_ob = bpy.data.objects.new(
            "Camera_Orange", camOrange)  # camera object
        camOrange_ob.parent = portalOrange
        camOrange_ob.rotation_euler = portalOrange_Normal.to_track_quat(
            '-Z', 'Y').to_euler()
        scn.collection.objects.link(camOrange_ob)

        camMain = bpy.data.cameras.new("Camera_Main")  # camera data
        camMain_ob = bpy.data.objects.new(
            "Camera_Main", camMain)  # camera object
        camMain_ob.location = (-8, 4, 1)
        camMain_ob.location += portalBlue.location
        # distance the main camera and make sure it has a view of the portals
        camMain_direction = portalBlue.location-camMain_ob.location
        camMain_ob.rotation_euler = camMain_direction.to_track_quat(
            '-Z', 'Y').to_euler()
        scn.collection.objects.link(camMain_ob)
        scn.camera = camMain_ob

        targetOrange = bpy.data.objects.new('empty', None)
        scn.collection.objects.link(targetOrange)
        # targetOrange.empty_display_type = 'CIRCLE'
        targetOrange.empty_display_size = .25
        targetOrange.name = 'targetOrange'
        targetOrange.location = portalOrange.location
        targetBlue = bpy.data.objects.new('empty', None)
        scn.collection.objects.link(targetBlue)
        # targetBlue.empty_display_type = 'CIRCLE'
        targetBlue.empty_display_size = .25
        targetBlue.name = 'targetBlue'
        targetBlue.location = portalBlue.location

        apply_camera_transformations(scn)

        # Set the render options to multiview
        scn.render.use_multiview = True
        scn.render.views_format = 'MULTIVIEW'
        for renderView in scn.render.views:
            renderView.use = False

        # bpy.ops.scene.render_view_add(name='Blue', suffix='_Blue')
        # bpy.ops.scene.render_view_add(name='Orange', suffix='_Orange')
        # bpy.ops.scene.render_view_add(name='Main', suffix='_Main')

        bpy.ops.scene.render_view_add()
        scn.render.views['RenderView'].name = 'Blue'
        bpy.ops.scene.render_view_add()
        scn.render.views['RenderView'].name = 'Orange'
        bpy.ops.scene.render_view_add()
        scn.render.views['RenderView'].name = 'Main'

        scn.render.views['Blue'].camera_suffix = '_Blue'
        scn.render.views['Orange'].camera_suffix = '_Orange'
        scn.render.views['Main'].camera_suffix = '_Main'

        # Add the portal material handler before each frame change
        bpy.app.handlers.frame_change_pre.append(apply_camera_transformations)
        bpy.app.handlers.frame_change_pre.append(apply_portal_materials)

        # Lets Blender know the operator finished successfully.
        return {'FINISHED'}


# store keymaps here to access after registration
addon_keymaps = []


def register():
    bpy.utils.register_class(CreatePortal)
    # keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(
            name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new(
            CreatePortal.bl_idname, 'P', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    # Clean up any leftover handlers
    portalHandlers = [handler for handler in bpy.app.handlers.frame_change_pre if handler.__name__ ==
                      'apply_camera_transformations' or handler.__name__ == 'apply_portal_materials']
    for handler in portalHandlers:
        bpy.app.handlers.frame_change_pre.remove(handler)

    bpy.utils.unregister_class(CreatePortal)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
if __name__ == "__main__":
    register()
