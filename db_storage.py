# -*- coding: utf-8 -*-
"""
업로드된 데이터 SQLite 저장·로드 (다중 테이블)
- 업로드 시 파일별로 테이블 단위 저장 (테이블명 = 파일명에서 추출)
- 앱에서 테이블 목록 조회·선택 후 해당 테이블 데이터 조회

[네이밍 규칙 — 메타화]
- 테이블명: snake_case, 영문, 의미 단위 (예: condition_extract_result, customer, loan)
- 컬럼명: snake_case, 영문, entity_attribute 또는 measure_name (예: customer_id, profitability_score)
- 인식성: 약어보다 풀네임 권장, 복수는 단수 테이블명 (예: customers → customer)
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

# 프로젝트 루트 기준 data/crm.db
DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "crm.db"
META_TABLE = "_crm_tables"  # 적재된 테이블명 목록 저장
TABLE_COMMENT_TABLE = "_table_comment"   # 테이블 한글명 (table_name, name_ko)
COLUMN_COMMENT_TABLE = "_column_comment"  # 컬럼 한글명 (table_name, column_name, name_ko)
COLUMN_MIN_MAX_TABLE = "_column_min_max"   # 컬럼 min/max (table_name, column_name, min_val, max_val)
ERD_JSON_PATH = DB_DIR / "erd_tables.json"  # ERD 시각화 연동용
ML_SEGMENTS_TABLE = "ML_CRM_SEGMENTS"  # RUN_KEY + SEGMENT_CD 키, 범주 요약·해석

# ---- 앱에서 사용하는 표준 테이블/컬럼명 (영문, snake_case) ----
TABLE_CONDITION_EXTRACT_RESULT = "condition_extract_result"
TABLE_EXTRACTION_CRITERIA = "extraction_criteria"  # 조회 조건 저장
TABLE_EXTRACTION_RESULT = "extraction_result"      # 조회 결과 저장 (AI 사유 포함)
COL_CUSTOMER_ID = "customer_id"
COL_CUSTOMER_NAME = "customer_name"
COL_PROFITABILITY_SCORE = "profitability_score"
COL_SOUNDNESS_SCORE = "soundness_score"
COL_RISK_SCORE = "risk_score"
COL_EXTRACTED_AT = "extracted_at"
COL_CRITERIA_PROFITABILITY_MIN = "criteria_profitability_min"
COL_CRITERIA_SOUNDNESS_MIN = "criteria_soundness_min"
COL_CRITERIA_RISK_MAX = "criteria_risk_max"

# ---- 감사 컬럼 (공통) ----
COL_CREATED_DATE = "created_date"
COL_CREATED_TIME = "created_time"
COL_CREATED_BY = "created_by"
COL_UPDATED_DATE = "updated_date"
COL_UPDATED_TIME = "updated_time"
COL_UPDATED_BY = "updated_by"
COL_AI_REASONING = "ai_reasoning"
COL_CRITERIA_ID = "criteria_id"


def _ensure_dir():
    DB_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_table_name(name: str) -> str:
    """테이블명을 DB 저장용으로 정리 (공백·특수문자 → _). 신규 테이블은 영문 snake_case 사용 권장."""
    if not name or not name.strip():
        return "uploaded_data"
    s = re.sub(r"[^\w\u3130-\u318f\uac00-\ud7af]", "_", name.strip())
    return s if s else "uploaded_data"


def _sanitize_column_name(name: str) -> str:
    """컬럼명을 DB 저장용으로 정리."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return "col"
    s = str(name).strip()
    if not s:
        return "col"
    s = re.sub(r"[^\w\u3130-\u318f\uac00-\ud7af]", "_", s)
    return s if s else "col"


def get_db_path():
    """DB 파일 경로 반환"""
    return str(DB_PATH)


def _ensure_meta(conn: sqlite3.Connection):
    """메타 테이블 생성 (저장된 테이블명 목록)"""
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {META_TABLE} (name TEXT PRIMARY KEY)"
    )
    conn.commit()


def _ensure_comment_tables(conn: sqlite3.Connection):
    """테이블/컬럼 한글명 저장용 메타 테이블 생성"""
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {TABLE_COMMENT_TABLE} (
            table_name TEXT PRIMARY KEY,
            name_ko TEXT
        )"""
    )
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {COLUMN_COMMENT_TABLE} (
            table_name TEXT,
            column_name TEXT,
            name_ko TEXT,
            data_type TEXT,
            data_length TEXT,
            scale_val TEXT,
            pk TEXT,
            null_yn TEXT,
            default_val TEXT,
            PRIMARY KEY (table_name, column_name)
        )"""
    )
    # 기존 DB: 새 컬럼이 없으면 추가
    cur = conn.execute(f"PRAGMA table_info({COLUMN_COMMENT_TABLE})")
    cols = [row[1] for row in cur.fetchall()]
    for new_col, typ in (
        ("data_type", "TEXT"),
        ("data_length", "TEXT"),
        ("scale_val", "TEXT"),
        ("pk", "TEXT"),
        ("null_yn", "TEXT"),
        ("default_val", "TEXT"),
    ):
        if new_col not in cols:
            try:
                conn.execute(f"ALTER TABLE {COLUMN_COMMENT_TABLE} ADD COLUMN {new_col} {typ}")
            except Exception:
                pass
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS {COLUMN_MIN_MAX_TABLE} (
            table_name TEXT,
            column_name TEXT,
            min_val TEXT,
            max_val TEXT,
            PRIMARY KEY (table_name, column_name)
        )"""
    )
    conn.commit()


def list_tables() -> list[str]:
    """DB에 실제로 존재하는 테이블명 목록 반환 (정렬). _crm_tables에만 있고 실제 테이블이 없으면 제외."""
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        cur = conn.execute(f"SELECT name FROM {META_TABLE} ORDER BY name")
        names = [row[0] for row in cur.fetchall()]
        # 마이그레이션: 예전 버전에서 uploaded_data 단일 테이블만 있던 경우
        cur2 = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='uploaded_data'"
        )
        if cur2.fetchone() and "uploaded_data" not in names:
            conn.execute(f"INSERT OR IGNORE INTO {META_TABLE} (name) VALUES ('uploaded_data')")
            conn.commit()
            names.append("uploaded_data")
        # 실제 sqlite_master에 있는 테이블만 반환 (유령 목록 제거)
        cur3 = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {row[0] for row in cur3.fetchall()}
        names = sorted(n for n in names if n in existing)
        conn.close()
        return names
    except Exception:
        return []


def save_table(df: pd.DataFrame, table_name: str) -> bool:
    """
    DataFrame을 지정한 테이블명으로 저장 (테이블 없으면 생성·있으면 교체).
    table_name은 파일명 등에서 추출 후 _sanitize_table_name 적용 권장.
    """
    if df is None or df.empty:
        return False
    table_name = _sanitize_table_name(table_name)
    try:
        _ensure_dir()
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.execute(
            f"INSERT OR REPLACE INTO {META_TABLE} (name) VALUES (?)",
            (table_name,),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def _fill_notnull_columns_for_insert(df: pd.DataFrame, conn: sqlite3.Connection, table_name: str) -> pd.DataFrame:
    """테이블의 NOT NULL 컬럼에 대해 DataFrame의 NaN을 기본값으로 채워 NOT NULL constraint 오류를 방지.
    INTEGER PRIMARY KEY 컬럼은 채우지 않음 — NULL이면 SQLite가 자동 생성하므로, 0으로 채우면 모든 행이 같은 키가 되어 INSERT OR IGNORE 시 0건만 들어감."""
    cur = conn.execute(f'PRAGMA table_info("{table_name}")')
    rows = cur.fetchall()
    # sqlite3: (cid, name, type, notnull, dflt_value, pk)
    out = df.copy()
    for r in rows:
        col_name, col_type, notnull = r[1], (r[2] or "TEXT").upper(), r[3]
        pk = r[5] if len(r) > 5 else 0
        if not notnull or col_name not in out.columns:
            continue
        # INTEGER PRIMARY KEY는 채우지 않음 — NULL로 두어 자동 생성되도록
        if pk and "INT" in col_type:
            continue
        if "INT" in col_type:
            fill_val = 0
        elif "REAL" in col_type or "FLOAT" in col_type or "NUM" in col_type:
            # 0 사용 (0.0이면 TEXT 컬럼에 "0.0" 3자로 들어가 CHECK(length≤1) 등에서 실패할 수 있음)
            fill_val = 0
        else:
            fill_val = ""
        out[col_name] = out[col_name].fillna(fill_val)
        # object 타입에서 pd.NA/None이 남을 수 있음
        if out[col_name].dtype == "object" and out[col_name].isna().any():
            out[col_name] = out[col_name].fillna("")
    return out


def insert_into_table(df: pd.DataFrame, table_name: str) -> tuple[bool, str | None, int]:
    """
    기존 테이블에만 데이터를 INSERT(추가). 테이블 생성·재생성·교체 없음.
    NOT NULL 컬럼의 빈 값(NaN)은 타입에 맞게 기본값(0, 0.0, '')으로 채운 뒤 삽입.
    UNIQUE/PRIMARY KEY 중복 행은 건너뛰고(INSERT OR IGNORE) 나머지만 적재.
    table_name은 파일명 등에서 추출 후 _sanitize_table_name 적용 권장.
    반환: (성공 여부, 실패 시 오류 메시지, 실제 삽입된 행 수)
    """
    if df is None or df.empty:
        return False, "데이터가 비어 있습니다.", 0
    table_name = _sanitize_table_name(table_name)
    if not DB_PATH.exists():
        return False, "DB가 없습니다. 먼저 **테이블 생성** 메뉴에서 테이블을 만든 뒤 업로드하세요.", 0
    existing = list_tables()
    if table_name not in existing:
        return False, f"테이블 **{table_name}** 이(가) 없습니다. 먼저 **테이블 생성** 메뉴에서 해당 테이블을 만든 뒤 업로드하세요.", 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(f'PRAGMA table_info("{table_name}")')
        target_cols = [r[1] for r in cur.fetchall()]
        df_reindexed = df.reindex(columns=[c for c in target_cols if c in df.columns]).reindex(columns=target_cols)
        df_filled = _fill_notnull_columns_for_insert(df_reindexed, conn, table_name)
        tmp_name = "_tmp_append"
        df_filled.to_sql(tmp_name, conn, if_exists="replace", index=False)
        conn.execute(f'INSERT OR IGNORE INTO "{table_name}" SELECT * FROM "{tmp_name}"')
        rows_inserted = conn.execute("SELECT changes()").fetchone()[0]
        conn.execute(f'DROP TABLE "{tmp_name}"')
        conn.commit()
        conn.close()
        return True, None, rows_inserted
    except Exception as e:
        return False, str(e) if str(e).strip() else "스키마가 맞지 않거나 저장 중 오류가 났습니다.", 0


def insert_one_row_and_get_error(df_one_row: pd.DataFrame, table_name: str) -> str | None:
    """
    한 행만 INSERT (OR IGNORE 없이) 시도하여 실패 시 SQLite 오류 메시지 반환.
    0건일 때 원인 파악용. 성공 시 None 반환.
    """
    if df_one_row is None or df_one_row.empty:
        return "데이터가 비어 있습니다."
    table_name = _sanitize_table_name(table_name)
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(f'PRAGMA table_info("{table_name}")')
        target_cols = [r[1] for r in cur.fetchall()]
        df_reindexed = df_one_row.reindex(columns=[c for c in target_cols if c in df_one_row.columns]).reindex(columns=target_cols)
        df_filled = _fill_notnull_columns_for_insert(df_reindexed, conn, table_name)
        tmp_name = "_tmp_append_one"
        df_filled.to_sql(tmp_name, conn, if_exists="replace", index=False)
        conn.execute(f'INSERT INTO "{table_name}" SELECT * FROM "{tmp_name}"')
        conn.execute(f'DROP TABLE "{tmp_name}"')
        conn.commit()
        conn.close()
        return None
    except Exception as e:
        return str(e).strip() or "알 수 없는 오류"


def create_table_from_schema(
    table_name: str,
    columns: list[dict],
    table_name_ko: str | None = None,
) -> tuple[bool, str, str | None]:
    """
    엑셀 양식 등에서 추출한 스키마로 빈 테이블 생성.
    columns: [ {"컬럼명": "id", "속성명": "식별자", "데이터타입": "INTEGER", "PK": True, ... }, ... ]
    table_name_ko: 테이블 한글명(엔티티명). 있으면 _table_comment에 저장.
    컬럼 한글명은 각 col의 "컬럼 한글명" 또는 "속성명"으로 _column_comment에 저장.
    반환: (성공여부, 실행한 CREATE SQL, 오류메시지 또는 None)
    """
    if not columns:
        return False, "", "컬럼 정의가 비어 있습니다."
    table_name = _sanitize_table_name(table_name)
    # PK 컬럼 개수·이름 수집 (복수 PK일 때 테이블 수준 PRIMARY KEY 사용)
    pk_names = []
    for col in columns:
        cname = _sanitize_column_name(col.get("name") or col.get("컬럼명", "col"))
        pk_val = col.get("PK") if "PK" in col else col.get("pk")
        pk = pk_val is True if isinstance(pk_val, bool) else _is_truthy(pk_val)
        if pk:
            pk_names.append(cname)
    multi_pk = len(pk_names) >= 2

    parts = []
    for col in columns:
        cname = _sanitize_column_name(col.get("name") or col.get("컬럼명", "col"))
        raw_type = (col.get("type") or col.get("데이터타입", "TEXT"))
        if raw_type is None or (isinstance(raw_type, float) and pd.isna(raw_type)):
            raw_type = "TEXT"
        ctype = _normalize_sqlite_type(str(raw_type).strip().upper())
        pk_val = col.get("PK") if "PK" in col else col.get("pk")
        pk = pk_val is True if isinstance(pk_val, bool) else _is_truthy(pk_val)
        null_yn = str((col.get("Null여부") if "Null여부" in col else col.get("notnull")) or "").strip().upper()
        notnull = null_yn in ("N", "NO", "아니오")
        default = col.get("DEFAULT") if "DEFAULT" in col else col.get("default")
        if default is not None and isinstance(default, float) and pd.isna(default):
            default = None
        if default is not None and str(default).strip() == "":
            default = None
        # 데이터길이: TEXT일 때 길이 제한 (CHECK)
        data_len = col.get("데이터길이") if "데이터길이" in col else col.get("data_length")
        length_val = None
        if data_len is not None and not (isinstance(data_len, float) and pd.isna(data_len)):
            try:
                length_val = int(float(str(data_len).strip()))
            except (ValueError, TypeError):
                pass
        # 소수점: REAL일 때 소수 자릿수 제한 (CHECK)
        scale_raw = col.get("소수점") if "소수점" in col else col.get("scale")
        scale_val = None
        if scale_raw is not None and not (isinstance(scale_raw, float) and pd.isna(scale_raw)):
            try:
                scale_val = int(float(str(scale_raw).strip()))
            except (ValueError, TypeError):
                pass
        seg = f'"{cname}" {ctype}'
        # PK: 단일일 때만 컬럼 수준 PRIMARY KEY (AUTOINCREMENT는 INTEGER 단일 PK만)
        if pk and not multi_pk:
            if ctype == "INTEGER":
                seg += " PRIMARY KEY AUTOINCREMENT"
            else:
                seg += " PRIMARY KEY"
        if notnull and "PRIMARY KEY" not in seg:
            seg += " NOT NULL"
        if default is not None and str(default).strip():
            dval = str(default).strip()
            if dval.upper() in ("CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME"):
                seg += f" DEFAULT {dval}"
            elif ctype == "INTEGER" or ctype == "REAL":
                try:
                    float(dval)
                    seg += f" DEFAULT {dval}"
                except ValueError:
                    seg += f" DEFAULT '{_sql_quote_string(dval)}'"
            else:
                seg += f" DEFAULT '{_sql_quote_string(dval)}'"
        if ctype == "TEXT" and length_val is not None and length_val > 0:
            seg += f' CHECK(length("{cname}") <= {length_val})'
        if ctype == "REAL" and scale_val is not None and scale_val >= 0:
            seg += f' CHECK("{cname}" = round("{cname}", {scale_val}))'
        parts.append(seg)
    if multi_pk:
        parts.append("PRIMARY KEY (" + ", ".join(f'"{n}"' for n in pk_names) + ")")
    sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  ' + ",\n  ".join(parts) + "\n)"
    try:
        _ensure_dir()
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        _ensure_comment_tables(conn)
        conn.execute(sql)
        conn.execute(f"INSERT OR REPLACE INTO {META_TABLE} (name) VALUES (?)", (table_name,))
        # 테이블 한글명 저장
        if table_name_ko is not None and str(table_name_ko).strip():
            conn.execute(
                f"INSERT OR REPLACE INTO {TABLE_COMMENT_TABLE} (table_name, name_ko) VALUES (?, ?)",
                (table_name, str(table_name_ko).strip()),
            )
        # 컬럼 한글명 + 데이터타입/데이터길이/소수점/PK/Null여부/DEFAULT 저장
        for col in columns:
            cname = _sanitize_column_name(col.get("name") or col.get("컬럼명", "col"))
            name_ko = col.get("컬럼 한글명") or col.get("속성명")
            if name_ko is not None and not (isinstance(name_ko, float) and pd.isna(name_ko)):
                name_ko = str(name_ko).strip() or None
            else:
                name_ko = None
            raw_type = col.get("type") or col.get("데이터타입")
            data_type = None if raw_type is None or (isinstance(raw_type, float) and pd.isna(raw_type)) else str(raw_type).strip() or None
            data_len = col.get("데이터길이") or col.get("data_length")
            data_length = None if data_len is None or (isinstance(data_len, float) and pd.isna(data_len)) else str(data_len).strip() or None
            scale_raw = col.get("소수점") or col.get("scale")
            scale_val = None if scale_raw is None or (isinstance(scale_raw, float) and pd.isna(scale_raw)) else str(scale_raw).strip() or None
            pk_val = col.get("PK") if "PK" in col else col.get("pk")
            pk = "Y" if (pk_val is True or _is_truthy(pk_val)) else "N"
            null_yn = col.get("Null여부") or col.get("notnull")
            null_yn = None if null_yn is None or (isinstance(null_yn, float) and pd.isna(null_yn)) else str(null_yn).strip() or None
            default_val = col.get("DEFAULT") or col.get("default")
            default_val = None if default_val is None or (isinstance(default_val, float) and pd.isna(default_val)) else str(default_val).strip() or None
            conn.execute(
                f"""INSERT OR REPLACE INTO {COLUMN_COMMENT_TABLE}
                    (table_name, column_name, name_ko, data_type, data_length, scale_val, pk, null_yn, default_val)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (table_name, cname, name_ko, data_type, data_length, scale_val, pk, null_yn, default_val),
            )
        conn.commit()
        conn.close()
        return True, sql, None
    except Exception as e:
        return False, sql, str(e)


def _normalize_sqlite_type(raw: str) -> str:
    """엑셀 데이터타입 문자열을 SQLite 타입으로 정규화."""
    u = raw.upper().strip()
    if not u or u in ("NAN", "NAT"):
        return "TEXT"
    if u in ("TEXT", "VARCHAR", "CHAR", "STRING", "NVARCHAR", "VARCHAR2", "CHARACTER", "문자"):
        return "TEXT"
    if u in ("INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "NUMBER", "NUMERIC", "정수"):
        return "INTEGER"
    if u in ("REAL", "FLOAT", "DOUBLE", "DECIMAL", "실수"):
        return "REAL"
    if u in ("BLOB", "BINARY"):
        return "BLOB"
    if u in ("DATE", "DATETIME", "TIMESTAMP", "날짜", "일시"):
        return "TEXT"
    return "TEXT"


def _sql_quote_string(s: str) -> str:
    """SQL 홑따옴표 리터럴용 이스케이프. ' → '' 로 하나만 치환하고, 이미 '' 인 부분은 다시 넣지 않아 홑따옴표 과다 방지."""
    if not s:
        return s
    # 이미 ''(이스케이프된 따옴표)를 플레이스홀더로 치환 후, ' → '' 처리, 마지막에 플레이스홀더를 '' 로 복원
    _ph = "\uE000"
    return s.replace("''", _ph).replace("'", "''").replace(_ph, "''")


def _is_truthy(v) -> bool:
    """PK/Null여부 등 엑셀 값이 Y/예/1/TRUE 등인지."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return False
    s = str(v).strip().upper()
    return s in ("Y", "YES", "예", "1", "TRUE", "T", "O", "○")


def get_table_comment(table_name: str) -> str | None:
    """테이블 한글명 반환. 없으면 None."""
    if not DB_PATH.exists():
        return None
    table_name = _sanitize_table_name(table_name)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            f"SELECT name_ko FROM {TABLE_COMMENT_TABLE} WHERE table_name = ?",
            (table_name,),
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row and row[0] else None
    except Exception:
        return None


def get_column_comments(table_name: str) -> dict[str, str]:
    """테이블별 컬럼 한글명 매핑. { column_name: name_ko }"""
    if not DB_PATH.exists():
        return {}
    table_name = _sanitize_table_name(table_name)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(
            f"SELECT column_name, name_ko FROM {COLUMN_COMMENT_TABLE} WHERE table_name = ?",
            (table_name,),
        )
        out = {row[0]: row[1] for row in cur.fetchall() if row[1]}
        conn.close()
        return out
    except Exception:
        return {}


def get_column_data_lengths(table_name: str) -> dict[str, int]:
    """
    _column_comment의 data_length 조회. { column_name: max_length } (없거나 숫자 변환 실패 시 제외).
    샘플 데이터 생성 시 해당 길이를 넘지 않도록 참고용.
    """
    if not DB_PATH.exists():
        return {}
    table_name = _sanitize_table_name(table_name)
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        _ensure_comment_tables(conn)
        cur = conn.execute(
            f"SELECT column_name, data_length FROM {COLUMN_COMMENT_TABLE} WHERE table_name = ? AND data_length IS NOT NULL AND data_length != ''",
            (table_name,),
        )
        out = {}
        for row in cur.fetchall():
            try:
                n = int(float(str(row[1]).strip()))
                if n > 0:
                    out[row[0]] = n
            except (ValueError, TypeError):
                pass
        conn.close()
        return out
    except Exception:
        return {}


def save_column_min_max_batch(rows: list[dict]) -> tuple[int, str | None]:
    """
    테이블·컬럼별 min/max 정의를 DB에 저장(INSERT OR REPLACE).
    rows: [{"table_name": str, "column_name": str, "min_val": str|None, "max_val": str|None}, ...]
    반환: (저장 건수, 오류 메시지 또는 None)
    """
    if not rows:
        return 0, None
    try:
        _ensure_dir()
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        _ensure_comment_tables(conn)
        cur = conn.cursor()
        saved = 0
        for r in rows:
            t = _sanitize_table_name((r.get("table_name") or r.get("테이블명") or "").strip())
            c = _sanitize_column_name((r.get("column_name") or r.get("컬럼명") or "").strip())
            if not t or not c:
                continue
            min_v = r.get("min_val") or r.get("min") or r.get("MIN") or r.get("최소")
            max_v = r.get("max_val") or r.get("max") or r.get("MAX") or r.get("최대")
            if min_v is not None and isinstance(min_v, float) and pd.isna(min_v):
                min_v = None
            if max_v is not None and isinstance(max_v, float) and pd.isna(max_v):
                max_v = None
            min_s = None if min_v is None else str(min_v).strip() or None
            max_s = None if max_v is None else str(max_v).strip() or None
            cur.execute(
                f"""INSERT OR REPLACE INTO {COLUMN_MIN_MAX_TABLE}
                    (table_name, column_name, min_val, max_val) VALUES (?, ?, ?, ?)""",
                (t, c, min_s, max_s),
            )
            saved += 1
        conn.commit()
        conn.close()
        return saved, None
    except Exception as e:
        return 0, str(e)


def get_column_min_max(table_name: str | None = None) -> dict:
    """
    컬럼별 min/max 조회.
    table_name이 있으면 { column_name: {"min": str|None, "max": str|None} }
    없으면 { table_name: { column_name: {"min", "max"} } }
    """
    if not DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        _ensure_comment_tables(conn)
        if table_name:
            t = _sanitize_table_name(table_name)
            cur = conn.execute(
                f"SELECT column_name, min_val, max_val FROM {COLUMN_MIN_MAX_TABLE} WHERE table_name = ?",
                (t,),
            )
            out = {row[0]: {"min": row[1], "max": row[2]} for row in cur.fetchall()}
        else:
            cur = conn.execute(
                f"SELECT table_name, column_name, min_val, max_val FROM {COLUMN_MIN_MAX_TABLE}"
            )
            out = {}
            for row in cur.fetchall():
                t, c, mn, mx = row[0], row[1], row[2], row[3]
                if t not in out:
                    out[t] = {}
                out[t][c] = {"min": mn, "max": mx}
        conn.close()
        return out
    except Exception:
        return {}


def get_table_row_count(table_name: str) -> int:
    """테이블의 현재 행 수 반환. 테이블이 없거나 오류 시 0."""
    if not table_name or not DB_PATH.exists():
        return 0
    table_name = _sanitize_table_name(table_name)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        n = cur.fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


def load_table(table_name: str, limit: int | None = None) -> pd.DataFrame | None:
    """지정한 테이블명의 데이터를 DataFrame으로 반환. 없거나 오류 시 None. limit 지정 시 해당 행 수만 읽음(통계 등 빠른 조회용)."""
    if not table_name or not DB_PATH.exists():
        return None
    table_name = _sanitize_table_name(table_name)
    try:
        conn = sqlite3.connect(DB_PATH)
        q = f'SELECT * FROM "{table_name}"'
        if limit is not None and limit > 0:
            q += f" LIMIT {int(limit)}"
        df = pd.read_sql(q, conn)
        conn.close()
        return df if not df.empty else None
    except Exception:
        return None


def clear_table(table_name: str) -> bool:
    """지정 테이블만 삭제"""
    if not DB_PATH.exists():
        return True
    table_name = _sanitize_table_name(table_name)
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.execute(f"DELETE FROM {META_TABLE} WHERE name = ?", (table_name,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def clear_all_tables() -> bool:
    """적재된 모든 테이블 삭제"""
    if not DB_PATH.exists():
        return True
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        for row in conn.execute(f"SELECT name FROM {META_TABLE}").fetchall():
            name = row[0]
            conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        conn.execute(f"DELETE FROM {META_TABLE}")
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def _ensure_extraction_tables(conn: sqlite3.Connection):
    """조회 조건·조회 결과 테이블이 없으면 생성 (감사 컬럼 포함)."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_EXTRACTION_CRITERIA} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {COL_CREATED_DATE} TEXT,
            {COL_CREATED_TIME} TEXT,
            {COL_CREATED_BY} TEXT,
            {COL_UPDATED_DATE} TEXT,
            {COL_UPDATED_TIME} TEXT,
            {COL_UPDATED_BY} TEXT,
            {COL_CRITERIA_PROFITABILITY_MIN} INTEGER,
            {COL_CRITERIA_SOUNDNESS_MIN} INTEGER,
            {COL_CRITERIA_RISK_MAX} INTEGER
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_EXTRACTION_RESULT} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {COL_CRITERIA_ID} INTEGER NOT NULL REFERENCES {TABLE_EXTRACTION_CRITERIA}(id),
            {COL_CREATED_DATE} TEXT,
            {COL_CREATED_TIME} TEXT,
            {COL_CREATED_BY} TEXT,
            {COL_UPDATED_DATE} TEXT,
            {COL_UPDATED_TIME} TEXT,
            {COL_UPDATED_BY} TEXT,
            {COL_CUSTOMER_ID} TEXT,
            {COL_CUSTOMER_NAME} TEXT,
            {COL_PROFITABILITY_SCORE} INTEGER,
            {COL_SOUNDNESS_SCORE} INTEGER,
            {COL_RISK_SCORE} INTEGER,
            {COL_AI_REASONING} TEXT
        )
    """)
    for name in (TABLE_EXTRACTION_CRITERIA, TABLE_EXTRACTION_RESULT):
        conn.execute(f"INSERT OR IGNORE INTO {META_TABLE} (name) VALUES (?)", (name,))
    conn.commit()


def save_extraction_run(
    criteria: dict,
    result_list: list[dict],
    ai_reasoning: str | None = None,
    created_by: str = "",
    updated_by: str = "",
) -> bool:
    """
    조회 조건을 extraction_criteria에, 조회 결과(고객별 점수 + AI 사유)를 extraction_result에 저장.
    criteria: {"수익성 이상": int, "건전성 이상": int, "리스크 이하": int}
    result_list: [ {"고객_ID", "고객명", "수익성", "건전성", "리스크"}, ... ]
    """
    if not result_list:
        return False
    from datetime import datetime
    now = datetime.now()
    cd, ct = now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")
    try:
        _ensure_dir()
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        _ensure_extraction_tables(conn)
        cur = conn.execute(
            f"""
            INSERT INTO {TABLE_EXTRACTION_CRITERIA} (
                {COL_CREATED_DATE}, {COL_CREATED_TIME}, {COL_CREATED_BY},
                {COL_UPDATED_DATE}, {COL_UPDATED_TIME}, {COL_UPDATED_BY},
                {COL_CRITERIA_PROFITABILITY_MIN}, {COL_CRITERIA_SOUNDNESS_MIN}, {COL_CRITERIA_RISK_MAX}
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cd, ct, created_by or "",
                cd, ct, updated_by or "",
                criteria.get("수익성 이상"),
                criteria.get("건전성 이상"),
                criteria.get("리스크 이하"),
            ),
        )
        criteria_id = cur.lastrowid
        for c in result_list:
            conn.execute(
                f"""
                INSERT INTO {TABLE_EXTRACTION_RESULT} (
                    {COL_CRITERIA_ID}, {COL_CREATED_DATE}, {COL_CREATED_TIME}, {COL_CREATED_BY},
                    {COL_UPDATED_DATE}, {COL_UPDATED_TIME}, {COL_UPDATED_BY},
                    {COL_CUSTOMER_ID}, {COL_CUSTOMER_NAME},
                    {COL_PROFITABILITY_SCORE}, {COL_SOUNDNESS_SCORE}, {COL_RISK_SCORE},
                    {COL_AI_REASONING}
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    criteria_id, cd, ct, created_by or "", cd, ct, updated_by or "",
                    c.get("고객_ID"), c.get("고객명"),
                    c.get("수익성"), c.get("건전성"), c.get("리스크"),
                    ai_reasoning or "",
                ),
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def load_extraction_result_with_criteria() -> pd.DataFrame | None:
    """
    extraction_result와 extraction_criteria를 criteria_id로 조인한 결과 반환.
    조회 결과(고객·점수·AI사유)와 해당 추출 시 사용한 조건(수익성/건전성/리스크 기준)을 함께 볼 수 있음.
    """
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        q = f"""
            SELECT r.*,
                   c.{COL_CREATED_DATE} AS criteria_created_date,
                   c.{COL_CREATED_TIME} AS criteria_created_time,
                   c.{COL_CRITERIA_PROFITABILITY_MIN},
                   c.{COL_CRITERIA_SOUNDNESS_MIN},
                   c.{COL_CRITERIA_RISK_MAX}
            FROM {TABLE_EXTRACTION_RESULT} r
            INNER JOIN {TABLE_EXTRACTION_CRITERIA} c ON r.{COL_CRITERIA_ID} = c.id
            ORDER BY r.{COL_CRITERIA_ID} DESC, r.id
        """
        df = pd.read_sql(q, conn)
        conn.close()
        return df if not df.empty else None
    except Exception:
        return None


# 하위 호환: 단일 테이블처럼 쓰던 API
def save_uploaded_data(df: pd.DataFrame, table_name: str | None = None) -> bool:
    """업로드된 DataFrame 저장. table_name 없으면 'uploaded_data' 사용."""
    name = (table_name and _sanitize_table_name(table_name)) or "uploaded_data"
    return save_table(df, name)


def load_uploaded_data(table_name: str | None = None) -> pd.DataFrame | None:
    """테이블명 없으면 목록 중 첫 번째 테이블 로드 (기존 동작 호환)."""
    if table_name:
        return load_table(table_name)
    tables = list_tables()
    if not tables:
        return None
    return load_table(tables[0])


def clear_uploaded_data(table_name: str | None = None) -> bool:
    """table_name 없으면 전체 삭제, 있으면 해당 테이블만 삭제."""
    if table_name:
        return clear_table(table_name)
    return clear_all_tables()


# --- ERD 시각화 연동: 테이블·컬럼 스키마 조회 및 JSON 파일 갱신 ---

def table_has_rows(table_name: str) -> bool:
    """테이블에 1건 이상 있는지만 확인 (전체 로드 없이 빠르게)."""
    table_name = _sanitize_table_name(table_name)
    if not table_name or not DB_PATH.exists():
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(f'SELECT 1 FROM "{table_name}" LIMIT 1')
        has = cur.fetchone() is not None
        conn.close()
        return has
    except Exception:
        return False


def update_ml_crm_segment_interpretations(run_key: str, updates: list[tuple]) -> bool:
    """
    ML_CRM_SEGMENTS 테이블의 SEGMENT_INTERPRETATION 컬럼을 갱신.
    updates: [ (segment_cd, interpretation_text), ... ]
    """
    if not run_key or not DB_PATH.exists():
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        for seg_cd, interpretation in updates:
            conn.execute(
                f"""UPDATE {ML_SEGMENTS_TABLE} SET SEGMENT_INTERPRETATION = ? WHERE RUN_KEY = ? AND SEGMENT_CD = ?""",
                (interpretation or "", run_key, seg_cd),
            )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_table_schema_with_comments(table_name: str) -> list[dict]:
    """
    단일 테이블의 컬럼 스키마 + 한글명 반환.
    반환: [ {"name": "CSTNO", "type": "INTEGER", "name_ko": "고객번호"}, ... ]
    """
    table_name = _sanitize_table_name(table_name)
    if not DB_PATH.exists():
        return []
    comments = get_column_comments(table_name)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute(f'PRAGMA table_info("{table_name}")')
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "name": r[1],
                "type": (r[2] or "TEXT").upper(),
                "name_ko": comments.get(r[1]) if comments else None,
                "pk": r[5] if len(r) > 5 else 0,
            }
            for r in rows
        ]
    except Exception:
        return []


def get_all_tables_schema_with_comments() -> dict[str, list[dict]]:
    """
    모든 테이블의 스키마+한글명을 한 번의 연결로 조회 (조건 추출 설정 등 대량 조회 시 로딩 완화).
    반환: { table_name: [ {"name", "type", "name_ko"}, ... ], ... }
    """
    if not DB_PATH.exists():
        return {}
    out = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        _ensure_meta(conn)
        try:
            cur = conn.execute(f"SELECT name FROM {META_TABLE} ORDER BY name")
            names = [row[0] for row in cur.fetchall()]
        except Exception:
            names = []
        comments_all = {}
        try:
            _ensure_comment_tables(conn)
            cur = conn.execute(
                f"SELECT table_name, column_name, name_ko FROM {COLUMN_COMMENT_TABLE}"
            )
            for row in cur.fetchall():
                t, c, ko = row[0], row[1], row[2]
                if t not in comments_all:
                    comments_all[t] = {}
                if ko:
                    comments_all[t][c] = ko
        except Exception:
            pass
        for tname in names:
            try:
                cur = conn.execute(f'PRAGMA table_info("{tname}")')
                rows = cur.fetchall()
                comments = comments_all.get(tname, {})
                out[tname] = [
                    {
                        "name": r[1],
                        "type": (r[2] or "TEXT").upper(),
                        "name_ko": comments.get(r[1]),
                    }
                    for r in rows
                ]
            except Exception:
                out[tname] = []
        conn.close()
    except Exception:
        pass
    return out


def get_tables_schema() -> list[dict]:
    """
    DB에 적재된 테이블별 스키마(컬럼명·타입) 반환.
    반환 형식: [ {"name": "고객", "columns": [ {"name": "id", "type": "INTEGER", "pk": 1}, ... ] }, ... ]
    """
    names = list_tables()
    if not names:
        return []
    out = []
    try:
        conn = sqlite3.connect(DB_PATH)
        for tname in names:
            cur = conn.execute(f'PRAGMA table_info("{tname}")')
            rows = cur.fetchall()
            # sqlite3: (cid, name, type, notnull, dflt_value, pk)
            cols = [
                {"name": r[1], "type": (r[2] or "TEXT"), "pk": bool(r[5])}
                for r in rows
            ]
            out.append({"name": tname, "columns": cols})
        conn.close()
    except Exception:
        pass
    return out


def refresh_erd_tables_json() -> bool:
    """ERD 시각화용 erd_tables.json 파일을 현재 DB 스키마로 갱신."""
    try:
        _ensure_dir()
        schema = get_tables_schema()
        import json
        with open(ERD_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump({"tables": schema}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
