import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";

export function SpotifySearch({ onSelect = () => {} }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  async function searchSongs(searchTerm) {
    if (!searchTerm) {
      setResults([]);
      return;
    }

    try {
      setLoading(true);

      const data = await apiFetch(
        `/spotify/requests/search/songs?q=${encodeURIComponent(searchTerm)}`
      );

      setResults(data || []);

    } catch (error) {
      console.error("Spotify search failed:", error);
      setResults([]);

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    if (!query) {
      setResults([]);
      return;
    }

    const timer = setTimeout(() => {
      searchSongs(query);
    }, 500);


    return () => clearTimeout(timer);

  }, [query]);


  return (
    <div className="space-y-4">

      <input
        className="input input-bordered w-full"
        placeholder="Search Spotify..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />


      {loading && (
        <div className="flex justify-center">
          <span className="loading loading-spinner" />
        </div>
      )}


      <div className="space-y-2">

        {results.map((track) => (
          <button
            key={track.id}
            className="
              w-full
              flex
              items-center
              gap-4
              p-3
              rounded-lg
              bg-base-200
              hover:bg-base-300
              transition
            "
            onClick={() => onSelect(track)}
          >

            <img
              src={track.image || "/favicon.svg"}
              className="w-12 h-12 rounded object-cover"
              alt={track.name}
              onError={(e) => {
                e.currentTarget.src = "/favicon.svg";
              }}
            />


            <div className="text-left">

              <p className="font-bold">
                {track.name}
              </p>

              <p className="text-sm opacity-70">
                {track.artist}
              </p>

            </div>

          </button>
        ))}

      </div>


      {!loading && query && results.length === 0 && (
        <p className="text-sm opacity-70">
          No songs found
        </p>
      )}

    </div>
  );
}