#  Volman Trend Pullback – 70 Tick Automation Model (2026 Edition)

Automation‑ready scalping framework inspired by Bob Volman’s price action methodology, engineered for modern algo‑driven forex market conditions.

---

#  Strategy Overview

**Model Type:** Trend Continuation Scalping  
**Execution Style:** Pullback Breakout  
**Chart Type:** 70 Tick  
**Primary Instrument:** EURUSD  
**Secondary (optional):** GBPUSD, XAUUSD  
**Holding Time:** 1 – 10 Minutes  
**Deployment:** Manual / Hybrid / Fully Automated

> Objective: Enter institutional continuation moves after liquidity pullbacks within a confirmed trend.

---

#  Market Environment (2026 Context)

Modern forex microstructure characteristics:

- High algorithmic participation
- Frequent breakout fakeouts
- Liquidity sweeps before continuation
- Spread volatility during news
- Cleaner trend legs due to execution algos

This model is optimized to:

- Avoid breakout traps
- Trade continuation momentum
- Filter low‑liquidity environments

---

#  Trading Sessions

Trade only during high liquidity windows.

| Session | IST |
|--------|------|
| London | 12:30 – 16:30 |
| New York | 18:30 – 21:30 |

### Avoid

- Asia session
- Pre‑news volatility
- Post‑NY low liquidity drift

---

#  Chart Specifications

- Chart Type: **70 Tick**
- EMA: **20 Period**
- Feed: Raw ECN (IC Markets recommended)
- Spread Model: Real‑time filtered

---

#  Strategy Logic Framework

The setup consists of 3 structural phases:

1. Impulse Leg
2. Pullback
3. Continuation Breakout (Entry)

---

#  Trend Qualification Rules

## Indicator

**20 EMA**

### Uptrend Criteria

- Price above EMA
- EMA sloping upward
- Higher highs present
- No impulse close below EMA

### Downtrend Criteria

Opposite conditions.

---

## EMA Slope Threshold

Minimum slope requirement:

```
EMA(now) − EMA(10 candles ago) ≥ 1.5 pips
```

Flat EMA → No trade.

---

#  Impulse Leg Detection

Impulse confirms institutional activity.

### Requirements

- Minimum 5 candles
- Directional closes
- Large bodies
- Minimal overlap
- Range expansion

### Quantified Rules

```
Impulse size ≥ 8 pips
Body dominance ≥ 60%
Overlap ≤ 30%
```

Weak impulse → Ignore setup.

---

#  Pullback Qualification

Pullback represents liquidity refill.

## Candle Count

```
Minimum: 2
Maximum: 5
```

> More than 5 = weakening trend

---

## Pullback Depth

Measured against impulse range:

```
Valid: 30% – 50%
Maximum: 60%
```

Beyond 60% → Setup invalid.

---

## EMA Interaction

Pullback must:

- Touch EMA  
OR
- Stay within 1.5 pips of EMA

Deep penetration invalidates trade.

---

## Candle Behavior

Healthy pullbacks show:

- Smaller bodies
- Momentum slowdown
- Wick presence
- Candle overlap

Automation proxy:

```
Pullback avg body < 70% of impulse avg
```

---

#  Structure Integrity Rule

Trend structure must remain intact.

### Buy Setup Invalid If

- Lower low forms
- Impulse origin breaks
- Close below EMA − 1 pip buffer

### Sell Setup

Opposite conditions.

---

#  Entry Trigger Rules

Continuation confirmation required.

## Buy Entry

```
Break of pullback high + 0.3 pip buffer
```

## Sell Entry

```
Break of pullback low + 0.3 pip buffer
```

---

## Entry Modes

| Mode | Application |
|------|-------------|
| Tick Break | Automation |
| Candle Close | Manual |
| Tick + Delay | Hybrid |

---

#  Spread Filter

Scalping viability depends on spread control.

| Spread | Action |
|--------|--------|
| ≤ 0.8 pip | Trade allowed |
| 0.8 – 1.0 | Caution |
| > 1.0 | Block trades |

---

#  Stop Loss Model

## Structural SL (Primary)

Buy:

```
Below pullback low − 0.5 pip
```

Sell:

```
Above pullback high + 0.5 pip
```

---

## Fixed SL Fallback

```
6 – 7 pips
```

Used when structural stop < 4 pips.

---

#  Take Profit Model

## Standard TP

```
10 pips
```

## Adaptive TP (Recommended)

Options:

- 1 : 1.2 RR
- Liquidity highs/lows
- Impulse projection

Automation Default:

```
RR = 1 : 1.2
```

---

#  Trade Management Rules

## Break‑Even

Move SL to BE at:

```
+5 pips
```

---

## Partial Scaling (Optional)

- Close 70% at TP1
- Trail 30% via EMA

---

## Time Stop

Exit if:

```
No TP hit within 15 candles
```

---

#  Volatility Filter

Minimum activity requirement:

```
Avg candle range ≥ 0.6 pip
```

Low volatility → Skip trades.

---

#  News Filter

Block trading:

```
15 min before red news
15 min after red news
```

High‑impact examples:

- NFP
- CPI
- FOMC
- Rate Decisions

---

#  Risk & Frequency Controls

- Max 5 trades per session
- Max 3 consecutive losses
- Pause trading 1 hour after loss streak

---

#  Automation Execution Flow

```
Session active?
 → Yes
Spread acceptable?
 → Yes
Trend confirmed?
 → Yes
Impulse detected?
 → Yes
Pullback qualified?
 → Yes
Structure intact?
 → Yes
Breakout triggered?
 → Execute trade
Manage SL/TP
```

---

#  A+ Setup Characteristics

Highest probability trades:

- Strong EMA angle
- Clean impulse leg
- 2–3 candle pullback
- EMA tap
- Sharp continuation break

---

#  Avoid Conditions

Do NOT trade when:

- EMA flat
- Deep pullbacks
- Choppy impulses
- Asia session
- News volatility
- Spread spikes

---

#  Performance Expectations

| Metric | Range |
|--------|-------|
| Win Rate | 62 – 72% |
| RR | 1 : 1.2 avg |
| Trades/Day | 3 – 8 |
| Drawdown | Low – Moderate |
| Automation Suitability | High |

---

#  Deployment Stack

Recommended environment:

- Broker: IC Markets Raw
- Platform: MetaTrader 5
- Data: Live Tick Feed
- Execution: Python API
- Hosting: London / NY VPS

---

#  Roadmap Extensions

Planned automation modules:

- Tick candle generator
- Impulse detection engine
- Pullback classifier
- Breakout execution bot
- Risk management layer
- Backtesting framework

---

# ⚠️ Disclaimer

This project is for educational and research purposes only. Live deployment involves financial risk. Past performance does not guarantee future results.

---

# 🤝 Contribution

Pull requests, optimizations, and research improvements are welcome.

---

# 📜 License

MIT License – Free to use, modify, and distribute.

---

**Engineered for modern price action automation.**

