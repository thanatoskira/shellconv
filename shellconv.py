#!/usr/bin/env python
"""shellconv.py: Fetches shellcode (in typical format) from a file, disassemble it with the help of objdump
and prettyprint.
"""

__author__ = 'hasherezade (hasherezade.net)'
__license__ = "GPL"

import os
import sys
import re
import subprocess
import binascii
import colorterm

HEX_BYTE = r'[0-9a-fA-F]{2}\s'
SHELC_CHUNK = r'\\x[0-9a-fA-F]{2}'
DISASM_LINE = r'\s?[0-9a-f]*:\s[0-9a-f]{2}.*'
IMM_DWORD = r'[0-9a-fA-F]{8}'
DISASM_LINENUM = r'^\s+[0-9a-f]+:\s+'
DISASM_BYTES = r':\s+([0-9a-f]{2}\s+)+'

ARG_INFILE = 1
ARG_ARCH = 2
ARG_OUTFILE = 3

ARG_MIN = ARG_INFILE + 1

def get_chunks(buf):
    t = re.findall (SHELC_CHUNK, buf)
    byte_buf = []
    for chunk in t:
        x = chunk[2:]
        num = int (x, 16)
        byte_buf.append(num)
    return byte_buf


def has_keyword(line, keywords):
    for key in keywords:
        if key in line:
            return True
    return False

def chunkstring(string, chunk_len):
    return (string[0+i:chunk_len+i] for i in range(0, len(string), chunk_len))

def dwordstr_to_str(imm_str):
    chunks = list(chunkstring(imm_str, 2))
    chars = []
    for c in chunks:
        chars.append(binascii.unhexlify(c))
    return "".join(chars)

def fetch_imm(line):
    vals = re.findall(IMM_DWORD, line)
    imm_strs = []
    for val in vals:
        imm_strs.append(dwordstr_to_str(val))
    if not imm_strs:
       return
    rev_strs = []
    for val in imm_strs:
        rev_strs.append(val[::-1])
    return "".join(imm_strs) + "-> \"" + "".join(rev_strs)+"\""

def is_printable(num):
    return (num >= 0x20 and num < 0x7f)

def append_ascii(line):
    m = re.search(DISASM_BYTES, line)
    if not m:
        return
    m_lnum = re.search(DISASM_LINENUM, line)
    if not m_lnum:
        return
    lnum_str = m_lnum.group(0)
    line = line[len(lnum_str):]

    bytes_str = m.group(0)
    t = re.findall(HEX_BYTE, bytes_str)
    ascii_line = []
    for bytestr in t:
        num = int (bytestr, 16)
        if (is_printable(num)):
            ascii_line.append(chr(num))
        else:
            ascii_line.append('.')
    return lnum_str + "".join(ascii_line) + "\t" + line

def color_disasm_print(disasm_lines):
    for orig_line in disasm_lines:
        line = append_ascii(orig_line)
        imm = fetch_imm(line)
        if (imm):
            line += " -> " + imm

        if has_keyword(orig_line, ['push']):
            colorterm.color_msg(colorterm.GREEN, line)
        elif has_keyword(orig_line, ['call','jmp']):
            colorterm.color_msg(colorterm.YELLOW, line)
        elif has_keyword(orig_line, ['jn']):
            colorterm.color_msg(colorterm.PURPLE, line)
        elif has_keyword(orig_line, ['j']):
            colorterm.color_msg(colorterm.LIGHTBLUE, line)
        elif has_keyword(orig_line,['int']):
            colorterm.color_msg(colorterm.RED, line)
        elif has_keyword(orig_line,['nop']):
            colorterm.color_msg(colorterm.GREY, line)
        elif has_keyword(orig_line,['bad']):
            colorterm.color_msg(colorterm.BG_RED, line)
        else:
            colorterm.color_msg(colorterm.BLUE, line)
    return

def process_out(out):
    t = re.findall(DISASM_LINE, out)
    lines = []
    for chunk in t:
        lines.append(chunk)
    return lines

def disasm(fileName, arch):
    print fileName
    print arch
    process_data = ['objdump', '-D', '-b','binary','-m', arch, '-M','intel', fileName]
    p = subprocess.Popen(process_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if err:
        colorterm.err("Error: " + err)
        return
    colorterm.info("OK!")
    lines = process_out(out)
    color_disasm_print(lines)

def print_charset(chunks):
    charset = set()
    for chunk in chunks:
        charset.add(chunk)
    print "Charset (unique = " + str(len(charset)) + "):"
    charset = sorted(charset)
    for char in charset:
        print '%02x'%(char),
    print "\n---"

def main():
    argc = sys.argv.__len__()
    argv = sys.argv
    arch = "i386"

    if (argc < ARG_MIN):
        print "Use: "+argv[0] + " " + "<inFile> <arch:optional> <outFile:optional>"
        print "arch: defined as in objdump -m, default: " + arch
        exit(-1)

    in_fileName = argv[ARG_INFILE]
    arch = "i386"
    if (argc > ARG_ARCH):
        arch = argv[ARG_ARCH]
    else:
        print "Default arch: " + arch

    out_fileName = "out.tmp"
    if (argc > ARG_OUTFILE):
        out_fileName = argv[ARG_OUTFILE]
    else:
        print "Default output (binary): " + out_fileName

    with open(in_fileName, "r") as fileIn:
        buf = fileIn.read()
        byte_buf = get_chunks(buf)

    print "---"
    print "Length (in bytes) = " + str(len(byte_buf))
    print_charset(byte_buf)

    byte_arr = bytearray(byte_buf)
    with open(out_fileName, "wb") as fileOut:
        fileOut.write(byte_arr)
    disasm(out_fileName, arch)

if __name__ == "__main__":
    sys.exit(main())

