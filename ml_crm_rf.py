# -*- coding: utf-8 -*-
"""
랜덤 포레스트 기반 CRM 고객 등급화 및 마케팅 점수 산출.
- 데이터 사용 설정에서 선택된 테이블을 CSTNO 기준 INNER JOIN
- BASE_YM 있으면 최신 연월만 사용
- 수익성·건전성·취급율 타겟: 테이블 데이터·컬럼명/한글명 분석으로 각 차원당 상위 3개 후보 선정 후, 유효한 1개씩 타겟으로 사용
- 수익성(Regressor)·건전성(Classifier)·취급율(Regressor) 학습 → 1~10등급·우선순위 점수(0~100)·ML_CRM_RESULTS 저장
"""

from pathlib import Path
import json
import sqlite3
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# db_storage와 동일 경로
DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "crm.db"
EXTRACTION_CONFIG_PATH = Path(__file__).resolve().parent / "data" / "extraction_config.json"
COLUMN_COMMENT_TABLE = "_column_comment"
ML_RESULTS_TABLE = "ML_CRM_RESULTS"
ML_SEGMENTS_TABLE = "ML_CRM_SEGMENTS"  # RUN_KEY + 범주코드 키, 범주 요약·해석 저장
# 고객 범주 코드 (범주명 → 코드)
SEGMENT_CD_MAP = {"VIP": "01", "우수고객": "02", "잠재고객": "03", "일반고객": "04", "주의고객": "05", "위험고객": "06"}

# 학습에서 제외할 컬럼: 식별자만 고정 제외. 타겟은 자동 선정된 컬럼으로 동적 제외.
IDENTIFIER_COLS = {"ID", "CSTNO", "BASE_YM", "IDNO", "LOANNO", "RUN_KEY", "CREATED_DATE", "CREATED_TIME"}

# 수익성·건전성·취급율 후보 선정용 키워드 (컬럼명/한글명 매칭). 각 차원당 상위 3개 후보 선정.
KEYWORDS_PROFIT = (
    "수익", "이익", "영업이익", "매출", "이익금", "PRFT", "PROFIT", "REVENUE", "AMT", "매출액", "손익", "평잔", "이익"
)
KEYWORDS_SOUNDNESS = (
    "연체", "위험", "건전", "OVRD", "OVERDUE", "RISK", "DEFAULT", "DPD", "정상", "부실", "등급",
)
KEYWORDS_HANDLING = (
    "취급", "원금", "잔액", "금액", "규모", "PCPL", "HNDL", "PRINCIPAL", "BALANCE", "AMT", "잔고",
)


def _next_run_key(conn: sqlite3.Connection) -> str:
    """오늘 날짜(YYYYMMDD) + 4자리 일련번호 생성. 예: 202602080001"""
    today = datetime.now().strftime("%Y%m%d")
    try:
        cur = conn.execute(
            f"SELECT MAX(RUN_KEY) FROM {ML_RESULTS_TABLE} WHERE RUN_KEY LIKE ?",
            (today + "%",),
        )
        row = cur.fetchone()
        if row and row[0]:
            last = str(row[0])
            if len(last) >= 12 and last[:8] == today:
                seq = int(last[8:12]) + 1
            else:
                seq = 1
        else:
            seq = 1
    except Exception:
        seq = 1
    return today + str(seq).zfill(4)


def _load_extraction_config():
    """데이터 사용 설정 로드. use=True인 테이블만."""
    if not EXTRACTION_CONFIG_PATH.exists():
        return []
    try:
        with open(EXTRACTION_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        tables = data.get("tables") or []
        return [t for t in tables if t.get("use") and t.get("table_name")]
    except Exception:
        return []


def _load_table_from_db(table_name: str) -> pd.DataFrame | None:
    """SQLite에서 테이블 전체 로드."""
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(f'SELECT * FROM "{table_name}"', conn)
        conn.close()
        return df if not df.empty else None
    except Exception:
        return None


def _get_column_comment(conn: sqlite3.Connection, table_name: str, column_name: str) -> str | None:
    """_column_comment에서 컬럼 한글명 조회."""
    try:
        cur = conn.execute(
            f"SELECT name_ko FROM {COLUMN_COMMENT_TABLE} WHERE table_name = ? AND column_name = ?",
            (table_name, column_name),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None


def get_column_comments_map(conn: sqlite3.Connection, table_name: str) -> dict[str, str]:
    """테이블별 컬럼 한글명 전체 조회. { column_name: name_ko }"""
    try:
        cur = conn.execute(
            f"SELECT column_name, name_ko FROM {COLUMN_COMMENT_TABLE} WHERE table_name = ?",
            (table_name,),
        )
        return {row[0]: row[1] for row in cur.fetchall() if row[1]}
    except Exception:
        return {}


def _column_name_ko_map(merged_columns: list, column_comments_by_table: dict) -> dict[str, str]:
    """병합 테이블 컬럼명 → 한글명. column_comments_by_table으로부터 생성."""
    out = {}
    for col in merged_columns:
        if col in out:
            continue
        for tname, comments in (column_comments_by_table or {}).items():
            if col in comments:
                out[col] = comments[col] or ""
                break
            suffix = "." + tname
            if col.endswith(suffix) and col[: -len(suffix)] in comments:
                out[col] = comments[col[: -len(suffix)]] or ""
                break
    return out


def _score_column_for_dimension(col: str, name_ko: str, keywords: tuple, is_numeric: bool, valid_count: int) -> float:
    """한 컬럼이 해당 차원(수익성/건전성/취급율)에 얼마나 적합한지 점수. 높을수록 적합."""
    score = 0.0
    combined = ((name_ko or "") + " " + (col or "")).upper()
    for kw in keywords:
        if kw.upper() in combined:
            score += 2.0
    if is_numeric and valid_count >= 10:
        score += 1.0
    if valid_count >= 50:
        score += 0.5
    return score


def select_target_candidates(
    merged: pd.DataFrame,
    column_comments_by_table: dict,
    top_k: int = 3,
) -> tuple[dict[str, list[str]], dict[str, str | None]]:
    """
    병합 데이터와 컬럼 한글명을 분석해 수익성·건전성·취급율 각각 상위 top_k개 후보 선정.
    반환: (candidates, selected_targets)
    - candidates: {"profit": [col1,col2,col3], "soundness": [...], "handling": [...]}
    - selected_targets: {"profit": col | None, "soundness": col | None, "handling": col | None}
      각 차원별 후보 중 유효 데이터가 충분한 첫 번째 컬럼을 타겟으로 선택.
    """
    exclude = set(c.upper() for c in IDENTIFIER_COLS)
    col_ko = _column_name_ko_map(merged.columns.tolist(), column_comments_by_table)
    candidates = {"profit": [], "soundness": [], "handling": []}
    selected = {"profit": None, "soundness": None, "handling": None}

    dim_keywords = [
        ("profit", KEYWORDS_PROFIT),
        ("soundness", KEYWORDS_SOUNDNESS),
        ("handling", KEYWORDS_HANDLING),
    ]

    for col in merged.columns:
        if (col or "").upper() in exclude:
            continue
        s = merged[col]
        valid = s.notna()
        valid_count = int(valid.sum())
        if valid_count < 5:
            continue
        name_ko = col_ko.get(col) or ""
        is_numeric = pd.api.types.is_numeric_dtype(s) or (s.dtype == object and pd.to_numeric(s, errors="coerce").notna().sum() >= valid_count // 2)

        for dim, keywords in dim_keywords:
            sc = _score_column_for_dimension(col, name_ko, keywords, is_numeric, valid_count)
            if sc > 0:
                candidates[dim].append((col, sc))

    # 차원별 점수 순 정렬 후 상위 top_k개만 이름만
    for dim in candidates:
        candidates[dim] = [c[0] for c in sorted(candidates[dim], key=lambda x: -x[1])[:top_k]]

    # 각 차원별로 타겟 1개 선택: 후보 중 유효값이 충분한 첫 컬럼
    for dim in ["profit", "soundness", "handling"]:
        for col in candidates[dim]:
            s = merged[col]
            valid = s.notna()
            n = int(valid.sum())
            if dim == "soundness":
                # 건전성: 분류용으로 Y/N 또는 2개 이하 범주가 있으면 좋음. 최소 10건 이상만.
                if n < 10:
                    continue
                try:
                    uniq = s.dropna().astype(str).str.upper().nunique()
                    if uniq >= 2:  # 둘 이상 범주
                        selected[dim] = col
                        break
                except Exception:
                    if n >= 30:
                        selected[dim] = col
                        break
            else:
                if n >= 10:
                    selected[dim] = col
                    break

    return candidates, selected


def build_merged_df(config_list: list[dict]) -> tuple[pd.DataFrame | None, str]:
    """
    데이터 사용 설정의 테이블을 CSTNO 기준 INNER JOIN.
    BASE_YM 있으면 해당 테이블은 최신 연월만 필터.
    반환: (merged_df, error_message). 성공 시 error_message는 "".
    """
    if not config_list:
        return None, "데이터 사용 설정에서 사용할 테이블이 없습니다."
    if not DB_PATH.exists():
        return None, "DB 파일이 없습니다."

    dfs = []
    for cfg in config_list:
        tname = cfg.get("table_name")
        if not tname:
            continue
        df = _load_table_from_db(tname)
        if df is None or df.empty:
            continue
        if "CSTNO" not in df.columns:
            continue
        if "BASE_YM" in df.columns:
            try:
                latest = df["BASE_YM"].astype(str).max()
                df = df[df["BASE_YM"].astype(str) == latest].copy()
            except Exception:
                pass
        # 컬럼명 충돌 방지: 모든 테이블에 컬럼명_테이블명 통일 (CSTNO 제외)
        suffix = f".{tname}"
        rename = {c: c + suffix for c in df.columns if c != "CSTNO"}
        df = df.rename(columns=rename)
        dfs.append(df)

    if not dfs:
        return None, "로드된 테이블이 없거나 CSTNO가 없습니다."

    merged = dfs[0]
    for df in dfs[1:]:
        merged = merged.merge(df, on="CSTNO", how="inner")
    return merged, ""


def prepare_features_and_targets(
    df: pd.DataFrame,
    selected_targets: dict[str, str | None],
) -> tuple[pd.DataFrame, pd.Series | None, pd.Series | None, pd.Series | None, list[str]]:
    """
    학습 변수(X): 식별자 + 선정된 타겟 컬럼만 제외하고, 나머지 전부 포함.
    selected_targets: {"profit": col|None, "soundness": col|None, "handling": col|None}
    반환: (X, y_profit, y_soundness, y_handling, feature_names).
    """
    exclude = set(c for c in df.columns if (c or "").upper() in IDENTIFIER_COLS)
    for col in (selected_targets.get("profit"), selected_targets.get("soundness"), selected_targets.get("handling")):
        if col and col in df.columns:
            exclude.add(col)

    y_profit = df[selected_targets["profit"]].copy() if selected_targets.get("profit") and selected_targets["profit"] in df.columns else None
    y_handling = df[selected_targets["handling"]].copy() if selected_targets.get("handling") and selected_targets["handling"] in df.columns else None
    y_soundness_raw = df[selected_targets["soundness"]].copy() if selected_targets.get("soundness") and selected_targets["soundness"] in df.columns else None

    feature_cols = [c for c in df.columns if c not in exclude and df[c].notna().any()]
    X = df[feature_cols].copy()
    X = X.fillna(0)

    for col in X.select_dtypes(include=["object"]).columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))

    # 건전성: 분류용. Y/N/숫자 → 0/1 또는 2범주 이상이면 LabelEncoder
    y_soundness = None
    if y_soundness_raw is not None:
        raw_str = y_soundness_raw.astype(str).str.strip().str.upper()
        raw_str = raw_str.replace({"Y": "1", "N": "0", "YES": "1", "NO": "0"})
        s = pd.to_numeric(raw_str, errors="coerce")
        valid = s.notna()
        n_uniq = s[valid].nunique() if valid.any() else 0
        if n_uniq >= 2:
            u = sorted(s[valid].unique().tolist())
            if len(u) == 2:
                s = s.fillna(-1).replace({u[0]: 0, u[1]: 1}).replace(-1, np.nan)
            else:
                med = s.median()
                s = (s >= med).astype(float)
            y_soundness = s.fillna(0).astype(int)
        else:
            # 숫자로 안 되면 한글/코드 등 → LabelEncoder로 2범주 이상이면 0/1
            raw = y_soundness_raw.astype(str).str.strip()
            raw = raw.replace({"": np.nan})
            raw = raw.dropna()
            if raw.nunique() >= 2:
                le = LabelEncoder()
                encoded = pd.Series(index=y_soundness_raw.index, dtype=float)
                encoded.loc[raw.index] = le.fit_transform(raw.astype(str))
                encoded = encoded.fillna(0)
                if encoded.nunique() >= 2:
                    # 2개 범주만 남기기: 가장 많은 2개로 0/1
                    vc = encoded.value_counts()
                    top2 = vc.head(2).index.tolist()
                    encoded = encoded.where(encoded.isin(top2), np.nan).replace({top2[0]: 0, top2[1]: 1}).fillna(0)
                    y_soundness = encoded.astype(int)
                else:
                    y_soundness = None
            else:
                y_soundness = None

    return X, y_profit, y_soundness, y_handling, feature_cols


def grade_1_to_10(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """시리즈를 1~10 등급으로 변환. higher_is_better=True면 상위 10%가 10등급."""
    if series is None or len(series) == 0:
        return series
    ranks = series.rank(method="average", ascending=not higher_is_better)
    pct = ranks.astype(float) / len(ranks)
    grade = (np.clip(pct, 0.001, 0.999) * 10).astype(int) + 1
    return np.clip(grade, 1, 10)


def run_ml_pipeline() -> tuple[bool, str, dict]:
    """
    전체 파이프라인 실행.
    반환: (성공여부, 오류메시지, 결과딕셔너리).
    결과딕셔너리: merged_rows, importance_profit, importance_soundness, importance_handling,
                 result_df, column_comments_by_table
    """
    result = {
        "merged_rows": 0,
        "importance_profit": [],
        "importance_soundness": [],
        "importance_handling": [],
        "result_df": None,
        "column_comments_by_table": {},
        "target_candidates": {"profit": [], "soundness": [], "handling": []},
        "selected_targets": {"profit": None, "soundness": None, "handling": None},
    }

    config_list = _load_extraction_config()
    merged, err = build_merged_df(config_list)
    if merged is None:
        return False, err or "병합 실패", result
    result["merged_rows"] = len(merged)

    conn = sqlite3.connect(DB_PATH)
    try:
        for cfg in config_list:
            tname = cfg.get("table_name")
            if tname:
                result["column_comments_by_table"][tname] = get_column_comments_map(conn, tname)
    finally:
        conn.close()

    # 수익성·건전성·취급율 타겟 후보 각 3개 선정 → 유효한 1개씩 타겟으로 선택
    candidates, selected = select_target_candidates(merged, result["column_comments_by_table"], top_k=3)
    result["target_candidates"] = candidates
    result["selected_targets"] = selected

    X, y_profit, y_soundness, y_handling, feature_names = prepare_features_and_targets(merged, selected)

    # 수익성 모델 (Regressor)
    model_profit = None
    pred_profit = None
    if y_profit is not None and y_profit.notna().sum() >= 10:
        mask = y_profit.notna()
        X_p = X[mask]
        y_p = pd.to_numeric(y_profit[mask], errors="coerce").fillna(0)
        if len(X_p) >= 10:
            model_profit = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
            model_profit.fit(X_p, y_p)
            pred_profit = pd.Series(model_profit.predict(X), index=X.index)
            imp = pd.Series(model_profit.feature_importances_, index=feature_names).sort_values(ascending=False)
            result["importance_profit"] = imp.head(9).index.tolist()

    # 건전성 모델 (Classifier) — 선정된 타겟 컬럼이 있고 Y/N(또는 2범주) 이상일 때
    model_soundness = None
    pred_soundness_prob = None
    if y_soundness is not None and y_soundness.sum() >= 1 and (len(y_soundness) - y_soundness.sum()) >= 1:
        model_soundness = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
        model_soundness.fit(X, y_soundness)
        pred_soundness_prob = pd.Series(
            model_soundness.predict_proba(X)[:, 1], index=X.index
        )
        imp = pd.Series(model_soundness.feature_importances_, index=feature_names).sort_values(ascending=False)
        result["importance_soundness"] = imp.head(9).index.tolist()

    # 취급율 모델 (Regressor)
    model_handling = None
    pred_handling = None
    if y_handling is not None and y_handling.notna().sum() >= 10:
        mask = y_handling.notna()
        X_h = X[mask]
        y_h = pd.to_numeric(y_handling[mask], errors="coerce").fillna(0)
        if len(X_h) >= 10:
            model_handling = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
            model_handling.fit(X_h, y_h)
            pred_handling = pd.Series(model_handling.predict(X), index=X.index)
            imp = pd.Series(model_handling.feature_importances_, index=feature_names).sort_values(ascending=False)
            result["importance_handling"] = imp.head(9).index.tolist()

    # 등급 1~10. 건전성 타겟 없으면 중립 5
    grade_profit = grade_1_to_10(pred_profit if pred_profit is not None else pd.Series(0.0, index=X.index), higher_is_better=True)
    grade_soundness = (
        grade_1_to_10(pred_soundness_prob if pred_soundness_prob is not None else pd.Series(0.0, index=X.index), higher_is_better=False)
        if pred_soundness_prob is not None
        else pd.Series(5, index=X.index)
    )
    grade_handling = grade_1_to_10(pred_handling if pred_handling is not None else pd.Series(0.0, index=X.index), higher_is_better=True)

    # 마케팅 우선순위 점수 0~100 (선정된 타겟 수에 따라 가중치)
    w_p, w_s, w_h = 0.0, 0.0, 0.0
    if selected.get("profit"): w_p = 0.4
    if selected.get("soundness"): w_s = 0.3
    if selected.get("handling"): w_h = 0.3
    total_w = w_p + w_s + w_h
    if total_w <= 0:
        total_w = 1.0
    priority_score = (grade_profit * w_p + grade_soundness * w_s + grade_handling * w_h) / total_w * 10
    priority_score = np.clip(priority_score.round(1), 0, 100)

    # 마케팅 그룹 (상/중/하)
    marketing_group = pd.cut(
        priority_score,
        bins=[-0.1, 33, 66, 100],
        labels=["하", "중", "상"],
    ).astype(str)

    # 고객 범주(5~7개): 점수·등급 조합 — VIP, 우수, 잠재, 일반, 주의, 위험
    def _assign_segment(row):
        sc = row.get("priority_score", 0) or 0
        sg = row.get("soundness_grade", 5) or 5
        if sg <= 3 or sc < 20:
            return "위험고객"
        if sc < 35:
            return "주의고객"
        if sc < 50:
            return "일반고객"
        if sc < 65:
            return "잠재고객"
        if sc < 80:
            return "우수고객"
        return "VIP"
    _df = pd.DataFrame({"priority_score": priority_score.values, "soundness_grade": grade_soundness.values})
    customer_segment = _df.apply(_assign_segment, axis=1)
    segment_cd = customer_segment.map(SEGMENT_CD_MAP)

    now = datetime.now()
    try:
        conn = sqlite3.connect(DB_PATH)
        run_key = _next_run_key(conn)
        conn.close()
    except Exception:
        run_key = now.strftime("%Y%m%d") + "0001"
    created_date = now.strftime("%Y-%m-%d")
    created_time = now.strftime("%H:%M:%S")
    out = pd.DataFrame({
        "RUN_KEY": [run_key] * len(merged),
        "CSTNO": merged["CSTNO"].values,
        "profit_grade": grade_profit.values,
        "soundness_grade": grade_soundness.values,
        "handling_grade": grade_handling.values,
        "priority_score": priority_score.values,
        "marketing_group": marketing_group.values,
        "SEGMENT_CD": segment_cd.values,
        "CREATED_DATE": [created_date] * len(merged),
        "CREATED_TIME": [created_time] * len(merged),
    })
    result["result_df"] = out
    # 범주별 요약 (AI 해석용) + segment_cd
    segment_order = ["VIP", "우수고객", "잠재고객", "일반고객", "주의고객", "위험고객"]
    result["segment_summary"] = []
    for seg in segment_order:
        seg_cd = SEGMENT_CD_MAP.get(seg, "")
        mask = out["SEGMENT_CD"] == seg_cd
        n = int(mask.sum())
        if n == 0:
            continue
        sub = out[mask]
        result["segment_summary"].append({
            "name": seg,
            "segment_cd": seg_cd,
            "count": n,
            "avg_profit_grade": round(sub["profit_grade"].mean(), 2),
            "avg_soundness_grade": round(sub["soundness_grade"].mean(), 2),
            "avg_handling_grade": round(sub["handling_grade"].mean(), 2),
            "avg_priority_score": round(sub["priority_score"].mean(), 2),
        })
    result["run_key"] = run_key

    # SQLite ML_CRM_RESULTS 저장 (append로 누적). 기존 테이블에 RUN_KEY 등 컬럼 없으면 ADD COLUMN
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(f"PRAGMA table_info({ML_RESULTS_TABLE})")
            existing_cols = {row[1] for row in cur.fetchall()}
        except Exception:
            existing_cols = set()
        if existing_cols:
            for col, col_type in [
                ("RUN_KEY", "TEXT"), ("CREATED_DATE", "TEXT"), ("CREATED_TIME", "TEXT"),
                ("SEGMENT_CD", "TEXT"),
            ]:
                if col not in existing_cols:
                    conn.execute(f"ALTER TABLE {ML_RESULTS_TABLE} ADD COLUMN [{col}] {col_type}")
                    conn.commit()
        # 컬럼 한글명 등록 (_column_comment)
        try:
            conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {COLUMN_COMMENT_TABLE} (
                    table_name TEXT, column_name TEXT, name_ko TEXT,
                    PRIMARY KEY (table_name, column_name)
                )"""
            )
            for col, name_ko in [
                ("RUN_KEY", "실행키"),
                ("CSTNO", "고객번호"),
                ("profit_grade", "수익성 등급"),
                ("soundness_grade", "건전성 등급"),
                ("handling_grade", "취급율 등급"),
                ("priority_score", "우선순위 점수"),
                ("marketing_group", "마케팅 그룹"),
                ("SEGMENT_CD", "범주코드"),
                ("CREATED_DATE", "생성 일자"),
                ("CREATED_TIME", "생성 시간"),
            ]:
                conn.execute(
                    f"INSERT OR REPLACE INTO {COLUMN_COMMENT_TABLE} (table_name, column_name, name_ko) VALUES (?, ?, ?)",
                    (ML_RESULTS_TABLE, col, name_ko),
                )
            conn.commit()
        except Exception:
            pass
        out.to_sql(ML_RESULTS_TABLE, conn, if_exists="append", index=False)
        conn.execute("INSERT OR REPLACE INTO _crm_tables (name) VALUES (?)", (ML_RESULTS_TABLE,))
        conn.commit()

        # ML_CRM_SEGMENTS: RUN_KEY + 범주코드(SEGMENT_CD) 키로 범주 요약·해석 저장
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {ML_SEGMENTS_TABLE} (
                RUN_KEY TEXT NOT NULL,
                SEGMENT_CD TEXT NOT NULL,
                SEGMENT_NM TEXT,
                CNT INTEGER,
                AVG_PROFIT_GRADE REAL,
                AVG_SOUNDNESS_GRADE REAL,
                AVG_HANDLING_GRADE REAL,
                AVG_PRIORITY_SCORE REAL,
                SEGMENT_INTERPRETATION TEXT,
                CREATED_DATE TEXT,
                CREATED_TIME TEXT,
                PRIMARY KEY (RUN_KEY, SEGMENT_CD)
            )"""
        )
        for seg in result.get("segment_summary") or []:
            conn.execute(
                f"""INSERT OR REPLACE INTO {ML_SEGMENTS_TABLE}
                    (RUN_KEY, SEGMENT_CD, SEGMENT_NM, CNT, AVG_PROFIT_GRADE, AVG_SOUNDNESS_GRADE, AVG_HANDLING_GRADE, AVG_PRIORITY_SCORE, SEGMENT_INTERPRETATION, CREATED_DATE, CREATED_TIME)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_key,
                    seg.get("segment_cd", ""),
                    seg.get("name", ""),
                    seg.get("count", 0),
                    seg.get("avg_profit_grade"),
                    seg.get("avg_soundness_grade"),
                    seg.get("avg_handling_grade"),
                    seg.get("avg_priority_score"),
                    None,  # 해석은 앱에서 AI 호출 후 UPDATE
                    created_date,
                    created_time,
                ),
            )
        conn.execute("INSERT OR REPLACE INTO _crm_tables (name) VALUES (?)", (ML_SEGMENTS_TABLE,))
        for col, name_ko in [
            ("RUN_KEY", "실행키"), ("SEGMENT_CD", "범주코드"), ("SEGMENT_NM", "범주명"),
            ("CNT", "건수"), ("AVG_PROFIT_GRADE", "평균 수익등급"), ("AVG_SOUNDNESS_GRADE", "평균 건전등급"),
            ("AVG_HANDLING_GRADE", "평균 취급등급"), ("AVG_PRIORITY_SCORE", "평균 우선순위점수"),
            ("SEGMENT_INTERPRETATION", "범주 해석"), ("CREATED_DATE", "생성 일자"), ("CREATED_TIME", "생성 시간"),
        ]:
            try:
                conn.execute(
                    f"INSERT OR REPLACE INTO {COLUMN_COMMENT_TABLE} (table_name, column_name, name_ko) VALUES (?, ?, ?)",
                    (ML_SEGMENTS_TABLE, col, name_ko),
                )
            except Exception:
                pass
        conn.commit()
        conn.close()
    except Exception as e:
        return False, f"ML_CRM_RESULTS 저장 실패: {e}", result

    return True, "", result
