# Resource banks radar by Smjert/Spasitjel
# Version 0.0.1
#
# This is a simple resource banks radar, which will show you the resource banks boundaries and permit you to save spots where you can gather resources from the optimal amount of them.
# Walkable tiles that have at least one reachable resource bank tile, will show the number of unique banks that are reachable from that spot.
#
# Place yourself on such a tile and hit S on the keyboard; this will save the position and map you are in on a file, plus the first reachable tile of each banks. The spots are always appended to the file.
# The current tile will be marked with a M and all the resource tiles in the reachable banks will be marked with an X to signify that they will be consumed if gathering from that spot.
# Only after moving the number of reachable banks from the various tiles will be updated.
#
# Finally, the radar also supports showing which specific banks are reached from each tile; just click on a tile with a number and the radar will highlight the reachable banks.
# Moving will reset the highghtlight status.
#
# Currently only Mining resource banks are supported.
#
# The marked spots file format currently has one line per marked spot, and each line is:
# <Marked Spot X>,<Marked Spot Y>,<Marked Spot Map Index>|<Resource Tile1 X>,<Resource Tile1 Y>|<Resource Tile2 X>,<Resource Tile2 Y>|[...]
#
# The Map Index is the Player.Map value.

import clr
import os
from threading import Lock
from ctypes import windll

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from System.Windows.Forms import Form, Application, FormBorderStyle, Padding, MouseButtons, OpenFileDialog
from System.Drawing import Point, Size, Font, Pen, Color, Rectangle, SolidBrush, FontFamily, StringFormat, StringAlignment
from System import Char, String, EventHandler, Array
from System.Collections.Generic import List
from System.Threading import Thread, ParameterizedThreadStart
from System import Action
from System.Windows.Forms.SystemInformation import VerticalScrollBarWidth, HorizontalScrollBarHeight

# SETTINGS
#
# Color settings; you can find the premade ones here: https://learn.microsoft.com/en-us/dotnet/api/system.drawing.color?view=net-8.0
# or you can insert an ARGB value.
gridLinesColor = Color.Black
bankBoundariesColor = Color.Red
normalTileColor = Color.Green
rockTileColor = Color.Gray
resourceTileColor = Color.DarkGray
playerTileColor = Color.Pink
bankHighlightColor = Color.FromArgb(128, 255, 255, 0) # Semi-transparent Yellow
tileNormalTextColor = Color.Black
consumedTileTextColor = Color.Red
markedTileTextColor = Color.Red

# Size in pixels of each tile, excluding the grid lines
tilePxSize = 22
# The radar is always a square; this is the distance from the player position to the furthest tile.
# (The formula then multiplies this by 2 and adds 1 for the center tile, where the player is)
visibleRange = 16
# How often to refresh the map, when moving. 1 tick = 100ms.
mapUpdateTicks = 5

# Relative path to the file where the marked spots are saved and loaded.
#
# Note that Razor Enhanced limits the accessible paths
# to the ones that are relative to where the Client was executed.
# If you are using the ClassicUOLauncher, from the folder where the ClassicUO client executable is,
# and down is accessible for writing (be careful to not name this equal to some file in your client folder!).
# If you are not using the ClassicUOLauncher and starting the Client manually by double clicking,
# then the root should be again where the executable is.
# If you are executing it through a .bat file, then the root folder is where the .bat file is located,
# unless you changed directory in the batch file before executing.
markedSpotsFilePath = "mining-spots.txt"

# Keyboard key to use to save a spot
saveASpotKey = 'S'

###################################################################################################
# The majority of you don't need to modify this, but if you find a tile that you would like to add
# or remove from the list of resource tiles, then this can be done here.
#
# The current selection is made so that only tiles that should be always reachable or visible are in the list.
# There may be some tiles that in some occasions are considered resource tiles and reachable,
# but in the majority of cases due to where they are used in the map and for the ServUO line of sight calculations,
# they aren't.
###################################################################################################

mountainResourceTiles = [0xDC, 0xDD, 0xDE, 0xDF, 0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6,
                         0xE7, 0xEC, 0xED, 0xEE, 0xEF, 0xF0, 0xF1, 0xF2, 0xF3, 0xF4,
                         0xF5, 0xF6, 0xF7, 0xFC, 0xFD, 0xFE, 0xFF, 0x100, 0x101, 0x102,
                         0x103, 0x104, 0x105, 0x106, 0x107, 0x10C, 0x10D, 0x10E, 0x10F, 0x110,
                         0x111, 0x112, 0x113, 0x114, 0x115, 0x116, 0x117, 0x11E, 0x11F, 0x120,
                         0x121, 0x122, 0x123, 0x124, 0x125, 0x126, 0x127, 0x128, 0x129, 0x141,
                         0x142, 0x143, 0x144, 0x1D3, 0x1D4, 0x1D5, 0x1D6, 0x1D7, 0x1D8, 0x1D9,
                         0x1DA, 0x1DC, 0x1DD, 0x1DE, 0x1DF, 0x1E0, 0x1E1, 0x1E2, 0x1E3, 0x1E4,
                         0x1E5, 0x1E6, 0x1E7, 0x1EC, 0x1ED, 0x1EE, 0x1EF, 0x231, 0x232, 0x233, 0x234, 0x235,
                         0x236, 0x237, 0x238, 0x239, 0x23A, 0x23B, 0x23C, 0x23D, 0x23E, 0x23F,
                         0x240, 0x241, 0x242, 0x243, 0x6CD, 0x6CE, 0x6CF, 0x6D0, 0x6D1, 0x6D2,
                         0x6D3, 0x6D4, 0x6D5, 0x6D6, 0x6D7, 0x6D8, 0x6D9, 0x709, 0x70A, 0x70B,
                         0x70C, 0x70D, 0x70E, 0x70F, 0x710, 0x711, 0x713, 0x714, 0x715, 0x716,
                         0x717, 0x718, 0x719, 0x71A, 0x71B, 0x71C, 0x727, 0x728, 0x729, 0x72A,
                         0x72B, 0x72C, 0x72D, 0x72E, 0x72F, 0x730,
                         0x731, 0x732, 0x733, 0x734, 0x735, 0x736, 0x737, 0x738, 0x739, 0x73A,
                         0x7BD, 0x7BE, 0x7BF, 0x7C0, 0x7C1, 0x7C2, 0x7C3, 0x7C4, 0x7C5, 0x7C6, 0x7C7, 0x7C8,
                         0x7C9, 0x7CA, 0x7CB, 0x7CC, 0x7CD, 0x7CE, 0x7CF, 0x7D0]

caveResourceTiles = [0x245, 0x246, 0x247, 0x248, 0x249, 0x24A,
                     0x24B, 0x24C, 0x24D, 0x24E, 0x24F, 0x250, 0x251, 0x252, 0x253, 0x254,
                     0x255, 0x256, 0x257, 0x258, 0x259, 0x262, 0x263, 0x264, 0x265]

# These are not resource tiles, but we still want to draw them differently from normal tiles
# Normally part of the mountains
rockTiles = [0x21F, 0x220, 0x221, 0x222, 0x223, 0x224, 0x225, 0x226, 0x227, 0x228,
             0x229, 0x22A, 0x22B, 0x22C, 0x22D, 0x22E, 0x22F, 0x230, 0x3F2, 0x6DA,
             0x6DB, 0x6DC, 0x6DD, 0x6EB, 0x6EC, 0x6ED, 0x6EE, 0x6EF, 0x6F0, 0x6F1,
             0x6F2, 0x6F3, 0x6F4, 0x6F5, 0x6F6, 0x6F7, 0x6F8, 0x6F9, 0x6FA, 0x6FB,
             0x6FC, 0x6FD, 0x6FE, 0x71D, 0x71E, 0x71F, 0x720, 0x73B, 0x73C, 0x73D,
             0x73E, 0x745, 0x746, 0x747, 0x748, 0x749, 0x74A, 0x74B, 0x74C, 0x74D,
             0x74E, 0x74F, 0x750, 0x751, 0x752, 0x753, 0x754, 0x755, 0x756, 0x757,
             0x758, 0x759, 0x75A, 0x75B, 0x75C, 0x7D1, 0x7D2, 0x7D3, 0x7D4, 0x7EC,
             0x7ED, 0x7EE, 0x7EF, 0x7F0, 0x7F1, 0x834, 0x835, 0x836, 0x837, 0x838,
             0x839, 0x453B, 0x453C, 0x453D, 0x453E, 0x453F, 0x4540, 0x4541, 0x4542,
             0x4543, 0x4544, 0x4545, 0x4546, 0x4547, 0x4548, 0x4549, 0x454A, 0x454B,
             0x454C, 0x454D, 0x454E, 0x454F]

###################################################################################################
# DO NOT MODIFY BELOW HERE (Unless you know what you're doing)
###################################################################################################

# Note, due to specifics on how a line is drawn, and which coordinates are used,
# that I have to better look into, increasing this value causes all the drawing offsets to be wrong.
# Keep it at 1 for now.
gridLinesWidth = 1

gridPen = Pen(gridLinesColor, gridLinesWidth)
bankBoundariesPen = Pen(bankBoundariesColor, gridLinesWidth)
normalTileBrush = SolidBrush(normalTileColor)
rockTileBrush = SolidBrush(rockTileColor)
resourceTileBrush = SolidBrush(resourceTileColor)
playerTileBrush = SolidBrush(playerTileColor)
bankHighlightBrush = SolidBrush(bankHighlightColor)
tileNormalTextBrush = SolidBrush(tileNormalTextColor)
consumedTileTextBrush = SolidBrush(consumedTileTextColor)
markedTileTextBrush = SolidBrush(markedTileTextColor)

gridLinesDistance = tilePxSize + gridLinesWidth
visibleTiles = (visibleRange * 2) + 1
centerTile = int(visibleTiles / 2)
scanRange = int(visibleTiles / 2) - 2

# This is a single value since ore banks are squares, but will need to be split in X and Y for lumberjacking and maybe others
bankSize = 8
# This is the number of maps present in a OSI like shards. Used to store map specific tile state.
numberOfMaps = 6

mineableTiles = []
mineableTiles.extend(mountainResourceTiles)
mineableTiles.extend(caveResourceTiles)

class TileInfo():
    def __init__(self, color, amount, bankX, bankY, blocked):
        self.Color = color
        self.Amount = amount
        self.BankX = bankX
        self.BankY = bankY
        self.Blocked = blocked
        self.MineableTiles = []

class MapState():
    def __init__(self, size):
        self.GridRows = [0] * (size + 1)
        self.GridCols = [0] * (size + 1)
        self.TilesInfo = Array.CreateInstance(TileInfo, size, size)
        for row in range(size):
            for col in range(size):
                self.TilesInfo[row, col] = TileInfo(0, 0, 0, 0, False)
                
        self.Size = size
        self.MarkedSpots = [[] for _ in range(numberOfMaps)]
        self.ConsumedBanks = [[] for _ in range(numberOfMaps)]
           
mapState = MapState(visibleTiles)
mapStateLock = Lock()

radarLock = Lock()

def FilterVisibleConsumedBanks(centerX, centerY):
    filteredBanks = []
    
    minX, minY = GridToWorldCoords(0, 0, centerX, centerY)
    maxX, maxY = GridToWorldCoords(visibleTiles - 1, visibleTiles - 1, centerX, centerY)
    
    minBankX = int(minX / bankSize)
    maxBankX = int(maxX / bankSize)

    minBankY = int(minY / bankSize)
    maxBankY = int(maxY / bankSize)
    
    mapConsumedBanks = mapState.ConsumedBanks[Player.Map]
    
    # Filter only the banks that are visible
    for coords in mapConsumedBanks:
        if coords[0] >= minBankX and coords[0] <= maxBankX and coords[1] >= minBankY and coords[1] <= maxBankX:
            filteredBanks.append((coords[0], coords[1]))
            
    return filteredBanks

def GridToWorldCoords(col, row, centerX, centerY):
    return (centerX + (col - centerTile), centerY + (row - centerTile))

def ShowRadar(radar):
    Application.Run(radar)

class Radar(Form):
    def __init__(self):
        self.FormBorderStyle = FormBorderStyle.FixedSingle
        self.MaximizeBox = False
        self.MinimizeBox = True
        self.DoubleBuffered = True
        self.AutoScroll = False
        self.IsShown = False
        self.Font = Font(FontFamily.GenericMonospace, 12)
        self.ClientSize = Size((visibleTiles * gridLinesDistance) + 1, (visibleTiles * gridLinesDistance) + 1)
        self.Load += self.OnFormLoad
        
        self.Paint += self.OnPaint
        self.FormClosing += self.OnRadarClosing
        self.Shown += self.OnShown
        self.MouseClick += self.OnMouseClick

        self.VisibleConsumedBanks = []
        self.HighlightedBanks = []
        self.PlayerPosition = (0, 0)
 

    def OnFormLoad(self, sender, args):
        # Ask for it to stay always on top
        hwnd = self.Handle.ToInt32()
        windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 1|2)
        
    def OnMouseClick(self, args):
        global radarLock
        
        if args.Button == MouseButtons.Left:
            with radarLock:
                col = int(args.X / gridLinesDistance)
                row = int(args.Y / gridLinesDistance)

                tileInfo = mapState.TilesInfo[row, col]

                self.HighlightedBanks = []

                for mineableCoords in tileInfo.MineableTiles:
                    bankX = int(mineableCoords[0] / bankSize)
                    bankY = int(mineableCoords[1] / bankSize)

                    if (bankX, bankY) not in self.HighlightedBanks:
                        self.HighlightedBanks.append((bankX, bankY))
                        
                self.Refresh()
            
    def OnShown(self, args):
        self.IsShown = True
        
    def OnPaint(self, args):
        global mapStateLock
             
        g = args.Graphics
        
        # Draw base grid
        with mapStateLock:
            for r in range(0, visibleTiles + 1):
                if mapState.GridRows[r] == 1:
                    g.DrawLine(bankBoundariesPen, 0, r * gridLinesDistance, gridLinesDistance * visibleTiles, r * gridLinesDistance)
                else:
                    g.DrawLine(gridPen, 0, r * gridLinesDistance, gridLinesDistance * visibleTiles, r * gridLinesDistance)
                
            for c in range(0, visibleTiles + 1):
                if mapState.GridCols[c] == 1:
                    g.DrawLine(bankBoundariesPen, c * gridLinesDistance, 0, c * gridLinesDistance, gridLinesDistance * visibleTiles)
                else:
                    g.DrawLine(gridPen, c * gridLinesDistance, 0, c * gridLinesDistance, gridLinesDistance * visibleTiles)
                
            # Draw the colored tiles
            rockTiles = List[Rectangle]()
            resourceTiles = List[Rectangle]()
            normalTiles = List[Rectangle]()
            highlightedTiles = List[Rectangle]()
            tilesWithBankCount = []
            markedTiles = []
            consumedTiles = []

            markedTilesCoords = mapState.MarkedSpots[Player.Map]
            consumedBanksCoords = self.VisibleConsumedBanks
            highlightedBanksCoords = self.HighlightedBanks

            for row in range(0, visibleTiles):
                for col in range(0, visibleTiles):
                    startX = (col * gridLinesDistance) + gridLinesWidth
                    startY = (row * gridLinesDistance) + gridLinesWidth
                    
                    tileInfo = mapState.TilesInfo[row, col]

                    rect = Rectangle(startX, startY, tilePxSize, tilePxSize)
                    
                    if tileInfo is None:
                        normalTiles.Add(rect)
                        continue 
                    
                    if tileInfo.Color == 1:
                        resourceTiles.Add(rect)
                    elif tileInfo.Color == 2:
                        rockTiles.Add(rect)
                    else:
                        normalTiles.Add(rect)

                    tileWorldX, tileWorldY = GridToWorldCoords(col, row, self.PlayerPosition[0],  self.PlayerPosition[1])
                    bankX = int(tileWorldX / bankSize)
                    bankY = int(tileWorldY / bankSize) 

                    if tileInfo.Color == 1 and (bankX, bankY) in consumedBanksCoords:
                        consumedTiles.append((col, row))
                    elif (tileWorldX, tileWorldY) in markedTilesCoords:
                        markedTiles.append((col, row))
                    elif tileInfo.Amount > 0:
                        tilesWithBankCount.append((col, row, tileInfo.Amount))

                    if (bankX, bankY) in highlightedBanksCoords:
                        highlightedTiles.Add(rect)

        if rockTiles.Count > 0:
            g.FillRectangles(rockTileBrush, rockTiles.ToArray())
        
        if normalTiles.Count > 0:
            g.FillRectangles(normalTileBrush, normalTiles.ToArray())

        if resourceTiles.Count > 0:
            g.FillRectangles(resourceTileBrush, resourceTiles.ToArray())

        if highlightedTiles.Count > 0:
            g.FillRectangles(bankHighlightBrush, highlightedTiles.ToArray())

            
        # Draw player pos
        g.FillRectangle(playerTileBrush, 
                      Rectangle((centerTile * gridLinesDistance) + 1, 
                      (centerTile * gridLinesDistance) + 1, tilePxSize, tilePxSize))

        stringFormat = StringFormat()
        stringFormat.Alignment = StringAlignment.Center
        stringFormat.LineAlignment = StringAlignment.Center
                  
        # Draw an X on mineable tiles that are reachable from marked spots
        for consumedTile in consumedTiles:
            rect = Rectangle((consumedTile[0] * gridLinesDistance) + 1, (consumedTile[1] * gridLinesDistance) + 1, tilePxSize, tilePxSize)
            g.DrawString(f"X", self.Font, consumedTileTextBrush, rect, stringFormat)
            
        # Drawn an M on tiles we marked a rune on
        for markedTile in markedTiles:
            rect = Rectangle((markedTile[0] * gridLinesDistance) + 1, (markedTile[1] * gridLinesDistance) + 1, tilePxSize, tilePxSize)
            g.DrawString(f"M", self.Font, markedTileTextBrush, rect, stringFormat)
        
        # Draw count of ore banks
        for tileBankInfo in tilesWithBankCount:
            rect = Rectangle((tileBankInfo[0] * gridLinesDistance) + 1, (tileBankInfo[1] * gridLinesDistance) + 1, tilePxSize, tilePxSize)
            g.DrawString(f"{tileBankInfo[2]}", self.Font, tileNormalTextBrush, rect, stringFormat)

    def OnRadarClosing(self, sender, args):
        with radarLock:
            self.IsShown = False

def RefreshUI(radar):
    radar.Refresh()

def SaveMiningSpot(mapState):
    tile = mapState.TilesInfo[centerTile, centerTile]

    with open(markedSpotsFilePath, "a") as f:
        f.write(f"{Player.Position.X},{Player.Position.Y},{Player.Map}")
        mapState.MarkedSpots[Player.Map].append((Player.Position.X, Player.Position.Y))

        mapConsumedBanks = mapState.ConsumedBanks[Player.Map]

        for miningCoords in tile.MineableTiles:
            f.write(f"|{miningCoords[0]},{miningCoords[1]}")
            
            bankX = int(miningCoords[0] / bankSize)
            bankY = int(miningCoords[1] / bankSize)

            if (bankX, bankY) not in mapConsumedBanks:
                mapConsumedBanks.append((bankX, bankY))

        f.write("\n")

lastKey = None
def HandleKey(radar):
    global lastKey
    key = Misc.LastHotKey()
    
    if key is None:
        return
    
    elif lastKey is not None and lastKey.Timestamp >= key.Timestamp:
        return
        
    lastKey = key
    
    if f"{key.HotKey}" != saveASpotKey:
        return

    global mapStateLock
    with mapStateLock:
        SaveMiningSpot(mapState)
        
        Player.HeadMessage(88, "Mining Spot Saved!")
        
    global radarLock
    with radarLock:
        radar.VisibleConsumedBanks = FilterVisibleConsumedBanks(radar.PlayerPosition[0], radar.PlayerPosition[1])
        if radar.IsShown:
            refreshDelegate = Action[Radar](RefreshUI)
            radar.Invoke(refreshDelegate, radar)

    
def LoadMiningSpots():
    global mapState

    if not os.path.exists(markedSpotsFilePath):
        return

    with open(markedSpotsFilePath, "r") as f:
        for line in f:
            spotsInfo = line.split("|")
            spotsInfoIt = iter(spotsInfo)
            
            markedSpot = next(spotsInfoIt)
            markedSpotInfo = markedSpot.split(",")

            mapState.MarkedSpots[int(markedSpotInfo[2])].append((int(markedSpotInfo[0]), int(markedSpotInfo[1])))
            mapConsumedBanks = mapState.ConsumedBanks[int(markedSpotInfo[2])]

            for miningSpot in spotsInfoIt:
                miningSpotInfo = miningSpot.split(",")

                bankX = int(int(miningSpotInfo[0]) / bankSize)
                bankY = int(int(miningSpotInfo[1]) / bankSize)

                if (bankX, bankY) not in mapConsumedBanks:
                    mapConsumedBanks.append((bankX, bankY))
        
def StartRadar():
    
    global mapState
    global lastKey
    global radarLock
    global mapStateLock

    radar = Radar()

    uiThread = Thread(ParameterizedThreadStart(ShowRadar))
    uiThread.Start(radar)

    # Wait for the radar to display
    while not radar.IsShown:
        Misc.Pause(200)

    prevPlayerX = 0
    prevPlayerY = 0

    gridRowsCount = len(mapState.GridRows)
    gridColsCount = len(mapState.GridCols)

    updateMapEvery = mapUpdateTicks
    tick = 0
    lastKey = Misc.LastHotKey()
    
    LoadMiningSpots()
    
    while True:
        if not radar.IsShown:
            return
            
        HandleKey(radar)
        Misc.Pause(100)
        tick += 1
        
        if tick < updateMapEvery:
            continue

        tick = 0
        
        currentPlayerX = Player.Position.X
        currentPlayerY = Player.Position.Y

        # We haven't moved, don't recalculate
        if prevPlayerX == currentPlayerX and prevPlayerY == currentPlayerY:
            continue
            
        prevPlayerX = currentPlayerX
        prevPlayerY = currentPlayerY

        with radarLock:
            radar.VisibleConsumedBanks = FilterVisibleConsumedBanks(currentPlayerX, currentPlayerY)
            visibleConsumedBanks = list(radar.VisibleConsumedBanks)
            radar.HighlightedBanks = []
            radar.PlayerPosition = (currentPlayerX, currentPlayerY)

        with mapStateLock:
        
            mapState.GridCols = [0] * (mapState.Size + 1)
            mapState.GridRows = [0] * (mapState.Size + 1)
                
            offsetCenterX = currentPlayerX % bankSize
            offsetCenterY = currentPlayerY % bankSize
            
            # Color the grid lines that represent the banks boundaries
            for x in range(0, int(gridColsCount / bankSize) + 1):
                col = ((x * bankSize) - offsetCenterX)
                if col >= 0 and col <= gridColsCount:
                    mapState.GridCols[col] = 1
                
            for y in range(0, int(gridRowsCount / bankSize) + 1):
                row = ((y * bankSize) - offsetCenterY)
                if row >= 0 and row <= gridRowsCount:
                    mapState.GridRows[row] = 1
               
            # Gather the land tiles IDs and check if it's impassable
            for row in range(0, visibleTiles):
                for col in range(0, visibleTiles):
                    
                    adjX = currentPlayerX + (col - centerTile)
                    adjY = currentPlayerY + (row - centerTile)
                    tileID = Statics.GetLandID(adjX, adjY, Player.Map)
                    blocked = Statics.GetLandFlag(tileID, "Impassable")
                    
                    color = 0
                    if tileID in mineableTiles:
                        color = 1
                    elif tileID in rockTiles:
                        color = 2

                    mapState.TilesInfo[row, col] = TileInfo(color, 0, int(adjX / bankSize), int(adjY / bankSize), blocked)
                  
            # For each walkable tiles, check how many mineable tiles,
            # each on a different bank, are reachable.
            for row in range(centerTile - scanRange,  centerTile + scanRange):
                for col in range(centerTile - scanRange, centerTile + scanRange):
                    tile = mapState.TilesInfo[row, col]

                    if tile.Blocked == True:
                     continue

                    # Keep track of the banks we've already seen, so we don't consider mineable tiles
                    # in a bank that we already counted.
                    banksSeen = []

                    # Then from the selected walkable tile, we check if there's any mineable tile in a distance of 2
                    # if there is, we count the bank it's in if we haven't already seen it.
                    for rowOffset in range(-2, 3):
                        for colOffset in range(-2, 3):
                            finalCol = col + colOffset
                            finalRow = row + rowOffset

                            targetTile = mapState.TilesInfo[finalRow, finalCol]

                            bankFound = False
                            for bank in banksSeen:
                                if bank[0] == targetTile.BankX and bank[1] == targetTile.BankY:
                                    bankFound = True
                                    break
                                
                            if bankFound:
                                continue
                             
                            for bank in visibleConsumedBanks:
                                 if bank[0] == targetTile.BankX and bank[1] == targetTile.BankY:
                                    bankFound = True
                                    break
                                    
                            if bankFound:
                                continue
                                 

                            # If it's a mineable tile, and the bank is new, count it
                            if targetTile.Color == 1:
                                tileWorldX, tileWorldY = GridToWorldCoords(finalCol, finalRow, currentPlayerX, currentPlayerY)
                                bankX = int(tileWorldX / bankSize)
                                bankY = int(tileWorldY / bankSize)
                                 
                                banksSeen.append((bankX, bankY))
                                tile.Amount += 1
                                tile.MineableTiles.append((tileWorldX, tileWorldY))
        
        with radarLock:
            if radar.IsShown:
                refreshDelegate = Action[Radar](RefreshUI)
                radar.Invoke(refreshDelegate, radar)
            else:
                break
        
StartRadar()