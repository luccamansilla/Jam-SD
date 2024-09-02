import serpent
from Pyro5.api import expose, serve, config
import Pyro5.socketutil
import os
import hashlib

save_directory = "C:/Users/lucca/Desktop/py/Jam-SD/songs"

# Verifica que la carpeta existe y muestra un mensaje
if not os.path.exists(save_directory):
    os.makedirs(save_directory)
    print(f"Directorio de guardado creado: {save_directory}")
else:
    print(f"Directorio de guardado ya existe: {save_directory}")

class Testclass(object):
    @expose
    def transfer(self, data, filename):
        if config.SERIALIZER == "serpent" and isinstance(data, dict):
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

serve(
    {
        Testclass: "example.hugetransfer"
    },
    host=Pyro5.socketutil.get_ip_address("localhost", workaround127=True),
    use_ns=False, verbose=True)
