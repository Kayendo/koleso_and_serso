/**
 * Колесо: резкий разгон → плавное замедление до точного сектора (targetIndex с сервера).
 */
export class WheelPhysicsSim {
  constructor(segmentCount) {
    this.n = Math.max(1, segmentCount);
    this.angle = 0;
    this.omega = 0;
    this.flapperAngle = 0;
    this.flapperOmega = 0;
    this.stopped = true;
    this.targetIndex = 0;
    this._startAngle = 0;
    this._targetAngle = 0;
    this._elapsed = 0;
    this._duration = 4;
    this._hitPegs = new Set();
    this._lastRev = 0;
  }

  /** Угол (рад), при котором центр сектора `targetIndex` под указателем справа */
  static targetAngleRad(segmentCount, targetIndex, extraTurns = 4) {
    const sliceDeg = 360 / segmentCount;
    const targetDeg =
      extraTurns * 360 + (360 - targetIndex * sliceDeg - sliceDeg / 2);
    return (targetDeg * Math.PI) / 180;
  }

  static segmentAtPointer(angleRad, segmentCount) {
    const n = Math.max(1, segmentCount);
    const slice = (2 * Math.PI) / n;
    let a = (-angleRad) % (2 * Math.PI);
    if (a < 0) a += 2 * Math.PI;
    return Math.floor(a / slice) % n;
  }

  /** Быстрый старт (8% времени), длинное плавное торможение */
  static spinEase(t) {
    const x = Math.max(0, Math.min(1, t));
    if (x < 0.08) {
      return (x / 0.08) * 0.05;
    }
    const u = (x - 0.08) / 0.92;
    return 0.05 + 0.95 * (1 - Math.pow(1 - u, 3.4));
  }

  startSpin(targetIndex, extraTurns = 4) {
    this.n = Math.max(1, this.n);
    this.targetIndex = targetIndex;
    this._startAngle = this.angle;
    const extra = extraTurns + Math.floor(Math.random() * 2);
    let target = WheelPhysicsSim.targetAngleRad(this.n, targetIndex, extra);
    const minTravel = Math.PI * 2 * 3;
    while (target - this._startAngle < minTravel) {
      target += Math.PI * 2;
    }
    this._targetAngle = target;
    this._elapsed = 0;
    this._duration = 3.6 + Math.random() * 0.9;
    this.stopped = false;
    this.flapperAngle = 0;
    this.flapperOmega = 0;
    this.omega = 0;
    this._hitPegs.clear();
    this._lastRev = Math.floor(this.angle / (2 * Math.PI));
  }

  snapTo(targetIndex, extraTurns = 4) {
    this.angle = WheelPhysicsSim.targetAngleRad(this.n, targetIndex, extraTurns);
    this._targetAngle = this.angle;
    this.omega = 0;
    this.flapperAngle = 0;
    this.flapperOmega = 0;
    this.stopped = true;
    this.targetIndex = targetIndex;
    this._hitPegs.clear();
  }

  _checkPegHits() {
    if (this.omega < 0.35) return;

    const slice = (2 * Math.PI) / this.n;
    const rev = Math.floor(this.angle / (2 * Math.PI));
    if (rev !== this._lastRev) {
      this._hitPegs.clear();
      this._lastRev = rev;
    }

    const hitWindow = slice * 0.09;
    for (let i = 0; i < this.n; i++) {
      let peg = (this.angle + i * slice) % (2 * Math.PI);
      if (peg < 0) peg += 2 * Math.PI;
      let dist = Math.abs(peg);
      if (dist > Math.PI) dist = 2 * Math.PI - dist;
      if (dist > hitWindow) continue;

      const key = `${rev}:${i}`;
      if (this._hitPegs.has(key)) continue;
      this._hitPegs.add(key);

      const strength = Math.min(Math.abs(this.omega) * 0.7, 4.8);
      this.flapperOmega += strength;
    }
  }

  step(dt) {
    if (this.stopped) return false;

    const h = Math.min(dt, 0.032);
    const prev = this.angle;
    this._elapsed += h;
    const t = Math.min(1, this._elapsed / this._duration);
    const eased = WheelPhysicsSim.spinEase(t);
    this.angle = this._startAngle + (this._targetAngle - this._startAngle) * eased;
    this.omega = (this.angle - prev) / Math.max(h, 0.001);

    this._checkPegHits();

    const springK = 260;
    const damp = 11;
    this.flapperOmega += -springK * this.flapperAngle * h;
    this.flapperOmega *= Math.exp(-damp * h);
    this.flapperAngle += this.flapperOmega * h;
    this.flapperAngle = Math.max(0, Math.min(1.1, this.flapperAngle));

    if (t >= 1) {
      this.angle = this._targetAngle;
      this.omega = 0;
      this.flapperAngle *= 0.8;
      if (this.flapperAngle < 0.01) {
        this.flapperAngle = 0;
        this.flapperOmega = 0;
      }
      this.stopped = true;
    }

    return !this.stopped;
  }

  getRotationDeg() {
    return (this.angle * 180) / Math.PI;
  }

  getFlapperDeg() {
    return (this.flapperAngle * 180) / Math.PI;
  }

  getVisibleIndex() {
    return WheelPhysicsSim.segmentAtPointer(this.angle, this.n);
  }
}
