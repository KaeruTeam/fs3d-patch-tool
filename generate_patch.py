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
import shutil

import scripts.ips as Ips
from scripts.darc import Darc
from scripts.msbt import Msbt

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

def build_codebin(region_config, output_path):
  # Create new IPS patch file
  patch = Ips.IpsPatch()
  # Set cert sizes - these are both uint32
  patch.add_record(int(region_config['CERT_A_SIZE']), struct.pack('<I', cert_a_size))
  # not sure why this needs to be shorter than the actual cert size -- should investigate this
  # patch.add_record(region_config['CERT_B_SIZE'], struct.pack('<I', cert_b_size - 148))
  patch.add_record(int(region_config['CERT_B_SIZE']), struct.pack('<I', cert_b_size))
  # Null out the ARM branch-if-equal operation that jumps into the NASC check
  # This is necessary since Nintendo's NASC server no longer supports Flipnote Studio 3D
  patch.add_record(int(region_config['NASC_BRANCH']), bytes(4))
  # Patch SSL certs
  patch.add_record(int(region_config['CERT_A_DATA']), cert_a_data)
  patch.add_record(int(region_config['CERT_B_DATA']), cert_b_data)
  # Null out the rest of the old cert data
  patch.add_record(int(region_config['CERT_A_DATA']) + cert_a_size, bytes(CERT_A_SIZE_MAX - cert_a_size))
  patch.add_record(int(region_config['CERT_B_DATA']) + cert_b_size, bytes(CERT_B_SIZE_MAX - cert_b_size))
  # add url
  patch.add_record(int(region_config['GALLERY_URL']), gallery_url.encode('ascii'))
  # null out rest of the url
  patch.add_record(int(region_config['GALLERY_URL']) + len(gallery_url), bytes(GALLERY_URL_SIZE_MAX - len(gallery_url)))
  # Save to file
  patch.save(output_path)

def build_romfs_dir(src_dir, output_dir):
  if src_dir.is_dir():
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in src_dir.iterdir():
      if child.is_dir() and child.match('*.blz'):
        darc = Darc()
        for subfile in child.iterdir():
          if subfile.match('*.msbt.json'):
            msbt = Msbt.from_json(subfile)
            darc_entry = darc.root.add_entry()
            darc_entry.name = str(subfile.relative_to(child).with_suffix(''))
            darc_entry.data = msbt.write()
          else:
            pass
        darc.save(output_dir / child.name)
      else:
        build_romfs_dir(child, output_dir / child.name)
  else: 
    shutil.copy(str(src_dir), str(output_dir))

for region in ['EUR', 'USA', 'JPN']:

  region_config = config[region]
  output_dir = pathlib.Path('./luma/titles/%s' % region_config['TITLE_ID'])
  output_dir.mkdir(parents=True, exist_ok=True)
  
  # Generate code.bin patches
  build_codebin(region_config, output_dir / 'code.ips')

  # Create romfs files
  romfs_src_dir = pathlib.Path('./%s/romfs' % region)
  romfs_output_dir = output_dir / 'romfs/'
  if not romfs_src_dir.exists(): 
    continue
  
  build_romfs_dir(romfs_src_dir, romfs_output_dir)


