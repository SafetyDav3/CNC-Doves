#!/usr/bin/env python3
# Fusion 360 add-in to create a dovetailed drawer box
# Author: Codex

import adsk.core
import adsk.fusion
import traceback

# Global set of event handlers kept referenced during the command
import math

# Global set of event handlers to keep them referenced for the duration of the command
handlers = []


class DrawerCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            values = {}
            for i in range(inputs.count):
                inp = inputs.item(i)
                values[inp.id] = (
                    inp.value if hasattr(inp, 'value') else inp.isChecked
                )


            design = adsk.fusion.Design.cast(self.app.activeProduct)
            root = design.rootComponent

            drawer_comp = root.occurrences.addNewComponent(
                adsk.core.Matrix3D.create()
            ).component
            drawer_comp.name = 'Drawer'

            width = values['width']
            depth = values['depth']
            height = values['height']
            side_thickness = values['sideThickness']
            bottom_thickness = values['bottomThickness']
            bottom_offset = values['bottomOffset']
            convert_to_components = values['convertComponents']

            # Create bottom sketch
            sketches = drawer_comp.sketches
            xy_plane = drawer_comp.xYConstructionPlane
            bottom_sketch = sketches.add(xy_plane)

            bottom_rect = bottom_sketch.sketchCurves.sketchLines
            p2 = adsk.core.Point3D.create(width / 2, depth / 2, 0)
            bottom_rect.addCenterPointRectangle(
                adsk.core.Point3D.create(0, 0, 0), p2
            )

            prof = bottom_sketch.profiles.item(0)
            extrudes = drawer_comp.features.extrudeFeatures
            ext_input = extrudes.createInput(
                prof,
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            )

            distance = adsk.core.ValueInput.createByReal(bottom_thickness)
            ext_input.setDistanceExtent(False, distance)
            bottom_body = extrudes.add(ext_input).bodies.item(0)
            bottom_body.name = 'Bottom'

            # Create side panels
            def create_side(width, height, thickness, name):
                sketch = sketches.add(xy_plane)
                lines = sketch.sketchCurves.sketchLines
                p2 = adsk.core.Point3D.create(width / 2, bottom_offset, 0)
                lines.addCenterPointRectangle(
                    adsk.core.Point3D.create(0, bottom_offset - height / 2, 0),
                    p2,
                )

                prof = sketch.profiles.item(0)
                ext_in = extrudes.createInput(
                    prof,
                    adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                )

                distance = adsk.core.ValueInput.createByReal(thickness)
                ext_in.setDistanceExtent(False, distance)
                body = extrudes.add(ext_in).bodies.item(0)
                body.name = name
                return body

            left = create_side(depth, height, side_thickness, 'Left')
            right = create_side(depth, height, side_thickness, 'Right')
            front = create_side(width, height, side_thickness, 'Front')
            back = create_side(width, height, side_thickness, 'Back')

            # Very basic positioning of sides around the bottom
            def move_body(body, vector):
                coll = adsk.core.ObjectCollection.create()
                coll.add(body)
                transform = adsk.core.Matrix3D.create()
                transform.translation = vector
                move_feats = drawer_comp.features.moveFeatures
                move_feats.add(coll, transform)

            move_body(
                left,
                adsk.core.Vector3D.create(
                    -width / 2 + side_thickness / 2,
                    0,
                    bottom_thickness,
                ),
            )
            move_body(
                right,
                adsk.core.Vector3D.create(
                    width / 2 - side_thickness / 2,
                    0,
                    bottom_thickness,
                ),
            )
            move_body(
                front,
                adsk.core.Vector3D.create(
                    0,
                    -depth / 2 + side_thickness / 2,
                    bottom_thickness,
                ),
            )
            move_body(
                back,
                adsk.core.Vector3D.create(
                    0,
                    depth / 2 - side_thickness / 2,
                    bottom_thickness,
                ),
            )

            # Convert bodies to components if requested
            if convert_to_components:
                bodies = adsk.core.ObjectCollection.create()
                for b in drawer_comp.bRepBodies:
                    bodies.add(b)
                drawer_comp.convertToComponents(bodies)

        except Exception:

            self.app.log('Failed:\n{}'.format(traceback.format_exc()))


class DrawerCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self, handlers):
        super().__init__()
        self.handlers = handlers

    def notify(self, args):
        while self.handlers:
            self.handlers.pop()


def create_command_inputs(cmd):
    inputs = cmd.commandInputs

    inputs.addValueInput(
        'width',
        'Width',
        'cm',
        adsk.core.ValueInput.createByReal(30),
    )
    inputs.addValueInput(
        'height',
        'Height',
        'cm',
        adsk.core.ValueInput.createByReal(10),
    )
    inputs.addValueInput(
        'depth',
        'Depth',
        'cm',
        adsk.core.ValueInput.createByReal(20),
    )
    inputs.addValueInput(
        'sideThickness',
        'Side Thickness',
        'cm',
        adsk.core.ValueInput.createByReal(1),
    )
    inputs.addValueInput(
        'bottomThickness',
        'Bottom Thickness',
        'cm',
        adsk.core.ValueInput.createByReal(0.5),
    )
    inputs.addValueInput(
        'tolerance',
        'Tolerance',
        'cm',
        adsk.core.ValueInput.createByReal(0.05),
    )
    inputs.addIntegerSpinnerCommandInput(
        'dovetailCount',
        'Dovetail Count',
        1,
        20,
        1,
        3,
    )
    inputs.addValueInput(
        'dovetailAngle',
        'Dovetail Angle',
        'deg',
        adsk.core.ValueInput.createByReal(7),
    )
    inputs.addValueInput(
        'bottomOffset',
        'Bottom Offset',
        'cm',
        adsk.core.ValueInput.createByReal(0.5),
    )
    inputs.addStringValueInput('material', 'Material', 'Plywood')
    inputs.addValueInput(
        'toolDiameter',
        'Tool Diameter',
        'cm',
        adsk.core.ValueInput.createByReal(0.3),
    )

    inputs.addIntegerSpinnerCommandInput(
        'holeCount',
        'Handle Holes',
        0,
        2,
        1,
        0,
    )
    inputs.addValueInput(
        'holeSpacing',
        'Hole Spacing',
        'cm',
        adsk.core.ValueInput.createByReal(4),
    )
    inputs.addValueInput(
        'holeDiameter',
        'Hole Diameter',
        'cm',
        adsk.core.ValueInput.createByReal(0.6),
    )

    inputs.addBoolValueInput(
        'convertComponents',
        'Convert to Components',
        True,
        '',
        False,
    )


class DrawerPaletteCommandCreatedEventHandler(
    adsk.core.CommandCreatedEventHandler,
):

    def __init__(self, app):
        super().__init__()
        self.app = app

    def notify(self, args):
        try:
            cmd = args.command
            cmd.isRepeatable = False

            on_execute = DrawerCommandExecuteHandler(self.app)
            cmd.execute.add(on_execute)
            handlers.append(on_execute)

            on_destroy = DrawerCommandDestroyHandler(handlers)
            cmd.destroy.add(on_destroy)
            handlers.append(on_destroy)

            create_command_inputs(cmd)
        except Exception:
            self.app.log(
                'Failed to create command inputs:\n{}'.format(
                    traceback.format_exc()
                )
            )



class DrawerAddin:
    def __init__(self, app):
        self.app = app
        self.ui = app.userInterface
        self.command_def = None

    def start(self):
        try:
            cmd_definitions = self.ui.commandDefinitions
            self.command_def = cmd_definitions.itemById('drawerAddin')
            if not self.command_def:
                self.command_def = cmd_definitions.addButtonDefinition(
                    'drawerAddin',
                    'Dovetail Drawer',
                    'Create a dovetail drawer box',
                )

            on_command_created = (
                DrawerPaletteCommandCreatedEventHandler(self.app)
            )
            self.command_def.commandCreated.add(on_command_created)
            handlers.append(on_command_created)

            create_panel = self.ui.allToolbarPanels.itemById(
                'SolidCreatePanel'
            )
            create_panel.controls.addCommand(self.command_def)
        except Exception:
            self.app.log(
                'Failed to start addin:\n{}'.format(
                    traceback.format_exc()
                )
            )

    def stop(self):
        try:
            create_panel = self.ui.allToolbarPanels.itemById(
                'SolidCreatePanel'
            )

            ctrl = create_panel.controls.itemById('drawerAddin')
            if ctrl:
                ctrl.deleteMe()

            if self.command_def:
                self.command_def.deleteMe()
        except Exception:
            self.app.log(
                'Failed to stop addin:\n{}'.format(
                    traceback.format_exc()
                )
            )



def run(context):
    app = adsk.core.Application.get()
    addin = DrawerAddin(app)
    addin.start()


def stop(context):
    app = adsk.core.Application.get()
    addin = DrawerAddin(app)
    addin.stop()

