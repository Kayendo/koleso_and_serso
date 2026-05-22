import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "./api";
import { getSocket } from "./socket";
import { runTokenPath } from "./tokenAnimation";
import Board from "./components/Board";
import DiceModal from "./components/DiceModal";
import DiceChoiceModal from "./components/DiceChoiceModal";
import TrinityDiceModal from "./components/TrinityDiceModal";
import RewardDiceModal from "./components/RewardDiceModal";
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
  const pendingMoveRef = useRef(null);
  const rewardChainRef = useRef(false);
  const beginRewardWheelsRef = useRef(null);
  const wheelRecoveryRef = useRef(false);
  const syncPlayerStateRef = useRef(null);
  const refreshPlayersRef = useRef(null);
  const applyMoveFinishedRef = useRef(null);
  const openWheelAfterMoveRef = useRef(null);

  const myIdRef = useRef(null);
  useEffect(() => {
    myIdRef.current = currentUser?.id ?? null;
  }, [currentUser]);

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

  const openWheelAfterMove = useCallback(
    async (p) => {
      if (myIdRef.current !== p.userId) return;
      const src = p.source;
      if (!src) return;
      setWheelMeta({
        source: src,
        lottery: src.lottery,
        itemWheel: !!src.itemWheel,
        blazerd: !!src.needsGenrePick,
        durka: src.durka,
      });
      if (src.itemWheel) return;
      try {
        const data = await apiPost("/turn/open-wheel", {});
        if (data.user) syncPlayerState(data.user);
        wheelSessionRef.current += 1;
        setSpinCommand(null);
        setWheelSpectacle({
          sessionId: wheelSessionRef.current,
          username: p.username || currentUser?.username,
          userId: p.userId,
          wheel: data.wheel || [],
          wheelItems: data.wheelItems,
          source: data.source || src,
          cellName: data.cellName || p.cell?.name,
        });
      } catch (ex) {
        setTurnError(ex.message);
      }
    },
    [syncPlayerState]
  );

  const applyMoveFinished = useCallback(
    async (p) => {
      syncPlayerState(p.user);
      pendingMoveRef.current = {
        userId: p.userId,
        username: p.username,
        source: p.source,
        cell: p.cell,
      };
      if (myIdRef.current === p.userId) {
        setTurnError("");
      }
    },
    [syncPlayerState]
  );

  useEffect(() => {
    syncPlayerStateRef.current = syncPlayerState;
    refreshPlayersRef.current = refreshPlayers;
    applyMoveFinishedRef.current = applyMoveFinished;
    openWheelAfterMoveRef.current = openWheelAfterMove;
  }, [syncPlayerState, refreshPlayers, applyMoveFinished, openWheelAfterMove]);

  useEffect(() => {
    apiGet("/board").then(setCells);
    apiGet("/rules").then((r) => setRulesHtml(r.html));
    apiGet("/auth/accounts").then(setAccountData);
    refreshPlayers();
  }, [refreshPlayers]);

  useEffect(() => {
    const s = getSocket();

    const onDice = (p) => {
      syncPlayerStateRef.current?.(p.user);
      const isMe = myIdRef.current === p.userId;

      if (p.needsDiceChoice?.type === "trinity" && isMe) {
        setTrinityChoice(true);
        setDiceChoice(null);
        return;
      }

      if (p.awaitingCheat && p.dice) {
        setDiceSpectacle({
          username: p.username,
          dice: p.dice,
          userId: p.userId,
          showEffects: false,
          awaitingCheatChoice: true,
        });
        return;
      }

      setDiceChoice(null);
      if (p.steps == null && !p.dice?.length) return;
      setPendingDiceLabel(p.label || "");
      setDiceSpectacle({
        username: p.username,
        dice: p.dice,
        rawDice: p.rawDice,
        userId: p.userId,
        factors: p.factors || [],
        steps: p.steps,
        label: p.label,
        showEffects: true,
      });
    };

    const onPath = async (p) => {
      await runTokenPath({
        userId: p.userId,
        path: p.path,
        fromPosition: p.fromPosition,
        stepMs: p.stepMs || 780,
        avatarUrl: p.avatarUrl || "/avatars/default.png",
        setFlyingToken,
        setAnimPositions,
        setPlayers,
      });
      if (myIdRef.current === p.userId && pendingMoveRef.current) {
        await openWheelAfterMoveRef.current?.(pendingMoveRef.current);
        pendingMoveRef.current = null;
      }
    };

    const onFinished = (p) => {
      applyMoveFinishedRef.current?.(p);
    };

    const onWheelOpened = (p) => {
      syncPlayerStateRef.current?.(p.user);
      wheelSessionRef.current += 1;
      setSpinCommand(null);
      setWheelHltbItems([]);
      setWheelSpectacle({
        sessionId: wheelSessionRef.current,
        username: p.username,
        userId: p.userId,
        wheel: p.wheel || [],
        wheelItems: p.wheelItems,
        wheelType: p.wheelType,
        source: p.source,
        cellName: p.cellName,
        rewardSpinsRemaining: p.rewardSpinsRemaining,
        rewardSpinIndex: p.rewardSpinIndex,
      });
    };

    const onWheelSpin = (p) => {
      syncPlayerStateRef.current?.(p.user);
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
        oopsPick: p.oopsPick ?? prev?.oopsPick,
        recovered: prev?.recovered,
      }));
    };

    const onWheelHltbReady = (p) => {
      if (p?.items?.length) setWheelHltbItems(p.items);
    };

    const onGameAssigned = (p) => {
      syncPlayerStateRef.current?.(p.user);
      setWheelSpectacle(null);
      setSpinCommand(null);
      setWheelMeta(null);
      setWheelHltbItems([]);
    };

    const onItemWheelResolved = (p) => {
      syncPlayerStateRef.current?.(p.user);
      if (!rewardChainRef.current) {
        setWheelSpectacle(null);
        setSpinCommand(null);
        setWheelMeta(null);
        setWheelHltbItems([]);
      }
      refreshPlayersRef.current?.();
    };

    const onRewardWheelsStarted = (p) => {
      if (myIdRef.current !== p.userId) return;
      syncPlayerStateRef.current?.(p.user);
      setRewardSpins(p.rewardItemSpins || 0);
      setRewardDiceRolled(false);
    };

    const onRewardWheelResolved = (p) => {
      syncPlayerStateRef.current?.(p.user);
      refreshPlayersRef.current?.();
      if (p.rewardSpinsRemaining > 0 && myIdRef.current === p.userId) {
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

    s.on("board_state", (st) => setPlayers(st.players || []));
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
    s.on("error", onError);

    return () => {
      s.off("board_state");
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
      s.off("error", onError);
    };
  }, []);

  useEffect(() => {
    if (!currentUser?.id) return;
    const phase = currentUser.turnPhase;
    // wheel_ready — ждём окончания анимации фишки (openWheelAfterMove), не открываем сразу
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
            blazerd: !!data.source.needsGenrePick,
            durka: data.source.durka,
          });
        }
        if (data.source?.needsGenrePick && !data.wheel?.length) {
          wheelSessionRef.current += 1;
          setWheelSpectacle({
            sessionId: wheelSessionRef.current,
            username: data.username || currentUser.username,
            userId: data.userId || currentUser.id,
            wheel: [],
            source: data.source,
            cellName: data.cellName,
          });
          return;
        }
        wheelSessionRef.current += 1;
        const spectacle = {
          sessionId: wheelSessionRef.current,
          username: data.username || currentUser.username,
          userId: data.userId || currentUser.id,
          wheel: data.wheel || [],
          wheelItems: data.wheelItems,
          wheelType: data.wheelType,
          source: data.source,
          cellName: data.cellName,
          rewardSpinsRemaining: data.rewardSpinsRemaining,
          rewardSpinIndex: data.rewardSpinIndex,
        };
        setWheelSpectacle(spectacle);
        if (data.recovered && typeof data.targetIndex === "number") {
          setSpinCommand({
            sessionId: wheelSessionRef.current,
            targetIndex: data.targetIndex,
            wheel: data.wheel,
            wheelItems: data.wheelItems,
            wheelType: data.wheelType,
            crownPick: data.crownPick,
            oopsPick: data.oopsPick,
            recovered: true,
          });
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
    });
  };

  const startTurn = async () => {
    if (!currentUser) return setModal("login");
    await runAction("dice", async () => {
      const data = await apiPost("/turn/roll-dice", {});
      if (data.user) syncPlayerState(data.user);
      if (data.needsDiceChoice?.type === "trinity") {
        setTrinityChoice(true);
        setDiceChoice(null);
      } else if (data.awaitingCheat && data.dice) {
        setDiceSpectacle({
          username: data.username || currentUser?.username,
          dice: data.dice,
          userId: data.userId || currentUser?.id,
          showEffects: false,
          awaitingCheatChoice: true,
        });
      } else if (data.steps != null && data.dice) {
        setPendingDiceLabel(data.label || "");
        setDiceSpectacle({
          username: data.username || currentUser?.username,
          dice: data.dice,
          rawDice: data.rawDice,
          userId: data.userId || currentUser?.id,
          factors: data.factors || [],
          steps: data.steps,
          label: data.label,
          showEffects: true,
        });
      }
    });
  };

  const openWheel = async () => {
    if (wheelMeta?.blazerd && !wheelMeta?.genreId && currentUser) {
      wheelSessionRef.current += 1;
      setWheelSpectacle({
        sessionId: wheelSessionRef.current,
        username: currentUser.username,
        userId: currentUser.id,
        wheel: [],
        source: { ...wheelMeta.source, needsGenrePick: true },
      });
      return;
    }
      await runAction("wheel", async () => {
      const data = await apiPost("/turn/open-wheel", {
        genreId: wheelMeta?.genreId,
      });
      if (data.user) syncPlayerState(data.user);
      wheelSessionRef.current += 1;
      setSpinCommand(null);
      setWheelSpectacle({
        sessionId: wheelSessionRef.current,
        username: data.username || currentUser?.username,
        userId: data.userId || currentUser?.id,
        wheel: data.wheel || [],
        wheelItems: data.wheelItems,
        source: data.source || wheelMeta?.source,
        cellName: data.cellName,
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
          oopsPick: data.oopsPick,
        });
      }
    });
  };

  const onBlazerdGenre = async (genreId) => {
    setWheelMeta((m) => ({ ...m, genreId }));
    await runAction("blazerd", async () => {
      const data = await apiPost("/turn/open-wheel", { genreId });
      if (data.user) syncPlayerState(data.user);
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
        username: data.username || currentUser?.username,
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

  const rollRewardDice = useCallback(async () => {
    await runAction("rewardDice", async () => {
      const data = await apiPost("/turn/roll-reward-dice", {});
      if (data.user) syncPlayerState(data.user);
      setRewardSpins(data.rewardItemSpins || 0);
      setRewardDiceRolled(true);
      setDiceSpectacle({
        username: data.username || currentUser?.username,
        dice: data.rewardDice || [data.rewardItemSpins],
        userId: data.userId || currentUser?.id,
        rewardDiceOnly: true,
      });
    });
  }, [currentUser, syncPlayerState]);

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
      wheelSpectacle?.source?.itemWheel ||
      payload?.wheelType === "item" ||
      payload?.selectedItemId != null;
    if (isItem) {
      if (
        payload?.oopsChoiceIndex == null &&
        payload?.selectedItemId == null &&
        payload?.targetIndex == null
      ) {
        setTurnError("Выберите соседний пункт");
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
        if (isReward && data.rewardSpinsRemaining > 0) {
          setRewardSpins(data.rewardSpinsRemaining);
          setRewardDiceRolled(false);
          beginRewardWheels();
          return;
        }
        if (isReward) {
          setRewardSpins(0);
          setRewardDiceRolled(false);
        }
        rewardChainRef.current = false;
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

  const boardPlayers = players.map((p) => ({
    ...p,
    position:
      animPositions[p.id] !== undefined ? animPositions[p.id] : p.position,
  }));

  const canInteractWheel =
    wheelSpectacle && myIdRef.current === wheelSpectacle.userId;

  return (
    <div className="app">
      <QuickMenu
        onOpen={openModal}
        currentUser={currentUser}
        onLogin={() => setModal("login")}
        onLogout={handleLogout}
        hoverCell={hoverCell}
        turnError={turnError}
        actionLoading={actionLoading}
        onRollDice={startTurn}
        onDurkaRoll={startDurka}
        onOpenWheel={openWheel}
        rewardSpins={rewardSpins}
        rewardDiceRolled={rewardDiceRolled}
        onRollRewardDice={rollRewardDice}
        onOpenRewardWheel={beginRewardWheels}
      />
      <main className="main">
        <Board
          cells={cells}
          players={boardPlayers}
          hoverCell={hoverCell}
          onHover={setHoverCell}
          flyingToken={flyingToken}
          centerGif={centerGif}
        />
      </main>
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
                username: data.username,
                dice: data.dice,
                userId: data.userId,
                showEffects: false,
                awaitingCheatChoice: true,
              });
            } else if (data.steps != null && data.dice) {
              setPendingDiceLabel(data.label || "");
              setDiceSpectacle({
                username: data.username,
                dice: data.dice,
                userId: data.userId,
                factors: data.factors || [],
                steps: data.steps,
                label: data.label,
                showEffects: true,
              });
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

      {diceSpectacle?.rewardDiceOnly && !diceChoice && !trinityChoice && (
        <RewardDiceModal
          dice={diceSpectacle.dice}
          actorUsername={diceSpectacle.username}
          onDone={() => setDiceSpectacle(null)}
        />
      )}

      {diceSpectacle && !diceSpectacle.rewardDiceOnly && !diceChoice && !trinityChoice && (
        <DiceModal
          dice={diceSpectacle.dice}
          rawDice={diceSpectacle.rawDice}
          actorUsername={diceSpectacle.username}
          factors={diceSpectacle.factors}
          steps={diceSpectacle.steps}
          label={diceSpectacle.label}
          showEffects={diceSpectacle.showEffects !== false}
          onDone={() => {
            const spec = diceSpectacle;
            setDiceSpectacle(null);
            if (
              spec?.awaitingCheatChoice &&
              myIdRef.current === spec.userId
            ) {
              setDiceChoice({ type: "cheat", dice: spec.dice });
            }
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
          blazerd={wheelSpectacle.source?.needsGenrePick}
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
          onBlazerdGenre={onBlazerdGenre}
          onRequestSpin={requestSpin}
          actionLoading={actionLoading}
          onConfirm={confirmWheel}
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
        <div className="overlay">
          <div className="modal-panel profile-loading-panel">
            <div className="profile-loading-body">
              <div className="profile-loading-spinner" aria-hidden="true" />
              <p className="profile-loading-title">Загрузка профиля</p>
              <p className="muted profile-loading-sub">
                Игры, инвентарь и эффекты…
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
        />
      )}
    </div>
  );
}
