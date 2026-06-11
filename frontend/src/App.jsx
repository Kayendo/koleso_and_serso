import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "./api";
import { payloadPlayerName, playerName } from "./playerName";
import { getSocket } from "./socket";
import { runTokenPath } from "./tokenAnimation";
import Board from "./components/Board";
import DiceModal from "./components/DiceModal";
import DiceChoiceModal from "./components/DiceChoiceModal";
import TrinityDiceModal from "./components/TrinityDiceModal";
import RewardSlotModal from "./components/RewardSlotModal";
import WheelModal from "./components/WheelModal";
import PlayerList from "./components/PlayerList";
import QuickMenu from "./components/QuickMenu";
import AdminPanel from "./components/AdminPanel";
import {
  RulesModal,
  HistoryModal,
  StatsModal,
  LoginModal,
  ProfileModal,
} from "./components/Modals";
import SceneBackground from "./ui/SceneBackground";
import NewsTicker from "./ui/NewsTicker";

export default function App() {
  const [cells, setCells] = useState([]);
  const [players, setPlayers] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [accountData, setAccountData] = useState({ players: [] });
  const [hoverCell, setHoverCell] = useState(null);
  const [modal, setModal] = useState(null);
  const [rulesHtml, setRulesHtml] = useState("");
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState([]);
  const [profileData, setProfileData] = useState(null);
  const [turnError, setTurnError] = useState("");

  const [diceSpectacle, setDiceSpectacle] = useState(null);
  const [diceChoice, setDiceChoice] = useState(null);
  const [trinityChoice, setTrinityChoice] = useState(false);
  const [rewardSpins, setRewardSpins] = useState(0);
  const [rewardDiceRolled, setRewardDiceRolled] = useState(false);
  const [rewardSlotOpen, setRewardSlotOpen] = useState(false);
  const [wheelSpectacle, setWheelSpectacle] = useState(null);
  const [wheelHltbItems, setWheelHltbItems] = useState([]);
  const [spinCommand, setSpinCommand] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [wheelMeta, setWheelMeta] = useState(null);
  const [pendingDiceLabel, setPendingDiceLabel] = useState("");
  const [animPositions, setAnimPositions] = useState({});
  const [flyingToken, setFlyingToken] = useState(null);
  const [centerGif, setCenterGif] = useState(null);
  const phaseSigRef = useRef("");
  const wheelSessionRef = useRef(0);
  const pendingPathRef = useRef(null);
  const pendingFinishRef = useRef(null);
  const moveAnimatingRef = useRef(false);
  const diceSpectacleRef = useRef(null);
  const diceWaitRef = useRef(false);
  const awaitingDiceAcceptRef = useRef(false);
  const physicsResolvedRef = useRef(false);
  const diceRollKeyRef = useRef(0);
  const rewardChainRef = useRef(false);
  const extraWheelChainRef = useRef(false);
  const beginRewardWheelsRef = useRef(null);
  const wheelRecoveryRef = useRef(false);
  const syncPlayerStateRef = useRef(null);
  const refreshPlayersRef = useRef(null);
  const applyMoveFinishedRef = useRef(null);
  const queueOrRunMoveRef = useRef(null);
  const finishMoveIfReadyRef = useRef(null);
  const openDiceResultRef = useRef(null);
  const storePendingMoveRef = useRef(null);

  const myIdRef = useRef(null);
  useEffect(() => {
    myIdRef.current = currentUser?.id ?? null;
  }, [currentUser]);

  useEffect(() => {
    diceSpectacleRef.current = diceSpectacle;
  }, [diceSpectacle]);

  const storePendingMove = useCallback((data) => {
    if (!data?.movePath?.length) return;
    pendingPathRef.current = {
      userId: data.userId || data.user?.id,
      fromPosition: data.fromPosition,
      path: data.movePath,
      stepMs: data.stepMs || 550,
      avatarUrl: data.avatarUrl || "/avatars/default.png",
    };
  }, []);

  const openDiceResult = useCallback(
    (data, username, extra = {}) => {
      awaitingDiceAcceptRef.current = true;
      diceWaitRef.current = true;
      storePendingMove(data);
      setPendingDiceLabel(data.label || "");
      setDiceSpectacle({
        username,
        dice: data.dice,
        rawDice: data.rawDice,
        userId: data.userId || data.user?.id,
        factors: data.factors || [],
        steps: data.steps,
        label: data.label,
        showEffects: true,
        ...extra,
      });
    },
    [storePendingMove]
  );

  const syncPlayerState = useCallback((user) => {
    if (!user?.id) return;
    setPlayers((prev) => {
      const i = prev.findIndex((u) => u.id === user.id);
      if (i >= 0) {
        const next = [...prev];
        next[i] = { ...next[i], ...user };
        return next;
      }
      return [...prev, user];
    });
    if (myIdRef.current === user.id) {
      setCurrentUser((prev) => (prev ? { ...prev, ...user } : user));
    }
  }, []);

  useEffect(() => {
    if (!myIdRef.current) return;
    const me = players.find((p) => p.id === myIdRef.current);
    if (me) {
      setCurrentUser((prev) => (prev ? { ...prev, ...me } : me));
    }
  }, [players]);

  const loadCenterGif = useCallback(async () => {
    try {
      const gif = await apiGet("/tenor/meme");
      if (gif?.url) setCenterGif(gif);
    } catch {
      /* оставляем предыдущую */
    }
  }, []);

  useEffect(() => {
    loadCenterGif();
  }, [loadCenterGif]);

  useEffect(() => {
    const sig = players
      .map((p) => `${p.id}:${p.turnPhase ?? "idle"}`)
      .sort()
      .join("|");
    if (phaseSigRef.current && phaseSigRef.current !== sig) {
      loadCenterGif();
    }
    phaseSigRef.current = sig;
  }, [players, loadCenterGif]);

  const refreshPlayers = useCallback(async () => {
    const list = await apiGet("/players");
    setPlayers(list);
    const me = await apiGet("/auth/me");
    setCurrentUser(me.user);
    myIdRef.current = me.user?.id ?? null;
  }, []);

  const applyMoveFinished = useCallback((p) => {
    syncPlayerState(p.user);
    if (p.source) {
      setWheelMeta({
        source: p.source,
        lottery: p.source.lottery,
        itemWheel: !!p.source.itemWheel,
        blazerd: !!p.source.blazerdGenre,
        durka: p.source.durka,
      });
    }
    if (myIdRef.current === p.userId) {
      setTurnError("");
    }
  }, [syncPlayerState]);

  const finishMoveIfReady = useCallback(() => {
    if (moveAnimatingRef.current || !pendingFinishRef.current) return;
    const payload = pendingFinishRef.current;
    pendingFinishRef.current = null;
    applyMoveFinished(payload);
  }, [applyMoveFinished]);

  const runPendingMove = useCallback(async () => {
    const p = pendingPathRef.current;
    if (!p || moveAnimatingRef.current) return;
    pendingPathRef.current = null;
    moveAnimatingRef.current = true;
    try {
      await runTokenPath({
        userId: p.userId,
        path: p.path,
        fromPosition: p.fromPosition,
        stepMs: p.stepMs || 550,
        avatarUrl: p.avatarUrl || "/avatars/default.png",
        setFlyingToken,
        setAnimPositions,
        setPlayers,
      });
    } finally {
      moveAnimatingRef.current = false;
      physicsResolvedRef.current = false;
      finishMoveIfReady();
    }
  }, [finishMoveIfReady]);

  const queueOrRunMove = useCallback(
    (p) => {
      const isActor = myIdRef.current === p.userId;

      if (isActor && (awaitingDiceAcceptRef.current || diceWaitRef.current)) {
        pendingPathRef.current = p;
        return;
      }

      pendingPathRef.current = p;
      runPendingMove();
    },
    [runPendingMove]
  );

  const onDiceModalDone = useCallback(() => {
    const spec = diceSpectacleRef.current;
    awaitingDiceAcceptRef.current = false;
    diceWaitRef.current = false;
    physicsResolvedRef.current = false;
    setDiceSpectacle(null);
    if (spec?.awaitingCheatChoice && myIdRef.current === spec.userId) {
      setDiceChoice({ type: "cheat", dice: spec.dice });
      return;
    }
    if (pendingPathRef.current) {
      runPendingMove();
    } else {
      finishMoveIfReady();
    }
  }, [runPendingMove, finishMoveIfReady]);

  useEffect(() => {
    syncPlayerStateRef.current = syncPlayerState;
    refreshPlayersRef.current = refreshPlayers;
    applyMoveFinishedRef.current = applyMoveFinished;
    queueOrRunMoveRef.current = queueOrRunMove;
    finishMoveIfReadyRef.current = finishMoveIfReady;
    openDiceResultRef.current = openDiceResult;
    storePendingMoveRef.current = storePendingMove;
  }, [syncPlayerState, refreshPlayers, applyMoveFinished, queueOrRunMove, finishMoveIfReady, openDiceResult, storePendingMove]);

  useEffect(() => {
    apiGet("/board").then(setCells);
    apiGet("/rules").then((r) => setRulesHtml(r.html));
    apiGet("/auth/accounts").then(setAccountData);
    refreshPlayers();
  }, [refreshPlayers]);

  useEffect(() => {
    const s = getSocket();

    const onGifPoolRefresh = () => {
      loadCenterGif();
    };

    const onDice = (p) => {
      const isMe = myIdRef.current === p.userId;

      if (isMe && diceSpectacleRef.current?.physicsRoll && !p.awaitingPhysics) {
        return;
      }

      if (
        isMe &&
        (awaitingDiceAcceptRef.current || physicsResolvedRef.current) &&
        p.steps != null &&
        !p.awaitingPhysics
      ) {
        return;
      }

      syncPlayerStateRef.current?.(p.user);

      if (p.awaitingPhysics) {
        physicsResolvedRef.current = false;
        awaitingDiceAcceptRef.current = false;
        if (isMe) {
          diceWaitRef.current = true;
          diceRollKeyRef.current += 1;
          setDiceSpectacle({
            username: playerName(p),
            userId: p.userId,
            physicsRoll: true,
            showEffects: true,
            rollKey: diceRollKeyRef.current,
          });
        } else {
          setDiceSpectacle({
            username: playerName(p),
            userId: p.userId,
            awaitingOthersRoll: true,
          });
        }
        return;
      }

      if (isMe && p.steps != null) {
        awaitingDiceAcceptRef.current = true;
        diceWaitRef.current = true;
        storePendingMoveRef.current?.(p);
      }

      if (p.needsDiceChoice?.type === "trinity" && isMe) {
        setTrinityChoice(true);
        setDiceChoice(null);
        return;
      }

      if (p.awaitingCheat && p.dice) {
        setDiceSpectacle({
          username: playerName(p),
          dice: p.dice,
          userId: p.userId,
          showEffects: false,
          awaitingCheatChoice: true,
        });
        return;
      }

      setDiceChoice(null);
      if (p.steps == null && !p.dice?.length) return;

      if (!isMe) {
        setDiceSpectacle(null);
        setPendingDiceLabel(p.label || "");
        return;
      }

      openDiceResultRef.current?.(p, playerName(p), {});
    };

    const onPath = (p) => {
      queueOrRunMoveRef.current?.(p);
    };

    const onFinished = (p) => {
      pendingFinishRef.current = p;
      if (
        !moveAnimatingRef.current &&
        !awaitingDiceAcceptRef.current &&
        !diceWaitRef.current &&
        !pendingPathRef.current
      ) {
        finishMoveIfReadyRef.current?.();
      }
    };

    const onWheelOpened = (p) => {
      if (myIdRef.current === p.userId) {
        syncPlayerStateRef.current?.(p.user);
      }
      wheelSessionRef.current += 1;
      setSpinCommand(null);
      setWheelHltbItems([]);
      setWheelSpectacle({
        sessionId: wheelSessionRef.current,
        username: playerName(p),
        userId: p.userId,
        wheel: p.wheel || [],
        wheelItems: p.wheelItems,
        wheelType: p.wheelType,
        source: p.source,
        cellName: p.cellName,
        blazerdGenreLabel: p.blazerdGenreLabel,
        rewardSpinsRemaining: p.rewardSpinsRemaining,
        rewardSpinIndex: p.rewardSpinIndex,
        extraWheelSpinsRemaining: p.extraWheelSpinsRemaining,
        voteLabels: p.voteLabels,
      });
      if (p.wheelType === "reward_item") {
        rewardChainRef.current = true;
      }
    };

    const onWheelSpin = (p) => {
      if (myIdRef.current === p.userId) {
        syncPlayerStateRef.current?.(p.user);
      }
      setSpinCommand((prev) => ({
        sessionId: wheelSessionRef.current,
        targetIndex: p.targetIndex,
        wheel: p.wheel ?? prev?.wheel,
        wheelItems: p.wheelItems ?? prev?.wheelItems,
        wheelType: p.wheelType ?? prev?.wheelType,
        selectedGame: p.selectedGame ?? prev?.selectedGame,
        selectedItemId: p.selectedItemId ?? prev?.selectedItemId,
        selectedItemName: p.selectedItemName ?? prev?.selectedItemName,
        crownPick: p.crownPick ?? prev?.crownPick,
        shopPick: p.shopPick ?? prev?.shopPick,
        duplicateGame: p.duplicateGame ?? prev?.duplicateGame,
        recovered: prev?.recovered,
      }));
      if (
        myIdRef.current === p.userId &&
        typeof p.extraWheelSpinsRemaining === "number"
      ) {
        setWheelSpectacle((prev) =>
          prev
            ? {
                ...prev,
                extraWheelSpinsRemaining: p.extraWheelSpinsRemaining,
                voteLabels: p.voteLabels ?? prev.voteLabels,
              }
            : prev
        );
      }
    };

    const onWheelHltbReady = (p) => {
      if (p?.items?.length) setWheelHltbItems(p.items);
    };

    const onGameAssigned = (p) => {
      if (myIdRef.current === p.userId) {
        syncPlayerStateRef.current?.(p.user);
      }
      setWheelSpectacle(null);
      setSpinCommand(null);
      setWheelMeta(null);
      setWheelHltbItems([]);
    };

    const onItemWheelResolved = (p) => {
      if (myIdRef.current === p.userId) {
        syncPlayerStateRef.current?.(p.user);
      }
      if (p.openExtraWheel && p.wheel?.length) {
        extraWheelChainRef.current = true;
        wheelSessionRef.current += 1;
        setSpinCommand(null);
        setWheelHltbItems([]);
        setWheelSpectacle({
          sessionId: wheelSessionRef.current,
          username: playerName(p),
          userId: p.userId,
          wheel: p.wheel,
          wheelItems: p.wheelItems,
          wheelType: p.wheelType || "item",
          source: p.source,
          cellName: p.cellName,
          extraWheelSpinsRemaining: p.extraWheelSpinsRemaining,
        });
        refreshPlayersRef.current?.();
        return;
      }
      if (p.resumeReward && p.rewardSpinsRemaining > 0 && myIdRef.current === p.userId) {
        setRewardSpins(p.rewardSpinsRemaining);
        setRewardDiceRolled(false);
        beginRewardWheelsRef.current?.();
        return;
      }
      if (!rewardChainRef.current && !extraWheelChainRef.current) {
        setWheelSpectacle(null);
        setSpinCommand(null);
        setWheelMeta(null);
        setWheelHltbItems([]);
      }
      extraWheelChainRef.current = false;
      refreshPlayersRef.current?.();
    };

    const onRewardWheelsStarted = (p) => {
      if (myIdRef.current !== p.userId) return;
      syncPlayerStateRef.current?.(p.user);
      setRewardSpins(p.rewardItemSpins || 0);
      setRewardDiceRolled(false);
    };

    const onRewardWheelResolved = (p) => {
      if (myIdRef.current === p.userId) {
        syncPlayerStateRef.current?.(p.user);
      }
      refreshPlayersRef.current?.();
      if (p.openExtraWheel && p.wheel?.length && myIdRef.current === p.userId) {
        extraWheelChainRef.current = true;
        rewardChainRef.current = true;
        wheelSessionRef.current += 1;
        setSpinCommand(null);
        setWheelHltbItems([]);
        setWheelSpectacle({
          sessionId: wheelSessionRef.current,
          username: playerName(p),
          userId: p.userId,
          wheel: p.wheel,
          wheelItems: p.wheelItems,
          wheelType: "item",
          source: p.source,
          cellName: p.cellName,
          extraWheelSpinsRemaining: p.extraWheelSpinsRemaining,
          rewardSpinsRemaining: p.rewardSpinsRemaining,
        });
        return;
      }
      if (p.rewardSpinsRemaining > 0 && myIdRef.current === p.userId) {
        setRewardSpins(p.rewardSpinsRemaining);
        setRewardDiceRolled(!!p.rewardDiceReady);
        beginRewardWheelsRef.current?.();
        return;
      }
      rewardChainRef.current = false;
      setWheelSpectacle(null);
      setSpinCommand(null);
      setWheelHltbItems([]);
    };

    const onError = (err) => {
      if (err?.message && myIdRef.current) setTurnError(err.message);
    };

    s.on("board_state", (st) => {
      if (moveAnimatingRef.current) return;
      setPlayers(st.players || []);
    });
    s.on("gif_pool_refresh", onGifPoolRefresh);
    s.on("dice_rolled", onDice);
    s.on("token_move_path", onPath);
    s.on("move_finished", onFinished);
    s.on("wheel_opened", onWheelOpened);
    s.on("wheel_spin", onWheelSpin);
    s.on("wheel_hltb_ready", onWheelHltbReady);
    s.on("game_assigned", onGameAssigned);
    s.on("item_wheel_resolved", onItemWheelResolved);
    s.on("reward_wheels_started", onRewardWheelsStarted);
    s.on("reward_wheel_resolved", onRewardWheelResolved);
    s.on("players_updated", () => {
      refreshPlayersRef.current?.();
    });
    s.on("error", onError);

    return () => {
      s.off("board_state");
      s.off("gif_pool_refresh", onGifPoolRefresh);
      s.off("dice_rolled", onDice);
      s.off("token_move_path", onPath);
      s.off("move_finished", onFinished);
      s.off("wheel_opened", onWheelOpened);
      s.off("wheel_spin", onWheelSpin);
      s.off("wheel_hltb_ready", onWheelHltbReady);
      s.off("game_assigned", onGameAssigned);
      s.off("item_wheel_resolved", onItemWheelResolved);
      s.off("reward_wheels_started", onRewardWheelsStarted);
      s.off("reward_wheel_resolved", onRewardWheelResolved);
      s.off("players_updated");
      s.off("error", onError);
    };
  }, []);

  useEffect(() => {
    if (!currentUser?.id) return;
    if (currentUser.turnPhase === "reward_items") {
      setRewardSpins(currentUser.rewardSpinsPending ?? 0);
      setRewardDiceRolled(!!currentUser.rewardDiceReady);
    }
  }, [
    currentUser?.id,
    currentUser?.turnPhase,
    currentUser?.rewardSpinsPending,
    currentUser?.rewardDiceReady,
  ]);

  useEffect(() => {
    if (!currentUser?.id) return;
    const phase = currentUser.turnPhase;
    // wheel_ready — кнопка «Крутить колесо», без авто-открытия
    if (phase !== "wheel") {
      wheelRecoveryRef.current = false;
      return;
    }
    if (wheelSpectacle || wheelRecoveryRef.current) return;
    wheelRecoveryRef.current = true;

    (async () => {
      try {
        const data = await apiPost("/turn/open-wheel", {});
        if (data.user) syncPlayerState(data.user);
        if (data.source) {
          setWheelMeta({
            source: data.source,
            lottery: data.source.lottery,
            itemWheel: !!data.source.itemWheel,
            blazerd: !!data.source.blazerdGenre,
            durka: data.source.durka,
            genreId: data.source.genreId,
          });
        }
        wheelSessionRef.current += 1;
        setWheelSpectacle({
          sessionId: wheelSessionRef.current,
          username: payloadPlayerName(data, currentUser),
          userId: data.userId || currentUser.id,
          wheel: data.wheel || [],
          wheelItems: data.wheelItems,
          wheelType: data.wheelType,
          source: data.source,
          cellName: data.cellName,
          rewardSpinsRemaining: data.rewardSpinsRemaining,
          rewardSpinIndex: data.rewardSpinIndex,
          extraWheelSpinsRemaining: data.extraWheelSpinsRemaining,
          voteLabels: data.voteLabels,
        });
        if (
          data.recovered &&
          (typeof data.targetIndex === "number" ||
            data.shopPick?.choices?.length)
        ) {
          setSpinCommand({
            sessionId: wheelSessionRef.current,
            targetIndex: data.targetIndex,
            wheel: data.wheel,
            wheelItems: data.wheelItems,
            wheelType: data.wheelType,
            selectedItemId: data.selectedItemId,
            selectedItemName: data.selectedItemName,
            selectedGame: data.selectedGame,
            crownPick: data.crownPick,
            shopPick: data.shopPick,
            recovered: true,
          });
        }
        if (data.wheelType === "reward_item") {
          rewardChainRef.current = true;
        }
      } catch {
        wheelRecoveryRef.current = false;
      }
    })();
  }, [currentUser?.id, currentUser?.turnPhase, currentUser?.username, wheelSpectacle, syncPlayerState]);

  const openModal = async (id) => {
    if (id === "rules") setModal("rules");
    if (id === "history") {
      setHistory(await apiGet("/history"));
      setModal("history");
    }
    if (id === "stats") {
      setStats(await apiGet("/statistics"));
      setModal("stats");
    }
    if (id === "admin") setModal("admin");
  };

  const runAction = async (key, fn) => {
    if (actionLoading) return;
    setActionLoading(key);
    setTurnError("");
    try {
      await fn();
    } catch (ex) {
      setTurnError(ex.message);
    } finally {
      setActionLoading(null);
    }
  };

  const startDurka = async () => {
    if (!currentUser) return setModal("login");
    await runAction("durka", async () => {
      const data = await apiPost("/turn/durka-roll", {});
      if (data.user) syncPlayerState(data.user);
      if (data.wheel?.length) {
        wheelSessionRef.current += 1;
        setSpinCommand(null);
        setWheelHltbItems([]);
        if (data.source) {
          setWheelMeta({
            source: data.source,
            durka: true,
            genreId: data.source.genreId,
            blazerd: !!data.source.blazerdGenre,
          });
        }
        setWheelSpectacle({
          sessionId: wheelSessionRef.current,
          username: payloadPlayerName(data, currentUser),
          userId: data.userId || currentUser?.id,
          wheel: data.wheel || [],
          wheelItems: data.wheelItems,
          wheelType: data.wheelType || "game",
          source: data.source,
          cellName: data.cellName || "Дурка",
          blazerdGenreLabel: data.blazerdGenreLabel,
        });
      }
    });
  };

  const durkaStep = async (direction) => {
    if (!currentUser) return setModal("login");
    const key = direction === "forward" ? "durkaForward" : "durkaBack";
    await runAction(key, async () => {
      const data = await apiPost("/turn/durka-step", { direction });
      if (data.user) syncPlayerState(data.user);
      if (data.wheel?.length || data.wheelItems?.length) {
        wheelSessionRef.current += 1;
        setSpinCommand(null);
        setWheelHltbItems([]);
        setWheelSpectacle({
          sessionId: wheelSessionRef.current,
          username: payloadPlayerName(data, currentUser),
          userId: data.userId || currentUser?.id,
          wheel: data.wheel || [],
          wheelItems: data.wheelItems,
          wheelType: data.wheelType,
          source: data.source,
          cellName: data.cellName,
        });
      }
    });
  };

  const startTurn = async () => {
    if (!currentUser) return setModal("login");
    await runAction("dice", async () => {
      awaitingDiceAcceptRef.current = false;
      diceWaitRef.current = true;
      physicsResolvedRef.current = false;
      pendingPathRef.current = null;
      const data = await apiPost("/turn/roll-dice", {});
      if (data.user) syncPlayerState(data.user);
      if (data.needsDiceChoice?.type === "trinity") {
        setTrinityChoice(true);
        setDiceChoice(null);
      } else if (data.awaitingCheat && data.dice) {
        setDiceSpectacle({
          username: payloadPlayerName(data, currentUser),
          dice: data.dice,
          userId: data.userId || currentUser?.id,
          showEffects: false,
          awaitingCheatChoice: true,
        });
      } else if (data.awaitingPhysics) {
        diceRollKeyRef.current += 1;
        setDiceSpectacle({
          username: payloadPlayerName(data, currentUser),
          userId: data.userId || currentUser?.id,
          physicsRoll: true,
          showEffects: true,
          rollKey: diceRollKeyRef.current,
        });
      } else if (data.steps != null && data.dice) {
        diceRollKeyRef.current += 1;
        openDiceResult(data, payloadPlayerName(data, currentUser), {
          rollKey: diceRollKeyRef.current,
        });
      }
    });
  };

  const openWheel = async (genreId) => {
    await runAction("wheel", async () => {
      setDiceSpectacle(null);
      const data = await apiPost("/turn/open-wheel", {
        genreId: genreId ?? wheelMeta?.genreId,
      });
      if (data.user) syncPlayerState(data.user);
      if (data.needsGenrePick && data.genres?.length) {
        setTurnError("Выберите жанр слева и нажмите «Роллить игру»");
        return;
      }
      if (data.source) {
        setWheelMeta({
          source: data.source,
          lottery: data.source.lottery,
          itemWheel: !!data.source.itemWheel,
          blazerd: !!data.source.blazerdGenre,
          durka: data.source.durka,
          genreId: data.source.genreId,
        });
      }
      wheelSessionRef.current += 1;
      setSpinCommand(null);
      setWheelSpectacle({
        sessionId: wheelSessionRef.current,
        username: payloadPlayerName(data, currentUser),
        userId: data.userId || currentUser?.id,
        wheel: data.wheel || [],
        wheelItems: data.wheelItems,
        wheelType: data.wheelType,
        source: data.source || wheelMeta?.source,
        cellName: data.cellName,
        blazerdGenreLabel: data.blazerdGenreLabel,
        rewardSpinsRemaining: data.rewardSpinsRemaining,
        rewardSpinIndex: data.rewardSpinIndex,
        extraWheelSpinsRemaining: data.extraWheelSpinsRemaining,
        voteLabels: data.voteLabels,
      });
    });
  };

  const requestSpin = async () => {
    await runAction("spin", async () => {
      const data = await apiPost("/turn/spin-wheel", {});
      if (data.user) syncPlayerState(data.user);
      if (typeof data.targetIndex === "number") {
        setSpinCommand({
          sessionId: wheelSessionRef.current,
          targetIndex: data.targetIndex,
          wheel: data.wheel,
          wheelItems: data.wheelItems,
          wheelType: data.wheelType,
          selectedGame: data.selectedGame,
          selectedItemId: data.selectedItemId,
          selectedItemName: data.selectedItemName,
          crownPick: data.crownPick,
          shopPick: data.shopPick,
          duplicateGame: data.duplicateGame,
        });
        if (typeof data.extraWheelSpinsRemaining === "number") {
          setWheelSpectacle((prev) =>
            prev
              ? {
                  ...prev,
                  extraWheelSpinsRemaining: data.extraWheelSpinsRemaining,
                  voteLabels: data.voteLabels ?? prev.voteLabels,
                }
              : prev
          );
        }
      }
    });
  };

  const beginRewardWheels = useCallback(async () => {
    await runAction("reward", async () => {
      const data = await apiPost("/turn/open-reward-wheel", {});
      if (data.user) syncPlayerState(data.user);
      rewardChainRef.current = true;
      wheelSessionRef.current += 1;
      setSpinCommand(null);
      setWheelHltbItems([]);
      setWheelSpectacle({
        sessionId: wheelSessionRef.current,
        username: payloadPlayerName(data, currentUser),
        userId: data.userId || currentUser?.id,
        wheel: data.wheel || [],
        wheelItems: data.wheelItems,
        wheelType: "reward_item",
        source: data.source || { itemWheel: true, rewardWheel: true },
        cellName: data.cellName,
        rewardSpinsRemaining: data.rewardSpinsRemaining,
        rewardSpinIndex: data.rewardSpinIndex,
      });
    });
  }, [currentUser, runAction, syncPlayerState]);

  const openRewardSlot = useCallback(() => {
    if (!currentUser) return setModal("login");
    setRewardSlotOpen(true);
  }, [currentUser]);

  const handleGameCompleted = useCallback(
    async (data) => {
      if (data?.user) syncPlayerState(data.user);
      await refreshPlayers();
      if (
        data?.rewardItemSpins > 0 &&
        myIdRef.current === (data.userId || data.user?.id)
      ) {
        setRewardSpins(data.rewardItemSpins);
        setRewardDiceRolled(false);
      }
    },
    [currentUser, refreshPlayers, syncPlayerState]
  );

  beginRewardWheelsRef.current = beginRewardWheels;

  const confirmWheel = async (payload) => {
    const isReward =
      wheelSpectacle?.wheelType === "reward_item" ||
      payload?.wheelType === "reward_item";
    const isItem =
      isReward ||
      wheelSpectacle?.wheelType === "item" ||
      wheelSpectacle?.wheelType === "reward_item" ||
      wheelSpectacle?.source?.itemWheel ||
      !!wheelSpectacle?.wheelItems?.length ||
      payload?.wheelType === "item" ||
      payload?.wheelType === "reward_item" ||
      payload?.selectedItemId != null ||
      (Array.isArray(payload?.shopChoiceIndexes) &&
        payload.shopChoiceIndexes.length > 0);
    if (isItem) {
      const hasPick =
        payload?.selectedItemId != null ||
        Number.isInteger(payload?.targetIndex) ||
        (Array.isArray(payload?.shopChoiceIndexes) &&
          payload.shopChoiceIndexes.length === 2) ||
        spinCommand?.shopPick?.mode === "chat";
      if (!hasPick) {
        setTurnError("Подтвердите выпавший предмет");
        return;
      }
      await runAction("confirm", async () => {
        const data = await apiPost("/turn/confirm-wheel", {
          ...payload,
          wheelType: isReward ? "reward_item" : "item",
          diceLabel: isReward ? "награда" : pendingDiceLabel,
        });
        if (data.user) syncPlayerState(data.user);
        await refreshPlayers();
        if (data.openExtraWheel && data.wheel?.length) {
          extraWheelChainRef.current = true;
          wheelSessionRef.current += 1;
          setSpinCommand(null);
          setWheelHltbItems([]);
          setWheelSpectacle({
            sessionId: wheelSessionRef.current,
            username: payloadPlayerName(data, currentUser),
            userId: data.userId || currentUser?.id,
            wheel: data.wheel,
            wheelItems: data.wheelItems,
            wheelType: "item",
            source: data.source,
            cellName: data.cellName,
            extraWheelSpinsRemaining: data.extraWheelSpinsRemaining,
            voteLabels: data.voteLabels,
          });
          return;
        }
        if (data.reopenWheel && data.wheel?.length) {
          extraWheelChainRef.current = true;
          wheelSessionRef.current += 1;
          setSpinCommand(null);
          setWheelHltbItems([]);
          setWheelSpectacle({
            sessionId: wheelSessionRef.current,
            username: payloadPlayerName(data, currentUser),
            userId: data.userId || currentUser?.id,
            wheel: data.wheel,
            wheelItems: data.wheelItems,
            wheelType: data.wheelType || "item",
            source: data.source,
            cellName: data.cellName,
            extraWheelSpinsRemaining: data.extraWheelSpinsRemaining,
            voteLabels: data.voteLabels,
          });
          return;
        }
        if (data.resumeReward && data.rewardSpinsRemaining > 0) {
          setRewardSpins(data.rewardSpinsRemaining);
          setRewardDiceRolled(false);
          beginRewardWheels();
          return;
        }
        if (isReward && data.rewardSpinsRemaining > 0) {
          setRewardSpins(data.rewardSpinsRemaining);
          setRewardDiceRolled(!!data.rewardDiceReady);
          setWheelSpectacle(null);
          setSpinCommand(null);
          beginRewardWheels();
          return;
        }
        if (isReward) {
          setRewardSpins(0);
          setRewardDiceRolled(false);
        }
        rewardChainRef.current = false;
        extraWheelChainRef.current = false;
        setWheelSpectacle(null);
        setSpinCommand(null);
        setWheelMeta(null);
        setWheelHltbItems([]);
      });
      return;
    }
    const title = String(payload?.selectedGame ?? "").trim();
    if (payload?.crownChoiceIndex == null && !title) {
      setTurnError("Выберите игру под колесом");
      return;
    }
    await runAction("confirm", async () => {
      const data = await apiPost("/turn/confirm-wheel", {
        ...payload,
        selectedGame: title,
        diceLabel: pendingDiceLabel,
        genreId: wheelMeta?.genreId ?? payload.genreId,
      });
      if (data.user) syncPlayerState(data.user);
      setWheelSpectacle(null);
      setSpinCommand(null);
      setWheelMeta(null);
      setWheelHltbItems([]);
    });
  };

  const handleLogout = async () => {
    try {
      await apiPost("/auth/logout", {});
    } catch {
      /* ignore */
    }
    setCurrentUser(null);
    myIdRef.current = null;
    setWheelSpectacle(null);
    setDiceSpectacle(null);
    refreshPlayers();
  };

  const openProfile = async (player) => {
    setProfileData({ player, games: [], inventory: null, loading: true });
    setModal("profile");
    try {
      const data = await apiGet(`/players/${player.id}`);
      setProfileData(data);
    } catch (ex) {
      setTurnError(ex.message);
      setModal(null);
    }
  };

  const dismissWheel = async () => {
    if (!wheelSpectacle || myIdRef.current !== wheelSpectacle.userId) return;
    await runAction("dismiss", async () => {
      const data = await apiPost("/turn/dismiss-wheel", {});
      if (data.user) syncPlayerState(data.user);
      setWheelSpectacle(null);
      setSpinCommand(null);
      setWheelHltbItems([]);
      wheelRecoveryRef.current = false;
    });
  };

  const openExtraWheel = async () => {
    if (!currentUser) return setModal("login");
    await runAction("wheel", async () => {
      setDiceSpectacle(null);
      const data = await apiPost("/turn/open-extra-wheel", {});
      if (data.user) syncPlayerState(data.user);
      wheelSessionRef.current += 1;
      setSpinCommand(null);
      setWheelHltbItems([]);
      setWheelSpectacle({
        sessionId: wheelSessionRef.current,
        username: payloadPlayerName(data, currentUser),
        userId: data.userId || currentUser?.id,
        wheel: data.wheel || [],
        wheelItems: data.wheelItems,
        wheelType: data.wheelType || "item",
        source: data.source,
        cellName: data.cellName,
        extraWheelSpinsRemaining: data.extraWheelSpinsRemaining,
        voteLabels: data.voteLabels,
      });
    });
  };

  const boardPlayers = players.map((p) => ({
    ...p,
    position:
      animPositions[p.id] !== undefined ? animPositions[p.id] : p.position,
  }));

  const canInteractWheel =
    wheelSpectacle && myIdRef.current === wheelSpectacle.userId;

  return (
    <>
      <SceneBackground />
      <div className="app app--with-ticker">
      <QuickMenu
        onOpen={openModal}
        currentUser={currentUser}
        cells={cells}
        onLogin={() => setModal("login")}
        onLogout={handleLogout}
        hoverCell={hoverCell}
        turnError={turnError}
        actionLoading={actionLoading}
        onRollDice={startTurn}
        onDurkaRoll={startDurka}
        onDurkaStepForward={() => durkaStep("forward")}
        onDurkaStepBackward={() => durkaStep("backward")}
        onOpenWheel={openWheel}
        onOpenExtraWheel={openExtraWheel}
        rewardSpins={rewardSpins}
        rewardDiceRolled={rewardDiceRolled}
        onOpenRewardSlot={openRewardSlot}
        onOpenRewardWheel={beginRewardWheels}
      />
      <div className="app-center-column">
        <div className="vip-arena-crown" aria-hidden="true">
          <span>♛ HIGH LIMIT FLOOR ♛</span>
        </div>
        <main className="main main--vip-arena">
          <Board
            cells={cells}
            players={boardPlayers}
            hoverCell={hoverCell}
            onHover={setHoverCell}
            flyingToken={flyingToken}
            centerGif={centerGif}
          />
        </main>
      </div>
      <PlayerList
        players={players}
        currentUser={currentUser}
        onSelect={openProfile}
      />

      {trinityChoice && (
        <TrinityDiceModal
          onClose={() => {}}
          onDone={(data) => {
            if (data.user) syncPlayerState(data.user);
            setTrinityChoice(false);
            refreshPlayers();
            if (data.awaitingCheat && data.dice) {
              setDiceSpectacle({
                username: payloadPlayerName(data, currentUser),
                dice: data.dice,
                userId: data.userId,
                showEffects: false,
                awaitingCheatChoice: true,
              });
            } else if (data.steps != null && data.dice) {
              openDiceResult(data, payloadPlayerName(data, currentUser), {});
            }
          }}
        />
      )}

      {diceChoice?.type === "cheat" && (
        <DiceChoiceModal
          choice={diceChoice}
          onClose={() => {}}
          onDone={(data) => {
            if (data.user) syncPlayerState(data.user);
            setDiceChoice(null);
            refreshPlayers();
          }}
        />
      )}

      {rewardSlotOpen &&
        currentUser?.turnPhase === "reward_items" &&
        !rewardDiceRolled && (
          <RewardSlotModal
            actorUsername={playerName(currentUser)}
            onComplete={(data) => {
              if (data?.user) syncPlayerState(data.user);
              setRewardSpins(data.rewardItemSpins || 0);
              setRewardDiceRolled(true);
              setRewardSlotOpen(false);
            }}
            onError={(msg) => {
              setTurnError(msg);
              setRewardSlotOpen(false);
            }}
          />
        )}

      {diceSpectacle && !diceChoice && !trinityChoice && (
        <DiceModal
          dice={diceSpectacle.dice}
          rawDice={diceSpectacle.rawDice}
          actorUsername={diceSpectacle.username}
          factors={diceSpectacle.factors}
          steps={diceSpectacle.steps}
          label={diceSpectacle.label}
          showEffects={diceSpectacle.showEffects !== false}
          physicsRoll={!!diceSpectacle.physicsRoll}
          awaitingOthersRoll={!!diceSpectacle.awaitingOthersRoll}
          rollKey={diceSpectacle.rollKey ?? 0}
          requireAccept={
            !diceSpectacle.awaitingOthersRoll &&
            currentUser?.id === diceSpectacle.userId
          }
          onDone={onDiceModalDone}
          onPhysicsConfirmed={(data) => {
            physicsResolvedRef.current = true;
            awaitingDiceAcceptRef.current = true;
            diceWaitRef.current = true;
            storePendingMove(data);
            if (data.user) syncPlayerState(data.user);
            setPendingDiceLabel(data.label || "");
            setDiceSpectacle({
              username: payloadPlayerName(data, currentUser),
              dice: data.dice,
              rawDice: data.rawDice,
              userId: data.userId || currentUser?.id,
              factors: data.factors || [],
              steps: data.steps,
              label: data.label,
              showEffects: true,
              rollKey: diceSpectacle?.rollKey,
              physicsResolved: true,
            });
          }}
        />
      )}

      {wheelSpectacle && (
        <WheelModal
          key={wheelSpectacle.sessionId}
          sessionId={wheelSpectacle.sessionId}
          actorUsername={wheelSpectacle.username}
          games={wheelSpectacle.wheel}
          hltbItems={wheelHltbItems}
          blazerdGenreLabel={wheelSpectacle.blazerdGenreLabel}
          lottery={wheelSpectacle.source?.lottery}
          itemWheel={
            wheelSpectacle.wheelType === "reward_item" ||
            wheelSpectacle.wheelType === "item" ||
            wheelSpectacle.source?.itemWheel
          }
          wheelType={wheelSpectacle.wheelType}
          wheelItems={wheelSpectacle.wheelItems}
          rewardSpinsRemaining={wheelSpectacle.rewardSpinsRemaining}
          rewardSpinIndex={wheelSpectacle.rewardSpinIndex}
          canInteract={canInteractWheel}
          spinCommand={
            spinCommand?.sessionId === wheelSpectacle.sessionId
              ? spinCommand
              : null
          }
          onRequestSpin={requestSpin}
          actionLoading={actionLoading}
          onConfirm={confirmWheel}
          turnError={turnError}
          extraWheelSpinsRemaining={wheelSpectacle.extraWheelSpinsRemaining}
          voteLabels={wheelSpectacle.voteLabels}
          onDismiss={canInteractWheel ? dismissWheel : undefined}
        />
      )}

      {modal === "rules" && (
        <RulesModal html={rulesHtml} onClose={() => setModal(null)} />
      )}
      {modal === "history" && (
        <HistoryModal items={history} onClose={() => setModal(null)} />
      )}
      {modal === "stats" && (
        <StatsModal rows={stats} onClose={() => setModal(null)} />
      )}
      {modal === "admin" && (
        <AdminPanel onClose={() => setModal(null)} />
      )}
      {modal === "login" && (
        <LoginModal
          accountData={accountData}
          onClose={() => setModal(null)}
          onSuccess={(u) => {
            setCurrentUser(u);
            myIdRef.current = u.id;
            refreshPlayers();
          }}
        />
      )}
      {modal === "profile" && profileData?.loading && (
        <div className="overlay overlay--casino">
          <div className="modal-panel profile-loading-panel modal-panel--casino">
            <div className="profile-loading-body">
              <div className="profile-loading-spinner" aria-hidden="true" />
              <p className="profile-loading-title">Загрузка профиля</p>
              <p className="muted profile-loading-sub">
                Игры, инвентарь и эффекты
              </p>
            </div>
          </div>
        </div>
      )}
      {modal === "profile" && profileData && !profileData.loading && (
        <ProfileModal
          profile={profileData.player}
          games={profileData.games || []}
          inventory={profileData.inventory}
          players={players}
          cells={cells}
          currentUser={currentUser}
          onClose={() => setModal(null)}
          onRefresh={async () => {
            await refreshPlayers();
            const data = await apiGet(`/players/${profileData.player.id}`);
            setProfileData(data);
          }}
          onGameCompleted={handleGameCompleted}
          onUserSync={syncPlayerState}
        />
      )}
      </div>
      <NewsTicker />
    </>
  );
}
