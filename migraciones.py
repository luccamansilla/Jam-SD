import sqlite3

# Conexión a la base de datos SQLite
def connect_db():
    return sqlite3.connect('spotify.db')

# Insertar datos de prueba en la tabla de usuarios
def insert_users():
    conn = connect_db()
    cursor = conn.cursor()

    users = [
        ("Alice",),
        ("Bob",),
        ("Charlie",)
    ]
    
    cursor.executemany("INSERT INTO users (name) VALUES (?)", users)
    conn.commit()
    conn.close()

# Insertar datos de prueba en la tabla de playlists
def insert_playlists():
    conn = connect_db()
    cursor = conn.cursor()

    playlists = [
        ("Rock Classics",),
        ("Pop Hits",),
        ("Jazz Vibes",)
    ]
    
    cursor.executemany("INSERT INTO playlist (name) VALUES (?)", playlists)
    conn.commit()
    conn.close()

# Insertar datos de prueba en la tabla de canciones
def insert_songs():
    conn = connect_db()  # Asegúrate de que esta función esté definida en tu código
    cursor = conn.cursor()

    # Lista de canciones con sus paths correspondientes
    songs = [
        ("Bohemian Rhapsody", "Bohemian Rhapsody.mp3"),
        ("Thriller", "Thriller.mp3"),
        ("Take Five", "Take Five.mp3"),
        ("Imagine", "Imagine.mp3"),
        ("Hotel California", "Hotel California.mp3")
    ]
    
    # Ejecutar el insert para todas las canciones
    cursor.executemany("INSERT INTO songs (name, path) VALUES (?, ?)", songs)

    # Confirmar los cambios en la base de datos
    conn.commit()
    conn.close()

# Insertar relaciones en la tabla songs_playlist
def insert_songs_playlist():
    conn = connect_db()
    cursor = conn.cursor()

    # Relacionar canciones con playlists y usuarios que subieron las canciones
    songs_playlist = [
        (1, 1, 1),  # "Bohemian Rhapsody" en "Rock Classics", subido por Alice
        (2, 2, 2),  # "Thriller" en "Pop Hits", subido por Bob
        (3, 3, 3),  # "Take Five" en "Jazz Vibes", subido por Charlie
        (4, 2, 1),  # "Imagine" en "Pop Hits", subido por Alice
        (5, 1, 2)   # "Hotel California" en "Rock Classics", subido por Bob
    ]

    cursor.executemany("""
        INSERT INTO songs_playlist (song_id, playlist_id, user_upload_id)
        VALUES (?, ?, ?)
    """, songs_playlist)
    conn.commit()
    conn.close()

# Insertar relaciones en la tabla users_playlist
def insert_users_playlist():
    conn = connect_db()
    cursor = conn.cursor()

    # Relacionar usuarios con playlists (indicar si son líderes)
    users_playlist = [
        (1, 1, 1),  # Alice en "Rock Classics", líder
        (2, 2, 1),  # Bob en "Pop Hits", no líder
        (3, 3, 1),  # Charlie en "Jazz Vibes", no líder
        (1, 3, 0),  # Alice también en "Jazz Vibes", no líder
        (2, 1, 0)   # Bob también en "Rock Classics", no líder
    ]

    cursor.executemany("""
        INSERT INTO users_playlist (user_id, playlist_id, user_leader)
        VALUES (?, ?, ?)
    """, users_playlist)
    conn.commit()
    conn.close()

# Ejecutar todas las inserciones
def populate_database():
    insert_users()            # Rellenar usuarios
    insert_playlists()        # Rellenar playlists
    insert_songs()            # Rellenar canciones
    insert_songs_playlist()   # Rellenar relación canciones-playlists
    insert_users_playlist()   # Rellenar relación usuarios-playlists

if __name__ == "__main__":
    populate_database()
    print("Base de datos rellenada con datos de prueba.")
