import zlib, struct
import numpy as np
            
def Build(image_data, palette=None):
    
    def png_pack(head, data):
        chunk = head + data
        return (struct.pack("!I", len(data)) +
                chunk +
                struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk)))

    if palette is None:
        color_type = 0
        transparent = b'\x00\x00'
        pal = ''
    else:
        color_type = 3
        pal = png_pack(b'PLTE', b''.join([struct.pack('!3B', 0xFF & b>>16, 0xFF & b>>8, 0xFF & b) for b in palette]))
        if np.any(palette>=16777216):
            transparent = b''.join([struct.pack('!B', 255-(0xFF & b>>24)) for b in palette])
        else:
            transparent = b'\x00'

    height, width = image_data.shape
    
    # Prepend each scan line with 0 for the filter type
    scan = np.zeros((height, width+1), np.uint8)
    scan[:,1:] = image_data;
    raw = scan.tobytes()

    return b''.join([
        b'\x89PNG\r\n\x1a\n',
        png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, color_type, 0, 0, 0)),
        pal,
        png_pack(b'tRNS', transparent),
        png_pack(b'IDAT', zlib.compress(raw)),
        png_pack(b'IEND', b'')])
