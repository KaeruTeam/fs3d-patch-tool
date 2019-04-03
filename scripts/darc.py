import struct

class DarcEntry:
  def __init__(self, name='', data=bytes(0)):
    self.name = name
    self.data = data

class DarcGroup:
  def __init__(self, name=''):
    self.name = name
    self.entries = []
  
  def add_entry(self, name='', data=bytes(0)):
    entry = DarcEntry(name=name, data=data)
    self.entries.append(entry)
    return entry

class Darc:
  def __init__(self):
    self.root = DarcGroup()
    self.endian = '<'

  @classmethod
  def Open(cls, path):
    darc = cls()
    with open(path, 'rb') as f:
      darc.read(f)
    return darc
  
  def save(self, path):
    with open(path, 'wb') as f:
      f.write(self.write)

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
    magic, byte_order_mark = struct.unpack('>4sH', buffer.read(6))
    self.endian = '<' if byte_order_mark == 0xFFFE else '>'
    header_size, version, darc_size = struct.unpack('%sH2I'%self.endian, buffer.read(10))
    table_offset, table_size, data_offset = struct.unpack('%s3I'%self.endian, buffer.read(12))

    total_entries = 0
    entry_index = 0
    while True:
      buffer.seek(table_offset + entry_index * 12)
      label_offset, entry_offset, entry_size = struct.unpack('%s3I'%self.endian, buffer.read(12))
      # upper 16 bits indicates whether this is for a folder entry
      is_folder = label_offset & 0xFF000000
      label_offset &= 0x00FFFFFF
      # if folder entry (there doesnt seem to be subfolders, just a single root folder)
      if is_folder:
        # get entry count from root node 
        if label_offset == 0:
          self.root = DarcGroup()
          total_entries = entry_size
        # get root node label 
        else:
          self.root.name = self.read_label(buffer, (table_offset + total_entries * 12) + label_offset)
      # if normal entry
      else:
        entry = self.root.add_entry()
        buffer.seek(entry_offset)
        entry.data = buffer.read(entry_size)
        entry.name = self.read_label(buffer, (table_offset + total_entries * 12) + label_offset)
      
      entry_index += 1
      if entry_index >= total_entries:
        break

  def write_label(self, label):
    return label.encode('UTF-16' + 'LE' if self.endian == '<' else 'BE') + bytes(2)
      
  def write(self, little_endian=True):
    self.endian = '<' if little_endian else '>'
  
    labels = bytes(2) # label data always begins with 2 empty bytes?
    label_offsets = []
    data = bytes()
    data_offsets = []
    # add root label, which is always '.'
    labels += self.write_label('.')
    # pack entry labels + data
    num_entries = len(self.root.entries) + 2
    for entry in self.root.entries: 
      label_offsets.append(len(labels))
      data_offset = len(data)
      # align data offset to a multiple of 0x80
      if data_offset % 0x80 != 0:
        align = 0x80 - data_offset % 0x80
        data += bytes(align)
        data_offset += align
      data_offsets.append(data_offset)
      labels += self.write_label(entry.name)
      data += entry.data

    # add padding to the label section so that the data section aligns to a multiple of 0x80
    table_size = (num_entries * 12) + len(labels)
    base_data_offset = 28 + table_size
    if base_data_offset % 0x80 != 0:
      align = 0x80 - base_data_offset % 0x80
      labels += bytes(align)
      base_data_offset += align

    # write entry table
    table = bytes()
    # add root node
    table += struct.pack('%s3I'%self.endian, 0x01000000, 0, num_entries)
    # add root label node
    table += struct.pack('%s3I'%self.endian, 0x01000002, 0, num_entries)
    # write entries
    for i in range(num_entries - 2):
      label_offset = label_offsets[i]
      data_offset = base_data_offset + data_offsets[i]
      data_size = len(self.root.entries[i].data)
      # pack table entry
      table += struct.pack('%s3I'%self.endian, label_offset, data_offset, data_size)

    # write header
    header = bytes()
    # pack magic + byte order mark
    header += struct.pack('>4sH', b'darc', 0xFFFE if little_endian else 0xFEFF)
    # pack headersize, version, filesize
    header += struct.pack('%sH2I'%self.endian, 28, 16777216, base_data_offset + len(data))
    # pack table offset, table size, data offset
    header += struct.pack('%s3I'%self.endian, 28, table_size, base_data_offset)
    return header + table + labels + data