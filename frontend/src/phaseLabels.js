/** Человекочитаемые названия фаз хода. */
export const PHASE_LABELS = {
  idle: "Ожидание — можно бросить кубик",
  dice_choice: "Выберите кубики (окно на поле)",
  rolling: "Бросок кубика и движение",
  wheel_ready: "Готов к вращению колеса",
  wheel: "Вращение колеса",
  playing: "Прохождение игры",
  reward_items: "Награда: крутите колёса предметов",
  durka: "Дурка — ролл игры",
};

export function phaseLabel(phase) {
  return PHASE_LABELS[phase] || phase || "—";
}
