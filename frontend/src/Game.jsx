import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useRoomSocket } from "./hooks/useRoomSocket";

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

  const [revealedAnswer, setRevealedAnswer] = useState(null);

  const [scores, setScores] = useState([]);

  const [answeredPlayers, setAnsweredPlayers] = useState([]);

  const [hasAnswered, setHasAnswered] = useState(false);

  // Create scoreboard when players join

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

          // keep existing score
          score: existingScore ? existingScore.score : 0,
        };
      });
    });
  }, [players]);
  // Handle game messages

  useEffect(() => {
    const latest = messages[messages.length - 1];

    if (!latest) return;

    switch (latest.type) {
      case "player_answered":
        setAnsweredPlayers((prev) =>
          prev.includes(latest.user) ? prev : [...prev, latest.user],
        );

        break;

      case "score_update":
        setScores(
          latest.scores.map((player) => ({
            id: player.id,
            name: player.name || player.username,
            score: player.score,
          })),
        );

        console.log(latest);

        break;

      case "question":
        console.log("Question received", latest.question);

        setCurrentQuestion(latest.question);

        setSelectedOption(null);

        setHasAnswered(false);

        setRevealedAnswer(null);

        setAnsweredPlayers([]);

        setIsLoadingQuestions(false);

        break;

      case "answer":
        setRevealedAnswer(latest.answer);

        break;

      default:
        break;
    }
  }, [messages]);
  return (
    <main className="min-h-screen bg-base-100 p-6">
      <div
        className="
          max-w-6xl
          mx-auto
          grid
          lg:grid-cols-4
          gap-6
        "
      >
        {/* SCOREBOARD */}

        <aside
          className="
            card
            bg-base-200
            shadow-xl
            lg:col-span-1
          "
        >
          <div className="card-body">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs opacity-60">ROOM</p>

                <h1 className="text-2xl font-bold">{safeRoomCode}</h1>
              </div>

              {connected ? (
                <span className="badge badge-success">Online</span>
              ) : (
                <span className="badge badge-error">Offline</span>
              )}
            </div>

            <div className="divider" />

            <h2 className="font-bold text-lg">🏆 Scoreboard</h2>

            <div className="space-y-3">
              {scores.length === 0 && (
                <p className="opacity-50 text-sm">Waiting for scores...</p>
              )}

              {scores
                .slice()
                .sort((a, b) => b.score - a.score)
                .map((player, index) => (
                  <div
                    key={player.id}
                    className="
                        flex
                        justify-between
                        items-center
                        bg-base-100
                        rounded-lg
                        p-3
                      "
                  >
                    <div className="flex items-center gap-2">
                      <span>
                        {index === 0
                          ? "🥇"
                          : index === 1
                            ? "🥈"
                            : index === 2
                              ? "🥉"
                              : `#${index + 1}`}
                      </span>

                      <span className="font-medium">{player.name}</span>
                    </div>

                    <span className="font-bold text-lg">{player.score}</span>
                  </div>
                ))}
            </div>
          </div>
        </aside>

        {/* GAME AREA */}

        <section
          className="
            card
            bg-base-200
            shadow-xl
            lg:col-span-3
          "
        >
          <div className="card-body">
            {error && <div className="alert alert-error">{error}</div>}

            {isLoadingQuestions ? (
              <div
                className="
                    flex
                    flex-col
                    items-center
                    py-20
                  "
              >
                <span className="loading loading-spinner loading-lg" />

                <p className="mt-4">Generating question...</p>
              </div>
            ) : (
              currentQuestion && (
                <>
                  {/* ANSWERS */}

                  <div
                    className="
                      bg-base-100
                      rounded-xl
                      p-4
                      flex
                      justify-between
                      items-center
                    "
                  >
                    <div>
                      <p className="font-bold">Answers submitted</p>

                      <p>
                        {answeredPlayers.length}/{players.length}
                      </p>
                    </div>

                    <div className="flex gap-2 flex-wrap">
                      {answeredPlayers.map((player) => (
                        <span key={player} className="badge badge-success">
                          ✅ {player}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* QUESTION */}

                  <div
                    className="
                      bg-base-100
                      rounded-xl
                      p-6
                    "
                  >
                    <span className="badge badge-primary">
                      {currentQuestion.type}
                    </span>

                    <h2
                      className="
                      text-3xl
                      font-bold
                      mt-4
                    "
                    >
                      {currentQuestion.question}
                    </h2>
                  </div>

                  {/* OPTIONS */}

                  <div className="grid gap-3">
                    {currentQuestion.options?.map((option, index) => (
                      <button
                        key={option}
                        onClick={() => setSelectedOption(option)}
                        className={`
                              btn
                              btn-lg
                              justify-start

                              ${
                                selectedOption === option
                                  ? "btn-primary"
                                  : "btn-outline"
                              }
                            `}
                      >
                        {String.fromCharCode(65 + index)}. {option}
                      </button>
                    ))}
                  </div>

                  <button
                    disabled={!selectedOption || hasAnswered}
                    className="
                      btn
                      btn-success
                      btn-lg
                    "
                    onClick={() => {
                      sendMessage({
                        type: "submit_answer",

                        answer: selectedOption,
                      });

                      setHasAnswered(true);
                    }}
                  >
                    {hasAnswered ? "Answer Submitted" : "Submit Answer"}
                  </button>

                  {revealedAnswer && (
                    <div className="alert alert-info">
                      <div>
                        <p className="font-bold">Correct answer</p>

                        <p>{revealedAnswer}</p>
                      </div>
                    </div>
                  )}
                </>
              )
            )}

            <button
              className="btn btn-ghost mt-6"
              onClick={() => navigate("/dashboard")}
            >
              Leave Game
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}

export default Game;
