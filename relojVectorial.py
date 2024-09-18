class RelojVectorial:
       
    def incrementar(self, client_id):
        # Incrementa el valor del reloj para el cliente correspondiente
        self.clock[client_id] += 1

    def fusionar(self, otro_reloj):
        # Fusiona otro reloj vectorial con el actual
        for i in range(len(self.clock)):
            self.clock[i] = max(self.clock[i], otro_reloj[i])

    def obtener_reloj(self):
        # Devuelve una copia del reloj vectorial actual
        return self.clock.copy()

    def __str__(self):
        # Representación en cadena del reloj vectorial
        return str(self.clock)
