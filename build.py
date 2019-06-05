# Patch generator tool for Flipnote Studio 3D
# Generates luma code patches which allow the app to connect to a custom server
# Original patch written for Kaeru Gallery by Shutterbug2000
# github.com/shutterbug2000
# JPN support and Python tooling by Jaames
# github.com/jaames | jamesdaniel.dev

from sys import argv
import struct
import configparser
import pathlib
import shutil
import subprocess

import scripts.ips as Ips
from scripts.darc import Darc
from scripts.msbt import Msbt

BLZ_PATH = './blz'

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

def build_romfs_dir(src_path, output_path):
  # If the src is a file, copy it directly to the romfs output location
  if not src_path.is_dir():
    shutil.copy(str(src_path), str(output_path))
  # If the src directory name ends with .blz or .arc, compile its contents into an DARC file
  elif src_path.match('*.blz') or src_path.match('*.arc'): 
    # Create a new DARC instance
    darc = Darc()
    # Loop through directory contents
    for child in src_path.iterdir():
      darc_entry = darc.root.add_entry()
      # If the file ends with .msbt.json, compile this to an .msbt
      if child.match('*.msbt.json'):
        msbt = Msbt.from_json(child)
        darc_entry.name = str(child.relative_to(src_path).with_suffix(''))
        darc_entry.data = msbt.write()
      # Else write the file as-is
      else:
        darc_entry.name = str(child.relative_to(src_path))
        darc_entry.data = child.read_bytes()
    darc.save(output_path)
    # If the directory name ends with .blz we also need to compress the resulting DARC archive
    if src_path.match('*.blz'):
      subprocess.call([BLZ_PATH, '-en', str(output_path)], stdout=subprocess.DEVNULL)
  # Otherwise make a new directory in the romfs output location
  else:
    output_path.mkdir(parents=True, exist_ok=True)
    # Recuresively repeat the process on all of its children
    for child in src_path.iterdir():
      build_romfs_dir(child, output_path / child.name)

for region in ['EUR', 'USA', 'JPN']:

  region_config = config[region]
  output_path = pathlib.Path('./luma/titles/%s' % region_config['TITLE_ID'])
  output_path.mkdir(parents=True, exist_ok=True)
  
  # Generate code.bin patches
  build_codebin(region_config, output_path / 'code.ips')

  # Create regional romfs files
  romfs_src_path = pathlib.Path('./%s/romfs' % region)
  romfs_output_path = output_path / 'romfs/'
  if romfs_src_path.exists():
    build_romfs_dir(romfs_src_path, romfs_output_path)

  # Add global romfs files
  romfs_src_path = pathlib.Path('./ALL/romfs')
  romfs_output_path = output_path / 'romfs/'
  if romfs_src_path.exists(): 
    build_romfs_dir(romfs_src_path, romfs_output_path)


