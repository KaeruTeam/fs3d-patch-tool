# IPS tool 
# Allows .ips patch files to be generated without needing the target file, as long as you know your target offsets
# Written by Jaames
# github.com/jaames | jamesdaniel.dev

class IpsRecord:
  def __init__(self, offset=0, data=bytes(0)):
    self.offset = offset
    self.data = data

class IpsPatch:
  def __init__(self):
    self.records = []

  def add_record(self, offset=0, data=bytes(0)):
    record = IpsRecord(offset, data)
    self.records.append(record)

  def write(self):
    # Write "PATCH" header
    result = b'PATCH'
    # Write records
    for record in self.records:
      result += record.offset.to_bytes(3, byteorder='big')
      data = record.data

      # if all bytes are the same
      if len(data) > 3 and all(byte == data[0] for byte in data):
        result += bytes([0, 0])
        result += len(data).to_bytes(2, byteorder='big')
        result += bytes([data[0]])
      
      else:
        result += len(record.data).to_bytes(2, byteorder='big')
        result += record.data
    # Write "EOF" end of file marker
    result += bytes([0x45, 0x4F, 0x46])
    return result

  def read(self, buffer):
    header = buffer.read(5)
    while True:
      chunk = buffer.read(3)

      # Break loop if end of file ("EOF") marker is reached
      if chunk == b'EOF':
        break;

      record_offset = int.from_bytes(chunk, byteorder='big')
      record_size = int.from_bytes(buffer.read(2), byteorder='big')

      # RLE entry
      if record_size == 0:
        count = int.from_bytes(buffer.read(2), byteorder='big')
        value = int.from_bytes(buffer.read(1), byteorder='big')
        self.add_record(offset=record_offset, data=bytes([value] * count))

      else: 
        self.add_record(offset=record_offset, data=buffer.read(record_size))

  def save(self, path):
    with open(path, 'wb') as buffer:
      buffer.write(self.write())

  def dump(self, dir):
    for record in self.records:
      path = dir + '/' + ('0x%08x_0x%04x.bin' % (record.offset, len(record.data)))
      with open(path, 'wb') as f:
        f.write(record.data)

  @classmethod
  def Open(cls, path):
    with open(path, 'rb') as buffer:
      patch = IpsPatch()
      patch.read(buffer)
    return patch