import sqlite3

def create_database():
    conn = sqlite3.connect('spotify.db')  # Nombre del archivo de base de datos
    cursor = conn.cursor()

    # Leer y ejecutar el archivo SQL
    with open('playlist_music.sql', 'r') as f:
        sql_script = f.read()
    
    cursor.executescript(sql_script)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database()