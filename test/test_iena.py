#-------------------------------------------------------------------------------
# Name:        
# Purpose:     
#
# Author:      
#
# Created:     
#
__author__ = '$USER'

import sys
sys.path.append("..")

import unittest
import datetime
import time
import AcraNetwork.IENA as iena
import AcraNetwork.SimpleEthernet as SimpleEthernet
import AcraNetwork.Pcap as pcap
import struct
import os
import random

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_udp_packet(pcapfilename):
    """
    Convienence method to read the first UDP packet in a pcap file

    :param pcapfilename: pcapfilename
    :type pcapfilename: str
    :rtype: SimpleEthernet.UDP
    """
    p = pcap.Pcap(os.path.join(THIS_DIR, pcapfilename))
    p.readGlobalHeader()
    mypcaprecord = p.readAPacket()
    e = SimpleEthernet.Ethernet()
    e.unpack(mypcaprecord.packet)
    ip = SimpleEthernet.IP()
    ip.unpack(e.payload)
    udp_pkt = SimpleEthernet.UDP()
    udp_pkt.unpack(ip.payload)

    return udp_pkt


class IENATest(unittest.TestCase):

    def setUp(self):
        # Get aUDP packet from a pack which can be used
        p = pcap.Pcap(os.path.join(THIS_DIR, "iena_test.pcap"))
        p.readGlobalHeader()

        # Loop through the pcap file reading one packet at a time
        try:
            mypcaprecord = p.readAPacket()
        except IOError:
            # End of file reached
            return
        e = SimpleEthernet.Ethernet()
        e.unpack(mypcaprecord.packet)
        ip =  SimpleEthernet.IP()
        ip.unpack(e.payload)
        self.upd = SimpleEthernet.UDP()
        self.upd.unpack(ip.payload)


    def test_defaultIENA(self):
        '''Check the defaults for the IENA packet'''
        i = iena.IENA()
        self.assertEqual(i.key,None)
        self.assertEqual(i.size,None)
        self.assertEqual(i.keystatus,None)
        self.assertEqual(i.status,None)
        self.assertEqual(i.sequence,None)
        self.assertEqual(i.endfield,0xdead)
        self.assertEqual(i.payload,None)

    def test_basicIENA(self):
        '''Build a very basic packet and check the packed result'''
        i = iena.IENA()
        i.key = 1
        i.keystatus = 2
        i.status = 3
        i.sequence = 10
        i.setPacketTime(time.mktime(datetime.datetime(datetime.datetime.today().year, 1, 2, 0, 0, 0,0).timetuple()),0)
        i.payload = struct.pack('H',0x5)
        # size = 9. Time = midnight Jan 02 = 86400s 0us = 0x14dd760000
        expected_payload = struct.pack(iena.IENA.IENA_HEADER_FORMAT,1,9,0x14,0x1dd76000,2,3,10) + struct.pack('H',0x5) + struct.pack('>H',0xdead)
        self.assertEqual(i.pack(),expected_payload)

    def test_basicIENA_streamid(self):
        '''Build a very basic packet and check the packed result'''
        i = iena.IENA()
        i.streamid = 1
        i.keystatus = 2
        i.status = 3
        i.sequence = 10
        i.setPacketTime(time.mktime(datetime.datetime(datetime.datetime.today().year, 1, 2, 0, 0, 0,0).timetuple()),0)
        i.payload = struct.pack('H',0x5)
        # size = 9. Time = midnight Jan 02 = 86400s 0us = 0x14dd760000
        expected_payload = struct.pack(iena.IENA.IENA_HEADER_FORMAT,1,9,0x14,0x1dd76000,2,3,10) + struct.pack('H',0x5) + struct.pack('>H',0xdead)
        self.assertEqual(i.pack(),expected_payload)
        self.assertEqual(repr(i), "IENAP: KEY=0X1 SEQ=10 TIMEUS=86400000000")

    def test_unpackIEANFromPcap(self):
        '''Read all the IENA packets in a pcap file and check each field'''

        # Now I have a _payload that will be an iena packet
        i = iena.IENA()
        i.unpack(self.upd.payload)
        self.assertEquals(i.key,0x1a)
        self.assertEquals(i.size,24)
        self.assertEquals(i.status,1)
        self.assertEquals(i.keystatus,1)
        self.assertEquals(i.sequence, 195)
        self.assertEqual(i.timeusec,0x1d102f800)
        self.assertEquals(i.endfield,0xdead)
        self.assertEqual(len(i), 48)

    def test_unpack_IENAM(self):
        '''Read all the IENA packets in a pcap file and check each field'''
        # Now I have a _payload that will be an iena packet
        i = iena.IENAM()
        i.unpack(self.upd.payload)
        self.assertEquals(i.key,0x1a)
        for mparam in i:
            self.assertEqual(mparam.paramid, 0xDC)
        print i
        self.assertEqual(repr(i), "IENAM: KEY=0X1A SEQ=195 TIMEUS=7801600000 NUM_MPARAM=1\n M-Param #0:ParamID=0XDC Delay=16 Dataset Length=26\n")

    def test_unpack_IENAN(self):
        # Decode as IENA-N
        i = iena.IENAN()
        i.unpack(self.upd.payload)
        self.assertEquals(i.key, 0x1a)
        param_1 = i.parameters[0] # type: iena.NParameter
        self.assertEqual(param_1.paramid, 0xDC)
        self.assertListEqual(param_1.dwords, [0x10])
        self.assertEqual(repr(i), "IENAN: KEY=0X1A SEQ=195 TIMEUS=7801600000 NUM_DPARAM=8")
        self.assertEqual(len(i), 8)

    def test_unpack_IENAD(self):
        # Decode as IENA-N
        udp_pkt = get_udp_packet("ienad.pcap")
        i = iena.IENAD()
        i.unpack(udp_pkt.payload)
        self.assertEquals(i.key, 0x2cfa)
        param_1 = i.parameters[0] # type: iena.DParameter
        self.assertEqual(param_1.paramid, 0xFFFF)
        self.assertEqual(param_1.delay, 0x0)
        self.assertListEqual(param_1.dwords, [0xfed1, 0x7cfe])
        self.assertEqual(repr(i), "IENAD: KEY=0X2CFA SEQ=0 TIMEUS=1837 NUM_DPARAM=11")
        self.assertEqual(len(i), 11)

    def test_corrupt_IENAD(self):
        udp_pkt = get_udp_packet("corrupt_ienad.pcap")
        iena_pkt = iena.IENAD()
        self.assertRaises(Exception, lambda : iena_pkt.unpack(udp_pkt.payload) )

    def test_create_ienam(self):
        i = iena.IENAM()
        i.key = 0xDC
        i.endfield = 0xDEAD
        i.keystatus = 0
        i.sequence = 2
        i.n2 = 0
        for idx in range(5):
            mparam = iena.MParameter(paramid=idx, delay=idx*2, dataset=os.urandom(idx+5))
            i.parameters.append(mparam)

        buf = i.pack()
        b = iena.IENAM()
        b.unpack(buf)
        self.assertEqual(b.sequence, 2)
        self.assertEqual(len(b), 5)
        for idx, p in enumerate(b):
            self.assertEqual(p.paramid, idx)
            self.assertEqual(p.delay, idx*2)
            self.assertEqual(len(p.dataset), idx+5)

    def test_create_ienaq(self):
        i = iena.IENAQ()
        i.key = 0xDC
        i.endfield = 0xDEAD
        i.keystatus = 0
        i.sequence = 2
        i.n2 = 0
        for idx in range(10,15):
            qparam = iena.QParameter(paramid=idx, dataset=os.urandom(idx+5))
            i.parameters.append(qparam)

        buf = i.pack()
        b = iena.IENAQ()
        b.unpack(buf)
        self.assertEqual(b.sequence, 2)
        self.assertEqual(len(b), 5)
        for idx, p in enumerate(b):
            self.assertEqual(p.paramid, idx+10)
            self.assertEqual(len(p.dataset), idx+5+10)
        print i

    def test_read_multiple_ienam(self):
        # Get aUDP packet from a pack which can be used
        p = pcap.Pcap(os.path.join(THIS_DIR, "ienam_multiple.pcap"))

        # Loop through the pcap file reading one packet at a time
        mypcaprecord = p[0]
        e = SimpleEthernet.Ethernet()
        e.unpack(mypcaprecord.packet)
        ip = SimpleEthernet.IP()
        ip.unpack(e.payload)
        udp = SimpleEthernet.UDP()
        udp.unpack(ip.payload)

        i = iena.IENAM()
        i.unpack(udp.payload)
        self.assertEqual(len(i), 2)


if __name__ == '__main__':
    unittest.main()
