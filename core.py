import numpy as np
import pandas as pd
from scipy.optimize import minimize



raw_t = np.array([1/12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30])

raw_y = np.array([3.72, 3.67, 3.58, 3.44, 3.47, 3.55, 3.74, 3.97, 4.21, 4.79, 4.85])

ACTUAL_MATURITIES = [1/12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]


def nelson_siegel(t, beta0, beta1, beta2, lamb):
    return beta0 + (beta1 + beta2) * (1 - np.exp(-t / lamb)) / (t / lamb) - beta2 * np.exp(-t / lamb)


def _error(params, t, y):
    return np.sum((nelson_siegel(t, *params) - y) ** 2)

_initial_guess = [raw_y[-1], raw_y[0] - raw_y[-1], 0, 0]

_bounds = [
    (0, 10),
    (-10, 10),
    (-10, 10),
    (0.1, 10),
]

_result = minimize(
    _error,
    _initial_guess,
    args=(raw_t, raw_y),
    bounds=_bounds,
    method="L-BFGS-B",
)

beta0, beta1, beta2, lamb = _result.x


def yield_curve(maturity):
    """Return the Nelson-Siegel fitted yield (%) for a given maturity (years)."""
    return nelson_siegel(maturity, beta0, beta1, beta2, lamb)


def present_value(face_value, coupon_rate, yield_rate, time):
    """Price a bond with semi-annual coupons.

    Parameters
    ----------
    face_value  : float  — par value ($)
    coupon_rate : float  — annual coupon rate as a decimal (e.g. 0.04)
    yield_rate  : float  — annual yield as a decimal (e.g. 0.04)
    time        : float  — years to maturity

    Returns
    -------
    float — clean price ($)
    """
    N = time * 2
    PMT = face_value * coupon_rate / 2
    r = yield_rate / 2

    pv_coupons = PMT * (1 - (1 + r) ** -N) / r
    pv_face = face_value / (1 + r) ** N
    return pv_coupons + pv_face


def macaulay_and_modified_duration(face_value, coupon_rate_annual, ytm_annual, maturity_years, freq=2):
    """
    Semi-annual coupons by default (freq=2).
    Returns: (macaulay_duration_years, modified_duration_years, price)
    """
    N = max(1, int(np.floor(maturity_years * freq)))
    c = face_value * coupon_rate_annual / freq
    y = ytm_annual / freq

    cashflows = np.full(N, c, dtype=float)
    cashflows[-1] += face_value

    periods = np.arange(1, N + 1)
    discount = (1 + y) ** (-periods)

    pv = cashflows * discount
    price = pv.sum()

    times_years = periods / freq
    D_mac = (times_years * pv).sum() / price
    D_mod = D_mac / (1 + y)

    return D_mac, D_mod, price


def run_analysis(H=0.5, face_value=1000):
    """Run the full roll-down simulation for every maturity on a 0.1-year grid.

    Parameters
    ----------
    H          : float — holding period in years (default 0.5 = 6 months)
    face_value : float — bond par value (default 1000)

    Returns
    -------
    pd.DataFrame with columns:
        maturity, price_today, new_maturity, price_after_H,
        carry_return, roll_down_return, total_HPR,
        macaulay_duration, modified_duration,
        approx_%ΔP_1bp, approx_$ΔP_1bp, roll_per_dur
    """
    step = 0.1
    max_maturity = 30.0
    tenor_grid = np.arange(H + step, max_maturity + 1e-9, step)
    tenor_grid = np.round(tenor_grid, 10)

    rows = []
    dy_1bp = 0.0001

    for t in tenor_grid:
        market_yield_pct = float(yield_curve(t))           # e.g. 3.74
        coupon_rate = market_yield_pct / 100               # decimal

        price_today = present_value(face_value, coupon_rate, coupon_rate, t)

        new_maturity = t - H
        new_yield_pct = float(yield_curve(new_maturity))
        new_yield = new_yield_pct / 100

        price_after_H = present_value(face_value, coupon_rate, new_yield, new_maturity)

        coupon_income = coupon_rate * face_value * H

        carry_return = coupon_income / price_today
        roll_down_return = (price_after_H - price_today) / price_today
        total_HPR = carry_return + roll_down_return

        D_mac, D_mod, _ = macaulay_and_modified_duration(
            face_value=face_value,
            coupon_rate_annual=coupon_rate,
            ytm_annual=coupon_rate,
            maturity_years=t,
            freq=2,
        )

        approx_dP_over_P_1bp = -D_mod * dy_1bp
        approx_dP_1bp = approx_dP_over_P_1bp * price_today

        rows.append({
            "maturity": round(t, 1),
            "price_today": price_today,
            "new_maturity": round(new_maturity, 1),
            "price_after_H": price_after_H,
            "carry_return": carry_return,
            "roll_down_return": roll_down_return,
            "total_HPR": total_HPR,
            "macaulay_duration": D_mac,
            "modified_duration": D_mod,
            "approx_%ΔP_1bp": approx_dP_over_P_1bp,
            "approx_$ΔP_1bp": approx_dP_1bp,
        })

    df = pd.DataFrame(rows)
    df["roll_per_dur"] = df["roll_down_return"] / df["modified_duration"]
    return df


# Quick self-test  (python core.py)

if __name__ == "__main__":
    df = run_analysis()
    print(df.head())
    print(f"\nColumns: {list(df.columns)}")
    print(f"Fitted params — beta0={beta0:.4f}, beta1={beta1:.4f}, beta2={beta2:.4f}, lambda={lamb:.4f}")