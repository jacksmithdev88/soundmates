import random

from services.spotify_requests import SpotifyRequests


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

        # Cache playlist data so we only hit Spotify once
        self.playlists = []
        self.used_playlist_ids = set()

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

    def build_song_clues(self, track: dict):
        artists = track.get("artists", [])
        artist_names = [
            artist.get("name")
            for artist in artists
            if artist.get("name")
        ]

        album_name = track.get("album", {}).get("name")
        release_year = (
            track.get("album", {}).get("release_date") or ""
        )[:4]

        duration_ms = track.get("duration_ms")
        duration_seconds = (
            round(duration_ms / 1000)
            if duration_ms
            else None
        )

        clues = [
            {
                "number": 1,
                "text": f"The song is from the album '{album_name}'"
            }
            if album_name
            else None,
            {
                "number": 2,
                "text": f"It was released in {release_year}"
            }
            if release_year
            else None,
            {
                "number": 3,
                "text": f"The track length is about {duration_seconds} seconds"
            }
            if duration_seconds
            else None,
            {
                "number": 4,
                "text": f"The main artist is {artist_names[0]}"
            }
            if artist_names
            else None,
            {
                "number": 5,
                "text": f"The song title is '{track.get('name')}'"
            },
        ]

        return [clue for clue in clues if clue]

    # ------------------------------------------------------------------
    # Guess the Song
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

        questions = []

        for song in songs:
            track = (
                song.get("track")
                if isinstance(song, dict) and "track" in song
                else song
            )

            if not isinstance(track, dict):
                continue

            artists = track.get("artists", [])

            artist_names = [
                artist.get("name")
                for artist in artists
                if artist.get("name")
            ]

            questions.append(
                {
                    "type": "guess_the_song",
                    "song_name": track.get("name"),
                    "artist_names": artist_names,
                    "answer": track.get("name"),
                    "clues": self.build_song_clues(track),
                }
            )

        return questions

    # ------------------------------------------------------------------
    # Guess Who? (Playlist)
    # ------------------------------------------------------------------

    async def load_playlists(self):
        """
        Downloads every player's playlists once and caches them.
        """

        if self.playlists:
            return

        for user in self.spotify_users:
            access_token, refresh_token = self.get_spotify_tokens(user)

            playlists = await self.spotify_requests.get_user_playlists(
                access_token,
                refresh_token,
                user,
            )

            if playlists:
                self.playlists.extend(playlists)

        random.shuffle(self.playlists)

    async def create_playlist_question(self):
        """
        Returns ONE random playlist question.
        Returns None when there are no more unused playlists.
        """

        await self.load_playlists()

        available = [
            playlist
            for playlist in self.playlists
            if playlist.get("id") not in self.used_playlist_ids
        ]

        if not available:
            return None

        playlist = random.choice(available)

        self.used_playlist_ids.add(playlist.get("id"))

        owner = playlist.get("owner", {})

        owner_name = (
            owner.get("display_name")
            or owner.get("id")
            or "Unknown"
        )

        playlist_name = (
            playlist.get("name")
            or "Untitled playlist"
        )

        return {
            "type": "guess_playlist_owner",
            "question": f"Who owns the playlist '{playlist_name}'?",
            "playlist_name": playlist_name,
            "playlist": playlist,
            "answer": owner_name,
            "options": random.sample(
                self.answer_options,
                k=min(len(self.answer_options), 4),
            ),
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    async def create_questions_for_game_mode(self):
        if self.game_mode == "Higher or Lower":
            return []

        if self.game_mode == "Whats the song?":
            return await self.create_guess_the_song_questions()

        if self.game_mode == "Guess who? (Playlist)":
            await self.load_playlists()

            questions = []

            while True:
                question = await self.create_playlist_question()

                if not question:
                    break

                questions.append(question)

            return questions
        return []