import subprocess
import time

class NodeController:
    def __init__(self):
        self.nodos = {}  # Diccionario para almacenar los procesos de los nodos

    def iniciar_nodo(self, node_id, script_path):
        """Inicia un nodo dado un ID de nodo y la ruta al script del nodo"""
        try:
            print(f"Iniciando Nodo {node_id}...")
            # Iniciar el script del nodo como un proceso separado
            process = subprocess.Popen(['python', script_path, str(node_id)], shell=True)
            self.nodos[node_id] = process
            print(f"Nodo {node_id} iniciado con PID: {process.pid}")
        except Exception as e:
            print(f"Error al iniciar el Nodo {node_id}: {e}")

    def detener_nodo(self, node_id):
        """Detiene un nodo dado su ID"""
        if node_id in self.nodos:
            process = self.nodos[node_id]
            print(f"Deteniendo Nodo {node_id} con PID: {process.pid}")
            process.terminate()
            process.wait()  # Esperar a que el proceso termine
            del self.nodos[node_id]
            print(f"Nodo {node_id} detenido.")
        else:
            print(f"Nodo {node_id} no está en ejecución.")

    def monitorear_nodos(self):
        """Monitorea los nodos activos"""
        while True:
            print("Monitoreando nodos...")
            for node_id, process in self.nodos.items():
                if process.poll() is None:  # El proceso sigue en ejecución
                    print(f"Nodo {node_id} (PID: {process.pid}) está activo.")
                else:
                    print(f"Nodo {node_id} ha terminado.")
            time.sleep(5)  # Esperar 5 segundos antes de volver a monitorear

    def detener_todos_nodos(self):
        """Detiene todos los nodos en ejecución"""
        print("Deteniendo todos los nodos...")
        for node_id in list(self.nodos.keys()):
            self.detener_nodo(node_id)
        print("Todos los nodos han sido detenidos.")


if __name__ == "__main__":
    controlador = NodeController()

    # Iniciar los nodos
    controlador.iniciar_nodo(1, ".\\Jam-SD\\nodo.py")
    # controlador.iniciar_nodo(2, ".\nodo.py")
    # controlador.iniciar_nodo(3, ".\nodo.py")

    # Monitorear los nodos (esto bloqueará la ejecución, podrías hacer esto en un hilo)
    try:
        controlador.monitorear_nodos()
    except KeyboardInterrupt:
        print("Interrupción del usuario, deteniendo todos los nodos.")
        controlador.detener_todos_nodos()
