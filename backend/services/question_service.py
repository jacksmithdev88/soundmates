import itertools
import random

from services.spotify_requests import SpotifyRequests


class QuestionService:
    def __init__(self, game_mode: str, spotify_users, question_count: int = 15):
        self.game_mode = game_mode
        self.spotify_users = spotify_users
        self.question_count = question_count
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

    def mask_title(self, title: str) -> str:
        masked_chars = []
        at_word_start = True

        for char in title:
            if char.isalnum():
                masked_chars.append(char if at_word_start else "_")
                at_word_start = False
            else:
                masked_chars.append(char)
                if char.isspace():
                    at_word_start = True

        return "".join(masked_chars)

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
                "text": f"The title looks like: '{self.mask_title(track.get('name') or '')}'",
            }
            if track.get("name")
            else None,
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
    # Guess the Year
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
    # Find a Song From the Year
    # ------------------------------------------------------------------

    async def create_match_the_year_questions(self, question_count=15):
        candidate_years = []

        for user in self.spotify_users:
            tracks = await self.get_tracks_for_user(user, limit=50)

            for track in tracks:
                release_year = (track.get("album", {}).get("release_date") or "")[:4]
                if release_year.isdigit():
                    candidate_years.append(release_year)

        if not candidate_years:
            return []

        random.shuffle(candidate_years)

        if len(candidate_years) >= question_count:
            selected_years = candidate_years[:question_count]
        else:
            selected_years = [
                random.choice(candidate_years) for _ in range(question_count)
            ]

        return [
            {
                "type": "match_the_year",
                "question": f"Search Spotify and pick a song released in {year}",
                "target_year": year,
            }
            for year in selected_years
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
                try:
                    tracks = await self.spotify_requests.get_playlist_tracks(
                        playlist["library_access_token"],
                        playlist["library_refresh_token"],
                        library_user,
                        playlist["id"],
                        limit=50,
                    )
                except Exception:
                    tracks = []

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

        while len(questions) < self.question_count:
            question = await self.create_playlist_question()
            if not question:
                break
            questions.append(question)

        return questions

    # ------------------------------------------------------------------
    # Playlist Vibes
    # ------------------------------------------------------------------

    async def create_playlist_vibe_questions(self):
        await self.load_playlists()

        available = [
            playlist
            for playlist in self.playlists
            if playlist.get("library_username")
        ]

        questions = []

        for playlist in available:
            if len(questions) >= self.question_count:
                break

            if playlist.get("id") in self.used_playlist_ids:
                continue

            library_user = next(
                (
                    user
                    for user in self.spotify_users
                    if user.id == playlist["library_user_id"]
                ),
                None,
            )

            if not library_user:
                continue

            try:
                tracks = await self.spotify_requests.get_playlist_tracks(
                    playlist["library_access_token"],
                    playlist["library_refresh_token"],
                    library_user,
                    playlist["id"],
                    limit=50,
                )
            except Exception:
                # Some playlists (Spotify-owned/algorithmic, or ones the
                # user follows but doesn't own) return errors when fetching
                # tracks. Skip them rather than let one bad playlist crash
                # the whole round.
                continue

            if len(tracks) < 3:
                continue

            self.used_playlist_ids.add(playlist.get("id"))
            sample_tracks = random.sample(tracks, 3)
            library_username = playlist["library_username"]

            questions.append(
                {
                    "type": "playlist_vibe",
                    "question": "Whose playlist has these three songs?",
                    "tracks": [self.track_summary(track) for track in sample_tracks],
                    "answer": library_username,
                    "options": self.build_player_options(library_username),
                }
            )

        return questions

    # ------------------------------------------------------------------
    # Cover Art Blur
    # ------------------------------------------------------------------

    async def create_cover_art_blur_questions(self, question_count=15):
        selected_user = self.pick_random_user()
        if not selected_user:
            return []

        tracks = await self.get_tracks_for_user(selected_user, limit=50)
        tracks = [
            track
            for track in tracks
            if track.get("name") and track.get("album", {}).get("images")
        ]

        if not tracks:
            return []

        all_song_names = [track.get("name") for track in tracks]

        random.shuffle(tracks)
        questions = []

        for track in tracks:
            if len(questions) >= question_count:
                break

            summary = self.track_summary(track)

            questions.append(
                {
                    "type": "cover_art_blur",
                    "question": "What song is behind this cover art?",
                    "track": summary,
                    "answer": summary["name"],
                    "options": self.build_song_options(summary["name"], all_song_names),
                    "blur_stages": 5,
                }
            )

        return questions

    # ------------------------------------------------------------------
    # Taste Twins
    # ------------------------------------------------------------------

    async def create_taste_twins_questions(self):
        if len(self.spotify_users) < 2:
            return []

        artist_sets = {}

        for user in self.spotify_users:
            access_token, refresh_token = self.get_spotify_tokens(user)

            top_artists = await self.spotify_requests.get_users_top_artists(
                access_token=access_token,
                refresh_token=refresh_token,
                user=user,
                limit=50,
            )

            artist_sets[user.id] = {
                artist.get("name")
                for artist in top_artists
                if artist.get("name")
            }

        pairs = list(itertools.combinations(self.spotify_users, 2))
        if not pairs:
            return []

        random.shuffle(pairs)

        questions = []

        # One round per unique pair, no repeats — round count is naturally
        # capped by how many players are in the room, not a chosen number.
        for player_a, player_b in pairs:
            overlap = len(
                artist_sets.get(player_a.id, set())
                & artist_sets.get(player_b.id, set())
            )

            name_a = player_a.username or "Player A"
            name_b = player_b.username or "Player B"

            questions.append(
                {
                    "type": "taste_twins",
                    "question": (
                        f"How many artists do {name_a} and {name_b} "
                        f"both have in their Top Artists?"
                    ),
                    "player_a_name": name_a,
                    "player_b_name": name_b,
                    "target_overlap": overlap,
                }
            )

        return questions

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    async def create_questions_for_game_mode(self):
        if self.game_mode == "Whats the song?":
            return await self.create_guess_the_song_questions(self.question_count)

        if self.game_mode == "Who Listened To This?":
            return await self.create_who_listened_questions(self.question_count)

        if self.game_mode == "Guess the Year":
            return await self.create_get_that_year_questions(self.question_count)

        if self.game_mode == "Guess the Artist":
            return await self.create_guess_the_artist_questions(self.question_count)

        if self.game_mode == "Guess who? (Playlist)":
            return await self.create_playlist_questions()

        if self.game_mode == "Find a Song From the Year":
            return await self.create_match_the_year_questions(self.question_count)

        if self.game_mode == "Playlist Vibes":
            return await self.create_playlist_vibe_questions()

        if self.game_mode == "Cover Art Blur":
            return await self.create_cover_art_blur_questions(self.question_count)

        if self.game_mode == "Taste Twins":
            return await self.create_taste_twins_questions()

        return []
