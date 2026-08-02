import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useRoomSocket } from "./hooks/useRoomSocket";
import { SpotifySearch } from "./components/Search";

const QUESTION_TYPE_LABELS = {
  guess_the_song: { icon: "🎷", label: "Whats the song?" },
  who_listened: { icon: "🕵️", label: "Who Listened To This?" },
  get_that_year: { icon: "📅", label: "Guess the Year" },
  guess_the_artist: { icon: "🎤", label: "Guess the Artist" },
  guess_playlist_owner: { icon: "📋", label: "Guess who? (Playlist)" },
  match_the_year: { icon: "🎯", label: "Find a Song From the Year" },
  playlist_vibe: { icon: "🎶", label: "Playlist Vibes" },
  cover_art_blur: { icon: "🖼️", label: "Cover Art Blur" },
  taste_twins: { icon: "👯", label: "Taste Twins" },
};

function TrackCard({ track, label, hideArtist = false }) {
  if (!track) return null;

  return (
    <div className="bg-base-100 rounded-box p-4 flex items-center gap-4 border border-base-300">
      {track.image ? (
        <img
          src={track.image}
          alt={track.name}
          className="w-16 h-16 rounded-box object-cover shadow-md shrink-0"
        />
      ) : (
        <div className="w-16 h-16 rounded-box bg-base-300 flex items-center justify-center text-2xl shrink-0">
          🎵
        </div>
      )}
      <div className="flex-1 min-w-0">
        {label ? <p className="text-xs opacity-60 uppercase">{label}</p> : null}
        <p className="font-display font-bold text-lg break-words">{track.name}</p>
        {!hideArtist ? (
          <p className="text-sm opacity-70 break-words">{track.artist || track.artists?.join(", ")}</p>
        ) : null}
      </div>
    </div>
  );
}

function Game() {
  const navigate = useNavigate();
  const { roomCode } = useParams();

  const safeRoomCode = roomCode?.toUpperCase() || "ROOM";

  const { connected, error, messages, sendMessage, players } = useRoomSocket(
    roomCode || "",
  );

  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(true);
  const [selectedOption, setSelectedOption] = useState(null);
  const [selectedTrack, setSelectedTrack] = useState(null);
  const [revealedAnswer, setRevealedAnswer] = useState(null);
  const [revealedExtra, setRevealedExtra] = useState(null);
  const [scores, setScores] = useState([]);
  const [answeredPlayers, setAnsweredPlayers] = useState([]);
  const [hasAnswered, setHasAnswered] = useState(false);
  const [visibleClues, setVisibleClues] = useState(0);
  const [gameOver, setGameOver] = useState(false);
  const [clueCountdown, setClueCountdown] = useState(0);
  const [blurStage, setBlurStage] = useState(1);
  const [blurCountdown, setBlurCountdown] = useState(0);
  const [playerReveals, setPlayerReveals] = useState([]);
  const [roundScores, setRoundScores] = useState([]);
  const [numberGuess, setNumberGuess] = useState("");
  const processedMessageCount = useRef(0);

  useEffect(() => {
    if (!players.length) return;

    setScores((currentScores) => {
      return players.map((player) => {
        const existingScore = currentScores.find(
          (score) => score.id === player.id,
        );

        return {
          id: player.id,
          name:
            player.display_name ||
            player.username ||
            player.name ||
            `User ${player.id}`,
          score: player.score != null ? player.score : (existingScore ? existingScore.score : 0),
        };
      });
    });
  }, [players]);

  useEffect(() => {
    if (currentQuestion?.type !== "guess_the_song") return;

    const maxClues = currentQuestion.clues?.length || 0;

    setVisibleClues(1);
    setClueCountdown(maxClues > 1 ? 5 : 0);

    const revealInterval = setInterval(() => {
      setVisibleClues((count) => {
        if (count >= maxClues) {
          clearInterval(revealInterval);
          return count;
        }

        const next = count + 1;
        setClueCountdown(next < maxClues ? 5 : 0);
        return next;
      });
    }, 5000);

    const countdownInterval = setInterval(() => {
      setClueCountdown((seconds) => (seconds > 0 ? seconds - 1 : 0));
    }, 1000);

    return () => {
      clearInterval(revealInterval);
      clearInterval(countdownInterval);
    };
  }, [currentQuestion]);

  useEffect(() => {
    if (currentQuestion?.type !== "cover_art_blur") return;

    const maxStages = currentQuestion.blur_stages || 5;

    setBlurStage(1);
    setBlurCountdown(maxStages > 1 ? 4 : 0);

    const revealInterval = setInterval(() => {
      setBlurStage((stage) => {
        if (stage >= maxStages) {
          clearInterval(revealInterval);
          return stage;
        }

        const next = stage + 1;
        setBlurCountdown(next < maxStages ? 4 : 0);
        return next;
      });
    }, 4000);

    const countdownInterval = setInterval(() => {
      setBlurCountdown((seconds) => (seconds > 0 ? seconds - 1 : 0));
    }, 1000);

    return () => {
      clearInterval(revealInterval);
      clearInterval(countdownInterval);
    };
  }, [currentQuestion]);

  useEffect(() => {
    for (let i = processedMessageCount.current; i < messages.length; i++) {
      const message = messages[i];

      switch (message.type) {
        case "player_answered":
          setAnsweredPlayers((prev) =>
            prev.includes(message.user) ? prev : [...prev, message.user],
          );
          break;

        case "score_update":
          setScores(
            message.scores.map((player) => ({
              id: player.id,
              name: player.name || player.username,
              score: player.score,
            })),
          );
          break;

        case "question":
          setCurrentQuestion(message.question);
          setSelectedOption(null);
          setSelectedTrack(null);
          setHasAnswered(false);
          setRevealedAnswer(null);
          setRevealedExtra(null);
          setAnsweredPlayers([]);
          setVisibleClues(0);
          setIsLoadingQuestions(false);
          setGameOver(false);
          setPlayerReveals([]);
          setRoundScores([]);
          setBlurStage(1);
          setBlurCountdown(0);
          setNumberGuess("");
          break;

        case "player_reveal":
          setPlayerReveals((prev) => [
            ...prev,
            {
              userId: message.user_id,
              name: message.name,
              trackName: message.track_name,
              trackArtist: message.track_artist,
              year: message.year,
              yearsOff: message.years_off,
              guess: message.guess,
              points: message.points,
            },
          ]);
          break;

        case "answer":
          setRevealedAnswer(message.answer);
          setRevealedExtra(message.reveal_extra || null);
          if (message.round_scores) {
            setRoundScores(
              message.round_scores.map((entry) => ({
                userId: entry.user_id,
                name: entry.name,
                points: entry.points,
              })),
            );
          }
          break;

        case "game_over":
          setGameOver(true);
          setIsLoadingQuestions(false);
          if (message.scores) {
            setScores(
              message.scores.map((player) => ({
                id: player.id,
                name: player.name || player.username,
                score: player.score,
              })),
            );
          }
          break;

        default:
          break;
      }
    }

    processedMessageCount.current = messages.length;
  }, [messages]);

  function renderQuestionContent() {
    if (!currentQuestion) return null;

    switch (currentQuestion.type) {
      case "guess_the_song":
        return (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 justify-between items-center">
              <p className="text-sm opacity-70 min-w-0">
                Clues revealed: {visibleClues}/{currentQuestion.clues?.length || 0}
              </p>
              {clueCountdown > 0 ? (
                <span className="badge badge-outline badge-accent shrink-0">
                  Next clue in {clueCountdown}s
                </span>
              ) : null}
            </div>
            <p className="text-xs opacity-50">
              You can answer at any time — you don't have to wait for the next clue.
            </p>
            {currentQuestion.clues?.slice(0, visibleClues).map((clue) => (
              <div key={clue.number} className="alert alert-info">
                <span>Clue {clue.number}: {clue.text}</span>
              </div>
            ))}
          </div>
        );

      case "cover_art_blur": {
        const maxStages = currentQuestion.blur_stages || 5;
        const blurPx = Math.max(0, (maxStages - blurStage) * 4);

        return (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 justify-between items-center">
              <p className="text-sm opacity-70 min-w-0">
                Coming into focus: {blurStage}/{maxStages}
              </p>
              {blurCountdown > 0 ? (
                <span className="badge badge-outline badge-accent shrink-0">
                  Sharper in {blurCountdown}s
                </span>
              ) : null}
            </div>
            <p className="text-xs opacity-50">
              You can answer at any time — the blurrier it still is, the more points you score.
            </p>
            <div className="flex justify-center">
              {currentQuestion.track?.image ? (
                <img
                  src={currentQuestion.track.image}
                  alt="Album cover"
                  className="w-48 h-48 rounded-box object-cover shadow-lg"
                  style={{ filter: `blur(${blurPx}px)`, transition: "filter 0.6s ease" }}
                />
              ) : (
                <div className="w-48 h-48 rounded-box bg-base-300 flex items-center justify-center text-4xl">
                  🎵
                </div>
              )}
            </div>
          </div>
        );
      }

      case "playlist_vibe":
        return (
          <div className="space-y-3">
            {currentQuestion.tracks?.map((track, index) => (
              <TrackCard key={`${track.name}-${index}`} track={track} />
            ))}
          </div>
        );

      case "who_listened":
      case "get_that_year":
        return <TrackCard track={currentQuestion.track} />;

      case "guess_the_artist":
        return <TrackCard track={currentQuestion.track} hideArtist />;

      case "match_the_year":
        return (
          <div className="space-y-3">
            <div className="text-center">
              <p className="text-xs uppercase tracking-widest opacity-60">Target year</p>
              <p className="font-display text-5xl font-bold brand-accent">
                {currentQuestion.target_year}
              </p>
            </div>

            {selectedTrack ? (
              <div className="bg-base-100 rounded-lg p-4 flex items-center gap-4 border border-primary/40">
                {selectedTrack.image ? (
                  <img
                    src={selectedTrack.image}
                    alt={selectedTrack.name}
                    className="w-16 h-16 rounded-lg object-cover"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-lg bg-base-300 flex items-center justify-center text-2xl">
                    🎵
                  </div>
                )}
                <div className="flex-1">
                  <p className="font-display font-bold text-lg">{selectedTrack.name}</p>
                  <p className="text-sm opacity-70">{selectedTrack.artist}</p>
                </div>
                {!hasAnswered ? (
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={() => setSelectedTrack(null)}
                  >
                    Change
                  </button>
                ) : null}
              </div>
            ) : !hasAnswered ? (
              <SpotifySearch onSelect={setSelectedTrack} />
            ) : (
              <p className="text-sm opacity-60">No song selected.</p>
            )}

            {playerReveals.length > 0 && (
              <div className="space-y-2 mt-2">
                <p className="text-xs uppercase tracking-widest opacity-60">Reveal</p>
                {playerReveals.map((reveal) => (
                  <div
                    key={reveal.userId}
                    className="bg-base-100 rounded-lg p-3 border border-base-300 flex gap-2 justify-between items-center pop-in"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-sm truncate">{reveal.name}</p>
                      <p className="text-sm opacity-70 break-words">
                        {reveal.trackName
                          ? `${reveal.trackName} (${reveal.year})`
                          : "No pick submitted"}
                      </p>
                    </div>
                    <span className={`badge shrink-0 ${reveal.points < 0 ? "badge-error" : "badge-primary"}`}>
                      {reveal.points > 0 ? `+${reveal.points}` : reveal.points}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "guess_playlist_owner":
        return (
          <div className="space-y-3">
            {currentQuestion.difficulty === "hard" && currentQuestion.track ? (
              <TrackCard track={currentQuestion.track} label="Song from playlist" />
            ) : (
              <div className="bg-base-100 rounded-box p-4 border border-base-300">
                <p className="text-xs opacity-60 uppercase">Playlist</p>
                <p className="font-display font-bold text-xl break-words">{currentQuestion.playlist_name}</p>
              </div>
            )}
          </div>
        );

      case "taste_twins":
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-4">
              <div className="bg-base-100 rounded-box border border-base-300 px-5 py-4 text-center flex-1">
                <p className="font-display font-bold text-lg break-words">{currentQuestion.player_a_name}</p>
              </div>
              <span className="text-2xl font-bold opacity-50 shrink-0">🆚</span>
              <div className="bg-base-100 rounded-box border border-base-300 px-5 py-4 text-center flex-1">
                <p className="font-display font-bold text-lg break-words">{currentQuestion.player_b_name}</p>
              </div>
            </div>

            {!hasAnswered ? (
              <div className="flex flex-col items-center gap-2">
                <label className="text-sm opacity-70">Your guess (0 or more)</label>
                <input
                  type="number"
                  min={0}
                  max={50}
                  value={numberGuess}
                  onChange={(e) => setNumberGuess(e.target.value)}
                  className="input input-bordered input-lg w-32 text-center font-display font-bold text-2xl"
                  placeholder="?"
                />
              </div>
            ) : (
              <p className="text-center text-sm opacity-60">
                Your guess: {numberGuess}
              </p>
            )}

            {playerReveals.length > 0 && (
              <div className="space-y-2 mt-2">
                <p className="text-xs uppercase tracking-widest opacity-60 text-center">Guesses</p>
                {playerReveals.map((reveal) => (
                  <div
                    key={reveal.userId}
                    className="bg-base-100 rounded-lg p-3 border border-base-300 flex gap-2 justify-between items-center pop-in"
                  >
                    <span className="text-sm font-medium truncate min-w-0">{reveal.name}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-sm opacity-70">
                        guessed {reveal.guess != null ? reveal.guess : "—"}
                      </span>
                      <span className={`badge ${reveal.points < 0 ? "badge-error" : "badge-primary"}`}>
                        {reveal.points > 0 ? `+${reveal.points}` : reveal.points}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  }

  const questionMeta = currentQuestion
    ? QUESTION_TYPE_LABELS[currentQuestion.type] || { icon: "🎲", label: currentQuestion.type }
    : null;

  const sortedScores = scores.slice().sort((a, b) => b.score - a.score);
  const isSearchMode = currentQuestion?.type === "match_the_year";
  const isNumberMode = currentQuestion?.type === "taste_twins";
  const canSubmit = isSearchMode
    ? Boolean(selectedTrack)
    : isNumberMode
      ? numberGuess !== "" && !Number.isNaN(Number(numberGuess))
      : Boolean(selectedOption);

  function handleSubmit() {
    let answer;

    if (isSearchMode) {
      answer = {
        name: selectedTrack.name,
        artist: selectedTrack.artist,
        year: selectedTrack.release_year,
      };
    } else if (isNumberMode) {
      answer = Number(numberGuess);
    } else if (currentQuestion?.type === "guess_the_song") {
      answer = {
        option: selectedOption,
        clues_shown: visibleClues,
      };
    } else if (currentQuestion?.type === "cover_art_blur") {
      answer = {
        option: selectedOption,
        blur_stage: blurStage,
      };
    } else {
      answer = selectedOption;
    }

    sendMessage({
      type: "submit_answer",
      answer,
    });
    setHasAnswered(true);
  }

  return (
    <main className="min-h-screen p-4 sm:p-6">
      <div className="max-w-6xl mx-auto grid lg:grid-cols-4 gap-6">
        <aside className="card bg-base-200 border border-base-300 shadow-xl lg:col-span-1 h-fit order-2 lg:order-1">
          <div className="card-body">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs opacity-60 uppercase tracking-widest">Room</p>
                <h1 className="font-display text-2xl font-bold">{safeRoomCode}</h1>
              </div>
              {connected ? (
                <span className="badge badge-success">Online</span>
              ) : (
                <span className="badge badge-error">Offline</span>
              )}
            </div>

            <div className="divider" />

            <h2 className="font-display font-bold text-lg">Scoreboard</h2>

            <div className="space-y-3">
              {sortedScores.length === 0 && (
                <p className="opacity-50 text-sm">Waiting for scores...</p>
              )}

              {sortedScores.map((player, index) => (
                <div
                  key={player.id}
                  className={`flex justify-between items-center rounded-lg p-3 border ${
                    index === 0
                      ? "bg-primary/10 border-primary/40"
                      : "bg-base-100 border-base-300"
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-lg shrink-0">
                      {index === 0
                        ? "🥇"
                        : index === 1
                          ? "🥈"
                          : index === 2
                            ? "🥉"
                            : `#${index + 1}`}
                    </span>
                    <span className="font-medium truncate">{player.name}</span>
                  </div>
                  <span className="font-display font-bold text-lg shrink-0 ml-2">{player.score}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <section className="card bg-base-200 border border-base-300 shadow-xl lg:col-span-3 order-1 lg:order-2">
          <div className="card-body">
            {error && <div className="alert alert-error">{error}</div>}

            {gameOver ? (
              <div className="flex flex-col items-center py-20">
                <h2 className="font-display text-3xl font-bold mb-2">Game Over</h2>
                <p className="opacity-70 mb-6">
                  Scores carry over — head back to the room to pick another game mode.
                </p>
                <button
                  className="btn btn-primary btn-lg"
                  onClick={() => navigate("/dashboard")}
                >
                  Back to Room
                </button>
              </div>
            ) : isLoadingQuestions ? (
              <div className="flex flex-col items-center py-20">
                <span className="loading loading-spinner loading-lg text-primary" />
                <p className="mt-4">Generating question...</p>
              </div>
            ) : (
              currentQuestion && (
                <>
                  <div className="bg-base-100 rounded-lg p-4 flex flex-wrap gap-2 justify-between items-center border border-base-300">
                    <div>
                      <p className="font-semibold text-sm opacity-70">Answers submitted</p>
                      <p className="font-display font-bold text-lg">
                        {answeredPlayers.length}/{players.length}
                      </p>
                    </div>
                    <div className="flex gap-2 flex-wrap justify-end">
                      {answeredPlayers.map((player) => (
                        <span key={player} className="badge badge-success">
                          {player}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="bg-base-100 rounded-lg p-6 border border-base-300 mt-4">
                    {questionMeta ? (
                      <span className="badge badge-primary gap-1">
                        {questionMeta.icon} {questionMeta.label}
                      </span>
                    ) : null}
                    <h2 className="font-display text-xl sm:text-2xl font-bold mt-4 break-words">
                      {currentQuestion.question}
                    </h2>
                    <div className="mt-4">{renderQuestionContent()}</div>
                  </div>

                  {revealedAnswer && (
                    <div className="alert alert-info mt-4">
                      <div className="min-w-0">
                        <p className="font-display font-bold">Correct answer</p>
                        <p className="break-words">{revealedAnswer}</p>
                        {revealedExtra ? <p className="text-sm mt-1 break-words">{revealedExtra}</p> : null}
                      </div>
                    </div>
                  )}

                  {!isSearchMode && !isNumberMode && (
                    <div className="grid gap-3 mt-4">
                      {currentQuestion.options?.map((option, index) => {
                        const isSelected = selectedOption === option;

                        return (
                          <button
                            key={option}
                            onClick={() => setSelectedOption(option)}
                            disabled={hasAnswered}
                            className={`tile-hover btn btn-lg justify-start gap-3 normal-case h-auto min-h-12 py-2 whitespace-normal ${
                              isSelected ? "btn-primary" : "btn-outline"
                            }`}
                          >
                            <span
                              className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold shrink-0 ${
                                isSelected ? "bg-primary-content text-primary" : "bg-base-300"
                              }`}
                            >
                              {String.fromCharCode(65 + index)}
                            </span>
                            <span className="text-left break-words min-w-0 flex-1">{option}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  <button
                    disabled={!canSubmit || hasAnswered}
                    className="btn btn-success btn-lg w-full mt-4"
                    onClick={handleSubmit}
                  >
                    {hasAnswered ? "Answer Submitted" : "Submit Answer"}
                  </button>

                  {roundScores.length > 0 && (
                    <div className="space-y-2 mt-3">
                      {roundScores.map((entry) => (
                        <div
                          key={entry.userId}
                          className="bg-base-100 rounded-lg p-3 border border-base-300 flex gap-2 justify-between items-center pop-in"
                        >
                          <span className="text-sm font-medium truncate min-w-0">{entry.name}</span>
                          <span className={`badge shrink-0 ${entry.points < 0 ? "badge-error" : entry.points > 0 ? "badge-success" : "badge-ghost"}`}>
                            {entry.points > 0 ? `+${entry.points}` : entry.points}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )
            )}

            {!gameOver && (
              <button
                className="btn btn-ghost mt-6 self-start"
                onClick={() => navigate("/dashboard")}
              >
                Leave Game
              </button>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

export default Game;
