import struct
import json

MAGIC = b'MsgStdBn'

# Format (as used by Flipnote Studio 3D)
# ======
# Header
# - char[8] magic 'MsgStdBn'
# - uint16 byte order mark (0xFFFE = little endian)
# - uint16 unknown1 (0)
# - uint16 unknown2 (769)
# - uint16 number of sections
# - uint16 unknown3 (0)
# - uint32 filesize
# Section Header
# - char[4] section type
# - uint32 section size (this is rounded up to nearest multiple of 0x10 bytes)
# - null[8] unused / padding
# LBL1 Section
# - uint32 number of groups
# - label groups (8 bytes * number of groups)
#   - uint32 number of labels - this can ve 0 if the group is empty
#   - uint32 label offset, relative to the start of this section
#     if there's more than one label in the group, the 
# - labels
#   - uint8 label size
#   - char[label size] label text
#   - uint32 string index for TXT2 section
# TXT2 Section
# - uint32 number of strings
# - uint32[number of strings] - string offsets
# - strings
#   - UTF-16 string terminated with a single null char (0x0000)
# ATR1 Section
# - uint32 number of non-empty groups
# - uint32 - always 0
# We don't know what this section does, but it always seems to be 

class MsbtEntry:
  def __init__(self, label='', text=''):
    self.label = label
    self.text = text

class MsbtGroup:
  def __init__(self):
    self.entries = []

  def add_entry(self, label='', text=''):
    entry = MsbtEntry(label, text)
    self.entries.append(entry)
    return entry

class Msbt:
  def __init__(self):
    self.endian = '<'
    self.groups = []

  @classmethod
  def Open(cls, path):
    with open(path, 'rb') as fp:
      msbt = cls()
      msbt.read(fp)
    return msbt

  @classmethod
  def from_json(cls, path):
    msbt = cls()
    with open(path, 'r') as fp:
      data = json.loads(fp.read())
    for group in data['groups']:
      msbt_group = msbt.add_group()
      for entry in group:
        msbt_entry = msbt_group.add_entry()
        msbt_entry.label = entry['label']
        msbt_entry.text = entry['text']
    return msbt

  def save(self, path):
    with open(path, 'wb') as fp:
      fp.write(self.write())

  def add_group(self):
    group = MsbtGroup()
    self.groups.append(group)
    return group

  def read_string(self, buffer, offset):
    cur = buffer.tell()
    buffer.seek(offset)
    result = bytes()
    while True:
      char = buffer.read(2)
      if char != b'\x00\x00':
        result += char
      else:
        buffer.seek(cur)
        return result.decode('UTF-16' + 'LE' if self.endian == '<' else 'BE')
  
  def read(self, buffer):
    magic, byte_order_mark = struct.unpack('>8sH', buffer.read(10))
    if magic != MAGIC:
      print('invalid MSBT magic')
      exit()

    self.endian = '<' if byte_order_mark == 0xFFFE else '>'
    unknown1, unknown2, num_sections, unknown3, filesize = struct.unpack('%s4HI'%self.endian, buffer.read(12))

    buffer.seek(10, 1) # skip padding (?)

    lbl1_offset = 0
    atr1_offset = 0
    txt2_offset = 0

    for i in range(num_sections):
      magic, size, _ = struct.unpack('%s4sI8s'%self.endian, buffer.read(16))
      padded_size = size + (0x10 - (size % 0x10)) if size % 0x10 != 0 else size 
      if magic == b'LBL1':   lbl1_offset = buffer.tell()
      elif magic == b'ATR1': atr1_offset = buffer.tell()
      elif magic == b'TXT2': txt2_offset = buffer.tell()
      buffer.seek(padded_size, 1)

    strings = []
    buffer.seek(txt2_offset)
    num_strings = struct.unpack('%sI'%self.endian, buffer.read(4))[0]
    for i in range(num_strings):
      offset = struct.unpack('%sI'%self.endian, buffer.read(4))[0]
      strings.append(self.read_string(buffer, txt2_offset + offset))

    buffer.seek(lbl1_offset)
    num_groups = struct.unpack('%sI'%self.endian, buffer.read(4))[0]
    groups = [struct.unpack('%s2I'%self.endian, buffer.read(8)) for i in range(num_groups)]
    for num_labels, offset in groups:
      group = self.add_group()
      buffer.seek(lbl1_offset + offset)
      for i in range(num_labels):
        entry = group.add_entry()
        # read label
        label_size = ord(buffer.read(1))
        entry.label = buffer.read(label_size).decode('ascii')
        # get string index
        string_index = struct.unpack('%sI'%self.endian, buffer.read(4))[0]
        entry.text = strings[string_index]

  def dump_json(self, path):
    msbt_json = {
      'groups': [],
    }
    for group in self.groups:
      group_json = []
      for entry in group.entries:
        group_json.append({
          'label': entry.label,
          'text': entry.text
        })
      msbt_json['groups'].append(group_json)
    with open(path, 'w') as fp:
      fp.write(json.dumps(msbt_json, ensure_ascii=False, indent=2, sort_keys=True))

  def write(self, little_endian=True):
    self.endian = '<' if little_endian else '>'

    # write txt2 section
    txt2 = bytes()
    strings = [entry.text for entry in sum([group.entries for group in self.groups], [])]
    num_strings = len(strings)
    # write number of strings
    txt2 += struct.pack('%sI'%self.endian, num_strings)
    # write string offsets
    # string offset is relative to the start of the txt2 section
    # so we account for the 4-byte num_strings and 4-byte offsets for each string
    offset = 4 + (num_strings * 4)
    for string in strings:
      txt2 += struct.pack('%sI'%self.endian, offset)
      # strings are 16-bits per char + 2 null bytes
      offset += (len(string) * 2) + 2
    # write strings
    for string in strings:
      txt2 += string.encode('UTF-16' + 'LE' if self.endian == '<' else 'BE')
      txt2 += bytes(2)
    txt2 = self.write_section(b'TXT2', txt2)

    # write atr1 section
    num_non_empty_groups = 0
    for group in self.groups:
      if len(group.entries) > 0:
        num_non_empty_groups += 1
    atr1 = self.write_section(b'ATR1', struct.pack('%sII'%self.endian, num_non_empty_groups, 0))

    # write lbl1 section
    # write number of groups
    lbl1 = bytes()
    num_groups = len(self.groups)
    lbl1 += struct.pack('%sI'%self.endian, num_groups)
    label_data = bytes()
    label_offset = 4 + (num_groups * 8)
    string_index = 0
    for group in self.groups:
      # write group
      lbl1 += struct.pack('%sII'%self.endian, len(group.entries), label_offset)
      # write group entries
      for entry in group.entries:
        # write label size
        label_size = len(entry.label)
        label_data += bytes([label_size])
        # write label
        label_data += entry.label.encode('ascii')
        # write string index
        label_data += struct.pack('%sI'%self.endian, string_index)
        label_offset += label_size + 5
        string_index += 1
    lbl1 += label_data
    lbl1 = self.write_section(b'LBL1', lbl1)

    filesize = 32 + len(lbl1) + len(atr1) + len(txt2)
    num_sections = 3
    # write header
    header = bytes()
    header += struct.pack('>8sH', MAGIC, 0xFFFE if little_endian else 0xFEFF)
    # pack unknown1, unknown2, num sections, unknown3, filesize
    header += struct.pack('%s4HI'%self.endian, 0, 769, num_sections, 0, filesize)
    header += bytes(10)
    return header + lbl1 + atr1 + txt2

  def write_section(self, section_magic, section_data):
    section_size = len(section_data)
    header = struct.pack('%s4sI'%self.endian, section_magic, section_size) + bytes(8)
    padding_size = (0x10 - (section_size % 0x10)) if section_size % 0x10 != 0 else 0
    return header + section_data + bytes([0xAB] * padding_size)

if __name__ == '__main__':
  from sys import argv

  msbt = Msbt.Open(argv[1])
  msbt.save(argv[2])
