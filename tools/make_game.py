"""Writes game.json — a simple Tetris for GDevelop 5.6.

Everything the game does lives in the event sheet of the scene "Game", so it can
be read and changed inside GDevelop. This script is only how the first version
was written; once the project is edited in GDevelop, edit it there instead.

Run:  python3 tools/make_game.py   (writes game.raw.json; it was then loaded with the
libGD.js inside the GDevelop app, validated, and saved out as game.json)
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CELL = 32
BOARD_X, BOARD_Y = 64, 48          # top-left of the 10 x 20 playfield
WIN_W, WIN_H = 720, 784   # extra room at the bottom for the "Made with GDevelop" badge


# ---------------------------------------------------------------- event helpers
def C(kind, *params, inv=False):
    t = {"value": kind}
    if inv:
        t["inverted"] = True
    return {"type": t, "parameters": list(params)}


def A(kind, *params):
    return {"type": {"value": kind}, "parameters": list(params)}


def ev(conds=(), acts=(), subs=()):
    e = {"type": "BuiltinCommonInstructions::Standard",
         "conditions": list(conds), "actions": list(acts)}
    if subs:
        e["events"] = list(subs)
    return e


def repeat(times, conds=(), acts=(), subs=()):
    e = {"type": "BuiltinCommonInstructions::Repeat", "repeatExpression": str(times),
         "conditions": list(conds), "actions": list(acts)}
    if subs:
        e["events"] = list(subs)
    return e


def for_each(obj, conds=(), acts=(), subs=()):
    e = {"type": "BuiltinCommonInstructions::ForEach", "object": obj,
         "conditions": list(conds), "actions": list(acts)}
    if subs:
        e["events"] = list(subs)
    return e


def comment(text):
    return {"type": "BuiltinCommonInstructions::Comment",
            "color": {"b": 109, "g": 230, "r": 255, "textB": 0, "textG": 0, "textR": 0},
            "comment": text}


def group(name, events, rgb=(74, 176, 228)):
    return {"type": "BuiltinCommonInstructions::Group", "name": name, "source": "",
            "colorR": rgb[0], "colorG": rgb[1], "colorB": rgb[2], "creationTime": 0,
            "parameters": [], "events": list(events)}


# common instructions
def setv(var, op, value):          # scene/global number variable
    return A("SetNumberVariable", var, op, str(value))


def sets(var, value):              # scene string variable
    return A("SetStringVariable", var, "=", value)


def isv(var, op, value):
    return C("NumberVariable", var, op, str(value))


def iss(var, value):
    return C("StringVariable", var, "=", value)


def key_down(key):
    return C("KeyFromTextPressed", "", f'"{key}"')


def key_hit(key):
    return C("KeyFromTextJustPressed", "", f'"{key}"')


def timer_over(name, value):
    return C("CompareTimer", "", f'"{name}"', ">", str(value))


def reset_timer(name):
    return A("ResetTimer", "", f'"{name}"')


def set_text(obj, expr):
    return A("TextContainerCapability::TextContainerBehavior::SetValue", obj, "Text", "=", expr)


def objvar(obj, var, op, expr):
    return A("SetNumberObjectVariable", obj, var, op, expr)


# ---------------------------------------------------------------- the pieces
# Cells are (column, row) inside the piece's box. The pivot is the point the piece
# spins around, in cells from the box's top-left corner.
PIECES = [
    # name, cells,                              pivot,      colour
    ("I", [(0, 1), (1, 1), (2, 1), (3, 1)], (2, 2), "0;220;240"),
    ("O", [(1, 0), (2, 0), (1, 1), (2, 1)], (2, 1), "250;215;0"),
    ("T", [(1, 0), (0, 1), (1, 1), (2, 1)], (1.5, 1.5), "170;60;230"),
    ("S", [(1, 0), (2, 0), (0, 1), (1, 1)], (1.5, 1.5), "60;210;80"),
    ("Z", [(0, 0), (1, 0), (1, 1), (2, 1)], (1.5, 1.5), "240;60;60"),
    ("J", [(0, 0), (0, 1), (1, 1), (2, 1)], (1.5, 1.5), "50;100;240"),
    ("L", [(2, 0), (0, 1), (1, 1), (2, 1)], (1.5, 1.5), "250;150;30"),
]


def num(name, value):
    return {"name": name, "type": "number", "value": value}


def text(name, value):
    return {"name": name, "type": "string", "value": value}


def num_array(name, values):
    return {"name": name, "type": "array",
            "children": [{"type": "number", "value": v} for v in values]}


shapes = {"name": "Shapes", "type": "array", "children": [
    {"type": "structure", "children": [
        text("Name", n),
        num_array("X", [c[0] for c in cells]),
        num_array("Y", [c[1] for c in cells]),
        num("PX", pivot[0]),
        num("PY", pivot[1]),
        text("Color", colour),
    ]} for n, cells, pivot, colour in PIECES]}

scene_variables = [
    shapes,
    num_array("Kicks", [0, CELL, -CELL]),           # sideways nudges tried when a turn is blocked
    num_array("LineScores", [0, 100, 300, 500, 800]),  # points for clearing 0,1,2,3,4 lines
    num("BoardX", BOARD_X), num("BoardY", BOARD_Y),
    num("SpawnX", BOARD_X + 3 * CELL), num("SpawnY", BOARD_Y),
    num("PreviewX", 464), num("PreviewY", 176),
    num("PieceType", 0), num("NextType", 0),
    num("PivotX", 0), num("PivotY", 0), num("OldPivotX", 0), num("OldPivotY", 0),
    num("MoveX", 0), num("MoveY", 0), num("Rot", 0), num("Steps", 0),
    num("Try", 0), num("Tries", 1), num("Checking", 0), num("Blocked", 0), num("Done", 0),
    num("Landed", 0), num("SpawnNeeded", 0),
    num("RowY", 0), num("Cleared", 0), num("LinesNow", 0),
    num("Score", 0), num("Lines", 0), num("Level", 1),
    num("FallDelay", 0.8), num("ShiftWait", 0.17),
    num("I", 0),
    text("State", "Playing"),
]

# ---------------------------------------------------------------- events
LEFT_EDGE = "BoardX"
RIGHT_EDGE = f"BoardX + {9 * CELL}"
FLOOR = f"BoardY + {19 * CELL}"

events = [
    comment("A simple Tetris. Every piece is 4 'Active' blocks. When a piece lands, "
            "each block is swapped for a 'Settled' block, full rows are removed, and a new "
            "piece appears. Piece shapes and colours live in the scene variable 'Shapes'."),

    group("Start", [
        ev([C("SceneJustBegins", "")], [
            A("Hide", "GameOverText"),
            A("Hide", "GameOverPanel"),
            setv("NextType", "=", "RandomInRange(0, 6)"),
            setv("SpawnNeeded", "=", 1),
            sets("State", '"Playing"'),
        ]),
    ]),

    group("Spawn the next piece", [
        comment("Take the piece shown under NEXT, pick a new NEXT, and build both from the 'Shapes' table."),
        ev([isv("SpawnNeeded", "=", 1), iss("State", '"Playing"')], [
            setv("SpawnNeeded", "=", 0),
            setv("PieceType", "=", "NextType"),
            setv("NextType", "=", "RandomInRange(0, 6)"),
            setv("PivotX", "=", "SpawnX + Shapes[PieceType].PX * 32"),
            setv("PivotY", "=", "SpawnY + Shapes[PieceType].PY * 32"),
            setv("I", "=", 0),
            A("Delete", "NextBlock", ""),
            reset_timer("Fall"),
        ], [
            repeat(4, [], [
                A("Create", "", "Active",
                  "SpawnX + Shapes[PieceType].X[I] * 32", "SpawnY + Shapes[PieceType].Y[I] * 32", ""),
                A("ChangeColor", "Active", "Shapes[PieceType].Color"),
                A("Create", "", "NextBlock",
                  "PreviewX + Shapes[NextType].X[I] * 32", "PreviewY + Shapes[NextType].Y[I] * 32", ""),
                A("ChangeColor", "NextBlock", "Shapes[NextType].Color"),
                setv("I", "+", 1),
            ]),
            comment("No room for the new piece: the stack reached the top."),
            ev([C("CollisionNP", "Active", "Settled", "", "", "")], [
                sets("State", '"GameOver"'),
                A("Show", "GameOverText", ""),
                A("Show", "GameOverPanel", ""),
                setv("Best", "=", "max(Best, Score)"),
            ]),
        ]),
    ]),

    group("Read the keyboard", [
        comment("Turn key presses into a move request: MoveX (left/right), MoveY (down), "
                "Rot (turn) and Steps (how many times to try it - 22 for a hard drop)."),
        ev([iss("State", '"Playing"')], [
            setv("MoveX", "=", 0), setv("MoveY", "=", 0), setv("Rot", "=", 0), setv("Steps", "=", 0),
        ], [
            comment("Holding left or right repeats the move after a short wait."),
            ev([key_down("Left"), timer_over("Shift", "ShiftWait")],
               [setv("MoveX", "=", -1), setv("Steps", "=", 1), reset_timer("Shift"), setv("ShiftWait", "=", 0.05)]),
            ev([key_hit("Left")],
               [setv("MoveX", "=", -1), setv("Steps", "=", 1), reset_timer("Shift"), setv("ShiftWait", "=", 0.17)]),
            ev([key_down("Right"), timer_over("Shift", "ShiftWait")],
               [setv("MoveX", "=", 1), setv("Steps", "=", 1), reset_timer("Shift"), setv("ShiftWait", "=", 0.05)]),
            ev([key_hit("Right")],
               [setv("MoveX", "=", 1), setv("Steps", "=", 1), reset_timer("Shift"), setv("ShiftWait", "=", 0.17)]),
            ev([key_hit("Up")], [setv("Rot", "=", 1), setv("Steps", "=", 1)]),
            ev([key_hit("x")], [setv("Rot", "=", 1), setv("Steps", "=", 1)]),
            comment("Gravity. It waits while the player is moving or turning in the same frame."),
            ev([isv("MoveX", "=", 0), isv("Rot", "=", 0), timer_over("Fall", "FallDelay")],
               [setv("MoveY", "=", 1), setv("Steps", "=", 1), reset_timer("Fall")]),
            ev([isv("MoveX", "=", 0), isv("Rot", "=", 0), key_down("Down"), timer_over("Fall", 0.04)],
               [setv("MoveY", "=", 1), setv("Steps", "=", 1), reset_timer("Fall")]),
            ev([key_hit("Space")],
               [setv("MoveX", "=", 0), setv("Rot", "=", 0), setv("MoveY", "=", 1), setv("Steps", "=", 22)]),
        ]),
    ]),

    group("Move the piece", [
        comment("Remember where the piece was, move it, then check it isn't inside a wall, the floor "
                "or another block. If it is, put it back. A blocked turn also tries one cell right, "
                "then one cell left (the 'Kicks' table) before giving up."),
        ev([iss("State", '"Playing"'), isv("Steps", ">", 0)], [], [
            repeat("Steps", [], [], [
                ev([], [
                    objvar("Active", "OldX", "=", "Active.X()"),
                    objvar("Active", "OldY", "=", "Active.Y()"),
                    setv("OldPivotX", "=", "PivotX"),
                    setv("OldPivotY", "=", "PivotY"),
                    setv("Done", "=", 0),
                    setv("Try", "=", 0),
                    setv("Tries", "=", "1 + Rot * 2"),
                ]),
                repeat(3, [], [], [
                    ev([isv("Done", "=", 0), isv("Try", "<", "Tries")], [
                        A("SetX", "Active", "=", "Active.OldX + MoveX * 32 + Kicks[Try]"),
                        A("SetY", "Active", "=", "Active.OldY + MoveY * 32"),
                        setv("PivotX", "=", "OldPivotX + MoveX * 32 + Kicks[Try]"),
                        setv("PivotY", "=", "OldPivotY + MoveY * 32"),
                        setv("Checking", "=", 1),
                        setv("Blocked", "=", 0),
                    ]),
                    comment("Turn a quarter clockwise around the pivot."),
                    ev([isv("Checking", "=", 1), isv("Rot", "=", 1)], [
                        objvar("Active", "DX", "=", "Active.X() + 16 - PivotX"),
                        objvar("Active", "DY", "=", "Active.Y() + 16 - PivotY"),
                        A("SetX", "Active", "=", "PivotX - Active.DY - 16"),
                        A("SetY", "Active", "=", "PivotY + Active.DX - 16"),
                    ]),
                    ev([isv("Checking", "=", 1), C("CollisionNP", "Active", "Settled", "", "", "")],
                       [setv("Blocked", "=", 1)]),
                    ev([isv("Checking", "=", 1), C("PosX", "Active", "<", LEFT_EDGE)],
                       [setv("Blocked", "=", 1)]),
                    ev([isv("Checking", "=", 1), C("PosX", "Active", ">", RIGHT_EDGE)],
                       [setv("Blocked", "=", 1)]),
                    ev([isv("Checking", "=", 1), C("PosY", "Active", ">", FLOOR)],
                       [setv("Blocked", "=", 1)]),
                    ev([isv("Checking", "=", 1), isv("Blocked", "=", 0)], [setv("Done", "=", 1)]),
                    ev([], [setv("Try", "+", 1), setv("Checking", "=", 0)]),
                ]),
                ev([isv("Done", "=", 0)], [
                    A("SetX", "Active", "=", "Active.OldX"),
                    A("SetY", "Active", "=", "Active.OldY"),
                    setv("PivotX", "=", "OldPivotX"),
                    setv("PivotY", "=", "OldPivotY"),
                ]),
                comment("Couldn't move down: the piece has landed."),
                ev([isv("Done", "=", 0), isv("MoveY", "=", 1)], [setv("Landed", "=", 1)]),
            ]),
        ]),
    ]),

    group("Land the piece and clear lines", [
        ev([isv("Landed", "=", 1)], [
            setv("Landed", "=", 0),
            setv("SpawnNeeded", "=", 1),
            setv("Cleared", "=", 0),
            setv("LinesNow", "=", 0),
            setv("RowY", "=", FLOOR),
        ], [
            for_each("Active", [], [
                A("Create", "", "Settled", "Active.X()", "Active.Y()", ""),
                A("ChangeColor", "Settled", "Shapes[PieceType].Color"),
            ]),
            ev([], [A("Delete", "Active", "")]),
            comment("Check each row from the bottom up. A row with 10 blocks is removed and "
                    "everything above it drops one cell; the same row is then checked again."),
            repeat(24, [], [], [
                ev([C("PosY", "Settled", "=", "RowY"), C("PickedInstancesCount", "Settled", "=", "10")], [
                    A("Delete", "Settled", ""),
                    setv("Cleared", "=", 1),
                    setv("LinesNow", "+", 1),
                ]),
                ev([isv("Cleared", "=", 1), C("PosY", "Settled", "<", "RowY")],
                   [A("SetY", "Settled", "+", "32")]),
                ev([isv("Cleared", "=", 0)], [setv("RowY", "-", 32)]),
                ev([], [setv("Cleared", "=", 0)]),
            ]),
            ev([isv("LinesNow", ">", 0)], [
                setv("Lines", "+", "LinesNow"),
                setv("Score", "+", "LineScores[LinesNow] * Level"),
                setv("Level", "=", "floor(Lines / 10) + 1"),
                setv("FallDelay", "=", "max(0.08, 0.8 - (Level - 1) * 0.07)"),
            ]),
        ]),
    ]),

    group("Game over", [
        ev([iss("State", '"GameOver"'), key_hit("Return")], [A("Scene", "", '"Game"', "")]),
        ev([iss("State", '"GameOver"'), key_hit("r")], [A("Scene", "", '"Game"', "")]),
    ]),

    group("Score panel", [
        ev([], [
            set_text("ScoreText", '"SCORE" + NewLine() + ToString(Score)'),
            set_text("LinesText", '"LINES" + NewLine() + ToString(Lines)'),
            set_text("LevelText", '"LEVEL" + NewLine() + ToString(Level)'),
            set_text("BestText", '"BEST" + NewLine() + ToString(max(Best, Score))'),
        ]),
    ]),
]

# ---------------------------------------------------------------- objects
def square_mask(inset, size=CELL):
    a, b = inset, size - inset
    return [[{"x": a, "y": a}, {"x": b, "y": a}, {"x": b, "y": b}, {"x": a, "y": b}]]


def block_object(name, variables=()):
    # A 32 px block. The collision mask is shrunk by 4 px on every side so that
    # blocks sitting side by side do not count as touching.
    return {
        "adaptCollisionMaskAutomatically": False, "assetStoreId": "", "name": name,
        "type": "Sprite", "updateIfNotVisible": False, "variables": list(variables), "effects": [],
        "behaviors": [],
        "animations": [{"name": "", "useMultipleDirections": False, "directions": [{
            "looping": False, "timeBetweenFrames": 0.1, "sprites": [{
                "hasCustomCollisionMask": True, "image": "block.png", "points": [],
                "originPoint": {"name": "origine", "x": 0, "y": 0},
                "centerPoint": {"automatic": True, "name": "centre", "x": 0, "y": 0},
                "customCollisionMask": square_mask(4),
            }]}]}],
    }


def tiled(name, texture, w, h):
    return {"assetStoreId": "", "name": name, "type": "TiledSpriteObject::TiledSprite",
            "texture": texture, "width": w, "height": h,
            "variables": [], "effects": [], "behaviors": []}


def label(name, string, size, colour="255;255;255", align="left"):
    content = {"bold": True, "isOutlineEnabled": True, "isShadowEnabled": False, "italic": False,
               "outlineColor": "20;16;40", "outlineThickness": 4,
               "shadowAngle": 90, "shadowBlurRadius": 2, "shadowColor": "0;0;0",
               "shadowDistance": 4, "shadowOpacity": 127, "smoothed": True, "underlined": False,
               "text": string, "font": "", "textAlignment": align, "verticalTextAlignment": "top",
               "characterSize": size, "lineHeight": 0, "color": colour}
    return {"assetStoreId": "", "name": name, "type": "TextObject::Text",
            "variables": [], "effects": [], "behaviors": [], "content": content}


objects = [
    tiled("Background", "background.png", 640, 480),
    tiled("BoardBg", "cell.png", CELL, CELL),
    tiled("Wall", "wall.png", CELL, CELL),
    tiled("GameOverPanel", "panel.png", CELL, CELL),
    # OldX/OldY remember where a block was before a move; DX/DY are used while turning.
    block_object("Active", [num("OldX", 0), num("OldY", 0), num("DX", 0), num("DY", 0)]),
    block_object("Settled"),
    block_object("NextBlock"),
    label("Title", "TETRIS", 52, "255;215;0"),
    label("NextLabel", "NEXT", 28),
    label("ScoreText", "SCORE\n0", 28),
    label("LinesText", "LINES\n0", 28),
    label("LevelText", "LEVEL\n1", 28),
    label("BestText", "BEST\n0", 28),
    label("HelpText", "Left / Right  move\nUp or X  turn\nDown  soft drop\nSpace  hard drop", 18,
          "225;220;255"),
    label("GameOverText", "GAME OVER\n\nEnter to play again", 34, "255;255;255", "center"),
]


def inst(name, x, y, z=0, w=None, h=None, layer=""):
    i = {"angle": 0, "customSize": w is not None, "height": h or 0, "layer": layer, "name": name,
         "persistentUuid": str(uuid.uuid4()), "width": w or 0, "x": x, "y": y, "zOrder": z,
         "numberProperties": [], "stringProperties": [], "initialVariables": []}
    return i


side = 448
instances = [
    inst("Background", 0, 0, -10, WIN_W, WIN_H),
    inst("BoardBg", BOARD_X, BOARD_Y, -5, 10 * CELL, 20 * CELL),
    inst("Wall", BOARD_X - CELL, BOARD_Y, 0, CELL, 20 * CELL),
    inst("Wall", BOARD_X + 10 * CELL, BOARD_Y, 0, CELL, 20 * CELL),
    inst("Wall", BOARD_X - CELL, BOARD_Y + 20 * CELL, 0, 12 * CELL, CELL),
    inst("Title", side, 40, 5, layer="UI"),
    inst("NextLabel", side, 128, 5, layer="UI"),
    inst("ScoreText", side, 270, 5, layer="UI"),
    inst("LinesText", side, 350, 5, layer="UI"),
    inst("LevelText", side, 430, 5, layer="UI"),
    inst("BestText", side, 510, 5, layer="UI"),
    inst("HelpText", side, 600, 5, layer="UI"),
    inst("GameOverPanel", BOARD_X, 9 * CELL, 0, 10 * CELL, 6 * CELL, "UI"),
    inst("GameOverText", BOARD_X, 9 * CELL + 40, 1, 10 * CELL, 150, "UI"),
]

folder = {"folderName": "__ROOT", "children": [{"objectName": o["name"]} for o in objects]}

UI_LAYER = {"ambientLightColorB": 200, "ambientLightColorG": 200, "ambientLightColorR": 200,
            "camera2DPlaneMaxDrawingDistance": 5000, "camera3DFarPlaneDistance": 10000,
            "camera3DFieldOfView": 45, "camera3DNearPlaneDistance": 0.1,
            "cameraType": "perspective", "followBaseLayerCamera": False,
            "isLightingLayer": False, "isLocked": False, "name": "UI", "renderingType": "",
            "visibility": True,
            "cameras": [{"defaultSize": True, "defaultViewport": True, "height": 0,
                         "viewportBottom": 1, "viewportLeft": 0, "viewportRight": 1,
                         "viewportTop": 0, "width": 0}],
            "effects": []}

layout = {
    "b": 80, "disableInputWhenNotFocused": True, "mangledName": "Game", "name": "Game",
    "r": 45, "standardSortMethod": True, "stopSoundsOnStartup": True, "title": "", "v": 30,
    "uiSettings": {"grid": True, "gridType": "rectangular", "gridWidth": CELL, "gridHeight": CELL,
                   "gridOffsetX": 0, "gridOffsetY": 0, "gridColor": 10401023, "gridAlpha": 0.3,
                   "snap": True, "zoomFactor": 1, "windowMask": False},
    "objectsGroups": [], "variables": scene_variables, "instances": instances,
    "objects": objects, "objectsFolderStructure": folder, "events": events,
    "layers": [{"ambientLightColorB": 200, "ambientLightColorG": 200, "ambientLightColorR": 200,
                "camera2DPlaneMaxDrawingDistance": 5000, "camera3DFarPlaneDistance": 10000,
                "camera3DFieldOfView": 45, "camera3DNearPlaneDistance": 0.1,
                "cameraType": "perspective", "followBaseLayerCamera": False,
                "isLightingLayer": False, "isLocked": False, "name": "", "renderingType": "",
                "visibility": True,
                "cameras": [{"defaultSize": True, "defaultViewport": True, "height": 0,
                             "viewportBottom": 1, "viewportLeft": 0, "viewportRight": 1,
                             "viewportTop": 0, "width": 0}],
                "effects": []}, UI_LAYER],
    "behaviorsSharedData": [],
}


def image(name):
    return {"file": f"assets/{name}", "kind": "image", "metadata": "", "name": name,
            "smoothed": True, "userAdded": True}


project = {
    "firstLayout": "Game",
    "gdVersion": {"build": 282, "major": 5, "minor": 6, "revision": 0},
    "properties": {
        "adaptGameResolutionAtRuntime": True, "antialiasingMode": "MSAA",
        "antialisingEnabledOnMobile": False, "folderProject": False, "orientation": "default",
        "packageName": "com.luqman.gdeveloptetris", "pixelsRounding": False,
        "projectUuid": str(uuid.uuid4()), "scaleMode": "linear", "sizeOnStartupMode": "adaptWidth",
        "templateSlug": "", "useDeprecatedZeroAsDefaultStringVariable": False, "version": "1.0.0",
        "name": "Tetris (GDevelop test)", "description": "", "author": "",
        "windowWidth": WIN_W, "windowHeight": WIN_H, "latestCompilationDirectory": "",
        "maxFPS": 60, "minFPS": 20, "verticalSync": True, "platformSpecificAssets": {},
        "loadingScreen": {"backgroundColor": 0, "backgroundFadeInDuration": 0.2,
                          "backgroundImageResourceName": "", "gdevelopLogoStyle": "light",
                          "logoAndProgressFadeInDuration": 0.2, "logoAndProgressLogoFadeInDelay": 0.2,
                          "minDuration": 0, "progressBarColor": 16777215, "progressBarHeight": 20,
                          "progressBarMaxWidth": 200, "progressBarMinWidth": 40,
                          "progressBarWidthPercent": 30, "showGDevelopSplash": True,
                          "showProgressBar": True},
        "watermark": {"placement": "bottom-left", "showWatermark": True},
        "authorIds": [], "authorUsernames": [], "categories": [], "playableDevices": [],
        "extensionProperties": [], "platforms": [{"name": "GDevelop JS platform"}],
        "currentPlatform": "GDevelop JS platform",
    },
    "resources": {"resources": [image(n) for n in
                                ("block.png", "wall.png", "cell.png", "background.png", "panel.png")],
                  "resourceFolders": []},
    "objects": [], "objectsFolderStructure": {"folderName": "__ROOT"}, "objectsGroups": [],
    "variables": [num("Best", 0)],
    "layouts": [layout],
    "externalEvents": [], "eventsFunctionsExtensions": [], "externalLayouts": [],
}

(ROOT / "game.raw.json").write_text(json.dumps(project, indent=2))
print("wrote", ROOT / "game.raw.json")
