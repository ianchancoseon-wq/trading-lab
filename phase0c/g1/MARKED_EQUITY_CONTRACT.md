# Marked equity & unrealized P&amp;L contract (G1-R1)

## Definitions

- `market_value = Σ (qty_i × mark_i)` over canonical holdings  
- `marked_equity = cash + market_value`  
- Submitted `equity` **must equal** `marked_equity` within `EQUITY_EPS` (1e-6 USD)

## Unrealized P&amp;L

- `unrealized_pnl` is **informational** only for stop inputs.  
- Stops use **marked `equity`** vs `day_start_equity` / `peak_equity`.  
- Because holdings are already marked in `market_value`, unrealized must **not** be subtracted again from cash or from marked equity.  
- If `equity ≈ (cash + market_value − unrealized_pnl)` while `unrealized_pnl ≠ 0` and `equity ≠ marked_equity`, gate emits `UNREALIZED_DOUBLE_COUNT`.

## Fail closed

NaN/Inf/negative marks, fractional holdings (when whole shares required), alias conflicts, or equity mismatches → `REJECT`.
