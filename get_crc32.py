import zlib

def calculate_crc32(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    return zlib.crc32(data) 

x = calculate_crc32(r"C:\Users\pjwri\Desktop\ARINC 615A\test test test.txt" )
print(x)