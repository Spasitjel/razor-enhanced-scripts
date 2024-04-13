# by Smjert/Spasitjel

from enum import Enum
import struct

class SpeechType(Enum):
    Normal = 0x00,
    Broadcast = 0x01,
    Emote = 0x02,
    System = 0x06,
    Message = 0x07,
    Whisper = 0x08,
    Yell = 0x09,
    Spell = 0x0A,
    Guild = 0x0D,
    Alliance = 0x0E,
    Command = 0x0F,

class ItemDirection(Enum):
    North = 0x00,
    Right = 0x01,
    East = 0x02,
    Down = 0x03,
    South = 0x04,
    Left = 0x05,
    West = 0x06,
    Up = 0x07,

def SendSpeech(message, object, type, color, name, font = 3):
    #BYTE[1] cmd
    #BYTE[2] Packet len
    #BYTE[4] itemID (FF FF FF FF = system)
    #BYTE[2] model (item # - FF FF = system)
    #BYTE[1] Type of Text
    #BYTE[2] Text Color
    #BYTE[2] Font
    #BYTE[30] Name
    #BYTE[?] Null-Terminated Msg (? = Packet length - 44)

    if isinstance(object, int):
        serial = object
    else:
        serial = object.Serial

    if type == SpeechType.System or type == SpeechType.Broadcast:
        graphic = 0xFFFF
        serial = 0xFFFFFF
    else:
        if serial >= 0x40000000:
            # it's an actual item
            graphic = object.ItemID
        else:
            graphic = object.Body

    format = f"!BHIHBHH30s{len(message)}sB"
    
    data = list(bytearray(struct.pack(format, 0x1C, 44 + len(message) + 1,
        serial, graphic, int(type.value[0]), color, font, name.encode('ascii'), message.encode('ascii'), 0)))
    
    PacketLogger.SendToClient(data)


def SpawnItem(itemID, serial, direction, amount, x, y, z, color):
    #Byte[1] Packet ID
    #Byte[2] 0x1 // always 0x1 on OSI
    #Byte[1] DataType // 0x00 = Item , 0x02 = Multi
    #Byte[4] Serial
    #Byte[2] Graphic // for multi its same value as the multi has in multi.mul
    #Byte[1] Facing // 0x00 if Multi
    #Byte[2] Amount // 0x1 if Multi
    #Byte[2] Amount // 0x1 if Multi , no idea why Amount is sent 2 times
    #Byte[2] X
    #Byte[2] Y
    #Byte[1] Z
    #Byte[1] Layer // 0x00 if Multi
    #Byte[2] Color // 0x00 if Multi
    #Byte[1] Flag // 0x20 = Movable if normally not , 0x80 = Hidden , 0x00 if Multi
    #Byte[2] Unknown // All 0x00

    format = "!BHBIHBHHHHbBHBH"

    data = list(bytearray(struct.pack(format,
            0xF3, 0x01, 0x00, serial, itemID, int(direction.value[0]), amount,
            amount, x, y, z, 0x00,
            color, 0x20, 0x00)))

    PacketLogger.SendToClient(data)