import serpent
import Pyro5.api
# from Pyro5.api import expose, serve, config
import Pyro5.socketutil
import os
import hashlib
# import Pyro5.api
import socket

save_directory = "C:/Users/bandi/OneDrive/Escritorio/songs"

# Verifica que la carpeta existe y muestra un mensaje
if not os.path.exists(save_directory):
    os.makedirs(save_directory)
    print(f"Directorio de guardado creado: {save_directory}")
else:
    print(f"Directorio de guardado ya existe: {save_directory}")

@Pyro5.api.expose
class Testclass(object):
    # @Pyro5.api.expose
    def transfer(self, data, filename):
        if Pyro5.api.config.SERIALIZER == "serpent" and isinstance(data, dict):
            data = serpent.tobytes(data)  # Convertir el diccionario en bytes si es necesario
        
        file_path = os.path.join(save_directory, filename)
        print(f"Ruta de archivo configurada: {file_path}")

        if not os.path.exists(file_path):
            try:
                with open(file_path, "wb") as f:
                    f.write(data)
                    print(f"Archivo guardado en: {file_path}")
            except Exception as e:
                print(f"Failed to save the file: {e}")
        else:
            print("Ya existe un archivo con el mismo nombre, no se volvio a guardar el archivo")
        return len(data)

hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

daemon = Pyro5.server.Daemon(host=IPAddr)
ns = Pyro5.api.locate_ns()
print(ns)
uri = daemon.register(Testclass)
ns.register("playlist2", uri)
print("Ready")
daemon.requestLoop()


# serve(
#     {
#         Testclass: "example.hugetransfer"
#     },
#     host=Pyro5.socketutil.get_ip_address("localhost", workaround127=True),
#     use_ns=False, verbose=True)
