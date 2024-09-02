import serpent
import os
from Pyro5.api import Proxy

print("Enter the server's uri that was printed:")
uri = input().strip()

with open("LinkinPark-GivenUp.mp3", "rb") as file:
    data = file.read()
    filename = os.path.basename(file.name)

datasize = len(data)

def do_test(data, datasize):
    with Proxy(uri) as obj:
        obj._pyroBind()
        obj.transfer(data, filename)
        print("¡Archivo transferido!")

do_test(data, datasize)
