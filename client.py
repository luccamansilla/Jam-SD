import serpent
from Pyro5.api import Proxy

print("Enter the server's uri that was printed:")
uri = input().strip()

with open("romeo.mp3", "rb") as file:
    data = file.read()

datasize = len(data)

def do_test(data, datasize):
    with Proxy(uri) as obj:
        obj._pyroBind()
        obj.transfer(data)
        print("¡Archivo transferido!!")

do_test(data, datasize)
