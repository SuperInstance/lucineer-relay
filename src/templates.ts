// Auto-generated build templates for the Worker fast path.
// Extracted from process_v2.py build functions + CHARACTER_BIBLE voice lines.
// Each template returns instantly with commands + a Lucineier voice line.

export interface BuildCommand {
  type: string;
  params: Record<string, unknown>;
}

export interface BuildTemplate {
  reply: string;
  commands: BuildCommand[];
}

export const BUILD_TEMPLATES: Record<string, BuildTemplate> = {
  "tower": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "TowerBase",
          "shape": "Cylinder",
          "size": {
            "x": 8,
            "y": 30,
            "z": 8
          },
          "position": {
            "x": 0,
            "y": 15,
            "z": 0
          },
          "material": "Concrete",
          "color": {
            "r": 130,
            "g": 125,
            "b": 120
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "TowerBattlement",
          "shape": "Cylinder",
          "size": {
            "x": 10,
            "y": 3,
            "z": 10
          },
          "position": {
            "x": 0,
            "y": 31,
            "z": 0
          },
          "material": "Concrete",
          "color": {
            "r": 110,
            "g": 105,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "TowerLantern",
          "shape": "Ball",
          "size": {
            "x": 3,
            "y": 3,
            "z": 3
          },
          "position": {
            "x": 0,
            "y": 34,
            "z": 0
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 220,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "TowerLantern",
          "lightType": "PointLight",
          "brightness": 5,
          "range": 40,
          "color": {
            "r": 255,
            "g": 220,
            "b": 100
          }
        }
      }
    ],
    "reply": "Stone shaft's up, battlements are on, beacon's lit. Top floor's open \u2014 didn't know what you wanted up there."
  },
  "house": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "HouseFoundation",
          "shape": "Block",
          "size": {
            "x": 22,
            "y": 1,
            "z": 18
          },
          "position": {
            "x": 0,
            "y": -0.5,
            "z": 0
          },
          "material": "Cobblestone",
          "color": {
            "r": 140,
            "g": 138,
            "b": 132
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "HouseFloor",
          "shape": "Block",
          "size": {
            "x": 20,
            "y": 1,
            "z": 16
          },
          "position": {
            "x": 0,
            "y": 0,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 120,
            "g": 80,
            "b": 50
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "DoorStep",
          "shape": "Block",
          "size": {
            "x": 4,
            "y": 0.5,
            "z": 1.5
          },
          "position": {
            "x": 0,
            "y": 0.25,
            "z": 9
          },
          "material": "Cobblestone",
          "color": {
            "r": 130,
            "g": 125,
            "b": 120
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WallN",
          "shape": "Block",
          "size": {
            "x": 20,
            "y": 10,
            "z": 1
          },
          "position": {
            "x": 0,
            "y": 5,
            "z": -8
          },
          "material": "Brick",
          "color": {
            "r": 150,
            "g": 130,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WallS",
          "shape": "Block",
          "size": {
            "x": 20,
            "y": 10,
            "z": 1
          },
          "position": {
            "x": 0,
            "y": 5,
            "z": 8
          },
          "material": "Brick",
          "color": {
            "r": 145,
            "g": 125,
            "b": 95
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WallW",
          "shape": "Block",
          "size": {
            "x": 1,
            "y": 10,
            "z": 16
          },
          "position": {
            "x": -10,
            "y": 5,
            "z": 0
          },
          "material": "Brick",
          "color": {
            "r": 140,
            "g": 120,
            "b": 90
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WallE",
          "shape": "Block",
          "size": {
            "x": 1,
            "y": 10,
            "z": 16
          },
          "position": {
            "x": 10,
            "y": 5,
            "z": 0
          },
          "material": "Brick",
          "color": {
            "r": 148,
            "g": 128,
            "b": 98
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindowGlass",
          "shape": "Block",
          "size": {
            "x": 1.2,
            "y": 3,
            "z": 3
          },
          "position": {
            "x": -10,
            "y": 5,
            "z": 0
          },
          "material": "Glass",
          "color": {
            "r": 180,
            "g": 210,
            "b": 255
          },
          "anchored": true,
          "transparency": 0.5,
          "reflectance": 0.2
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindowGlow",
          "shape": "Block",
          "size": {
            "x": 0.5,
            "y": 2.5,
            "z": 2.5
          },
          "position": {
            "x": -9.8,
            "y": 5,
            "z": 0
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 120
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindowShutterL",
          "shape": "Block",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.5
          },
          "position": {
            "x": -10,
            "y": 5,
            "z": -2
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindowShutterR",
          "shape": "Block",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.5
          },
          "position": {
            "x": -10,
            "y": 5,
            "z": 2
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "WindowGlow",
          "lightType": "PointLight",
          "brightness": 4,
          "range": 18,
          "color": {
            "r": 255,
            "g": 200,
            "b": 120
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "FlowerBox",
          "shape": "Block",
          "size": {
            "x": 1,
            "y": 0.6,
            "z": 4
          },
          "position": {
            "x": -10.3,
            "y": 3,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 65,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "Flower1",
          "shape": "Ball",
          "size": {
            "x": 0.5,
            "y": 0.5,
            "z": 0.5
          },
          "position": {
            "x": -10.3,
            "y": 3.5,
            "z": -1
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 100,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "Flower2",
          "shape": "Ball",
          "size": {
            "x": 0.5,
            "y": 0.5,
            "z": 0.5
          },
          "position": {
            "x": -10.3,
            "y": 3.5,
            "z": 0.5
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 220,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "Flower3",
          "shape": "Ball",
          "size": {
            "x": 0.5,
            "y": 0.5,
            "z": 0.5
          },
          "position": {
            "x": -10.3,
            "y": 3.5,
            "z": 1.5
          },
          "material": "Neon",
          "color": {
            "r": 200,
            "g": 100,
            "b": 255
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "RoofPeakN",
          "shape": "Wedge",
          "size": {
            "x": 22,
            "y": 5,
            "z": 9
          },
          "position": {
            "x": 0,
            "y": 12.5,
            "z": -4
          },
          "material": "WoodPlanks",
          "color": {
            "r": 90,
            "g": 50,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "RoofPeakS",
          "shape": "Wedge",
          "size": {
            "x": 22,
            "y": 5,
            "z": 9
          },
          "position": {
            "x": 0,
            "y": 12.5,
            "z": 4
          },
          "material": "WoodPlanks",
          "color": {
            "r": 85,
            "g": 48,
            "b": 28
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "Chimney",
          "shape": "Block",
          "size": {
            "x": 2,
            "y": 6,
            "z": 2
          },
          "position": {
            "x": 6,
            "y": 15,
            "z": -4
          },
          "material": "Brick",
          "color": {
            "r": 100,
            "g": 78,
            "b": 68
          },
          "anchored": true
        }
      },
      {
        "type": "addParticle",
        "params": {
          "parent": "Chimney",
          "texture": "rbxassetid://241876428",
          "rate": 8,
          "lifetime": {
            "min": 2,
            "max": 4
          },
          "speed": {
            "min": 1,
            "max": 3
          },
          "color": {
            "r": 180,
            "g": 180,
            "b": 180
          },
          "size": {
            "min": 1,
            "max": 2.5
          },
          "transparency": 0.3,
          "velocity": {
            "x": 0,
            "y": 2,
            "z": 0
          }
        }
      }
    ],
    "reply": "Foundation's set, walls are brick, roof's pitched and the chimney's drawing. Didn't hang the door \u2014 figured you'd want to pick it."
  },
  "castle": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "CastleFloor",
          "shape": "Block",
          "size": {
            "x": 40,
            "y": 1,
            "z": 40
          },
          "position": {
            "x": 0,
            "y": 0,
            "z": 0
          },
          "material": "Slate",
          "color": {
            "r": 160,
            "g": 155,
            "b": 150
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GravelPath",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 0.5,
            "z": 14
          },
          "position": {
            "x": 0,
            "y": 0.6,
            "z": 8
          },
          "material": "Ground",
          "color": {
            "r": 120,
            "g": 110,
            "b": 95
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleWall0",
          "shape": "Block",
          "size": {
            "x": 40,
            "y": 15,
            "z": 2
          },
          "position": {
            "x": 0,
            "y": 7.5,
            "z": -20
          },
          "material": "Slate",
          "color": {
            "r": 155,
            "g": 150,
            "b": 145
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleWall1",
          "shape": "Block",
          "size": {
            "x": 40,
            "y": 15,
            "z": 2
          },
          "position": {
            "x": 0,
            "y": 7.5,
            "z": 20
          },
          "material": "Cobblestone",
          "color": {
            "r": 140,
            "g": 138,
            "b": 132
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleWall2",
          "shape": "Block",
          "size": {
            "x": 2,
            "y": 15,
            "z": 40
          },
          "position": {
            "x": -20,
            "y": 7.5,
            "z": 0
          },
          "material": "Slate",
          "color": {
            "r": 150,
            "g": 148,
            "b": 142
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleWall3",
          "shape": "Block",
          "size": {
            "x": 2,
            "y": 15,
            "z": 40
          },
          "position": {
            "x": 20,
            "y": 7.5,
            "z": 0
          },
          "material": "Cobblestone",
          "color": {
            "r": 135,
            "g": 133,
            "b": 128
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WallTorch0",
          "shape": "Ball",
          "size": {
            "x": 0.8,
            "y": 0.8,
            "z": 0.8
          },
          "position": {
            "x": -12,
            "y": 10,
            "z": -19.5
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 140,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WallTorch1",
          "shape": "Ball",
          "size": {
            "x": 0.8,
            "y": 0.8,
            "z": 0.8
          },
          "position": {
            "x": 12,
            "y": 10,
            "z": 19.5
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 140,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "WallTorch0",
          "lightType": "PointLight",
          "brightness": 6,
          "range": 24,
          "color": {
            "r": 255,
            "g": 160,
            "b": 60
          },
          "shadows": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "WallTorch1",
          "lightType": "PointLight",
          "brightness": 6,
          "range": 24,
          "color": {
            "r": 255,
            "g": 160,
            "b": 60
          },
          "shadows": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleTower0",
          "shape": "Cylinder",
          "size": {
            "x": 6,
            "y": 22,
            "z": 6
          },
          "position": {
            "x": -18,
            "y": 11,
            "z": -18
          },
          "material": "Slate",
          "color": {
            "r": 150,
            "g": 145,
            "b": 140
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleTowerRoof0",
          "shape": "Cone",
          "size": {
            "x": 8,
            "y": 6,
            "z": 8
          },
          "position": {
            "x": -18,
            "y": 25,
            "z": -18
          },
          "material": "WoodPlanks",
          "color": {
            "r": 80,
            "g": 40,
            "b": 20
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BannerPole0",
          "shape": "Cylinder",
          "size": {
            "x": 0.3,
            "y": 4,
            "z": 0.3
          },
          "position": {
            "x": -18,
            "y": 29,
            "z": -18
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 70,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BannerCloth0",
          "shape": "Block",
          "size": {
            "x": 0.2,
            "y": 3,
            "z": 2
          },
          "position": {
            "x": -18,
            "y": 29,
            "z": -17.5
          },
          "material": "Neon",
          "color": {
            "r": 180,
            "g": 40,
            "b": 40
          },
          "anchored": true,
          "transparency": 0.1
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleTower1",
          "shape": "Cylinder",
          "size": {
            "x": 6,
            "y": 22,
            "z": 6
          },
          "position": {
            "x": 18,
            "y": 11,
            "z": -18
          },
          "material": "Cobblestone",
          "color": {
            "r": 135,
            "g": 132,
            "b": 128
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleTowerRoof1",
          "shape": "Cone",
          "size": {
            "x": 8,
            "y": 6,
            "z": 8
          },
          "position": {
            "x": 18,
            "y": 25,
            "z": -18
          },
          "material": "WoodPlanks",
          "color": {
            "r": 80,
            "g": 40,
            "b": 20
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleTower2",
          "shape": "Cylinder",
          "size": {
            "x": 6,
            "y": 22,
            "z": 6
          },
          "position": {
            "x": -18,
            "y": 11,
            "z": 18
          },
          "material": "Concrete",
          "color": {
            "r": 145,
            "g": 142,
            "b": 138
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleTowerRoof2",
          "shape": "Cone",
          "size": {
            "x": 8,
            "y": 6,
            "z": 8
          },
          "position": {
            "x": -18,
            "y": 25,
            "z": 18
          },
          "material": "WoodPlanks",
          "color": {
            "r": 80,
            "g": 40,
            "b": 20
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BannerPole2",
          "shape": "Cylinder",
          "size": {
            "x": 0.3,
            "y": 4,
            "z": 0.3
          },
          "position": {
            "x": -18,
            "y": 29,
            "z": 18
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 70,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BannerCloth2",
          "shape": "Block",
          "size": {
            "x": 0.2,
            "y": 3,
            "z": 2
          },
          "position": {
            "x": -18,
            "y": 29,
            "z": 18.5
          },
          "material": "Neon",
          "color": {
            "r": 180,
            "g": 40,
            "b": 40
          },
          "anchored": true,
          "transparency": 0.1
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleTower3",
          "shape": "Cylinder",
          "size": {
            "x": 6,
            "y": 22,
            "z": 6
          },
          "position": {
            "x": 18,
            "y": 11,
            "z": 18
          },
          "material": "Basalt",
          "color": {
            "r": 115,
            "g": 112,
            "b": 108
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleTowerRoof3",
          "shape": "Cone",
          "size": {
            "x": 8,
            "y": 6,
            "z": 8
          },
          "position": {
            "x": 18,
            "y": 25,
            "z": 18
          },
          "material": "WoodPlanks",
          "color": {
            "r": 80,
            "g": 40,
            "b": 20
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleKeep",
          "shape": "Block",
          "size": {
            "x": 12,
            "y": 20,
            "z": 12
          },
          "position": {
            "x": 0,
            "y": 10,
            "z": 0
          },
          "material": "Slate",
          "color": {
            "r": 155,
            "g": 150,
            "b": 145
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleGate",
          "shape": "Block",
          "size": {
            "x": 6,
            "y": 8,
            "z": 2
          },
          "position": {
            "x": 0,
            "y": 4,
            "z": 20
          },
          "material": "WoodPlanks",
          "color": {
            "r": 60,
            "g": 35,
            "b": 18
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CastleBeacon",
          "shape": "Ball",
          "size": {
            "x": 3,
            "y": 3,
            "z": 3
          },
          "position": {
            "x": 0,
            "y": 22,
            "z": 0
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "CastleBeacon",
          "lightType": "PointLight",
          "brightness": 8,
          "range": 60,
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          },
          "shadows": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "KeepFlagPole",
          "shape": "Cylinder",
          "size": {
            "x": 0.3,
            "y": 5,
            "z": 0.3
          },
          "position": {
            "x": 0,
            "y": 24,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 80,
            "g": 75,
            "b": 70
          },
          "anchored": true
        }
      },
      {
        "type": "addParticle",
        "params": {
          "parent": "CastleBeacon",
          "texture": "rbxassetid://243660364",
          "rate": 6,
          "lifetime": {
            "min": 0.5,
            "max": 1.5
          },
          "speed": {
            "min": 1,
            "max": 3
          },
          "color": {
            "r": 255,
            "g": 120,
            "b": 50
          },
          "size": {
            "min": 0.5,
            "max": 1.5
          },
          "transparency": 0.3,
          "velocity": {
            "x": 0,
            "y": 3,
            "z": 0
          }
        }
      }
    ],
    "reply": "Walls are up, towers are capped, banners are flying. Left the murder holes off \u2014 seemed like your department."
  },
  "bridge": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "BridgeArch0",
          "shape": "Block",
          "size": {
            "x": 8,
            "y": 8,
            "z": 2
          },
          "position": {
            "x": 0,
            "y": -1,
            "z": -10
          },
          "material": "Cobblestone",
          "color": {
            "r": 130,
            "g": 125,
            "b": 118
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeArchPier0",
          "shape": "Cylinder",
          "size": {
            "x": 3,
            "y": 10,
            "z": 3
          },
          "position": {
            "x": 0,
            "y": -3,
            "z": -10
          },
          "material": "Stone",
          "color": {
            "r": 115,
            "g": 110,
            "b": 103
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeArch1",
          "shape": "Block",
          "size": {
            "x": 8,
            "y": 8,
            "z": 2
          },
          "position": {
            "x": 0,
            "y": -1,
            "z": 0
          },
          "material": "Cobblestone",
          "color": {
            "r": 130,
            "g": 125,
            "b": 118
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeArchPier1",
          "shape": "Cylinder",
          "size": {
            "x": 3,
            "y": 10,
            "z": 3
          },
          "position": {
            "x": 0,
            "y": -3,
            "z": 0
          },
          "material": "Stone",
          "color": {
            "r": 115,
            "g": 110,
            "b": 103
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeArch2",
          "shape": "Block",
          "size": {
            "x": 8,
            "y": 8,
            "z": 2
          },
          "position": {
            "x": 0,
            "y": -1,
            "z": 10
          },
          "material": "Cobblestone",
          "color": {
            "r": 130,
            "g": 125,
            "b": 118
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeArchPier2",
          "shape": "Cylinder",
          "size": {
            "x": 3,
            "y": 10,
            "z": 3
          },
          "position": {
            "x": 0,
            "y": -3,
            "z": 10
          },
          "material": "Stone",
          "color": {
            "r": 115,
            "g": 110,
            "b": 103
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeDeck",
          "shape": "Block",
          "size": {
            "x": 7,
            "y": 1,
            "z": 28
          },
          "position": {
            "x": 0,
            "y": 3,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 120,
            "g": 80,
            "b": 45
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeWornPlank",
          "shape": "Block",
          "size": {
            "x": 7,
            "y": 0.2,
            "z": 2
          },
          "position": {
            "x": 0,
            "y": 3.6,
            "z": -3
          },
          "material": "WoodPlanks",
          "color": {
            "r": 160,
            "g": 120,
            "b": 75
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailL",
          "shape": "Block",
          "size": {
            "x": 0.5,
            "y": 3,
            "z": 28
          },
          "position": {
            "x": -3.5,
            "y": 4.5,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 100,
            "g": 70,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailR",
          "shape": "Block",
          "size": {
            "x": 0.5,
            "y": 3,
            "z": 28
          },
          "position": {
            "x": 3.5,
            "y": 4.5,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 100,
            "g": 70,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostL0",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 5,
            "z": -12
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostR0",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 5,
            "z": -12
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostL1",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 5,
            "z": -6
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostR1",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 5,
            "z": -6
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostL2",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 5,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostR2",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 5,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostL3",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 5,
            "z": 6
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostR3",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 5,
            "z": 6
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostL4",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 5,
            "z": 12
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRailPostR4",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 4,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 5,
            "z": 12
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofBeam",
          "shape": "Block",
          "size": {
            "x": 0.6,
            "y": 0.6,
            "z": 28
          },
          "position": {
            "x": 0,
            "y": 11,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 85,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostL0",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 8,
            "z": -12
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostR0",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 8,
            "z": -12
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostL1",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 8,
            "z": -6
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostR1",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 8,
            "z": -6
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostL2",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 8,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostR2",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 8,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostL3",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 8,
            "z": 6
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostR3",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 8,
            "z": 6
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostL4",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": -3.5,
            "y": 8,
            "z": 12
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofPostR4",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": 3.5,
            "y": 8,
            "z": 12
          },
          "material": "Wood",
          "color": {
            "r": 88,
            "g": 58,
            "b": 33
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofL",
          "shape": "Wedge",
          "size": {
            "x": 9,
            "y": 4,
            "z": 28
          },
          "position": {
            "x": 0,
            "y": 12,
            "z": -7
          },
          "material": "WoodPlanks",
          "color": {
            "r": 80,
            "g": 48,
            "b": 25
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeRoofR",
          "shape": "Wedge",
          "size": {
            "x": 9,
            "y": 4,
            "z": 28
          },
          "position": {
            "x": 0,
            "y": 12,
            "z": 7
          },
          "material": "WoodPlanks",
          "color": {
            "r": 75,
            "g": 45,
            "b": 22
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgePortalNL",
          "shape": "Block",
          "size": {
            "x": 1,
            "y": 8,
            "z": 1
          },
          "position": {
            "x": -4,
            "y": 7,
            "z": -14
          },
          "material": "WoodPlanks",
          "color": {
            "r": 95,
            "g": 65,
            "b": 38
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgePortalNR",
          "shape": "Block",
          "size": {
            "x": 1,
            "y": 8,
            "z": 1
          },
          "position": {
            "x": 4,
            "y": 7,
            "z": -14
          },
          "material": "WoodPlanks",
          "color": {
            "r": 95,
            "g": 65,
            "b": 38
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgePortalNTop",
          "shape": "Block",
          "size": {
            "x": 9,
            "y": 1,
            "z": 1
          },
          "position": {
            "x": 0,
            "y": 11,
            "z": -14
          },
          "material": "WoodPlanks",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgePortalSL",
          "shape": "Block",
          "size": {
            "x": 1,
            "y": 8,
            "z": 1
          },
          "position": {
            "x": -4,
            "y": 7,
            "z": 14
          },
          "material": "WoodPlanks",
          "color": {
            "r": 95,
            "g": 65,
            "b": 38
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgePortalSR",
          "shape": "Block",
          "size": {
            "x": 1,
            "y": 8,
            "z": 1
          },
          "position": {
            "x": 4,
            "y": 7,
            "z": 14
          },
          "material": "WoodPlanks",
          "color": {
            "r": 95,
            "g": 65,
            "b": 38
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgePortalSTop",
          "shape": "Block",
          "size": {
            "x": 9,
            "y": 1,
            "z": 1
          },
          "position": {
            "x": 0,
            "y": 11,
            "z": 14
          },
          "material": "WoodPlanks",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeLanternN",
          "shape": "Ball",
          "size": {
            "x": 1,
            "y": 1,
            "z": 1
          },
          "position": {
            "x": 0,
            "y": 9,
            "z": -13
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "BridgeLanternN",
          "lightType": "PointLight",
          "brightness": 3,
          "range": 15,
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeLanternS",
          "shape": "Ball",
          "size": {
            "x": 1,
            "y": 1,
            "z": 1
          },
          "position": {
            "x": 0,
            "y": 9,
            "z": 13
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "BridgeLanternS",
          "lightType": "PointLight",
          "brightness": 3,
          "range": 15,
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BridgeCarving",
          "shape": "Block",
          "size": {
            "x": 0.3,
            "y": 0.3,
            "z": 1.5
          },
          "position": {
            "x": -3.7,
            "y": 5,
            "z": 13.5
          },
          "material": "Neon",
          "color": {
            "r": 200,
            "g": 180,
            "b": 160
          },
          "anchored": true,
          "transparency": 0.3
        }
      }
    ],
    "reply": "Piers are seated, deck's laid, roof's on. Didn't bolt the cleats down. Depends what you're tying off."
  },
  "windmill": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "WindmillBaseStone",
          "shape": "Block",
          "size": {
            "x": 10,
            "y": 3,
            "z": 10
          },
          "position": {
            "x": 0,
            "y": 1.5,
            "z": 0
          },
          "material": "Cobblestone",
          "color": {
            "r": 135,
            "g": 130,
            "b": 123
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillTowerBrick",
          "shape": "Cylinder",
          "size": {
            "x": 7,
            "y": 8,
            "z": 7
          },
          "position": {
            "x": 0,
            "y": 7,
            "z": 0
          },
          "material": "Brick",
          "color": {
            "r": 145,
            "g": 120,
            "b": 95
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillTowerWood",
          "shape": "Cylinder",
          "size": {
            "x": 6.5,
            "y": 10,
            "z": 6.5
          },
          "position": {
            "x": 0,
            "y": 16,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 115,
            "g": 80,
            "b": 48
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillCap",
          "shape": "Cone",
          "size": {
            "x": 8,
            "y": 4,
            "z": 8
          },
          "position": {
            "x": 0,
            "y": 23,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 95,
            "g": 90,
            "b": 85
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillHub",
          "shape": "Cylinder",
          "size": {
            "x": 1.5,
            "y": 1.5,
            "z": 1.5
          },
          "position": {
            "x": 0,
            "y": 21,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 80,
            "g": 75,
            "b": 70
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillSail0",
          "shape": "Block",
          "size": {
            "x": 1.5,
            "y": 0.3,
            "z": 8
          },
          "position": {
            "x": 0,
            "y": 21,
            "z": -4
          },
          "material": "Plastic",
          "color": {
            "r": 220,
            "g": 210,
            "b": 190
          },
          "anchored": true,
          "transparency": 0.1
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillSail1",
          "shape": "Block",
          "size": {
            "x": 1.5,
            "y": 0.3,
            "z": 8
          },
          "position": {
            "x": 0,
            "y": 21,
            "z": 4
          },
          "material": "Plastic",
          "color": {
            "r": 210,
            "g": 200,
            "b": 180
          },
          "anchored": true,
          "transparency": 0.1
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillSail2",
          "shape": "Block",
          "size": {
            "x": 8,
            "y": 0.3,
            "z": 1.5
          },
          "position": {
            "x": 4,
            "y": 21,
            "z": 0
          },
          "material": "Plastic",
          "color": {
            "r": 200,
            "g": 190,
            "b": 170
          },
          "anchored": true,
          "transparency": 0.1
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillSail3",
          "shape": "Block",
          "size": {
            "x": 8,
            "y": 0.3,
            "z": 1.5
          },
          "position": {
            "x": -4,
            "y": 21,
            "z": 0
          },
          "material": "Plastic",
          "color": {
            "r": 220,
            "g": 210,
            "b": 190
          },
          "anchored": true,
          "transparency": 0.1
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillRedPatch",
          "shape": "Block",
          "size": {
            "x": 1.2,
            "y": 0.15,
            "z": 2.5
          },
          "position": {
            "x": 0.2,
            "y": 21,
            "z": -3
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 90,
            "b": 90
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillChute",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 3,
            "z": 1
          },
          "position": {
            "x": 4,
            "y": 4,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 90,
            "g": 85,
            "b": 80
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillDoor",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 4,
            "z": 0.5
          },
          "position": {
            "x": 0,
            "y": 2.5,
            "z": 3.8
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WindmillLantern",
          "shape": "Ball",
          "size": {
            "x": 1,
            "y": 1,
            "z": 1
          },
          "position": {
            "x": -3,
            "y": 5,
            "z": 3.8
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "WindmillLantern",
          "lightType": "PointLight",
          "brightness": 3,
          "range": 15,
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          }
        }
      },
      {
        "type": "addParticle",
        "params": {
          "parent": "WindmillChute",
          "texture": "rbxassetid://241876428",
          "rate": 6,
          "lifetime": {
            "min": 1,
            "max": 3
          },
          "speed": {
            "min": 0.5,
            "max": 1.5
          },
          "color": {
            "r": 230,
            "g": 220,
            "b": 200
          },
          "size": {
            "min": 0.5,
            "max": 1.5
          },
          "transparency": 0.3,
          "velocity": {
            "x": 0,
            "y": -1,
            "z": 0
          }
        }
      }
    ],
    "reply": "Tower's rebuilt \u2014 stone base, brick lower, timber up top where the fire got it. Sails are balanced but the grain chute is still empty. Haven't sourced the stones."
  },
  "garden": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "GardenPlazaFloor",
          "shape": "Block",
          "size": {
            "x": 24,
            "y": 0.5,
            "z": 24
          },
          "position": {
            "x": 0,
            "y": 0,
            "z": 0
          },
          "material": "Concrete",
          "color": {
            "r": 155,
            "g": 152,
            "b": 146
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GrassIsland0",
          "shape": "Block",
          "size": {
            "x": 4,
            "y": 0.6,
            "z": 4
          },
          "position": {
            "x": -7,
            "y": 0.4,
            "z": -7
          },
          "material": "Grass",
          "color": {
            "r": 55,
            "g": 125,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GrassIsland1",
          "shape": "Block",
          "size": {
            "x": 4,
            "y": 0.6,
            "z": 4
          },
          "position": {
            "x": 7,
            "y": 0.4,
            "z": -7
          },
          "material": "Grass",
          "color": {
            "r": 60,
            "g": 130,
            "b": 43
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GrassIsland2",
          "shape": "Block",
          "size": {
            "x": 4,
            "y": 0.6,
            "z": 4
          },
          "position": {
            "x": -7,
            "y": 0.4,
            "z": 7
          },
          "material": "Grass",
          "color": {
            "r": 65,
            "g": 135,
            "b": 46
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GrassIsland3",
          "shape": "Block",
          "size": {
            "x": 4,
            "y": 0.6,
            "z": 4
          },
          "position": {
            "x": 7,
            "y": 0.4,
            "z": 7
          },
          "material": "Grass",
          "color": {
            "r": 70,
            "g": 140,
            "b": 49
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GrassIsland4",
          "shape": "Block",
          "size": {
            "x": 4,
            "y": 0.6,
            "z": 4
          },
          "position": {
            "x": 0,
            "y": 0.4,
            "z": 0
          },
          "material": "Grass",
          "color": {
            "r": 75,
            "g": 145,
            "b": 52
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenTrellis",
          "shape": "Block",
          "size": {
            "x": 8,
            "y": 0.3,
            "z": 0.3
          },
          "position": {
            "x": -8,
            "y": 4,
            "z": -8
          },
          "material": "Metal",
          "color": {
            "r": 90,
            "g": 60,
            "b": 45
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "TrellisPostL",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": -10,
            "y": 3,
            "z": -8
          },
          "material": "Metal",
          "color": {
            "r": 85,
            "g": 58,
            "b": 42
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "TrellisPostR",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 6,
            "z": 0.4
          },
          "position": {
            "x": -6,
            "y": 3,
            "z": -8
          },
          "material": "Metal",
          "color": {
            "r": 85,
            "g": 58,
            "b": 42
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "NeonVine0",
          "shape": "Ball",
          "size": {
            "x": 0.8,
            "y": 0.8,
            "z": 0.8
          },
          "position": {
            "x": -9,
            "y": 3.5,
            "z": -7
          },
          "material": "Neon",
          "color": {
            "r": 150,
            "g": 255,
            "b": 150
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "NeonVine1",
          "shape": "Ball",
          "size": {
            "x": 0.8,
            "y": 0.8,
            "z": 0.8
          },
          "position": {
            "x": -7,
            "y": 3.5,
            "z": -7
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 220,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "NeonVine2",
          "shape": "Ball",
          "size": {
            "x": 0.8,
            "y": 0.8,
            "z": 0.8
          },
          "position": {
            "x": -8,
            "y": 3.5,
            "z": -6
          },
          "material": "Neon",
          "color": {
            "r": 200,
            "g": 150,
            "b": 255
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "FountainBowl",
          "shape": "Cylinder",
          "size": {
            "x": 6,
            "y": 1.5,
            "z": 6
          },
          "position": {
            "x": 0,
            "y": 0.8,
            "z": 0
          },
          "material": "Slate",
          "color": {
            "r": 150,
            "g": 148,
            "b": 142
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "FountainWater",
          "shape": "Cylinder",
          "size": {
            "x": 5,
            "y": 0.4,
            "z": 5
          },
          "position": {
            "x": 0,
            "y": 1.3,
            "z": 0
          },
          "material": "Glass",
          "color": {
            "r": 170,
            "g": 210,
            "b": 255
          },
          "anchored": true,
          "transparency": 0.6
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "FountainSpout",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 2,
            "z": 1
          },
          "position": {
            "x": 0,
            "y": 1.5,
            "z": 0
          },
          "material": "Concrete",
          "color": {
            "r": 140,
            "g": 138,
            "b": 132
          },
          "anchored": true
        }
      },
      {
        "type": "addParticle",
        "params": {
          "parent": "FountainSpout",
          "texture": "rbxassetid://243660364",
          "rate": 8,
          "lifetime": {
            "min": 1,
            "max": 2
          },
          "speed": {
            "min": 0.5,
            "max": 1.5
          },
          "color": {
            "r": 200,
            "g": 230,
            "b": 255
          },
          "size": {
            "min": 0.5,
            "max": 1.2
          },
          "transparency": 0.3,
          "velocity": {
            "x": 0,
            "y": 2,
            "z": 0
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenBenchSeat",
          "shape": "Block",
          "size": {
            "x": 5,
            "y": 0.4,
            "z": 1.5
          },
          "position": {
            "x": 7,
            "y": 1.5,
            "z": 7
          },
          "material": "Wood",
          "color": {
            "r": 110,
            "g": 75,
            "b": 45
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenBenchLegL",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 1.2,
            "z": 0.4
          },
          "position": {
            "x": 5,
            "y": 0.8,
            "z": 7
          },
          "material": "Wood",
          "color": {
            "r": 95,
            "g": 65,
            "b": 38
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenBenchLegR",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 1.2,
            "z": 0.4
          },
          "position": {
            "x": 9,
            "y": 0.8,
            "z": 7
          },
          "material": "Wood",
          "color": {
            "r": 95,
            "g": 65,
            "b": 38
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenPath0",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 0.2,
            "z": 2.5
          },
          "position": {
            "x": 0.0,
            "y": 0.7,
            "z": -12.0
          },
          "material": "Slate",
          "color": {
            "r": 160,
            "g": 155,
            "b": 148
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenPath1",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 0.2,
            "z": 2.5
          },
          "position": {
            "x": 3.0,
            "y": 0.7,
            "z": -6.0
          },
          "material": "Slate",
          "color": {
            "r": 160,
            "g": 155,
            "b": 148
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenPath2",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 0.2,
            "z": 2.5
          },
          "position": {
            "x": -3.0,
            "y": 0.7,
            "z": 0.0
          },
          "material": "Slate",
          "color": {
            "r": 160,
            "g": 155,
            "b": 148
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenPath3",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 0.2,
            "z": 2.5
          },
          "position": {
            "x": 1.5,
            "y": 0.7,
            "z": 6.0
          },
          "material": "Slate",
          "color": {
            "r": 160,
            "g": 155,
            "b": 148
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "GardenPath4",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 0.2,
            "z": 2.5
          },
          "position": {
            "x": 0.0,
            "y": 0.7,
            "z": 12.0
          },
          "material": "Slate",
          "color": {
            "r": 160,
            "g": 155,
            "b": 148
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "FireflyCore",
          "shape": "Ball",
          "size": {
            "x": 0.4,
            "y": 0.4,
            "z": 0.4
          },
          "position": {
            "x": 0,
            "y": 4,
            "z": 0
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 255,
            "b": 150
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "FireflyCore",
          "lightType": "PointLight",
          "brightness": 2,
          "range": 12,
          "color": {
            "r": 255,
            "g": 255,
            "b": 150
          }
        }
      },
      {
        "type": "addParticle",
        "params": {
          "parent": "FireflyCore",
          "texture": "rbxassetid://258128463",
          "rate": 6,
          "lifetime": {
            "min": 2,
            "max": 4
          },
          "speed": {
            "min": 0.3,
            "max": 1
          },
          "color": {
            "r": 255,
            "g": 255,
            "b": 150
          },
          "size": {
            "min": 0.2,
            "max": 0.6
          },
          "transparency": 0.2,
          "velocity": {
            "x": 0,
            "y": 0,
            "z": 0
          }
        }
      }
    ],
    "reply": "Plaza's reclaimed, beds are in, fountain's weeping. Trellis is up but I didn't plant anything on it. That's your call."
  },
  "dock": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "DockDeck",
          "shape": "Block",
          "size": {
            "x": 6,
            "y": 1,
            "z": 20
          },
          "position": {
            "x": 0,
            "y": 1,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 120,
            "g": 80,
            "b": 45
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "DockPile0",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 6,
            "z": 1
          },
          "position": {
            "x": -2,
            "y": -2,
            "z": -8
          },
          "material": "Wood",
          "color": {
            "r": 85,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "DockPile1",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 6,
            "z": 1
          },
          "position": {
            "x": 2,
            "y": -2,
            "z": -8
          },
          "material": "Wood",
          "color": {
            "r": 85,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "DockPile2",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 6,
            "z": 1
          },
          "position": {
            "x": -2,
            "y": -2,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 85,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "DockPile3",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 6,
            "z": 1
          },
          "position": {
            "x": 2,
            "y": -2,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 85,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "DockPile4",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 6,
            "z": 1
          },
          "position": {
            "x": -2,
            "y": -2,
            "z": 8
          },
          "material": "Wood",
          "color": {
            "r": 85,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "DockPile5",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 6,
            "z": 1
          },
          "position": {
            "x": 2,
            "y": -2,
            "z": 8
          },
          "material": "Wood",
          "color": {
            "r": 85,
            "g": 55,
            "b": 30
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WaterSurface",
          "shape": "Block",
          "size": {
            "x": 10,
            "y": 0.3,
            "z": 24
          },
          "position": {
            "x": 0,
            "y": -1,
            "z": 0
          },
          "material": "Glass",
          "color": {
            "r": 170,
            "g": 210,
            "b": 255
          },
          "anchored": true,
          "transparency": 0.7,
          "reflectance": 0.1
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "MooringPost1",
          "shape": "Cylinder",
          "size": {
            "x": 1.2,
            "y": 4,
            "z": 1.2
          },
          "position": {
            "x": -3,
            "y": 3,
            "z": 9
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 65,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "MooringPost2",
          "shape": "Cylinder",
          "size": {
            "x": 1.2,
            "y": 4,
            "z": 1.2
          },
          "position": {
            "x": 3,
            "y": 3,
            "z": 9
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 65,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "MooringRope1",
          "shape": "Block",
          "size": {
            "x": 6,
            "y": 0.3,
            "z": 0.3
          },
          "position": {
            "x": 0,
            "y": 2.5,
            "z": 9
          },
          "material": "Wood",
          "color": {
            "r": 140,
            "g": 110,
            "b": 70
          },
          "anchored": true,
          "transparency": 0.1
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CargoCrate1",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 3,
            "z": 3
          },
          "position": {
            "x": -1.5,
            "y": 3,
            "z": -8
          },
          "material": "Wood",
          "color": {
            "r": 110,
            "g": 75,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CargoCrate2",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 3,
            "z": 3
          },
          "position": {
            "x": 1.5,
            "y": 3,
            "z": -8
          },
          "material": "Wood",
          "color": {
            "r": 120,
            "g": 85,
            "b": 48
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CargoCrate3",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 3,
            "z": 3
          },
          "position": {
            "x": 0,
            "y": 6,
            "z": -8
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 68,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LanternPost1",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 7,
            "z": 0.4
          },
          "position": {
            "x": -2.5,
            "y": 4.5,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 60,
            "g": 55,
            "b": 50
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LanternHead1",
          "shape": "Ball",
          "size": {
            "x": 1.2,
            "y": 1.2,
            "z": 1.2
          },
          "position": {
            "x": -2.5,
            "y": 8,
            "z": 0
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LanternPost2",
          "shape": "Cylinder",
          "size": {
            "x": 0.4,
            "y": 7,
            "z": 0.4
          },
          "position": {
            "x": 2.5,
            "y": 4.5,
            "z": 8
          },
          "material": "Metal",
          "color": {
            "r": 60,
            "g": 55,
            "b": 50
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LanternHead2",
          "shape": "Ball",
          "size": {
            "x": 1.2,
            "y": 1.2,
            "z": 1.2
          },
          "position": {
            "x": 2.5,
            "y": 8,
            "z": 8
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "LanternHead1",
          "lightType": "PointLight",
          "brightness": 4,
          "range": 18,
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "SeagullPerch",
          "shape": "Cylinder",
          "size": {
            "x": 0.5,
            "y": 5,
            "z": 0.5
          },
          "position": {
            "x": -3,
            "y": 3.5,
            "z": -9
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 60,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "SeagullPerchCap",
          "shape": "Ball",
          "size": {
            "x": 1,
            "y": 0.5,
            "z": 1
          },
          "position": {
            "x": -3,
            "y": 6,
            "z": -9
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 70,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "addParticle",
        "params": {
          "parent": "WaterSurface",
          "texture": "rbxassetid://258128463",
          "rate": 8,
          "lifetime": {
            "min": 2,
            "max": 4
          },
          "speed": {
            "min": 0.3,
            "max": 1
          },
          "color": {
            "r": 200,
            "g": 210,
            "b": 220
          },
          "size": {
            "min": 1.5,
            "max": 3
          },
          "transparency": 0.4,
          "velocity": {
            "x": 0,
            "y": 0.5,
            "z": 0.3
          }
        }
      }
    ],
    "reply": "Piles are driven, planks are down, mooring posts are set. Didn't rig the bumpers \u2014 different boats need different ones."
  },
  "lighthouse": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "LighthouseFoundation",
          "shape": "Block",
          "size": {
            "x": 12,
            "y": 3,
            "z": 12
          },
          "position": {
            "x": 0,
            "y": 1.5,
            "z": 0
          },
          "material": "Basalt",
          "color": {
            "r": 90,
            "g": 88,
            "b": 84
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LighthouseBaseTower",
          "shape": "Cylinder",
          "size": {
            "x": 9,
            "y": 12,
            "z": 9
          },
          "position": {
            "x": 0,
            "y": 9,
            "z": 0
          },
          "material": "Cobblestone",
          "color": {
            "r": 125,
            "g": 120,
            "b": 113
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LighthouseMidTower",
          "shape": "Cylinder",
          "size": {
            "x": 7,
            "y": 12,
            "z": 7
          },
          "position": {
            "x": 0,
            "y": 21,
            "z": 0
          },
          "material": "Concrete",
          "color": {
            "r": 200,
            "g": 200,
            "b": 195
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LighthouseGallery",
          "shape": "Cylinder",
          "size": {
            "x": 9,
            "y": 1,
            "z": 9
          },
          "position": {
            "x": 0,
            "y": 28,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 100,
            "g": 60,
            "b": 45
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LighthouseLanternRoom",
          "shape": "Block",
          "size": {
            "x": 5,
            "y": 5,
            "z": 5
          },
          "position": {
            "x": 0,
            "y": 31,
            "z": 0
          },
          "material": "Glass",
          "color": {
            "r": 180,
            "g": 210,
            "b": 180
          },
          "anchored": true,
          "transparency": 0.4,
          "reflectance": 0.2
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LighthouseBeacon",
          "shape": "Ball",
          "size": {
            "x": 2.5,
            "y": 2.5,
            "z": 2.5
          },
          "position": {
            "x": 0,
            "y": 31,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 180,
            "g": 150,
            "b": 80
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "LighthouseBeacon",
          "lightType": "SpotLight",
          "brightness": 12,
          "range": 250,
          "color": {
            "r": 255,
            "g": 245,
            "b": 180
          },
          "angle": 25
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "KeeperCottage",
          "shape": "Block",
          "size": {
            "x": 9,
            "y": 6,
            "z": 7
          },
          "position": {
            "x": 9,
            "y": 3,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 130,
            "g": 95,
            "b": 60
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "KeeperRoof",
          "shape": "Wedge",
          "size": {
            "x": 10,
            "y": 3,
            "z": 7
          },
          "position": {
            "x": 9,
            "y": 7.5,
            "z": -2
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 70,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "KeeperWindow",
          "shape": "Block",
          "size": {
            "x": 0.5,
            "y": 1.5,
            "z": 1.5
          },
          "position": {
            "x": 13.2,
            "y": 3.5,
            "z": 0
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 120
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "KeeperWindow",
          "lightType": "PointLight",
          "brightness": 3,
          "range": 15,
          "color": {
            "r": 255,
            "g": 200,
            "b": 120
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "BoatWinch",
          "shape": "Cylinder",
          "size": {
            "x": 2,
            "y": 2,
            "z": 2
          },
          "position": {
            "x": -6,
            "y": 2,
            "z": 5
          },
          "material": "Metal",
          "color": {
            "r": 70,
            "g": 68,
            "b": 65
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LighthouseRock1",
          "shape": "Ball",
          "size": {
            "x": 4,
            "y": 3,
            "z": 4
          },
          "position": {
            "x": 5,
            "y": 1,
            "z": 5
          },
          "material": "Slate",
          "color": {
            "r": 115,
            "g": 110,
            "b": 105
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "LighthouseRock2",
          "shape": "Ball",
          "size": {
            "x": 3,
            "y": 2.5,
            "z": 3
          },
          "position": {
            "x": -5,
            "y": 0.5,
            "z": -4
          },
          "material": "Cobblestone",
          "color": {
            "r": 130,
            "g": 125,
            "b": 118
          },
          "anchored": true
        }
      },
      {
        "type": "addParticle",
        "params": {
          "parent": "LighthouseRock1",
          "texture": "rbxassetid://258128463",
          "rate": 8,
          "lifetime": {
            "min": 3,
            "max": 6
          },
          "speed": {
            "min": 0.5,
            "max": 1.5
          },
          "color": {
            "r": 200,
            "g": 210,
            "b": 220
          },
          "size": {
            "min": 2,
            "max": 4
          },
          "transparency": 0.4,
          "velocity": {
            "x": 0.5,
            "y": 0,
            "z": 0.5
          }
        }
      }
    ],
    "reply": "Tower's up, beacon's lit, keeper's cottage is sealed in. Boat winch is mounted but I didn't run the cable. Didn't want to guess the length."
  },
  "cottage": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "CottageFoundation",
          "shape": "Block",
          "size": {
            "x": 14,
            "y": 1.5,
            "z": 12
          },
          "position": {
            "x": 0,
            "y": 0.75,
            "z": 0
          },
          "material": "Cobblestone",
          "color": {
            "r": 132,
            "g": 128,
            "b": 120
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageFrontStep",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 0.5,
            "z": 1.5
          },
          "position": {
            "x": 0,
            "y": 0.25,
            "z": 6.5
          },
          "material": "Slate",
          "color": {
            "r": 125,
            "g": 120,
            "b": 113
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWallN",
          "shape": "Block",
          "size": {
            "x": 12,
            "y": 7,
            "z": 0.5
          },
          "position": {
            "x": 0,
            "y": 5,
            "z": -6
          },
          "material": "Brick",
          "color": {
            "r": 155,
            "g": 125,
            "b": 95
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWallS",
          "shape": "Block",
          "size": {
            "x": 12,
            "y": 7,
            "z": 0.5
          },
          "position": {
            "x": 0,
            "y": 5,
            "z": 6
          },
          "material": "Brick",
          "color": {
            "r": 150,
            "g": 120,
            "b": 90
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWallW",
          "shape": "Block",
          "size": {
            "x": 0.5,
            "y": 7,
            "z": 12
          },
          "position": {
            "x": -6,
            "y": 5,
            "z": 0
          },
          "material": "Brick",
          "color": {
            "r": 148,
            "g": 118,
            "b": 88
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWallE",
          "shape": "Block",
          "size": {
            "x": 0.5,
            "y": 7,
            "z": 12
          },
          "position": {
            "x": 6,
            "y": 5,
            "z": 0
          },
          "material": "Brick",
          "color": {
            "r": 152,
            "g": 122,
            "b": 92
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottagePatch",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 4,
            "z": 0.55
          },
          "position": {
            "x": -3,
            "y": 4,
            "z": 6.02
          },
          "material": "Brick",
          "color": {
            "r": 135,
            "g": 108,
            "b": 80
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWindowFrame0",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 3,
            "z": 0.6
          },
          "position": {
            "x": -4,
            "y": 5,
            "z": -5.8
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 58,
            "b": 32
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWindowGlass0",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 2.5,
            "z": 0.3
          },
          "position": {
            "x": -4,
            "y": 5,
            "z": -5.7
          },
          "material": "Glass",
          "color": {
            "r": 190,
            "g": 215,
            "b": 255
          },
          "anchored": true,
          "transparency": 0.5,
          "reflectance": 0.15
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWindowGlow0",
          "shape": "Block",
          "size": {
            "x": 2,
            "y": 2,
            "z": 0.2
          },
          "position": {
            "x": -4,
            "y": 5,
            "z": -5.6
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 120
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "CottageWindowGlow0",
          "lightType": "PointLight",
          "brightness": 3,
          "range": 14,
          "color": {
            "r": 255,
            "g": 200,
            "b": 120
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWindowFrame1",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 3,
            "z": 0.6
          },
          "position": {
            "x": 4,
            "y": 5,
            "z": -5.8
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 58,
            "b": 32
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWindowGlass1",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 2.5,
            "z": 0.3
          },
          "position": {
            "x": 4,
            "y": 5,
            "z": -5.7
          },
          "material": "Glass",
          "color": {
            "r": 190,
            "g": 215,
            "b": 255
          },
          "anchored": true,
          "transparency": 0.5,
          "reflectance": 0.15
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageWindowGlow1",
          "shape": "Block",
          "size": {
            "x": 2,
            "y": 2,
            "z": 0.2
          },
          "position": {
            "x": 4,
            "y": 5,
            "z": -5.6
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 120
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "CottageWindowGlow1",
          "lightType": "PointLight",
          "brightness": 3,
          "range": 14,
          "color": {
            "r": 255,
            "g": 200,
            "b": 120
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageFlowerBox",
          "shape": "Block",
          "size": {
            "x": 3.5,
            "y": 0.5,
            "z": 0.6
          },
          "position": {
            "x": -4,
            "y": 3,
            "z": -6.3
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 65,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageFlower0",
          "shape": "Ball",
          "size": {
            "x": 0.4,
            "y": 0.4,
            "z": 0.4
          },
          "position": {
            "x": -5.2,
            "y": 3.4,
            "z": -6.3
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 100,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageFlower1",
          "shape": "Ball",
          "size": {
            "x": 0.4,
            "y": 0.4,
            "z": 0.4
          },
          "position": {
            "x": -4.5,
            "y": 3.4,
            "z": -6.3
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 220,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageFlower2",
          "shape": "Ball",
          "size": {
            "x": 0.4,
            "y": 0.4,
            "z": 0.4
          },
          "position": {
            "x": -3.8,
            "y": 3.4,
            "z": -6.3
          },
          "material": "Neon",
          "color": {
            "r": 200,
            "g": 100,
            "b": 255
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageFlower3",
          "shape": "Ball",
          "size": {
            "x": 0.4,
            "y": 0.4,
            "z": 0.4
          },
          "position": {
            "x": -3.0,
            "y": 3.4,
            "z": -6.3
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 150,
            "b": 200
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageRoofN",
          "shape": "Wedge",
          "size": {
            "x": 14,
            "y": 4,
            "z": 7
          },
          "position": {
            "x": 0,
            "y": 10.5,
            "z": -3
          },
          "material": "WoodPlanks",
          "color": {
            "r": 85,
            "g": 50,
            "b": 28
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageRoofS",
          "shape": "Wedge",
          "size": {
            "x": 14,
            "y": 4,
            "z": 7
          },
          "position": {
            "x": 0,
            "y": 10.5,
            "z": 3
          },
          "material": "WoodPlanks",
          "color": {
            "r": 80,
            "g": 47,
            "b": 25
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageChimneyBase",
          "shape": "Block",
          "size": {
            "x": 2,
            "y": 5,
            "z": 2
          },
          "position": {
            "x": 4,
            "y": 10,
            "z": -3
          },
          "material": "Brick",
          "color": {
            "r": 110,
            "g": 85,
            "b": 72
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageChimneyTop",
          "shape": "Block",
          "size": {
            "x": 2,
            "y": 2,
            "z": 2
          },
          "position": {
            "x": 4,
            "y": 13.5,
            "z": -3
          },
          "material": "Brick",
          "color": {
            "r": 80,
            "g": 60,
            "b": 52
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageChimneyCap",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 0.5,
            "z": 2.5
          },
          "position": {
            "x": 4,
            "y": 14.8,
            "z": -3
          },
          "material": "Slate",
          "color": {
            "r": 100,
            "g": 95,
            "b": 88
          },
          "anchored": true
        }
      },
      {
        "type": "addParticle",
        "params": {
          "parent": "CottageChimneyTop",
          "texture": "rbxassetid://241876428",
          "rate": 5,
          "lifetime": {
            "min": 2,
            "max": 4
          },
          "speed": {
            "min": 0.5,
            "max": 1.5
          },
          "color": {
            "r": 180,
            "g": 180,
            "b": 180
          },
          "size": {
            "min": 0.8,
            "max": 2
          },
          "transparency": 0.3,
          "velocity": {
            "x": 0,
            "y": 2,
            "z": 0
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageDoor",
          "shape": "Block",
          "size": {
            "x": 2.5,
            "y": 4.5,
            "z": 0.4
          },
          "position": {
            "x": 0,
            "y": 3,
            "z": 6.2
          },
          "material": "WoodPlanks",
          "color": {
            "r": 95,
            "g": 60,
            "b": 32
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageDoorHingeL",
          "shape": "Cylinder",
          "size": {
            "x": 0.2,
            "y": 3,
            "z": 0.2
          },
          "position": {
            "x": -1,
            "y": 4,
            "z": 6.3
          },
          "material": "Metal",
          "color": {
            "r": 70,
            "g": 65,
            "b": 60
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageDoorHingeR",
          "shape": "Cylinder",
          "size": {
            "x": 0.2,
            "y": 3,
            "z": 0.2
          },
          "position": {
            "x": 1,
            "y": 4,
            "z": 6.3
          },
          "material": "Metal",
          "color": {
            "r": 70,
            "g": 65,
            "b": 60
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "CottageDoorKnocker",
          "shape": "Ball",
          "size": {
            "x": 0.5,
            "y": 0.5,
            "z": 0.5
          },
          "position": {
            "x": 0,
            "y": 4.5,
            "z": 6.5
          },
          "material": "Metal",
          "color": {
            "r": 60,
            "g": 55,
            "b": 50
          },
          "anchored": true
        }
      }
    ],
    "reply": "Foundation's cobble, walls are warm brick, roof's pitched and the chimney's smoking. Flower box is up but I didn't plant anything. Didn't want to pick the wrong seeds."
  },
  "well": {
    "commands": [
      {
        "type": "createPart",
        "params": {
          "name": "WellBase",
          "shape": "Block",
          "size": {
            "x": 8,
            "y": 0.5,
            "z": 8
          },
          "position": {
            "x": 0,
            "y": 0.25,
            "z": 0
          },
          "material": "Ground",
          "color": {
            "r": 110,
            "g": 100,
            "b": 85
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellPaving",
          "shape": "Block",
          "size": {
            "x": 7,
            "y": 0.4,
            "z": 7
          },
          "position": {
            "x": 0,
            "y": 0.5,
            "z": 0
          },
          "material": "Slate",
          "color": {
            "r": 140,
            "g": 135,
            "b": 128
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellWornStep",
          "shape": "Block",
          "size": {
            "x": 3,
            "y": 0.3,
            "z": 1.5
          },
          "position": {
            "x": 0,
            "y": 0.65,
            "z": 3.5
          },
          "material": "Slate",
          "color": {
            "r": 125,
            "g": 118,
            "b": 108
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellRingBase",
          "shape": "Cylinder",
          "size": {
            "x": 5,
            "y": 1.5,
            "z": 5
          },
          "position": {
            "x": 0,
            "y": 1.5,
            "z": 0
          },
          "material": "Cobblestone",
          "color": {
            "r": 130,
            "g": 125,
            "b": 118
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellRingMid",
          "shape": "Cylinder",
          "size": {
            "x": 4.5,
            "y": 1,
            "z": 4.5
          },
          "position": {
            "x": 0,
            "y": 2.75,
            "z": 0
          },
          "material": "Cobblestone",
          "color": {
            "r": 125,
            "g": 120,
            "b": 113
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellRingTop",
          "shape": "Cylinder",
          "size": {
            "x": 5,
            "y": 0.8,
            "z": 5
          },
          "position": {
            "x": 0,
            "y": 3.65,
            "z": 0
          },
          "material": "Stone",
          "color": {
            "r": 140,
            "g": 135,
            "b": 128
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellWater",
          "shape": "Cylinder",
          "size": {
            "x": 3.5,
            "y": 0.3,
            "z": 3.5
          },
          "position": {
            "x": 0,
            "y": 1.5,
            "z": 0
          },
          "material": "Glass",
          "color": {
            "r": 100,
            "g": 150,
            "b": 200
          },
          "anchored": true,
          "transparency": 0.6,
          "reflectance": 0.3
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellPostL",
          "shape": "Cylinder",
          "size": {
            "x": 0.6,
            "y": 6,
            "z": 0.6
          },
          "position": {
            "x": -2,
            "y": 5,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 95,
            "g": 62,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellPostR",
          "shape": "Cylinder",
          "size": {
            "x": 0.6,
            "y": 6,
            "z": 0.6
          },
          "position": {
            "x": 2,
            "y": 5,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 95,
            "g": 62,
            "b": 35
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellCrossBeam",
          "shape": "Block",
          "size": {
            "x": 5,
            "y": 0.8,
            "z": 0.8
          },
          "position": {
            "x": 0,
            "y": 8,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 100,
            "g": 68,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellRoofL",
          "shape": "Wedge",
          "size": {
            "x": 6,
            "y": 2.5,
            "z": 3
          },
          "position": {
            "x": 0,
            "y": 10,
            "z": -1.5
          },
          "material": "WoodPlanks",
          "color": {
            "r": 85,
            "g": 50,
            "b": 25
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellRoofR",
          "shape": "Wedge",
          "size": {
            "x": 6,
            "y": 2.5,
            "z": 3
          },
          "position": {
            "x": 0,
            "y": 10,
            "z": 1.5
          },
          "material": "WoodPlanks",
          "color": {
            "r": 80,
            "g": 47,
            "b": 22
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellBucketArm",
          "shape": "Block",
          "size": {
            "x": 0.4,
            "y": 0.4,
            "z": 4
          },
          "position": {
            "x": 0,
            "y": 7.5,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 90,
            "g": 58,
            "b": 32
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellCrank",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 1,
            "z": 1
          },
          "position": {
            "x": 2.5,
            "y": 7,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 85,
            "g": 80,
            "b": 75
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellCrankHandle",
          "shape": "Block",
          "size": {
            "x": 1.5,
            "y": 0.3,
            "z": 0.3
          },
          "position": {
            "x": 3.5,
            "y": 7,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 100,
            "g": 70,
            "b": 40
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellRope",
          "shape": "Cylinder",
          "size": {
            "x": 0.2,
            "y": 4,
            "z": 0.2
          },
          "position": {
            "x": 0,
            "y": 5.5,
            "z": 0
          },
          "material": "Wood",
          "color": {
            "r": 130,
            "g": 100,
            "b": 65
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellBucket",
          "shape": "Cylinder",
          "size": {
            "x": 1,
            "y": 1.2,
            "z": 1
          },
          "position": {
            "x": 0,
            "y": 3.5,
            "z": 0
          },
          "material": "WoodPlanks",
          "color": {
            "r": 105,
            "g": 72,
            "b": 42
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellBucketBand",
          "shape": "Cylinder",
          "size": {
            "x": 1.1,
            "y": 0.2,
            "z": 1.1
          },
          "position": {
            "x": 0,
            "y": 3.8,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 75,
            "g": 70,
            "b": 65
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellLanternHook",
          "shape": "Block",
          "size": {
            "x": 1,
            "y": 0.3,
            "z": 0.3
          },
          "position": {
            "x": -2.5,
            "y": 7,
            "z": 0
          },
          "material": "Metal",
          "color": {
            "r": 65,
            "g": 60,
            "b": 55
          },
          "anchored": true
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellLantern",
          "shape": "Ball",
          "size": {
            "x": 0.8,
            "y": 0.8,
            "z": 0.8
          },
          "position": {
            "x": -2.8,
            "y": 6.5,
            "z": 0
          },
          "material": "Neon",
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          },
          "anchored": true
        }
      },
      {
        "type": "addLight",
        "params": {
          "parent": "WellLantern",
          "lightType": "PointLight",
          "brightness": 3,
          "range": 12,
          "color": {
            "r": 255,
            "g": 200,
            "b": 100
          }
        }
      },
      {
        "type": "createPart",
        "params": {
          "name": "WellMoss",
          "shape": "Block",
          "size": {
            "x": 2,
            "y": 1,
            "z": 0.3
          },
          "position": {
            "x": 0,
            "y": 1.8,
            "z": -2.3
          },
          "material": "Grass",
          "color": {
            "r": 45,
            "g": 100,
            "b": 35
          },
          "anchored": true
        }
      }
    ],
    "reply": "Stone ring's laid, water's in, bucket's on the rope. Roof is up but I left the crank handle loose. Tighten it when you've got a wrench."
  }
};
