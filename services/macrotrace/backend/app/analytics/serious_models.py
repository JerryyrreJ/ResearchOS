from __future__ import annotations

import math
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan, linear_reset
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.api import VAR

from ..registry import RegistryStore
from ..schemas import PanelConfig
from ..storage import MacroStore
from .panel import run_state_panel
from .series_utils import load_values


def _finite(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return round(number, digits)


def _stars(p_value: float) -> str:
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.1:
        return "*"
    return ""


def _diagnostic(
    diagnostic_id: str,
    name: str,
    statistic: float | str | None,
    p_value: float | None,
    status: str,
    interpretation: str,
    impact: str,
) -> dict[str, Any]:
    return {
        "diagnostic_id": diagnostic_id,
        "name": name,
        "statistic": _finite(statistic) if isinstance(statistic, (int, float, np.number)) else statistic,
        "p_value": _finite(p_value) if p_value is not None else None,
        "status": status,
        "interpretation": interpretation,
        "credibility_impact": impact,
    }


def _coefficient(label: str, variable_id: str, coef: float, se: float, p_value: float) -> dict[str, Any]:
    critical = stats.norm.ppf(0.975)
    return {
        "variable_id": variable_id,
        "label": label,
        "coefficient": _finite(coef),
        "standard_error": _finite(se),
        "p_value": _finite(p_value),
        "ci_low": _finite(coef - critical * se),
        "ci_high": _finite(coef + critical * se),
        "stars": _stars(p_value),
    }


def _factor_metadata(registry: RegistryStore, factor_ids: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "factor_id": factor_id,
            "definition": registry.get("factors", factor_id)["definition"],
            "series_id": registry.get("factors", factor_id)["series_id"],
            "unit": registry.get("factors", factor_id)["unit"],
            "frequency": registry.get("factors", factor_id)["frequency"],
            "dataset_id": registry.get("factors", factor_id)["dataset_id"],
            "release_lag": registry.get("factors", factor_id)["release_lag"],
        }
        for factor_id in factor_ids
    ]


def _series(store: MacroStore, registry: RegistryStore, factor_id: str, as_of: date) -> pd.Series:
    series_id = registry.get("factors", factor_id)["series_id"]
    if series_id.startswith("STATE_"):
        return pd.Series(dtype=float)
    return load_values(store, series_id, as_of).astype(float)


def _monthly(series: pd.Series, how: str = "last") -> pd.Series:
    if series.empty:
        return series
    ordered = series.sort_index()
    monthly = ordered.resample("MS")
    output = monthly.mean() if how == "mean" else monthly.last()
    # Quarterly official observations are step information sets.  Carry the
    # last released quarterly value through the intervening months before
    # differencing; otherwise pandas' empty monthly buckets make every
    # quarterly difference NaN and silently disable fiscal/GDP models.
    observed_gaps = ordered.index.to_series().diff().dt.days.dropna()
    if not observed_gaps.empty and float(observed_gaps.median()) > 45:
        output = output.ffill()
    return output


def _stationary_transform(factor_id: str, series: pd.Series) -> pd.Series:
    monthly = _monthly(series, "mean" if factor_id.startswith("F.RATES") or factor_id == "F.MONETARY.NFCI" else "last")
    if factor_id == "F.ACTIVITY.RECESSION":
        return monthly
    if factor_id in {
        "F.LABOR.UNEMPLOYMENT",
        "F.LABOR.YOUTH_UR",
        "F.LABOR.YOUTH_EPOP",
        "F.LABOR.BACHELOR_UR",
        "F.LABOR.HS_UR",
        "F.MONETARY.NFCI",
        "F.ACTIVITY.CFNAI",
        "F.HOUSEHOLD.SAVING",
        "F.INFLATION.FORWARD_5Y5Y",
        "F.FISCAL.DEBT_GDP",
        "F.FISCAL.NET_SAVING",
    }:
        return monthly.diff()
    if factor_id.startswith("F.RATES") or factor_id in {"F.INFLATION.BREAKEVEN10", "F.MONETARY.CURVE_10Y2Y", "F.FIN.CREDIT_SPREAD"}:
        return monthly.diff()
    if factor_id == "F.FISCAL.DEBT":
        return np.log(monthly.where(monthly > 0)).diff() * 100
    return np.log(monthly.where(monthly > 0)).diff() * 100


def _linear_forecast_result(
    store: MacroStore,
    registry: RegistryStore,
    as_of: date,
    node_id: str,
    factor_ids: list[str],
    parameters: dict[str, Any],
    *,
    bridge: bool,
) -> dict[str, Any]:
    if not factor_ids:
        raise RuntimeError("A registered target factor is required")
    target_id = factor_ids[0]
    transformed: dict[str, pd.Series] = {}
    for factor_id in factor_ids:
        raw = _series(store, registry, factor_id, as_of)
        if not raw.empty:
            transformed[factor_id] = _stationary_transform(factor_id, raw)
    if target_id not in transformed:
        raise RuntimeError("The registered target factor has no eligible point-in-time data")
    if bridge and len(transformed) < 2:
        raise RuntimeError("Bridge OLS requires a target and at least one available predictor")

    frame = pd.concat(transformed, axis=1).dropna()
    window = int(parameters["estimation_window_years"]) * 12
    horizon = int(parameters["forecast_horizon"])
    lags = int(parameters["lags"])
    minimum = 60 if bridge else 48
    # Keep the full eligible history for the rolling-origin audit.  The
    # registered estimation window limits each fitted model, not the amount of
    # history that may be used to form genuinely prior backtest origins.
    if len(frame) < minimum + horizon + lags:
        raise RuntimeError("Registered linear forecast has insufficient effective monthly history")

    outcome = frame[target_id].shift(-horizon).rename("target_forward")
    regressors = pd.DataFrame(index=frame.index)
    regressors[f"{target_id}.lag0"] = frame[target_id]
    for lag in range(1, lags + 1):
        regressors[f"{target_id}.lag{lag}"] = frame[target_id].shift(lag)
    if bridge:
        for factor_id in factor_ids[1:]:
            if factor_id in frame:
                regressors[factor_id] = frame[factor_id]
    full_regression = pd.concat([outcome, regressors], axis=1).dropna()
    regression = full_regression.tail(window)
    if len(regression) < minimum:
        raise RuntimeError("Registered linear forecast regression is too short")

    x = sm.add_constant(regression.drop(columns="target_forward"), has_constant="add")
    fit = sm.OLS(regression["target_forward"], x).fit(cov_type="HAC", cov_kwds={"maxlags": max(1, horizon)})
    latest_x = sm.add_constant(regressors.dropna().tail(1), has_constant="add").reindex(columns=x.columns, fill_value=1.0)
    point_forecast = float(fit.predict(latest_x).iloc[0])

    holdout = min(30, max(12, len(full_regression) // 5))
    predictions: list[float] = []
    actuals: list[float] = []
    baselines: list[float] = []
    origins: list[pd.Timestamp] = []
    for origin in full_regression.index[-holdout:]:
        cutoff = origin - pd.offsets.MonthBegin(horizon)
        train = full_regression.loc[full_regression.index <= cutoff].tail(window)
        if len(train) < minimum:
            continue
        train_x = sm.add_constant(train.drop(columns="target_forward"), has_constant="add")
        train_fit = sm.OLS(train["target_forward"], train_x).fit()
        origin_x = sm.add_constant(full_regression.loc[[origin]].drop(columns="target_forward"), has_constant="add").reindex(columns=train_x.columns, fill_value=1.0)
        predictions.append(float(train_fit.predict(origin_x).iloc[0]))
        actuals.append(float(full_regression.loc[origin, "target_forward"]))
        baselines.append(float(train["target_forward"].mean()))
        origins.append(origin)
    if len(predictions) < 8:
        raise RuntimeError("Registered rolling-origin backtest has insufficient valid origins")
    predicted = np.asarray(predictions)
    actual = np.asarray(actuals)
    baseline = np.asarray(baselines)
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    baseline_rmse = float(np.sqrt(np.mean((actual - baseline) ** 2)))

    residuals = pd.Series(fit.resid)
    lb = acorr_ljungbox(residuals, lags=[min(12, max(3, len(residuals) // 10))], return_df=True).iloc[-1]
    jb_stat, jb_p, _, _ = sm.stats.jarque_bera(residuals)
    bp_stat, bp_p, _, _ = het_breuschpagan(residuals, fit.model.exog)
    warning_count = int(float(lb["lb_pvalue"]) < 0.05) + int(float(bp_p) < 0.05) + int(rmse > baseline_rmse)
    confidence = _confidence_from_oos(rmse, baseline_rmse, warning_count)
    method = "Registered bridge OLS forecast" if bridge else "Registered univariate autoregressive benchmark"
    recipe_id = "M.BRIDGE_OLS.V1" if bridge else "M.UNIVARIATE_AR.V1"
    evidence_type = "PREDICTIVE_ASSOCIATION" if bridge else "PREDICTIVE_BENCHMARK"
    diagnostics = [
        _diagnostic(f"{recipe_id}.OOS", "Rolling-origin RMSE ratio", rmse / baseline_rmse if baseline_rmse else None, None, "PASS" if rmse < baseline_rmse else "WARNING", "Compares the registered forecast with a training-mean benchmark using only outcomes available at each origin.", "Failure to beat the benchmark caps confidence."),
        _diagnostic(f"{recipe_id}.LB", "Ljung-Box residual autocorrelation", float(lb["lb_stat"]), float(lb["lb_pvalue"]), "PASS" if float(lb["lb_pvalue"]) >= 0.05 else "WARNING", "Tests residual serial correlation at a registered lag.", "Residual dependence can understate forecast uncertainty."),
        _diagnostic(f"{recipe_id}.BP", "Breusch-Pagan heteroskedasticity", float(bp_stat), float(bp_p), "PASS" if float(bp_p) >= 0.05 else "WARNING", "HAC covariance is reported regardless of this diagnostic.", "Heteroskedasticity changes inference, not OLS unbiasedness by itself."),
        _diagnostic(f"{recipe_id}.JB", "Jarque-Bera residual distribution", float(jb_stat), float(jb_p), "PASS" if float(jb_p) >= 0.05 else "WARNING", "Residual normality is shown as a finite-sample diagnostic, not an OLS unbiasedness requirement.", "Non-normality makes small-sample Gaussian inference less persuasive."),
    ]
    coefficients = [
        _coefficient(name, name, float(fit.params[name]), float(fit.bse[name]), float(fit.pvalues[name]))
        for name in fit.params.index
    ]
    points = [
        {"date": timestamp.date().isoformat(), "value": _finite(value)}
        for timestamp, value in zip(origins, predictions, strict=True)
    ]
    return {
        "status": "SUCCESS",
        "node_id": node_id,
        "model_recipe_id": recipe_id,
        "method": method,
        "evidence_type": evidence_type,
        "title": f"{method}: {target_id}",
        "summary": f"The registered {horizon}-month transformed forecast for {target_id} is {point_forecast:.3f}; rolling-origin RMSE is {rmse:.3f} versus {baseline_rmse:.3f} for the benchmark.",
        "direction": "INCREASING" if point_forecast > 0 else "DECREASING",
        "signal": float(np.tanh(point_forecast)),
        "confidence": confidence,
        "specification": {
            "formula": f"{target_id}_{{t+{horizon}}} = alpha + phi(L){target_id}_t" + (" + beta'X_t + epsilon_t" if bridge else " + epsilon_t"),
            "estimand": f"Registered {horizon}-month-ahead transformed value of {target_id}",
            "dependent_variable": target_id,
            "independent_variables": list(regressors.columns),
            "controls": [],
            "causal_interpretation_allowed": False,
        },
        "variables": _factor_metadata(registry, factor_ids),
        "sample": {"start": regression.index[0].date().isoformat(), "end": regression.index[-1].date().isoformat(), "observations": len(regression), "frequency": "monthly", "window_years": parameters["estimation_window_years"]},
        "table": {"table_id": f"T.{node_id}.{recipe_id}", "title": method, "dependent_variable": target_id, "columns": ["(1)"], "coefficients": {"(1)": coefficients}, "statistics": {"Observations": [len(regression)], "R-squared": [_finite(fit.rsquared)], "Adjusted R-squared": [_finite(fit.rsquared_adj)], "HAC max lag": [max(1, horizon)], "Forecast horizon": [horizon], "Model version": [recipe_id]}, "notes": ["HAC standard errors.", "Predictive/associational specification; no causal interpretation."]},
        "diagnostics": diagnostics,
        "robustness": {"oos_design": "expanding-origin with label-availability cutoff", "oos_origins": len(predictions), "rmse": _finite(rmse), "baseline_rmse": _finite(baseline_rmse), "rmse_ratio": _finite(rmse / baseline_rmse if baseline_rmse else None)},
        "charts": [{"chart_id": f"CH.{node_id}.OOS", "kind": "actual_fitted", "title": "Rolling-origin transformed forecasts", "series": [{"series_id": "forecast", "label": "预测", "points": points}, {"series_id": "actual", "label": "实际", "points": [{"date": timestamp.date().isoformat(), "value": _finite(value)} for timestamp, value in zip(origins, actuals, strict=True)]}]}],
        "aggregation_input": {"target": target_id, "horizon": horizon, "point_forecast": _finite(point_forecast), "oos_loss": _finite(rmse**2), "baseline_oos_loss": _finite(baseline_rmse**2)},
    }


def run_univariate_ar(store: MacroStore, registry: RegistryStore, as_of: date, node_id: str, factor_ids: list[str], parameters: dict[str, Any]) -> dict[str, Any]:
    return _linear_forecast_result(store, registry, as_of, node_id, factor_ids, parameters, bridge=False)


def run_bridge_ols(store: MacroStore, registry: RegistryStore, as_of: date, node_id: str, factor_ids: list[str], parameters: dict[str, Any]) -> dict[str, Any]:
    return _linear_forecast_result(store, registry, as_of, node_id, factor_ids, parameters, bridge=True)


def _confidence_from_oos(rmse: float | None, baseline_rmse: float | None, warning_count: int) -> str:
    if rmse is None or baseline_rmse is None:
        return "LOW"
    if rmse < baseline_rmse and warning_count == 0:
        return "HIGH"
    if rmse <= baseline_rmse * 1.15 and warning_count <= 2:
        return "MEDIUM"
    return "LOW"


def run_dynamic_factor(
    store: MacroStore,
    registry: RegistryStore,
    as_of: date,
    node_id: str,
    factor_ids: list[str],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    if len(factor_ids) < 3:
        raise RuntimeError("Dynamic factor requires at least three registered indicators")
    transformed: dict[str, pd.Series] = {}
    for factor_id in factor_ids:
        raw = _series(store, registry, factor_id, as_of)
        if not raw.empty:
            transformed[factor_id] = _stationary_transform(factor_id, raw)
    if len(transformed) < 3:
        raise RuntimeError("Dynamic factor has fewer than three available registered indicators")
    frame = pd.concat(transformed, axis=1).dropna()
    window = int(parameters["estimation_window_years"]) * 12
    frame = frame.tail(window)
    horizon = int(parameters["forecast_horizon"])
    if len(frame) < 60 + horizon:
        raise RuntimeError("Dynamic factor has fewer than 60 effective months")

    target_id = factor_ids[0]
    if target_id not in frame:
        target_id = frame.columns[0]
    feature_ids = [column for column in frame.columns if column != target_id]
    if not feature_ids:
        feature_ids = [target_id]
    feature_frame = frame[feature_ids]
    means = feature_frame.mean()
    scales = feature_frame.std(ddof=1).replace(0, np.nan)
    standardized = ((feature_frame - means) / scales).dropna(axis=1)
    if standardized.empty:
        raise RuntimeError("Dynamic factor standardization failed")
    u, singular_values, vt = np.linalg.svd(standardized.to_numpy(), full_matrices=False)
    factor_count = min(int(parameters["factor_count"]), vt.shape[0])
    scores = u[:, :factor_count] * singular_values[:factor_count]
    loadings = vt[:factor_count].T
    explained = singular_values**2 / np.sum(singular_values**2)

    regressors = pd.DataFrame(scores, index=standardized.index, columns=[f"factor_{i+1}" for i in range(factor_count)])
    regressors["target_lag_1"] = frame[target_id].shift(1)
    outcome = frame[target_id].shift(-horizon).rename("target_forward")
    regression = pd.concat([outcome, regressors], axis=1).dropna()
    if len(regression) < 48:
        raise RuntimeError("Dynamic factor bridge regression has insufficient history")
    x = sm.add_constant(regression.drop(columns="target_forward"), has_constant="add")
    model = sm.OLS(regression["target_forward"], x).fit(cov_type="HAC", cov_kwds={"maxlags": max(1, horizon)})
    latest_x = sm.add_constant(regressors.tail(1), has_constant="add").reindex(columns=x.columns, fill_value=1.0)
    forecast = float(model.predict(latest_x).iloc[0])

    # Re-estimate scaling, PCA loadings and the bridge at every historical
    # origin.  The test block is never used to estimate its own factor space.
    holdout = min(24, max(12, len(regression) // 5))
    test_origins = list(regression.index[-holdout:])
    oos_predictions: dict[pd.Timestamp, float] = {}
    oos_actual: dict[pd.Timestamp, float] = {}
    oos_baseline: dict[pd.Timestamp, float] = {}
    for origin in test_origins:
        origin_pos = int(frame.index.get_loc(origin))
        if origin_pos <= horizon + 48:
            continue
        feature_history = feature_frame.iloc[: origin_pos + 1]
        history_means = feature_history.mean()
        history_scales = feature_history.std(ddof=1).replace(0, np.nan)
        history_standardized = ((feature_history - history_means) / history_scales).dropna(axis=1)
        if history_standardized.empty:
            continue
        u_bt, singular_bt, vt_bt = np.linalg.svd(history_standardized.to_numpy(), full_matrices=False)
        factor_count_bt = min(factor_count, vt_bt.shape[0])
        scores_bt = history_standardized.to_numpy() @ vt_bt[:factor_count_bt].T
        regressors_bt = pd.DataFrame(scores_bt, index=history_standardized.index, columns=[f"factor_{i+1}" for i in range(factor_count_bt)])
        regressors_bt["target_lag_1"] = frame[target_id].shift(1).reindex(regressors_bt.index)
        regression_bt = pd.concat([outcome, regressors_bt], axis=1).dropna()
        last_known_outcome_origin = frame.index[origin_pos - horizon]
        train_bt = regression_bt.loc[regression_bt.index <= last_known_outcome_origin]
        if len(train_bt) < 48 or origin not in regressors_bt.index or origin not in regression.index:
            continue
        x_bt = sm.add_constant(train_bt.drop(columns="target_forward"), has_constant="add")
        model_bt = sm.OLS(train_bt["target_forward"], x_bt).fit()
        origin_x = sm.add_constant(regressors_bt.loc[[origin]], has_constant="add").reindex(columns=model_bt.model.exog_names, fill_value=1.0)
        oos_predictions[origin] = float(model_bt.predict(origin_x).iloc[0])
        oos_actual[origin] = float(regression.loc[origin, "target_forward"])
        oos_baseline[origin] = float(train_bt["target_forward"].mean())
    if len(oos_predictions) < 8:
        raise RuntimeError("Dynamic factor rolling-origin backtest has insufficient valid origins")
    predictions = pd.Series(oos_predictions).sort_index()
    test = regression.loc[predictions.index]
    actual_oos = pd.Series(oos_actual).reindex(predictions.index)
    baseline_oos = pd.Series(oos_baseline).reindex(predictions.index)
    rmse = float(np.sqrt(np.mean((actual_oos - predictions) ** 2)))
    baseline_rmse = float(np.sqrt(np.mean((actual_oos - baseline_oos) ** 2)))
    lb = acorr_ljungbox(model.resid, lags=[min(12, max(3, len(model.resid) // 10))], return_df=True).iloc[-1]
    warning_count = int(float(lb["lb_pvalue"]) < 0.05) + int(rmse > baseline_rmse)
    diagnostics = [
        _diagnostic("DFM.VARIANCE", "First-factor explained variance", float(explained[0]), None, "PASS" if explained[0] >= 0.25 else "WARNING", "Share of standardized predictor variance captured by the first common factor.", "Low variance share weakens the latent-state interpretation."),
        _diagnostic("DFM.LJUNG_BOX", "Residual Ljung-Box", float(lb["lb_stat"]), float(lb["lb_pvalue"]), "PASS" if float(lb["lb_pvalue"]) >= 0.05 else "WARNING", "Tests remaining serial correlation in the bridge residuals.", "Serial correlation can make interval estimates too optimistic."),
        _diagnostic("DFM.OOS", "Rolling-origin holdout RMSE ratio", rmse / baseline_rmse if baseline_rmse else None, None, "PASS" if rmse < baseline_rmse else "WARNING", "Compares the registered bridge model with a training-mean baseline.", "A model that does not beat the baseline is supporting evidence only."),
        _diagnostic("DFM.RAGGED_EDGE", "Ragged-edge handling", "complete-case monthly snapshot", None, "WARNING", "This MVP aligns the latest common complete month rather than running a full release-calendar Kalman filter.", "The nowcast is conservative but may omit the newest partial information set."),
    ]
    coefficients = [
        _coefficient(name, name, float(model.params[name]), float(model.bse[name]), float(model.pvalues[name]))
        for name in model.params.index
    ]
    latest_date = regression.index[-1]
    return {
        "status": "SUCCESS",
        "node_id": node_id,
        "model_recipe_id": "M.DFM_NOWCAST.V1",
        "method": "Dynamic factor / bridge nowcast",
        "evidence_type": "PREDICTIVE",
        "title": "Common-factor bridge forecast",
        "summary": f"The registered common-factor system forecasts a {forecast:.3f} transformed-unit move at horizon {horizon} month(s).",
        "direction": "UP" if forecast > 0 else "DOWN",
        "signal": float(np.tanh(forecast / max(frame[target_id].std(), 1e-6))),
        "confidence": _confidence_from_oos(rmse, baseline_rmse, warning_count),
        "specification": {
            "formula": f"y_{{t+{horizon}}} = alpha + beta' F_t + rho y_{{t-1}} + epsilon_t",
            "estimand": f"Conditional {horizon}-month-ahead transformed change in {target_id}",
            "dependent_variable": target_id,
            "independent_variables": [f"Common factor {index + 1}" for index in range(factor_count)],
            "controls": [f"Lagged {target_id}"],
        },
        "variables": _factor_metadata(registry, list(frame.columns)),
        "sample": {"start": regression.index[0].date().isoformat(), "end": latest_date.date().isoformat(), "observations": int(model.nobs), "frequency": "monthly", "window_policy": f"last {parameters['estimation_window_years']} years"},
        "table": {"table_id": f"T.{node_id}.DFM", "title": "Dynamic-factor bridge regression", "dependent_variable": target_id, "columns": [f"h={horizon}"], "coefficients": {f"h={horizon}": coefficients}, "statistics": {"Observations": [int(model.nobs)], "R-squared": [_finite(model.rsquared)], "Adjusted R-squared": [_finite(model.rsquared_adj)], "Covariance": ["HAC"], "HAC lags": [max(1, horizon)], "Model version": ["M.DFM_NOWCAST.V1"]}, "notes": ["Standard errors in parentheses in the rendered three-line table.", "* p<0.10, ** p<0.05, *** p<0.01."]},
        "diagnostics": diagnostics,
        "robustness": {"oos_design": "rolling-origin; scaling, PCA loadings, and bridge refit at every origin", "pca_test_leakage_allowed": False, "equal_weight_baseline_rmse": _finite(baseline_rmse), "model_oos_rmse": _finite(rmse), "rmse_ratio": _finite(rmse / baseline_rmse if baseline_rmse else None)},
        "charts": [
            {"chart_id": f"CH.{node_id}.LOADINGS", "kind": "factor_loadings", "title": "Estimated common-factor loadings", "series": [{"series_id": "factor_1", "label": "因子 1 载荷", "points": [{"date": factor_id, "value": _finite(loadings[index, 0])} for index, factor_id in enumerate(standardized.columns)]}]},
            {"chart_id": f"CH.{node_id}.OOS", "kind": "actual_vs_forecast", "title": "Out-of-sample bridge forecast", "series": [{"series_id": "actual", "label": "实际", "points": [{"date": idx.date().isoformat(), "value": _finite(value)} for idx, value in test["target_forward"].items()]}, {"series_id": "forecast", "label": "预测", "points": [{"date": idx.date().isoformat(), "value": _finite(value)} for idx, value in predictions.items()]}]},
        ],
        "aggregation_input": {"target": target_id, "horizon": horizon, "point_forecast": _finite(forecast), "oos_loss": _finite(rmse**2), "baseline_oos_loss": _finite(baseline_rmse**2)},
    }


def run_var(
    store: MacroStore,
    registry: RegistryStore,
    as_of: date,
    node_id: str,
    factor_ids: list[str],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    unique_ids = list(dict.fromkeys(factor_ids))[:5]
    columns: dict[str, pd.Series] = {}
    for factor_id in unique_ids:
        raw = _series(store, registry, factor_id, as_of)
        if not raw.empty:
            columns[factor_id] = _stationary_transform(factor_id, raw)
    if len(columns) < 2:
        raise RuntimeError("VAR requires at least two available registered series")
    frame = pd.concat(columns, axis=1).dropna().tail(int(parameters["estimation_window_years"]) * 12)
    lags = int(parameters["lags"])
    horizon = int(parameters["forecast_horizon"])
    if len(frame) < max(80, lags * len(frame.columns) * 4):
        raise RuntimeError("VAR effective sample is too short")
    model = VAR(frame).fit(lags, trend="c")
    stable = bool(model.is_stable(verbose=False))
    forecast_array, forecast_lower, forecast_upper = model.forecast_interval(
        frame.to_numpy()[-lags:], steps=horizon, alpha=0.05
    )
    forecast_index = pd.date_range(frame.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    forecast = pd.DataFrame(forecast_array, index=forecast_index, columns=frame.columns)
    target_id = frame.columns[0]

    holdout = min(18, max(12, len(frame) // 6))
    train = frame.iloc[:-holdout]
    test = frame.iloc[-holdout:]
    history = train.copy()
    oos_values: list[float] = []
    for idx in test.index:
        # Expanding-origin refit: parameters are estimated only with data that
        # would have been available at this forecast origin.
        oos_fit = VAR(history).fit(lags, trend="c")
        prediction = oos_fit.forecast(history.to_numpy()[-lags:], steps=1)[0]
        oos_values.append(float(prediction[0]))
        history = pd.concat([history, test.loc[[idx]]])
    actual = test[target_id].to_numpy()
    rmse = float(np.sqrt(np.mean((actual - np.asarray(oos_values)) ** 2)))
    baseline_values = train[target_id].tail(12).mean()
    baseline_rmse = float(np.sqrt(np.mean((actual - baseline_values) ** 2)))
    portmanteau = model.test_whiteness(nlags=max(lags + 1, min(12, lags + 6)), adjusted=True)
    normality = model.test_normality()
    warning_count = int(not stable) + int(portmanteau.pvalue < 0.05) + int(rmse > baseline_rmse)

    equation = target_id
    coefficients = [
        _coefficient(name, name, float(model.params.loc[name, equation]), float(model.stderr.loc[name, equation]), float(model.pvalues.loc[name, equation]))
        for name in model.params.index
    ]
    irf = model.irf(min(12, horizon)).irfs
    fevd = model.fevd(min(12, horizon))
    fevd_decomp = fevd.decomp
    response_column = 0
    shock_column = min(1, len(frame.columns) - 1)
    diagnostics = [
        _diagnostic("VAR.STABILITY", "Companion-matrix stability", max(abs(model.roots)) if len(model.roots) else None, None, "PASS" if stable else "FAIL", "All inverse characteristic roots must lie outside the unit circle under statsmodels' convention.", "An unstable VAR invalidates long-horizon forecasts and impulse responses."),
        _diagnostic("VAR.PORTMANTEAU", "Residual Portmanteau whiteness", float(portmanteau.test_statistic), float(portmanteau.pvalue), "PASS" if portmanteau.pvalue >= 0.05 else "WARNING", "Tests joint residual autocorrelation.", "Residual dependence suggests the lag specification is incomplete."),
        _diagnostic("VAR.NORMALITY", "Multivariate residual normality", float(normality.test_statistic), float(normality.pvalue), "PASS" if normality.pvalue >= 0.05 else "WARNING", "Normality affects small-sample inference, not unbiasedness of a correctly specified large-sample OLS equation.", "Non-normal residuals make Gaussian intervals less reliable."),
        _diagnostic("VAR.OOS", "Rolling one-step RMSE ratio", rmse / baseline_rmse if baseline_rmse else None, None, "PASS" if rmse < baseline_rmse else "WARNING", "Compares recursive one-step forecasts with a training-window mean.", "Failure to beat the baseline lowers the evidence tier."),
    ]
    return {
        "status": "SUCCESS" if stable else "FAILED",
        "node_id": node_id,
        "model_recipe_id": "M.VAR_SYSTEM.V1",
        "method": "Registered vector autoregression",
        "evidence_type": "PREDICTIVE_STRUCTURAL_PROXY",
        "title": "Registered VAR system",
        "summary": f"The {len(frame.columns)}-variable VAR projects {target_id} at {forecast[target_id].iloc[-1]:.3f} transformed units at month {horizon}.",
        "direction": "UP" if forecast[target_id].iloc[-1] > 0 else "DOWN",
        "signal": float(np.tanh(forecast[target_id].mean() / max(frame[target_id].std(), 1e-6))),
        "confidence": _confidence_from_oos(rmse, baseline_rmse, warning_count),
        "specification": {"formula": f"Y_t = c + A_1Y_{{t-1}} + ... + A_{lags}Y_{{t-{lags}}} + u_t", "estimand": f"Joint dynamic system and {horizon}-month forecast", "dependent_variable": target_id, "independent_variables": list(frame.columns), "controls": [f"{lags} registered lag(s)"]},
        "variables": _factor_metadata(registry, list(frame.columns)),
        "sample": {"start": frame.index[0].date().isoformat(), "end": frame.index[-1].date().isoformat(), "observations": int(model.nobs), "frequency": "monthly", "window_policy": f"last {parameters['estimation_window_years']} years"},
        "table": {"table_id": f"T.{node_id}.VAR", "title": f"VAR equation: {target_id}", "dependent_variable": target_id, "columns": [equation], "coefficients": {equation: coefficients}, "statistics": {"Observations": [int(model.nobs)], "System variables": [len(frame.columns)], "Lags": [lags], "Log likelihood": [_finite(model.llf)], "AIC": [_finite(model.aic)], "BIC": [_finite(model.bic)], "Stable": ["Yes" if stable else "No"], "Model version": ["M.VAR_SYSTEM.V1"]}, "notes": ["Registered Cholesky ordering follows the displayed variable order.", "Impulse responses are structural proxies unless the ordering is substantively defended."]},
        "diagnostics": diagnostics,
        "robustness": {"model_oos_rmse": _finite(rmse), "baseline_oos_rmse": _finite(baseline_rmse), "rmse_ratio": _finite(rmse / baseline_rmse if baseline_rmse else None), "identification": parameters["identification"], "forecast_interval": "analytic 95% VAR interval", "fevd_final_horizon": {column: _finite(fevd_decomp[response_column, -1, index]) for index, column in enumerate(frame.columns)}},
        "charts": [
            {"chart_id": f"CH.{node_id}.FORECAST", "kind": "forecast_fan", "title": f"VAR forecast: {target_id}", "series": [{"series_id": "history", "label": "历史", "points": [{"date": idx.date().isoformat(), "value": _finite(value)} for idx, value in frame[target_id].tail(48).items()]}, {"series_id": "lower95", "label": "95% 下界", "points": [{"date": idx.date().isoformat(), "value": _finite(forecast_lower[row, response_column])} for row, idx in enumerate(forecast.index)]}, {"series_id": "forecast", "label": "点预测", "points": [{"date": idx.date().isoformat(), "value": _finite(value)} for idx, value in forecast[target_id].items()]}, {"series_id": "upper95", "label": "95% 上界", "points": [{"date": idx.date().isoformat(), "value": _finite(forecast_upper[row, response_column])} for row, idx in enumerate(forecast.index)]}]},
            {"chart_id": f"CH.{node_id}.IRF", "kind": "irf", "title": f"IRF: {target_id} response to {frame.columns[shock_column]}", "series": [{"series_id": "irf", "label": "脉冲响应", "points": [{"date": str(step), "value": _finite(irf[step, response_column, shock_column])} for step in range(irf.shape[0])]}]},
            {"chart_id": f"CH.{node_id}.FEVD", "kind": "fevd", "title": f"FEVD: innovations explaining {target_id}", "series": [{"series_id": column, "label": column, "points": [{"date": str(step + 1), "value": _finite(fevd_decomp[response_column, step, index])} for step in range(fevd_decomp.shape[1])]} for index, column in enumerate(frame.columns)]},
        ],
        "aggregation_input": {
            "target": target_id,
            "horizon": horizon,
            "point_forecast": _finite(forecast[target_id].iloc[-1]),
            "oos_loss": _finite(rmse**2),
            "baseline_oos_loss": _finite(baseline_rmse**2),
            "scenario_response": {
                "response_factor_id": target_id,
                "shock_factor_id": frame.columns[shock_column],
                "shock_definition": "one-standard-deviation registered Cholesky innovation",
                "identification_strength": "STRUCTURAL_PROXY",
                "response_horizon": min(12, horizon),
                "response_path": [
                    {"horizon": step, "effect": _finite(irf[step, response_column, shock_column])}
                    for step in range(irf.shape[0])
                ],
                "interpretation": "Ordering-based conditional system response; not an externally identified structural shock.",
            },
        },
    }


def run_local_projection(
    store: MacroStore,
    registry: RegistryStore,
    as_of: date,
    node_id: str,
    factor_ids: list[str],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    if "F.ENERGY.WTI" not in factor_ids:
        factor_ids = ["F.ENERGY.WTI", *factor_ids]
    response_id = "F.CPI.HEADLINE" if "F.CPI.HEADLINE" in factor_ids else next((item for item in factor_ids if item.startswith("F.CPI")), None)
    if response_id is None:
        raise RuntimeError("Local projection lacks a registered inflation response")
    wti = _monthly(_series(store, registry, "F.ENERGY.WTI", as_of), "mean")
    cpi = _monthly(_series(store, registry, response_id, as_of), "last")
    unemployment = _monthly(_series(store, registry, "F.LABOR.UNEMPLOYMENT", as_of), "last")
    shock = (np.log(wti.where(wti > 0)).diff() * 100).rename("shock")
    response = (np.log(cpi.where(cpi > 0)).diff() * 100).rename("inflation")
    controls = unemployment.diff().rename("delta_unemployment")
    base = pd.concat([shock, response, controls], axis=1).dropna()
    shock_std = float(base["shock"].std(ddof=1))
    if len(base) < 90 or shock_std < 1e-8:
        raise RuntimeError("Local projection lacks sufficient shock history")
    base["shock"] = base["shock"] / shock_std
    lags = int(parameters["lags"])
    horizon = int(parameters["response_horizon"])
    rows: list[dict[str, Any]] = []
    models: dict[int, Any] = {}
    for h in range(-6, horizon + 1):
        data = base.copy()
        data["outcome"] = data["inflation"].shift(-h)
        for lag in range(1, lags + 1):
            data[f"inflation_lag_{lag}"] = data["inflation"].shift(lag)
            data[f"shock_lag_{lag}"] = data["shock"].shift(lag)
        data = data.dropna()
        x_columns = ["shock", "delta_unemployment", *[f"inflation_lag_{lag}" for lag in range(1, lags + 1)], *[f"shock_lag_{lag}" for lag in range(1, lags + 1)]]
        fit = sm.OLS(data["outcome"], sm.add_constant(data[x_columns], has_constant="add")).fit(cov_type="HAC", cov_kwds={"maxlags": max(1, lags)})
        models[h] = fit
        rows.append({"horizon": h, **_coefficient("WTI shock (1 SD)", "F.ENERGY.WTI", float(fit.params["shock"]), float(fit.bse["shock"]), float(fit.pvalues["shock"]))})
    post_rows = [row for row in rows if row["horizon"] >= 0]
    pre_rows = [row for row in rows if row["horizon"] < 0]
    pre_stat = sum((row["coefficient"] / row["standard_error"]) ** 2 for row in pre_rows if row["standard_error"])
    pre_p = float(stats.chi2.sf(pre_stat, max(1, len(pre_rows))))
    placebo_data = base.copy()
    placebo_data["placebo_shock"] = placebo_data["shock"].shift(12)
    placebo_data = placebo_data.dropna()
    placebo_fit = sm.OLS(placebo_data["inflation"], sm.add_constant(placebo_data[["placebo_shock", "delta_unemployment"]], has_constant="add")).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    peak = max(post_rows, key=lambda row: abs(row["coefficient"]))
    main_model = models[0]
    lb = acorr_ljungbox(main_model.resid, lags=[min(12, max(3, len(main_model.resid) // 10))], return_df=True).iloc[-1]
    diagnostics = [
        _diagnostic("LP.PRETREND", "Joint pre-response diagnostic", pre_stat, pre_p, "PASS" if pre_p >= 0.05 else "WARNING", "Approximate joint Wald diagnostic for non-zero pre-event response coefficients.", "Non-zero pre-responses weaken shock timing and causal interpretation."),
        _diagnostic("LP.PLACEBO", "12-month shifted-shock placebo", float(placebo_fit.tvalues["placebo_shock"]), float(placebo_fit.pvalues["placebo_shock"]), "PASS" if placebo_fit.pvalues["placebo_shock"] >= 0.05 else "WARNING", "A distant shifted shock should not explain current inflation.", "A significant placebo suggests persistent confounding."),
        _diagnostic("LP.LJUNG_BOX", "Horizon-zero residual Ljung-Box", float(lb["lb_stat"]), float(lb["lb_pvalue"]), "PASS" if lb["lb_pvalue"] >= 0.05 else "WARNING", "Checks residual serial correlation after HAC inference.", "Strong residual dependence lowers precision confidence."),
        _diagnostic("LP.IDENTIFICATION", "Shock identification", "WTI log innovation", None, "WARNING", "WTI innovations are not an externally identified supply shock in this MVP.", "Results are dynamic associations and must not be labeled causal."),
    ]
    columns = [f"h={row['horizon']}" for row in post_rows]
    coefficient_map = {column: [{key: value for key, value in row.items() if key != "horizon"}] for column, row in zip(columns, post_rows, strict=True)}
    return {
        "status": "SUCCESS",
        "node_id": node_id,
        "model_recipe_id": "M.LOCAL_PROJECTION.V1",
        "method": "Local projection event study",
        "evidence_type": "DYNAMIC_ASSOCIATION",
        "title": "WTI-to-inflation local projection",
        "summary": f"The largest registered response is {peak['coefficient']:.3f} monthly inflation points at horizon {peak['horizon']} after a one-standard-deviation WTI innovation.",
        "direction": "INFLATIONARY" if peak["coefficient"] > 0 else "DISINFLATIONARY",
        "signal": float(np.tanh(peak["coefficient"] / max(abs(peak["standard_error"]), 0.1))),
        "confidence": "MEDIUM" if pre_p >= 0.05 and placebo_fit.pvalues["placebo_shock"] >= 0.05 else "LOW",
        "specification": {"formula": f"pi_{{t+h}} = alpha_h + beta_h shock_t + Gamma_h(L)X_t + epsilon_{{t+h}}, h=-6,...,{horizon}", "estimand": "Dynamic inflation response to a one-standard-deviation WTI log innovation", "dependent_variable": response_id, "independent_variables": ["F.ENERGY.WTI"], "controls": ["change in unemployment", f"{lags} lags of inflation and shock"]},
        "variables": _factor_metadata(registry, ["F.ENERGY.WTI", response_id, "F.LABOR.UNEMPLOYMENT"]),
        "sample": {"start": base.index[0].date().isoformat(), "end": base.index[-1].date().isoformat(), "observations": int(main_model.nobs), "frequency": "monthly", "window_policy": "maximum common registered history"},
        "table": {"table_id": f"T.{node_id}.LP", "title": "Local-projection response by horizon", "dependent_variable": response_id, "columns": columns, "coefficients": coefficient_map, "statistics": {"Observations": [int(models[row["horizon"]].nobs) for row in post_rows], "HAC lags": [lags] * len(post_rows), "Controls": ["Yes"] * len(post_rows), "Model version": ["M.LOCAL_PROJECTION.V1"] * len(post_rows)}, "notes": ["Each column is a separately estimated horizon regression.", "The WTI innovation is not an externally identified supply shock; estimates are associational and not causal."]},
        "diagnostics": diagnostics,
        "robustness": {"pre_response_joint_p_value": _finite(pre_p), "placebo_p_value": _finite(placebo_fit.pvalues["placebo_shock"]), "shock_standard_deviation_pct": _finite(shock_std)},
        "charts": [{"chart_id": f"CH.{node_id}.EVENT", "kind": "event_study", "title": "Inflation response to a WTI innovation", "series": [{"series_id": "coefficient", "label": "响应", "points": [{"date": str(row["horizon"]), "value": row["coefficient"]} for row in rows]}, {"series_id": "ci_low", "label": "95% 置信下界", "points": [{"date": str(row["horizon"]), "value": row["ci_low"]} for row in rows]}, {"series_id": "ci_high", "label": "95% 置信上界", "points": [{"date": str(row["horizon"]), "value": row["ci_high"]} for row in rows]}]}],
        "aggregation_input": {
            "target": response_id,
            "horizon": int(peak["horizon"]),
            "effect": peak["coefficient"],
            "standard_error": peak["standard_error"],
            "estimand": "monthly inflation response to one-SD WTI innovation",
            "scenario_response": {
                "response_factor_id": response_id,
                "shock_factor_id": "F.ENERGY.WTI",
                "shock_definition": "one-standard-deviation WTI log innovation",
                "observed_shock_standard_deviation_pct": _finite(shock_std),
                "identification_strength": "ASSOCIATIONAL_DYNAMIC",
                "response_horizon": horizon,
                "response_path": [
                    {
                        "horizon": row["horizon"],
                        "effect": row["coefficient"],
                        "standard_error": row["standard_error"],
                        "ci_low": row["ci_low"],
                        "ci_high": row["ci_high"],
                        "p_value": row["p_value"],
                    }
                    for row in post_rows
                ],
                "interpretation": "Dynamic association with HAC inference; WTI innovations are not externally identified oil-supply shocks.",
            },
        },
    }


def _pinball(actual: np.ndarray, predicted: np.ndarray, quantile: float) -> float:
    error = actual - predicted
    return float(np.mean(np.maximum(quantile * error, (quantile - 1) * error)))


def run_growth_at_risk(
    store: MacroStore,
    registry: RegistryStore,
    as_of: date,
    node_id: str,
    factor_ids: list[str],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    gdp = _series(store, registry, "F.ACTIVITY.REAL_GDP", as_of).resample("QS").last()
    nfci = _series(store, registry, "F.MONETARY.NFCI", as_of).resample("QS").mean()
    horizon = int(parameters["forecast_horizon_quarters"])
    current_growth = ((gdp / gdp.shift(1)) ** 4 - 1) * 100
    forward_growth = ((gdp.shift(-horizon) / gdp) ** (4 / horizon) - 1) * 100
    predictors = pd.concat([nfci.rename("nfci"), current_growth.rename("current_growth")], axis=1).dropna()
    frame = pd.concat([forward_growth.rename("forward_growth"), predictors], axis=1).dropna()
    if len(frame) < 80:
        raise RuntimeError("Growth-at-Risk requires at least 80 quarterly observations; sync GDPC1 history")
    if parameters["estimation_window"] == "ROLLING_20Y":
        frame = frame.tail(80)
    quantiles = [float(value) for value in parameters["quantiles"]]
    x = sm.add_constant(frame[["nfci", "current_growth"]], has_constant="add")
    fits = {quantile: sm.QuantReg(frame["forward_growth"], x).fit(q=quantile, max_iter=5000) for quantile in quantiles}
    # Forecast from the genuinely latest predictor information, not the last
    # row whose future GDP outcome is already observable.
    latest_predictors = predictors.tail(1)
    latest_x = sm.add_constant(latest_predictors, has_constant="add").reindex(columns=x.columns, fill_value=1.0)
    predictions = {quantile: float(fit.predict(latest_x).iloc[0]) for quantile, fit in fits.items()}
    crossing = any(predictions[left] > predictions[right] for left, right in zip(quantiles, quantiles[1:]))

    holdout = min(16, max(8, len(frame) // 6))
    test = frame.iloc[-holdout:]
    oos_losses: dict[float, float] = {}
    baseline_losses: dict[float, float] = {}
    rolling_predictions: dict[float, list[float]] = {quantile: [] for quantile in quantiles}
    rolling_baselines: dict[float, list[float]] = {quantile: [] for quantile in quantiles}
    for quantile in quantiles:
        for origin in test.index:
            origin_position = int(frame.index.get_loc(origin))
            safe_label_position = origin_position - horizon
            if safe_label_position < 0:
                continue
            # At origin t, a forward h-quarter label is observable only for
            # base dates <= t-h.  Excluding merely the origin leaks h-1 future
            # quarterly outcomes when h > 1.
            expanding = frame.loc[frame.index <= frame.index[safe_label_position]]
            if len(expanding) < 60:
                continue
            fit_bt = sm.QuantReg(expanding["forward_growth"], sm.add_constant(expanding[["nfci", "current_growth"]], has_constant="add")).fit(q=quantile, max_iter=5000)
            origin_x = sm.add_constant(frame.loc[[origin], ["nfci", "current_growth"]], has_constant="add").reindex(columns=fit_bt.model.exog_names, fill_value=1.0)
            rolling_predictions[quantile].append(float(fit_bt.predict(origin_x).iloc[0]))
            rolling_baselines[quantile].append(float(np.quantile(expanding["forward_growth"], quantile)))
        actual_bt = test["forward_growth"].to_numpy()[-len(rolling_predictions[quantile]):]
        predicted = np.asarray(rolling_predictions[quantile])
        baseline = np.asarray(rolling_baselines[quantile])
        oos_losses[quantile] = _pinball(actual_bt, predicted, quantile)
        baseline_losses[quantile] = _pinball(actual_bt, baseline, quantile)
    median_quantile = min(quantiles, key=lambda value: abs(value - 0.5))
    downside_quantile = min(quantiles)
    downside_actual = test["forward_growth"].to_numpy()[-len(rolling_predictions[downside_quantile]):]
    downside_predicted = np.asarray(rolling_predictions[downside_quantile])
    tail_exceedance = float(np.mean(downside_actual < downside_predicted))
    calibration_tolerance = max(0.05, 2 * np.sqrt(downside_quantile * (1 - downside_quantile) / max(len(downside_actual), 1)))
    diagnostics = [
        _diagnostic("GAR.CROSSING", "Quantile crossing", int(crossing), None, "FAIL" if crossing else "PASS", "Predicted conditional quantiles must be monotonically ordered.", "Crossing invalidates a coherent conditional distribution."),
        _diagnostic("GAR.OOS_DOWNSIDE", "Downside quantile pinball-loss ratio", oos_losses[downside_quantile] / baseline_losses[downside_quantile] if baseline_losses[downside_quantile] else None, None, "PASS" if oos_losses[downside_quantile] < baseline_losses[downside_quantile] else "WARNING", "Compares conditional downside forecasting with an unconditional training quantile.", "A weak downside backtest lowers tail-risk confidence."),
        _diagnostic("GAR.TAIL_CALIBRATION", "Out-of-sample lower-tail exceedance rate", tail_exceedance, None, "PASS" if abs(tail_exceedance - downside_quantile) <= calibration_tolerance else "WARNING", f"Across repeated expanding-origin forecasts, the realized share below q={downside_quantile:.2f} should be close to its nominal rate within sampling uncertainty.", "A single realization above the fifth percentile is expected; only repeated calibration failure weakens the model."),
        _diagnostic("GAR.COVERAGE", "Effective quarterly observations", len(frame), None, "PASS", "The active recipe requires at least 80 quarters.", "Long samples reduce but do not remove structural-break risk."),
        _diagnostic("GAR.DENSITY", "Density integrity", "quantile grid only", None, "WARNING", "The MVP reports conditional quantiles and does not fit a parametric density between them.", "Do not interpret the result as a fully calibrated recession probability."),
    ]
    coefficient_map: dict[str, list[dict[str, Any]]] = {}
    columns = []
    for quantile, fit in fits.items():
        column = f"q={quantile:.2f}"
        columns.append(column)
        coefficient_map[column] = [_coefficient(name, name, float(fit.params[name]), float(fit.bse[name]), float(fit.pvalues[name])) for name in fit.params.index]
    confidence = "MEDIUM" if not crossing and oos_losses[downside_quantile] <= baseline_losses[downside_quantile] and abs(tail_exceedance - downside_quantile) <= calibration_tolerance else "LOW"
    downside = predictions[downside_quantile]
    median = predictions[median_quantile]
    return {
        "status": "FAILED" if crossing else "SUCCESS",
        "node_id": node_id,
        "model_recipe_id": "M.GROWTH_AT_RISK.V1",
        "method": "Quantile Growth-at-Risk",
        "evidence_type": "TAIL_RISK_PREDICTIVE",
        "title": "Conditional US Growth-at-Risk",
        "summary": f"Conditional annualized real GDP growth is {downside:.2f}% at q={downside_quantile:.2f} versus a {median:.2f}% median over {horizon} quarter(s).",
        "direction": "DOWNSIDE_ELEVATED" if downside < 0 else "DOWNSIDE_CONTAINED",
        "signal": float(np.tanh(downside / 3.0)),
        "confidence": confidence,
        "specification": {"formula": f"Q_q(g_{{t+{horizon}}}|X_t) = alpha_q + beta_q NFCI_t + gamma_q g_t", "estimand": f"Conditional quantiles of annualized real GDP growth {horizon} quarter(s) ahead", "dependent_variable": "F.ACTIVITY.REAL_GDP", "independent_variables": ["F.MONETARY.NFCI"], "controls": ["current annualized GDP growth"]},
        "variables": _factor_metadata(registry, ["F.ACTIVITY.REAL_GDP", "F.MONETARY.NFCI"]),
        "sample": {"start": frame.index[0].date().isoformat(), "end": frame.index[-1].date().isoformat(), "forecast_origin": latest_predictors.index[-1].date().isoformat(), "observations": len(frame), "frequency": "quarterly", "window_policy": parameters["estimation_window"]},
        "table": {"table_id": f"T.{node_id}.GAR", "title": "Growth-at-Risk quantile regressions", "dependent_variable": "Forward annualized real GDP growth", "columns": columns, "coefficients": coefficient_map, "statistics": {"Observations": [len(frame)] * len(columns), "Forecast horizon (quarters)": [horizon] * len(columns), "Pseudo R-squared": [_finite(fits[q].prsquared) for q in quantiles], "Model version": ["M.GROWTH_AT_RISK.V1"] * len(columns)}, "notes": ["Koenker-Bassett quantile regressions.", "Quantile estimates are not recession probabilities."]},
        "diagnostics": diagnostics,
        "robustness": {"oos_design": "expanding-origin, no future outcomes in training", "oos_training_cutoff_rule": "base_date <= forecast_origin - horizon", "label_availability_lag_quarters": horizon, "oos_pinball_loss": {str(key): _finite(value) for key, value in oos_losses.items()}, "baseline_pinball_loss": {str(key): _finite(value) for key, value in baseline_losses.items()}, "tail_exceedance_rate": _finite(tail_exceedance), "tail_nominal_rate": downside_quantile, "calibration_tolerance": _finite(calibration_tolerance)},
        "charts": [{"chart_id": f"CH.{node_id}.FAN", "kind": "forecast_fan", "title": "Conditional real-GDP growth quantiles", "series": [{"series_id": f"q{quantile}", "label": f"q={quantile:.2f}", "points": [{"date": f"+{horizon}Q", "value": _finite(predictions[quantile])}]} for quantile in quantiles]}],
        "aggregation_input": {"target": "F.ACTIVITY.REAL_GDP", "horizon": horizon, "point_forecast": _finite(median), "downside_quantile": _finite(downside), "quantile": downside_quantile, "oos_loss": _finite(oos_losses[median_quantile]), "baseline_oos_loss": _finite(baseline_losses[median_quantile])},
    }


def _daily_transform(factor_id: str, series: pd.Series) -> pd.Series:
    """Build a business-day information set without inventing long gaps."""
    daily = series.sort_index().resample("B").last().ffill(limit=5)
    if factor_id.startswith("F.RATES") or factor_id in {
        "F.MONETARY.NFCI",
        "F.MONETARY.CURVE_10Y2Y",
        "F.FIN.CREDIT_SPREAD",
    }:
        return daily.diff()
    return np.log(daily.where(daily > 0)).diff() * 100


def _daily_market_linear(
    store: MacroStore,
    registry: RegistryStore,
    as_of: date,
    node_id: str,
    factor_ids: list[str],
    parameters: dict[str, Any],
    *,
    bridge: bool,
) -> dict[str, Any]:
    if not factor_ids:
        raise RuntimeError("A registered daily market target is required")
    target_id = factor_ids[0]
    transformed = {
        factor_id: _daily_transform(factor_id, raw)
        for factor_id in factor_ids
        if not (raw := _series(store, registry, factor_id, as_of)).empty
    }
    if target_id not in transformed:
        raise RuntimeError("The registered market target has no eligible point-in-time data")
    if bridge and len(transformed) < 2:
        raise RuntimeError("Daily market bridge requires at least one available driver")
    frame = pd.concat(transformed, axis=1).dropna()
    horizon = int(parameters["forecast_horizon_days"])
    lags = int(parameters["lags"])
    window = int(parameters["estimation_window_years"]) * 252
    minimum = 252 if bridge else 180
    if len(frame) < minimum + horizon + lags + 30:
        raise RuntimeError("Registered daily market forecast has insufficient history")

    outcome = frame[target_id].shift(-horizon).rename("target_forward")
    regressors = pd.DataFrame(index=frame.index)
    regressors[f"{target_id}.lag0"] = frame[target_id]
    for lag in range(1, lags + 1):
        regressors[f"{target_id}.lag{lag}"] = frame[target_id].shift(lag)
    if bridge:
        for factor_id in factor_ids[1:]:
            if factor_id in frame:
                regressors[factor_id] = frame[factor_id]
    full = pd.concat([outcome, regressors], axis=1).dropna()
    regression = full.tail(window)
    if len(regression) < minimum:
        raise RuntimeError("Registered daily market regression is too short")
    x = sm.add_constant(regression.drop(columns="target_forward"), has_constant="add")
    hac_lags = max(1, min(21, horizon))
    fit = sm.OLS(regression["target_forward"], x).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    latest_x = sm.add_constant(regressors.dropna().tail(1), has_constant="add").reindex(columns=x.columns, fill_value=1.0)
    point_forecast = float(fit.predict(latest_x).iloc[0])

    holdout = min(60, max(30, len(full) // 8))
    predictions: list[float] = []
    actuals: list[float] = []
    baselines: list[float] = []
    origins: list[pd.Timestamp] = []
    start = len(full) - holdout
    for position in range(start, len(full)):
        train_end = position - horizon
        if train_end < minimum:
            continue
        train = full.iloc[max(0, train_end - window):train_end]
        if len(train) < minimum:
            continue
        train_x = sm.add_constant(train.drop(columns="target_forward"), has_constant="add")
        train_fit = sm.OLS(train["target_forward"], train_x).fit()
        origin_row = full.iloc[[position]]
        origin_x = sm.add_constant(origin_row.drop(columns="target_forward"), has_constant="add").reindex(columns=train_x.columns, fill_value=1.0)
        predictions.append(float(train_fit.predict(origin_x).iloc[0]))
        actuals.append(float(origin_row["target_forward"].iloc[0]))
        baselines.append(float(train["target_forward"].mean()))
        origins.append(full.index[position])
    if len(predictions) < 20:
        raise RuntimeError("Daily rolling-origin backtest has insufficient valid origins")
    predicted = np.asarray(predictions)
    actual = np.asarray(actuals)
    baseline = np.asarray(baselines)
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    baseline_rmse = float(np.sqrt(np.mean((actual - baseline) ** 2)))
    residuals = pd.Series(fit.resid)
    lb = acorr_ljungbox(residuals, lags=[min(21, max(5, len(residuals) // 20))], return_df=True).iloc[-1]
    bp_stat, bp_p, _, _ = het_breuschpagan(residuals, fit.model.exog)
    warning_count = int(float(lb["lb_pvalue"]) < 0.05) + int(float(bp_p) < 0.05) + int(rmse > baseline_rmse)
    recipe_id = "M.DAILY_MARKET_BRIDGE.V1" if bridge else "M.DAILY_MARKET_AR.V1"
    method = "Daily market bridge forecast with HAC inference" if bridge else "Daily market autoregressive benchmark"
    coefficients = [
        _coefficient(name, name, float(fit.params[name]), float(fit.bse[name]), float(fit.pvalues[name]))
        for name in fit.params.index
    ]
    diagnostics = [
        _diagnostic(f"{recipe_id}.OOS", "Rolling-origin RMSE ratio", rmse / baseline_rmse if baseline_rmse else None, None, "PASS" if rmse < baseline_rmse else "WARNING", "Uses strictly earlier business-day observations at every forecast origin.", "Failure to beat the historical-mean benchmark caps confidence."),
        _diagnostic(f"{recipe_id}.LB", "Ljung-Box residual autocorrelation", float(lb["lb_stat"]), float(lb["lb_pvalue"]), "PASS" if float(lb["lb_pvalue"]) >= 0.05 else "WARNING", "Tests remaining serial dependence in daily residuals.", "Residual dependence may make intervals too narrow."),
        _diagnostic(f"{recipe_id}.BP", "Breusch-Pagan heteroskedasticity", float(bp_stat), float(bp_p), "PASS" if float(bp_p) >= 0.05 else "WARNING", "HAC covariance remains active regardless of this diagnostic.", "Volatility clustering weakens conventional Gaussian inference."),
    ]
    return {
        "status": "SUCCESS",
        "node_id": node_id,
        "model_recipe_id": recipe_id,
        "method": method,
        "evidence_type": "PREDICTIVE_ASSOCIATION" if bridge else "PREDICTIVE_BENCHMARK",
        "title": f"{method}: {target_id}",
        "summary": f"The registered {horizon}-business-day log-return forecast for {target_id} is {point_forecast:.3f}%; rolling-origin RMSE is {rmse:.3f} versus {baseline_rmse:.3f} for the benchmark.",
        "direction": "UP" if point_forecast > 0 else "DOWN",
        "signal": float(np.tanh(point_forecast / max(frame[target_id].std(), 1e-6))),
        "confidence": _confidence_from_oos(rmse, baseline_rmse, warning_count),
        "specification": {"formula": f"r_{{t+{horizon}}} = alpha + phi(L)r_t" + (" + beta'X_t + epsilon_t" if bridge else " + epsilon_t"), "estimand": f"Conditional {horizon}-business-day log return of {target_id}", "dependent_variable": target_id, "independent_variables": list(regressors.columns), "controls": [], "causal_interpretation_allowed": False},
        "variables": _factor_metadata(registry, list(transformed)),
        "sample": {"start": regression.index[0].date().isoformat(), "end": regression.index[-1].date().isoformat(), "observations": len(regression), "frequency": "business-day", "window_years": parameters["estimation_window_years"]},
        "table": {"table_id": f"T.{node_id}.{recipe_id}", "title": method, "dependent_variable": target_id, "columns": ["(1)"], "coefficients": {"(1)": coefficients}, "statistics": {"Observations": [len(regression)], "R-squared": [_finite(fit.rsquared)], "Adjusted R-squared": [_finite(fit.rsquared_adj)], "HAC max lag": [hac_lags], "Forecast horizon (business days)": [horizon], "Model version": [recipe_id]}, "notes": ["HAC standard errors.", "Predictive specification; no causal interpretation."]},
        "diagnostics": diagnostics,
        "robustness": {"oos_design": "rolling origin with horizon embargo", "oos_origins": len(predictions), "rmse": _finite(rmse), "baseline_rmse": _finite(baseline_rmse), "rmse_ratio": _finite(rmse / baseline_rmse if baseline_rmse else None)},
        "charts": [{"chart_id": f"CH.{node_id}.DAILY_OOS", "kind": "actual_vs_forecast", "title": "日频滚动样本外预测", "series": [{"series_id": "forecast", "label": "预测", "points": [{"date": stamp.date().isoformat(), "value": _finite(value)} for stamp, value in zip(origins, predictions, strict=True)]}, {"series_id": "actual", "label": "实际", "points": [{"date": stamp.date().isoformat(), "value": _finite(value)} for stamp, value in zip(origins, actuals, strict=True)]}]}],
        "aggregation_input": {"target": target_id, "horizon": horizon, "point_forecast": _finite(point_forecast), "oos_loss": _finite(rmse**2), "baseline_oos_loss": _finite(baseline_rmse**2)},
    }


def run_daily_market_ar(store: MacroStore, registry: RegistryStore, as_of: date, node_id: str, factor_ids: list[str], parameters: dict[str, Any]) -> dict[str, Any]:
    return _daily_market_linear(store, registry, as_of, node_id, factor_ids, parameters, bridge=False)


def run_daily_market_bridge(store: MacroStore, registry: RegistryStore, as_of: date, node_id: str, factor_ids: list[str], parameters: dict[str, Any]) -> dict[str, Any]:
    return _daily_market_linear(store, registry, as_of, node_id, factor_ids, parameters, bridge=True)


def run_daily_market_var(
    store: MacroStore,
    registry: RegistryStore,
    as_of: date,
    node_id: str,
    factor_ids: list[str],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    unique_ids = list(dict.fromkeys(factor_ids))[:5]
    columns = {
        factor_id: _daily_transform(factor_id, raw)
        for factor_id in unique_ids
        if not (raw := _series(store, registry, factor_id, as_of)).empty
    }
    if len(columns) < 2:
        raise RuntimeError("Daily market VAR requires at least two available series")
    window = int(parameters["estimation_window_years"]) * 252
    frame = pd.concat(columns, axis=1).dropna().tail(window)
    lags = int(parameters["lags"])
    horizon = int(parameters["forecast_horizon_days"])
    if len(frame) < max(400, lags * len(frame.columns) * 12):
        raise RuntimeError("Daily market VAR effective sample is too short")
    model = VAR(frame).fit(lags, trend="c")
    stable = bool(model.is_stable(verbose=False))
    forecast_array, lower, upper = model.forecast_interval(frame.to_numpy()[-lags:], steps=horizon, alpha=0.05)
    forecast_index = pd.bdate_range(frame.index[-1] + pd.offsets.BDay(1), periods=horizon)
    forecast = pd.DataFrame(forecast_array, index=forecast_index, columns=frame.columns)
    target_id = frame.columns[0]
    holdout = min(40, max(25, len(frame) // 20))
    train = frame.iloc[:-holdout]
    test = frame.iloc[-holdout:]
    history = train.copy()
    oos: list[float] = []
    for stamp in test.index:
        fitted = VAR(history).fit(lags, trend="c")
        oos.append(float(fitted.forecast(history.to_numpy()[-lags:], steps=1)[0][0]))
        history = pd.concat([history, test.loc[[stamp]]])
    actual = test[target_id].to_numpy()
    rmse = float(np.sqrt(np.mean((actual - np.asarray(oos)) ** 2)))
    baseline_rmse = float(np.sqrt(np.mean((actual - train[target_id].tail(60).mean()) ** 2)))
    portmanteau = model.test_whiteness(nlags=max(lags + 1, min(21, lags + 10)), adjusted=True)
    warning_count = int(not stable) + int(portmanteau.pvalue < 0.05) + int(rmse > baseline_rmse)
    equation = target_id
    coefficients = [
        _coefficient(name, name, float(model.params.loc[name, equation]), float(model.stderr.loc[name, equation]), float(model.pvalues.loc[name, equation]))
        for name in model.params.index
    ]
    irf = model.irf(min(21, horizon)).irfs
    shock_column = min(1, len(frame.columns) - 1)
    diagnostics = [
        _diagnostic("DAILY_VAR.STABILITY", "Companion-matrix stability", max(abs(model.roots)) if len(model.roots) else None, None, "PASS" if stable else "FAIL", "Checks stability of the registered daily VAR.", "Unstable systems cannot support directional synthesis."),
        _diagnostic("DAILY_VAR.WHITENESS", "Residual Portmanteau whiteness", float(portmanteau.test_statistic), float(portmanteau.pvalue), "PASS" if portmanteau.pvalue >= 0.05 else "WARNING", "Tests joint residual serial correlation.", "Residual dependence suggests omitted daily dynamics."),
        _diagnostic("DAILY_VAR.OOS", "Rolling one-day RMSE ratio", rmse / baseline_rmse if baseline_rmse else None, None, "PASS" if rmse < baseline_rmse else "WARNING", "Refits the system using only prior business-day observations.", "Failure to beat the baseline lowers confidence."),
    ]
    return {
        "status": "SUCCESS" if stable else "FAILED",
        "node_id": node_id,
        "model_recipe_id": "M.DAILY_MARKET_VAR.V1",
        "method": "Registered daily market VAR",
        "evidence_type": "PREDICTIVE_STRUCTURAL_PROXY",
        "title": f"日频市场 VAR：{target_id}",
        "summary": f"The registered daily VAR projects a {forecast[target_id].iloc[-1]:.3f}% transformed move in {target_id} at {horizon} business day(s).",
        "direction": "UP" if forecast[target_id].iloc[-1] > 0 else "DOWN",
        "signal": float(np.tanh(forecast[target_id].mean() / max(frame[target_id].std(), 1e-6))),
        "confidence": _confidence_from_oos(rmse, baseline_rmse, warning_count),
        "specification": {"formula": f"R_t = c + A_1R_{{t-1}} + ... + A_{lags}R_{{t-{lags}}} + u_t", "estimand": f"Joint daily return system and {horizon}-business-day forecast", "dependent_variable": target_id, "independent_variables": list(frame.columns), "controls": [f"{lags} registered daily lag(s)"], "causal_interpretation_allowed": False},
        "variables": _factor_metadata(registry, list(frame.columns)),
        "sample": {"start": frame.index[0].date().isoformat(), "end": frame.index[-1].date().isoformat(), "observations": int(model.nobs), "frequency": "business-day", "window_years": parameters["estimation_window_years"]},
        "table": {"table_id": f"T.{node_id}.DAILY_VAR", "title": f"Daily VAR equation: {target_id}", "dependent_variable": target_id, "columns": [equation], "coefficients": {equation: coefficients}, "statistics": {"Observations": [int(model.nobs)], "System variables": [len(frame.columns)], "Lags": [lags], "AIC": [_finite(model.aic)], "BIC": [_finite(model.bic)], "Stable": ["Yes" if stable else "No"], "Model version": ["M.DAILY_MARKET_VAR.V1"]}, "notes": ["Ordering-based impulse responses are structural proxies, not identified shocks."]},
        "diagnostics": diagnostics,
        "robustness": {"model_oos_rmse": _finite(rmse), "baseline_oos_rmse": _finite(baseline_rmse), "rmse_ratio": _finite(rmse / baseline_rmse if baseline_rmse else None), "identification": parameters["identification"]},
        "charts": [{"chart_id": f"CH.{node_id}.DAILY_VAR_FORECAST", "kind": "forecast_fan", "title": f"{target_id} 日频预测扇形图", "series": [{"series_id": "lower95", "label": "95% 下界", "points": [{"date": stamp.date().isoformat(), "value": _finite(lower[index, 0])} for index, stamp in enumerate(forecast_index)]}, {"series_id": "forecast", "label": "点预测", "points": [{"date": stamp.date().isoformat(), "value": _finite(value)} for stamp, value in forecast[target_id].items()]}, {"series_id": "upper95", "label": "95% 上界", "points": [{"date": stamp.date().isoformat(), "value": _finite(upper[index, 0])} for index, stamp in enumerate(forecast_index)]}]}, {"chart_id": f"CH.{node_id}.DAILY_VAR_IRF", "kind": "irf", "title": f"{target_id} 对 {frame.columns[shock_column]} 的响应", "series": [{"series_id": "irf", "label": "脉冲响应", "points": [{"date": str(step), "value": _finite(irf[step, 0, shock_column])} for step in range(irf.shape[0])]}]}],
        "aggregation_input": {"target": target_id, "horizon": horizon, "point_forecast": _finite(forecast[target_id].iloc[-1]), "oos_loss": _finite(rmse**2), "baseline_oos_loss": _finite(baseline_rmse**2)},
    }


def run_panel_fixture(
    store: MacroStore,
    registry: RegistryStore,
    as_of: date,
    node_id: str,
    factor_ids: list[str],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    raw = run_state_panel(
        store,
        as_of,
        PanelConfig(
            start_year=int(parameters["start_year"]),
            fixed_effects=parameters["fixed_effects"],
            covariance=parameters["covariance"],
        ),
    )
    metrics = raw["metrics"]
    coefficient = float(metrics["coefficient_house_price_yoy"])
    standard_error = float(metrics["standard_error"])
    p_value = float(metrics["p_value"])
    diagnostics = [
        _diagnostic("PANEL.CLUSTERS", "Entity cluster count", metrics["entities"], None, "WARNING" if metrics["entities"] < 30 else "PASS", "Cluster-robust asymptotics are weak with only ten state clusters.", "Inference is displayed but confidence is capped at LOW."),
        _diagnostic("PANEL.WITHIN_R2", "Reported R-squared", metrics["r_squared"], None, "WARNING", "The legacy fixture currently reports full-model R-squared; a dedicated within R-squared is required before research activation.", "Do not compare this value with a conventional pooled OLS R-squared."),
        _diagnostic("PANEL.SERIAL", "Within-panel serial correlation", "not yet implemented for fixture", None, "WARNING", "The fixture is retained to test parameter locking and academic rendering.", "This blocks use as primary evidence."),
        _diagnostic("PANEL.CAUSAL", "Causal identification", "none", None, "NOT_APPLICABLE", "Two-way fixed effects do not by themselves identify a causal effect.", "The estimate is labeled associational and excluded from general synthesis."),
    ]
    return {
        "status": "SUCCESS",
        "node_id": node_id,
        "model_recipe_id": "M.PANEL_FE_FIXTURE.V1",
        "method": "Panel fixed effects fixture",
        "evidence_type": "ASSOCIATIONAL_FIXTURE",
        "title": "Ten-state housing and unemployment panel fixture",
        "summary": raw["summary"],
        "direction": "NEGATIVE_ASSOCIATION" if coefficient < 0 else "POSITIVE_ASSOCIATION",
        "signal": 0.0,
        "confidence": "LOW",
        "specification": {"formula": "unemployment_{i,t} = alpha_i + gamma_t + beta HPIYoY_{i,t} + epsilon_{i,t}", "estimand": "Conditional within-state association between HPI growth and unemployment", "dependent_variable": "F.STATE.UNEMPLOYMENT", "independent_variables": ["F.STATE.HPI"], "controls": [], "fixed_effects": parameters["fixed_effects"]},
        "variables": _factor_metadata(registry, factor_ids),
        "sample": {"start": f"{parameters['start_year']}-01-01", "end": as_of.isoformat(), "observations": metrics["observations"], "entities": metrics["entities"], "periods": metrics["quarters"], "frequency": "state-quarter"},
        "table": {"table_id": f"T.{node_id}.PANEL", "title": "Panel fixed-effects fixture", "dependent_variable": "State unemployment rate", "columns": ["(1)"], "coefficients": {"(1)": [_coefficient("House-price index YoY", "F.STATE.HPI", coefficient, standard_error, p_value)]}, "statistics": {"Observations": [metrics["observations"]], "Entities": [metrics["entities"]], "Periods": [metrics["quarters"]], "R-squared": [metrics["r_squared"]], "Entity fixed effects": ["Yes" if parameters["fixed_effects"] in {"ENTITY", "TWO_WAY"} else "No"], "Time fixed effects": ["Yes" if parameters["fixed_effects"] in {"TIME", "TWO_WAY"} else "No"], "Covariance": [parameters["covariance"]], "Model version": ["M.PANEL_FE_FIXTURE.V1"]}, "notes": ["This is a real-data execution fixture, not an approved causal research route.", "Ten clusters are insufficient for high-confidence clustered inference."]},
        "diagnostics": diagnostics,
        "robustness": {"fixture_only": True, "causal_claim_allowed": False, "activation_blocker": "research provenance and panel diagnostics incomplete"},
        "charts": raw["charts"],
        "latest_entities": raw.get("latest_entities", []),
        "aggregation_input": None,
    }


MODEL_RUNNERS = {
    "M.UNIVARIATE_AR.V1": run_univariate_ar,
    "M.BRIDGE_OLS.V1": run_bridge_ols,
    "M.DFM_NOWCAST.V1": run_dynamic_factor,
    "M.VAR_SYSTEM.V1": run_var,
    "M.LOCAL_PROJECTION.V1": run_local_projection,
    "M.GROWTH_AT_RISK.V1": run_growth_at_risk,
    "M.DAILY_MARKET_AR.V1": run_daily_market_ar,
    "M.DAILY_MARKET_BRIDGE.V1": run_daily_market_bridge,
    "M.DAILY_MARKET_VAR.V1": run_daily_market_var,
    "M.PANEL_FE_FIXTURE.V1": run_panel_fixture,
}
