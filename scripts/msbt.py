import struct

MAGIC = b'MsgStdBn'

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

  def add_group(self):
    group = MsbtGroup()
    self.groups.append(group)
    return group

  def read_label(self, buffer, offset):
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
      strings.append(self.read_label(buffer, txt2_offset + offset))

    group = self.add_group()
    buffer.seek(lbl1_offset)
    num_groups = struct.unpack('%sI'%self.endian, buffer.read(4))[0]
    groups = [struct.unpack('%s2I'%self.endian, buffer.read(8)) for i in range(num_groups)]
    for num_labels, offset in groups:
      if num_labels > 0:
        entry = group.add_entry()
      for i in range(num_labels):
        buffer.seek(lbl1_offset + offset)
        # read label
        label_size = ord(buffer.read(1))
        entry.label = buffer.read(label_size).decode('ascii')
        # get string index
        index = struct.unpack('%sI'%self.endian, buffer.read(4))[0]
        entry.text = strings[index]

  def write(self, little_endian=True):
    self.endian = '<' if little_endian else '>'

    label_offsets = []
    labels = bytes()
    for group in self.groups:
      for entry in group.entries:
        print(entry.label, entry.text)

    filesize = 30
    header = bytes()
    header += struct.pack('>8sH', MAGIC, 0xFFFE if little_endian else 0xFEFF)
    # pack unknown1, unknown2, num sections, unknown3, filesize
    header += struct.pack('%s4HI'%self.endian, 0, 769, 3, 0, filesize)
    header += bytes(10)

# with open('./out/WindowTheater.msbt', 'rb') as f:
#   msbt = Msbt()
#   msbt.read(f)