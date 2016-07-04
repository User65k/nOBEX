#!/usr/bin/env python

import bluetooth, os, struct, sys
from xml.etree import ElementTree
from PyOBEX import client, headers, responses

def usage():
    sys.stderr.write("Usage: %s <device address> <dest directory> [SIM]\n" % sys.argv[0])
    sys.exit(1)

def connect(device_address):
    d = bluetooth.find_service(address=device_address, uuid="1130")
    if not d:
        sys.stderr.write("No Phonebook service found.\n")
        sys.exit(1)

    port = d[0]["port"]

    # Use the generic Client class to connect to the phone.
    c = client.Client(device_address, port)
    uuid = b'\x79\x61\x35\xf0\xf0\xc5\x11\xd8\x09\x66\x08\x00\x20\x0c\x9a\x66'
    result = c.connect(header_list=[headers.Target(uuid)])

    if not isinstance(result, responses.ConnectSuccess):
        sys.stderr.write("Failed to connect to phone.\n")
        sys.exit(1)

    return c

def get_file(c, src_path, dest_path, verbose=True, folder_name=None, book=False):
    if verbose:
        if folder_name is not None:
            print("Fetching %s/%s" % (folder_name, src_path))
        else:
            print("Fetching %s" % src_path)

    if book:
        mimetype = b'x-bt/phonebook'
    else:
        mimetype = b'x-bt/vcard'

    hdrs, card = c.get(src_path, header_list=[headers.Type(mimetype)])
    with open(dest_path, 'wb') as f:
        f.write(card)

def dump_dir(c, src_path, dest_path):
    src_path = src_path.strip("/")

    # since some people may still be holding back progress with Python 2, I'll support
    # them for now and not use the Python 3 exists_ok option :(
    try:
        os.makedirs(dest_path)
    except OSError as e:
        pass

    # Access the list of vcards in the directory
    hdrs, cards = c.get(src_path, header_list=[headers.Type(b'x-bt/vcard-listing')])

    # Parse the XML response to the previous request.
    # Extract a list of file names in the directory
    names = []
    root = ElementTree.fromstring(cards)
    for card in root.findall("card"):
        names.append(card.attrib["handle"])

    c.setpath(src_path)

    # get all the files
    for name in names:
        get_file(c, name, "/".join([dest_path, name]), folder_name=src_path)

    # return to the root directory
    depth = len([f for f in src_path.split("/") if len(f)])
    for i in range(depth):
        c.setpath(to_parent=True)

def main():
    if not 3 <= len(sys.argv) <= 4:
        usage()
    elif len(sys.argv) == 4:
        if sys.argv[3] == "SIM":
            # If the SIM command line option was given, look in the SIM1
            # directory. Maybe the SIM2 directory exists on dual-SIM phones.
            prefix = "SIM1/"
        else:
            usage()
    else:
        prefix = ""

    device_address = sys.argv[1]
    dest_dir = os.path.abspath(sys.argv[2]) + "/"

    c = connect(device_address)

    # dump the phone book and other folders
    dump_dir(c, prefix+"telecom/pb", dest_dir+prefix+"telecom/pb")
    dump_dir(c, prefix+"telecom/ich", dest_dir+prefix+"telecom/ich")
    dump_dir(c, prefix+"telecom/och", dest_dir+prefix+"telecom/och")
    dump_dir(c, prefix+"telecom/mch", dest_dir+prefix+"telecom/mch")
    dump_dir(c, prefix+"telecom/cch", dest_dir+prefix+"telecom/cch")

    # dump the combined vcards
    c.setpath(prefix + "telecom")
    get_file(c, "pb.vcf", dest_dir+prefix+"telecom/pb.vcf",
            folder_name=prefix+"telecom", book=True)
    get_file(c, "ich.vcf", dest_dir+prefix+"telecom/ich.vcf",
            folder_name=prefix+"telecom", book=True)
    get_file(c, "och.vcf", dest_dir+prefix+"telecom/och.vcf",
            folder_name=prefix+"telecom", book=True)
    get_file(c, "mch.vcf", dest_dir+prefix+"telecom/mch.vcf",
            folder_name=prefix+"telecom", book=True)
    get_file(c, "cch.vcf", dest_dir+prefix+"telecom/cch.vcf",
            folder_name=prefix+"telecom", book=True)

    c.disconnect()
    return 0

if __name__ == "__main__":
    sys.exit(main())