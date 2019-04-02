# Patch generator tool for Flipnote Studio 3D
# Generates luma code patches which allow the app to connect to a custom server
# Original patch written for Kaeru World by Shutterbug2000
# github.com/shutterbug2000
# JPN support and Python tooling by Jaames
# github.com/jaames | jamesdaniel.dev

from sys import argv
import struct
import configparser
import pathlib

import scripts.ips as ips

# load config

config = configparser.ConfigParser()
config.read('config.ini')

# check and load config data

sections = config.sections()
if 'SETUP' not in sections or 'EUR' not in sections or 'USA' not in sections or 'JPN' not in sections:
  exit('Config section missing, please check the project readme')

CERT_A_SIZE_MAX = int(config['SETUP']['CERT_A_SIZE_MAX'])
CERT_B_SIZE_MAX = int(config['SETUP']['CERT_B_SIZE_MAX'])
GALLERY_URL_SIZE_MAX = int(config['SETUP']['GALLERY_URL_SIZE_MAX'])

with open(config['SETUP']['CERT_A_PATH'], 'rb') as f:
  cert_a_data = f.read()
  cert_a_size = len(cert_a_data)

with open(config['SETUP']['CERT_B_PATH'], 'rb') as f:
  cert_b_data = f.read()
  cert_b_size = len(cert_b_data)

gallery_url = config['SETUP']['GALLERY_URL']

if cert_a_size > CERT_A_SIZE_MAX:
  exit('Maximum filesize for cert A is', CERT_B_SIZE_MAX, 'bytes')

if cert_b_size > CERT_B_SIZE_MAX:
  exit('Maximum filesize for cert B is', CERT_B_SIZE_MAX, 'bytes')

if len(gallery_url) > GALLERY_URL_SIZE_MAX:
  exit('Gallery URL cannot exceed', GALLERY_URL_SIZE_MAX, 'characters')

# generate code.bin patches

for region in ['EUR', 'USA', 'JPN']:
  regionConfig = config[region]
  # Create new IPS patch file
  patch = ips.IpsPatch()
  # Set cert sizes - these are both uint32
  patch.add_record(int(regionConfig['CERT_A_SIZE']), struct.pack('<I', cert_a_size))
  # not sure why this needs to be shorter than the actual cert size -- should investigate this
  # patch.add_record(regionConfig['CERT_B_SIZE'], struct.pack('<I', cert_b_size - 148))
  patch.add_record(int(regionConfig['CERT_B_SIZE']), struct.pack('<I', cert_b_size))
  # Null out the ARM branch-if-equal operation that jumps into the NASC check
  # This is necessary since Nintendo's NASC server no longer supports Flipnote Studio 3D
  patch.add_record(int(regionConfig['NASC_BRANCH']), bytes(4))
  # Patch SSL certs
  patch.add_record(int(regionConfig['CERT_A_DATA']), cert_a_data)
  patch.add_record(int(regionConfig['CERT_B_DATA']), cert_b_data)
  # Null out the rest of the old cert data
  patch.add_record(int(regionConfig['CERT_A_DATA']) + cert_a_size, bytes(CERT_A_SIZE_MAX - cert_a_size))
  patch.add_record(int(regionConfig['CERT_B_DATA']) + cert_b_size, bytes(CERT_B_SIZE_MAX - cert_b_size))
  # add url
  patch.add_record(int(regionConfig['GALLERY_URL']), gallery_url.encode('ascii'))
  # null out rest of the url
  patch.add_record(int(regionConfig['GALLERY_URL']) + len(gallery_url), bytes(GALLERY_URL_SIZE_MAX - len(gallery_url)))
  
  p = pathlib.Path('./luma/titles/%s' % regionConfig['TITLE_ID'])
  p.mkdir(parents=True, exist_ok=True)
  code_path = p / 'code.ips'
  patch.save(code_path)