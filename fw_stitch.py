#!/usr/bin/env python
"""Parses a DVB stream dump and creates a binary FW file.
"""

import argparse
import crcmod
import logging
import struct
import sys

# sudo apt-get install gcc python-dev python-setuptools
# sudo easy_install -U pip
# sudo pip uninstall crcmod
# sudo pip install -U crcmod


def read_block(infile, crc_func, verbose=False):

    while True:
        crc_block = []

        rec = infile.read(4)
        if len(rec) != 4:
            break

        crc_block.append(rec)

        (val,) = struct.unpack('>I', rec)

        logging.debug("val: %08X", val)

        rec = infile.read(4)
        if len(rec) != 4:
            break

        crc_block.append(rec)

        (seq,) = struct.unpack('>I', rec)
        blocklen = (val >> 8) & 0xfff
        table = seq >> 24

        logging.debug("seq: %08X, blocklen: %u, table: %08X",
                      seq, blocklen, table)

        rec = infile.read(14)
        if len(rec) != 14:
            break

        crc_block.append(rec)

        block_data = infile.read(blocklen - 23)
        if len(block_data) != blocklen - 23:
            break

        crc_block.append(block_data)

        rec = infile.read(4)
        if len(rec) != 4:
            break

        crc_block.append(rec)

        (block_crc,) = struct.unpack('>I', rec)

        crc = crc_func(b''.join(crc_block))

        block_number = ((seq >> 16) & 0xff00) | ((seq >> 8) & 0xff)
        block_number &= 0x1fff

        logging.debug("block_crc: %08X, block_number:%u, crc:%08X",
                      block_crc, block_number, crc)

        yield block_number, block_data, crc


def _main(argv):
    parser = argparse.ArgumentParser(argv)
    parser.add_argument("-v", "--verbose",
                        help="increase output verbosity",
                        action="store_true")
    parser.add_argument("-i", "--infile",
                        help="file to read",
                        required=True)
    parser.add_argument("-o", "--outfile",
                        help="file to write",
                        required=True)
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    with open(args.infile, mode='rb') as infile, open(
        args.outfile, mode='wb') as outfile:

        dvb_crc32 = crcmod.mkCrcFun(0x104c11db7,
                                    rev=False,
                                    initCrc=0xFFFFFFFF,
                                    xorOut=0)
        blocks = [bytearray() for i in range(8192)]
        max_block = 0

        for block_number, block_data, crc in (
                read_block(infile, dvb_crc32, args.verbose)):

            if crc == 0:
                if block_number > max_block:
                    max_block = block_number

                blocks[block_number] = block_data

        for index, block in enumerate(blocks):
            if index > max_block:
                break
            if len(block) == 0:
                print "Missing block: %u" % index
                break
            else:
                outfile.write(block)

if __name__ == "__main__":
    _main(sys.argv)
