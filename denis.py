#!/usr/bin/python3

import os
import sys
import tty
import time
import struct
import termios
from textwrap import wrap
import argparse
import bitstruct
import multiprocessing

debug=False

###################################################################################################
#
#  0. Some useful routines for later
#
###################################################################################################
def bold(text):
  return '\033[1m'+text+'\033[0m'

def red(text):
  return '\033[31m'+text+'\033[0m'

def blue(text):
  return '\033[34m'+text+'\033[0m'

def yellow(text):
  return '\033[33m'+text+'\033[0m'

def green(text):
  return '\033[32m'+text+'\033[0m'

def magenta(text):
  return '\033[35m'+text+'\033[0m'

def cyan(text):
  return '\033[36m'+text+'\033[0m'

def lightgrey(text):
  return '\033[37m'+text+'\033[0m'

def darkgrey(text):
  return '\033[90m'+text+'\033[0m'

pcu={ "energy_unit": 0,
      "time_unit": 0,
      "pwr_unit": 0
    }


def rdmsr(offset, size ):
  with open("/dev/cpu/0/msr", "rb") as msrfile:
    msrfile.seek(offset)
    return msrfile.read(size)


###################################################################################################
#
#  2. PCU CR1 registers (bus:B31, device:30, function: 1)
#     External Design Specification vol 2 : Registers, §18.2 page 5748
#
###################################################################################################
def decode_VID_BCAST_1(reg):
  comment="assigned by PCI-SIG to Intel"  
  reg=bitstruct.byteswap("{}".format(len(reg)),reg)
  vendor_id = bitstruct.unpack("u16", reg)[0]
  if vendor_id==0x8086:
    return "{0}\t\t{1}".format( bold(green("INTEL")), blue(comment) )
  else:
    return "Unknown\t\t"+blue(comment)   


def decode_SVID_BCAST_1(reg):
  comment="specifies Intel® but can be set to any value once after reset"
  reg=bitstruct.byteswap("{}".format(len(reg)),reg)
  vendor_id = bitstruct.unpack("u16", reg)[0]
  if vendor_id==0x8086:
    return "{0}\t\t{1}".format( bold(green("INTEL")), blue(comment) )
  else:
    return "Unknown\t\t"+blue(comment)   


def decode_TOR_THRESHOLDS_CFG(reg):
  comment="how much of the TOR various types of requests are allowed to occupy"  
  reg=bitstruct.byteswap("{}".format(len(reg)),reg)
  _,prq_count_threshold,_,loc2rem_thresh_empty,loc2remthresh_norm,rrq_count_threshold= \
    bitstruct.unpack("u11 u5 b1 u5 u5 u5", reg)
  return "\t\t{0}\n  prq_count_threshold={1}\n" \
"  loc2rem_thresh_empty = {2}\n" \
"  loc2remthresh_norm   = {3}\n" \
"  rrq_count_threshold  = {4}".format(blue(comment),prq_count_threshold,loc2rem_thresh_empty,loc2remthresh_norm, rrq_count_threshold)


registers_3457= [
  (0x00, "vendor ID"                , 2, decode_VID_BCAST_1 ),
  (0x02, "Device ID"                , 2, "RO 3457h assigned by each IP/function owner as a unique identifier"),
  (0x04, "PCI Command"              , 2, "mostly hardwired to 0"),
  (0x06, "PCI status"               , 2, ""),
  (0x08, "Rev ID & Class code reg." , 8, ""),
  (0x0C, "CACHE LINE SIZE REGISTER" , 1, "size of cache line"),
  (0x0D, "PCI LATENCY TIMER"        , 1, "Not applicable to PCIe. Hardwired to 0"),
 (0x0E, "HEADER TYPE"              , 1, "PCI header type : multi function device, type 0 header"),
  (0x0F, "BUILT IN SELF TEST"       , 1, "Not supported. Hardwired to 0"),
  (0x2C, "Subsystem vendor ID"      , 2, decode_SVID_BCAST_1),
  (0x2E, "Subsystem ID"             , 2, "Assigned to uniquely identify the subsystem"),
  (0x34, "Capability pointer"       , 1, "Points to the first capability structure : the PCIe capability"),
  (0x3C, "Interrupt line"           , 1, "N/A for PCU"),
  (0x3D, "Interrupt pin"            , 1, "N/A for PCU"),
  (0x3E, "Minimum grant"            , 1, "PCI min grant reg : PCU doesn't burst as a PCI compliant master"),
  (0x3F, "Maximum latency"          , 1, "PCU has no specific requirements for how often it accesses PCI"),
  (0x420, "TOR THRESHOLDS CFG"      , 4, decode_TOR_THRESHOLDS_CFG)
]


###################################################################################################
#
#  3. main routine that deals with displaying things on the terminal
#     uses "config" (256 bytes) of binary registers to decode,
#     and "registers" a constant array that describes the bitfield
#
###################################################################################################

with open("/sys/bus/pci/devices/0000:7f:1d.1/config","rb") as fd:
  config= fd.read()

#move cursor to upper left corner
print( '\033[1;1f\033[2J'+"register dump:")
for offset,text,size, comment in registers_3457:
    reg = bytearray(config[offset:offset+size])
  
    if size==1:
      hexa = "{0:02X}".format( reg[0] )
      print( "{0:24s}: {1}h\t\t{2}".format( text, blue(hexa), blue(comment) ) )
    elif size==2:
      if not isinstance(comment, str):
        print( "{0:24s}: {1}".format( text, comment(reg) ) )
      else:  
        a,b = struct.unpack("<BB", reg)
        hexa = "{1:02X}{0:02X}".format( a, b )
        print( "{0:24s}: {1}h\t\t{2}".format( text, blue(hexa), blue(comment) ) )
    elif size==4:
      if not isinstance(comment, str):
        print( "{0:24s}: {1}".format( text, comment(reg) ) )
      else:
        a,b,c,d = struct.unpack("<BBBB", reg)
        hexa = "{3:02X}{2:02X}{1:02X}{0:02X}".format( a,b,c,d )
        print( "{0:24s}: {1}\t{2}".format( text, blue(hexa), blue(comment) ) )
    elif size==8:
      if not isinstance(comment, str):
        print( "{0:24s}: {1}".format( text, comment(reg) ) )
      else:  
        a,b,c,d,e,f,g,h = struct.unpack("<BBBBBBBB", reg)
        hexa = "{7:02X}{6:02X}{5:02X}{4:02X}{3:02X}{2:02X}{1:02X}{0:02X}".format( a,b,c,d,e,f,g,h )
        print( "{0:24s}: {1}h {2}".format( text, blue(hexa), blue(comment) ) )
  

