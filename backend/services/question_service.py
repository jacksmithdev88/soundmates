import random

from services.spotify_requests import SpotifyRequests

MUSIC_TRIVIA = [
    {
        "question": "Which band released 'Bohemian Rhapsody'?",
        "answer": "Queen",
        "options": ["Queen", "The Beatles", "Led Zeppelin", "Pink Floyd"],
    },
    {
        "question": "What instrument does a drummer play?",
        "answer": "Drums",
        "options": ["Drums", "Guitar", "Piano", "Violin"],
    },
    {
        "question": "Which artist is known as the 'King of Pop'?",
        "answer": "Michael Jackson",
        "options": ["Michael Jackson", "Elvis Presley", "Prince", "Justin Timberlake"],
    },
    {
        "question": "What genre originated in Jamaica in the late 1960s?",
        "answer": "Reggae",
        "options": ["Reggae", "Ska", "Dubstep", "Calypso"],
    },
    {
        "question": "Which band wrote 'Stairway to Heaven'?",
        "answer": "Led Zeppelin",
        "options": ["Led Zeppelin", "Deep Purple", "Black Sabbath", "The Who"],
    },
    {
        "question": "How many strings does a standard guitar have?",
        "answer": "6",
        "options": ["6", "4", "5", "8"],
    },
    {
        "question": "Which artist released the album '1989'?",
        "answer": "Taylor Swift",
        "options": ["Taylor Swift", "Adele", "Lady Gaga", "Katy Perry"],
    },
    {
        "question": "What does 'DJ' stand for?",
        "answer": "Disc Jockey",
        "options": ["Disc Jockey", "Digital Jukebox", "Dance Jam", "Direct Jam"],
    },
    {
        "question": "Which composer wrote the 'Moonlight Sonata'?",
        "answer": "Beethoven",
        "options": ["Beethoven", "Mozart", "Bach", "Chopin"],
    },
    {
        "question": "Which festival is famously held in the California desert?",
        "answer": "Coachella",
        "options": ["Coachella", "Glastonbury", "Burning Man", "Lollapalooza"],
    },
    {
        "question": "What is the highest male singing voice called?",
        "answer": "Tenor",
        "options": ["Tenor", "Baritone", "Bass", "Alto"],
    },
    {
        "question": "Which rapper released 'The Marshall Mathers LP'?",
        "answer": "Eminem",
        "options": ["Eminem", "Jay-Z", "Drake", "Kanye West"],
    },
    {
        "question": "What country is K-pop most associated with?",
        "answer": "South Korea",
        "options": ["South Korea", "Japan", "China", "Thailand"],
    },
    {
        "question": "Which Beatles album features a zebra crossing on the cover?",
        "answer": "Abbey Road",
        "options": ["Abbey Road", "Revolver", "Help!", "Rubber Soul"],
    },
    {
        "question": "What does 'BPM' stand for in music production?",
        "answer": "Beats Per Minute",
        "options": ["Beats Per Minute", "Bass Per Measure", "Band Performance Mode", "Beat Pattern Mix"],
    },
]


class QuestionService:
    def __init__(self, game_mode: str, spotify_users):
        self.game_mode = game_mode
        self.spotify_users = spotify_users
        self.spotify_requests = SpotifyRequests()

        self.answer_options = [
            user.username
            for user in self.spotify_users
            if user.username
        ]

        self.playlists = []
        self.used_playlist_ids = set()
        self.playlist_question_count = 0

        self.questions = []
        self.current_question = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def get_next_question(self):
        if not self.questions:
            self.questions = await self.create_questions_for_game_mode()

        if self.current_question >= len(self.questions):
            return None

        question = self.questions[self.current_question]
        self.current_question += 1

        return question

    def pick_random_user(self):
        if not self.spotify_users:
            return None

        return random.choice(self.spotify_users)

    def get_spotify_tokens(self, user):
        return user.spotify_access_token, user.spotify_refresh_token

    def build_player_options(self, correct_username, count=4):
        if not correct_username:
            return random.sample(
                self.answer_options,
                k=min(len(self.answer_options), count),
            )

        others = [name for name in self.answer_options if name != correct_username]
        wrong_count = min(len(others), count - 1)
        options = random.sample(others, k=wrong_count) + [correct_username]
        random.shuffle(options)
        return options

    def build_year_options(self, correct_year):
        year = int(correct_year)
        wrong_years = set()

        while len(wrong_years) < 3:
            offset = random.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5])
            candidate = str(year + offset)
            if candidate != correct_year:
                wrong_years.add(candidate)

        options = list(wrong_years) + [correct_year]
        random.shuffle(options)
        return options

    def build_artist_options(self, correct_artist, other_artists, count=4):
        pool = [name for name in other_artists if name and name != correct_artist]
        wrong_count = min(len(pool), count - 1)
        options = random.sample(pool, k=wrong_count) + [correct_artist]
        random.shuffle(options)
        return options

    def build_song_options(self, correct_song, other_songs, count=4):
        pool = [name for name in other_songs if name and name != correct_song]
        wrong_count = min(len(pool), count - 1)
        options = random.sample(pool, k=wrong_count) + [correct_song]
        random.shuffle(options)
        return options

    def track_summary(self, track):
        artists = track.get("artists", [])
        artist_names = [
            artist.get("name")
            for artist in artists
            if artist.get("name")
        ]
        album = track.get("album", {})
        images = album.get("images") or []

        return {
            "name": track.get("name"),
            "artists": artist_names,
            "artist": artist_names[0] if artist_names else "Unknown",
            "popularity": track.get("popularity"),
            "image": images[0]["url"] if images else None,
        }

    def build_song_clues(self, track: dict):
        artists = track.get("artists", [])
        artist_names = [
            artist.get("name")
            for artist in artists
            if artist.get("name")
        ]

        album_name = track.get("album", {}).get("name")
        release_year = (track.get("album", {}).get("release_date") or "")[:4]

        duration_ms = track.get("duration_ms")
        duration_seconds = (
            round(duration_ms / 1000)
            if duration_ms
            else None
        )

        clues = [
            {
                "number": 1,
                "text": f"The song is from the album '{album_name}'",
            }
            if album_name
            else None,
            {
                "number": 2,
                "text": f"It was released in {release_year}",
            }
            if release_year
            else None,
            {
                "number": 3,
                "text": f"The track length is about {duration_seconds} seconds",
            }
            if duration_seconds
            else None,
            {
                "number": 4,
                "text": f"The main artist is {artist_names[0]}",
            }
            if artist_names
            else None,
            {
                "number": 5,
                "text": f"The song title is '{track.get('name')}'",
            },
        ]

        return [clue for clue in clues if clue]

    async def get_tracks_for_user(self, user, limit=50):
        access_token, refresh_token = self.get_spotify_tokens(user)
        return await self.spotify_requests.get_users_top_tracks(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Higher or Lower
    # ------------------------------------------------------------------

    async def create_higher_or_lower_questions(self, question_count=15):
        selected_user = self.pick_random_user()
        if not selected_user:
            return []

        tracks = await self.get_tracks_for_user(selected_user, limit=50)
        if len(tracks) < 2:
            return []

        random.shuffle(tracks)
        questions = []

        for index in range(min(question_count, len(tracks) - 1)):
            track_a = tracks[index]
            track_b = tracks[index + 1]

            pop_a = track_a.get("popularity", 0)
            pop_b = track_b.get("popularity", 0)

            if pop_a == pop_b:
                continue

            answer = "Higher" if pop_b > pop_a else "Lower"

            questions.append(
                {
                    "type": "higher_or_lower",
                    "question": "Is the next song higher or lower on the charts?",
                    "track_a": self.track_summary(track_a),
                    "track_b": self.track_summary(track_b),
                    "answer": answer,
                    "options": ["Higher", "Lower"],
                }
            )

        return questions

    # ------------------------------------------------------------------
    # Whats the song?
    # ------------------------------------------------------------------

    async def create_guess_the_song_questions(self, question_count=15):
        selected_user = self.pick_random_user()
        if not selected_user:
            return []

        access_token, refresh_token = self.get_spotify_tokens(selected_user)

        songs = await self.spotify_requests.get_random_songs(
            access_token,
            refresh_token,
            selected_user,
            question_count,
        )

        all_song_names = [
            track.get("name")
            for track in songs
            if isinstance(track, dict) and track.get("name")
        ]

        questions = []

        for song in songs:
            track = (
                song.get("track")
                if isinstance(song, dict) and "track" in song
                else song
            )

            if not isinstance(track, dict) or not track.get("name"):
                continue

            song_name = track.get("name")

            questions.append(
                {
                    "type": "guess_the_song",
                    "question": "What song is this?",
                    "song_name": song_name,
                    "clues": self.build_song_clues(track),
                    "answer": song_name,
                    "options": self.build_song_options(song_name, all_song_names),
                }
            )

        return questions

    # ------------------------------------------------------------------
    # Who Listened To This?
    # ------------------------------------------------------------------

    async def create_who_listened_questions(self, question_count=15):
        user_tracks = []

        for user in self.spotify_users:
            access_token, refresh_token = self.get_spotify_tokens(user)
            tracks = await self.spotify_requests.get_recently_played(
                access_token,
                refresh_token,
                user,
                limit=20,
            )

            if tracks and user.username:
                user_tracks.append((user, tracks))

        if not user_tracks:
            return []

        random.shuffle(user_tracks)
        questions = []

        for user, tracks in user_tracks:
            if len(questions) >= question_count:
                break

            track = random.choice(tracks)
            summary = self.track_summary(track)

            questions.append(
                {
                    "type": "who_listened",
                    "question": (
                        f"Who recently listened to '{summary['name']}' "
                        f"by {summary['artist']}?"
                    ),
                    "track": summary,
                    "answer": user.username,
                    "options": self.build_player_options(user.username),
                }
            )

        while len(questions) < question_count and user_tracks:
            user, tracks = random.choice(user_tracks)
            track = random.choice(tracks)
            summary = self.track_summary(track)

            questions.append(
                {
                    "type": "who_listened",
                    "question": (
                        f"Who recently listened to '{summary['name']}' "
                        f"by {summary['artist']}?"
                    ),
                    "track": summary,
                    "answer": user.username,
                    "options": self.build_player_options(user.username),
                }
            )

        return questions[:question_count]

    # ------------------------------------------------------------------
    # Get that year
    # ------------------------------------------------------------------

    async def create_get_that_year_questions(self, question_count=15):
        selected_user = self.pick_random_user()
        if not selected_user:
            return []

        tracks = await self.get_tracks_for_user(selected_user, limit=50)
        random.shuffle(tracks)

        questions = []

        for track in tracks:
            if len(questions) >= question_count:
                break

            release_year = (track.get("album", {}).get("release_date") or "")[:4]
            if not release_year.isdigit():
                continue

            summary = self.track_summary(track)

            questions.append(
                {
                    "type": "get_that_year",
                    "question": (
                        f"What year was '{summary['name']}' "
                        f"by {summary['artist']} released?"
                    ),
                    "track": summary,
                    "answer": release_year,
                    "options": self.build_year_options(release_year),
                }
            )

        return questions

    # ------------------------------------------------------------------
    # Guess the Artist
    # ------------------------------------------------------------------

    async def create_guess_the_artist_questions(self, question_count=15):
        selected_user = self.pick_random_user()
        if not selected_user:
            return []

        access_token, refresh_token = self.get_spotify_tokens(selected_user)

        tracks = await self.get_tracks_for_user(selected_user, limit=50)
        top_artists = await self.spotify_requests.get_users_top_artists(
            access_token=access_token,
            refresh_token=refresh_token,
            user=selected_user,
            limit=50,
        )

        artist_pool = [
            artist.get("name")
            for artist in top_artists
            if artist.get("name")
        ]

        random.shuffle(tracks)
        questions = []

        for track in tracks:
            if len(questions) >= question_count:
                break

            summary = self.track_summary(track)
            correct_artist = summary["artist"]

            if not correct_artist or correct_artist == "Unknown":
                continue

            questions.append(
                {
                    "type": "guess_the_artist",
                    "question": f"Who is the artist of '{summary['name']}'?",
                    "track": summary,
                    "answer": correct_artist,
                    "options": self.build_artist_options(correct_artist, artist_pool),
                }
            )

        return questions

    # ------------------------------------------------------------------
    # Music Trivia
    # ------------------------------------------------------------------

    def create_music_trivia_questions(self, question_count=15):
        selected = random.sample(
            MUSIC_TRIVIA,
            k=min(question_count, len(MUSIC_TRIVIA)),
        )

        return [
            {
                "type": "music_trivia",
                "question": item["question"],
                "answer": item["answer"],
                "options": item["options"],
            }
            for item in selected
        ]

    # ------------------------------------------------------------------
    # Guess Who? (Playlist)
    # ------------------------------------------------------------------

    async def load_playlists(self):
        if self.playlists:
            return

        for user in self.spotify_users:
            access_token, refresh_token = self.get_spotify_tokens(user)

            playlists = await self.spotify_requests.get_user_playlists(
                access_token,
                refresh_token,
                user,
            )

            for playlist in playlists or []:
                self.playlists.append(
                    {
                        **playlist,
                        "library_username": user.username,
                        "library_user_id": user.id,
                        "library_access_token": access_token,
                        "library_refresh_token": refresh_token,
                    }
                )

        random.shuffle(self.playlists)

    async def create_playlist_question(self):
        await self.load_playlists()

        available = [
            playlist
            for playlist in self.playlists
            if playlist.get("id") not in self.used_playlist_ids
            and playlist.get("library_username")
        ]

        if not available:
            return None

        playlist = random.choice(available)
        self.used_playlist_ids.add(playlist.get("id"))

        library_username = playlist["library_username"]
        playlist_name = playlist.get("name") or "Untitled playlist"
        total_playlists = len(self.playlists) or 1
        hard_round = self.playlist_question_count >= total_playlists // 2
        self.playlist_question_count += 1

        question_data = {
            "type": "guess_playlist_owner",
            "playlist_name": playlist_name,
            "answer": library_username,
            "options": self.build_player_options(library_username),
        }

        if hard_round:
            library_user = next(
                (
                    user
                    for user in self.spotify_users
                    if user.id == playlist["library_user_id"]
                ),
                None,
            )

            tracks = []
            if library_user:
                tracks = await self.spotify_requests.get_playlist_tracks(
                    playlist["library_access_token"],
                    playlist["library_refresh_token"],
                    library_user,
                    playlist["id"],
                    limit=50,
                )

            if tracks:
                track = random.choice(tracks)
                summary = self.track_summary(track)
                question_data["track"] = summary
                question_data["question"] = (
                    f"Whose library contains a playlist with the song "
                    f"'{summary['name']}' by {summary['artist']}?"
                )
                question_data["difficulty"] = "hard"
            else:
                question_data["question"] = (
                    f"Whose library contains the playlist '{playlist_name}'?"
                )
                question_data["difficulty"] = "easy"
        else:
            question_data["question"] = (
                f"Whose library contains the playlist '{playlist_name}'?"
            )
            question_data["difficulty"] = "easy"

        return question_data

    async def create_playlist_questions(self):
        await self.load_playlists()

        questions = []

        while True:
            question = await self.create_playlist_question()
            if not question:
                break
            questions.append(question)

        return questions

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    async def create_questions_for_game_mode(self):
        if self.game_mode == "Higher or Lower":
            return await self.create_higher_or_lower_questions()

        if self.game_mode == "Whats the song?":
            return await self.create_guess_the_song_questions()

        if self.game_mode == "Who Listened To This?":
            return await self.create_who_listened_questions()

        if self.game_mode == "Get that year":
            return await self.create_get_that_year_questions()

        if self.game_mode == "Guess the Artist":
            return await self.create_guess_the_artist_questions()

        if self.game_mode == "Music Trivia":
            return self.create_music_trivia_questions()

        if self.game_mode == "Guess who? (Playlist)":
            return await self.create_playlist_questions()

        return []
