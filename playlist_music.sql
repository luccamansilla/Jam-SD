-- Crear la tabla de playlist
CREATE TABLE playlist (
    playlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- Crear la tabla de canciones (songs)
CREATE TABLE songs (
    song_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    uri TEXT NOT NULL

);

-- Crear la tabla intermedia entre canciones y playlists (songs_playlist)
CREATE TABLE songs_playlist (
    id_song_playlist INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id INTEGER NOT NULL,
    playlist_id INTEGER NOT NULL,
    user_upload_id INTEGER NOT NULL,
    FOREIGN KEY (song_id) REFERENCES songs(song_id),
    FOREIGN KEY (playlist_id) REFERENCES playlist(playlist_id),
    FOREIGN KEY (user_upload_id) REFERENCES users(user_id)
);

-- Crear la tabla de usuarios (users)
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

-- Crear la tabla intermedia entre usuarios y playlists (users_playlist)
CREATE TABLE users_playlist (
    id_user_playlist INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    playlist_id INTEGER NOT NULL,
    user_leader INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (playlist_id) REFERENCES playlist(playlist_id)
);
