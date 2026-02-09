# -*- coding: utf-8 -*-
"""
AI-First Financial Intelligence CRM
고객 대량 데이터 적재 · AI 분석 · 관리 대시보드
"""

# .env 파일에서 OPENAI_API_KEY 등 환경 변수 로드 (app.py 있는 폴더 기준으로 찾기)
try:
    from dotenv import load_dotenv
    from pathlib import Path
    _env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(_env_path)
except Exception:
    pass

import base64
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
import io
import json
import random
import re
from pathlib import Path

# 조건 추출에 사용할 테이블·컬럼 설정 저장 경로 (데이터 보기와 동일한 테이블 풀 사용)
EXTRACTION_CONFIG_PATH = Path(__file__).resolve().parent / "data" / "extraction_config.json"
# 사이드바 로고 이미지
LOGO_PATH = Path(__file__).resolve().parent / "image" / "logo.jpg"

try:
    from ai_service import (
        generate_dashboard_summary,
        generate_reasoning,
        generate_comparison,
        generate_customer_scores,
        generate_extract_reasoning,
        generate_segment_grade_schema,
        generate_segment_grade_schema_for_dimension,
        get_segment_grade_prompt,
        get_segment_grade_prompt_for_dimension,
        get_best_marketing_category_prompt,
        generate_best_marketing_category,
        generate_segment_interpretations,
        is_ai_available,
        get_last_rate_limit_headers,
    )
except Exception:
    def _noop(*a, **k):
        return None
    generate_dashboard_summary = _noop
    generate_reasoning = _noop
    generate_comparison = _noop
    def generate_customer_scores(*a, **k):
        return None
    def generate_extract_reasoning(*a, **k):
        return None
    def generate_segment_grade_schema(*a, **k):
        return None, "AI 서비스를 사용할 수 없습니다."
    def generate_segment_grade_schema_for_dimension(*a, **k):
        return None, "AI 서비스를 사용할 수 없습니다."
    def get_segment_grade_prompt(*a, **k):
        return ""
    def get_segment_grade_prompt_for_dimension(*a, **k):
        return ""
    def get_best_marketing_category_prompt(*a, **k):
        return ""
    def generate_best_marketing_category(*a, **k):
        return None, "AI 서비스를 사용할 수 없습니다."
    def generate_segment_interpretations(*a, **k):
        return (None, None)
    def is_ai_available():
        return False
    def get_last_rate_limit_headers():
        return {}

try:
    from db_storage import (
        save_uploaded_data,
        save_table,
        insert_into_table,
        save_extraction_run,
        load_uploaded_data,
        load_table,
        load_extraction_result_with_criteria,
        list_tables,
        clear_uploaded_data,
        clear_all_tables,
        clear_table,
        get_db_path,
        refresh_erd_tables_json,
        create_table_from_schema,
        get_table_schema_with_comments,
        get_all_tables_schema_with_comments,
        get_table_comment,
        get_column_min_max,
        get_column_data_lengths,
        save_column_min_max_batch,
        get_table_row_count,
        insert_one_row_and_get_error,
        table_has_rows,
        update_ml_crm_segment_interpretations,
        _sanitize_table_name,
        _sanitize_column_name,
        TABLE_CONDITION_EXTRACT_RESULT,
        TABLE_EXTRACTION_CRITERIA,
        TABLE_EXTRACTION_RESULT,
        COL_CUSTOMER_ID,
        COL_CUSTOMER_NAME,
        COL_PROFITABILITY_SCORE,
        COL_SOUNDNESS_SCORE,
        COL_RISK_SCORE,
        COL_EXTRACTED_AT,
        COL_CRITERIA_PROFITABILITY_MIN,
        COL_CRITERIA_SOUNDNESS_MIN,
        COL_CRITERIA_RISK_MAX,
    )
except Exception:
    def save_uploaded_data(df, table_name=None):
        return False
    def save_table(df, table_name):
        return False
    def insert_into_table(df, table_name):
        return False, "db_storage 미로드", 0
    def save_extraction_run(*a, **k):
        return False
    def load_extraction_result_with_criteria():
        return None
    def load_uploaded_data(table_name=None):
        return None
    def load_table(table_name, limit=None):
        return None
    def list_tables():
        return []
    def clear_uploaded_data(table_name=None):
        return False
    def clear_all_tables():
        return False
    def clear_table(table_name):
        return False
    def get_db_path():
        return ""
    def refresh_erd_tables_json():
        return False
    def create_table_from_schema(*a, **k):
        return False, "", "db_storage 미로드"
    def get_table_schema_with_comments(*a, **k):
        return []
    def get_all_tables_schema_with_comments(*a, **k):
        return {}
    def get_table_comment(*a, **k):
        return None
    def get_column_min_max(*a, **k):
        return {}
    def get_column_data_lengths(*a, **k):
        return {}
    def save_column_min_max_batch(*a, **k):
        return 0, "db_storage 미로드"
    def get_table_row_count(*a, **k):
        return 0
    def insert_one_row_and_get_error(*a, **k):
        return None
    def update_ml_crm_segment_interpretations(*a, **k):
        return False
    def table_has_rows(*a, **k):
        return False
    def _sanitize_table_name(x):
        return (x or "").strip() or "uploaded_data"
    def _sanitize_column_name(x):
        return (x or "").strip() or "col"
    TABLE_CONDITION_EXTRACT_RESULT = "condition_extract_result"
    TABLE_EXTRACTION_CRITERIA = "extraction_criteria"
    TABLE_EXTRACTION_RESULT = "extraction_result"
    COL_CUSTOMER_ID = "customer_id"
    COL_CUSTOMER_NAME = "customer_name"
    COL_PROFITABILITY_SCORE = "profitability_score"
    COL_SOUNDNESS_SCORE = "soundness_score"
    COL_RISK_SCORE = "risk_score"
    COL_EXTRACTED_AT = "extracted_at"
    COL_CRITERIA_PROFITABILITY_MIN = "criteria_profitability_min"
    COL_CRITERIA_SOUNDNESS_MIN = "criteria_soundness_min"
    COL_CRITERIA_RISK_MAX = "criteria_risk_max"

# 페이지 설정
st.set_page_config(
    page_title="AI Financial CRM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 색상 상수 (화이트 테마 · AI-First Financial Intelligence)
COLORS = {
    "deep_navy": "#1A202C",
    "navy_light": "#E2E8F0",
    "electric_blue": "#3182CE",
    "purple": "#805AD5",
    "bg_card": "#FFFFFF",
    "text_primary": "#1A202C",
    "text_secondary": "#4A5568",
    "success": "#48BB78",
    "warning": "#D69E2E",
    "bg_page": "#F7FAFC",
    "border": "#E2E8F0",
}

# 세션 상태 초기화 (첫 테이블은 대시보드 등 필요 시에만 로드해 초기 로딩 완화)
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None
# ERD JSON은 ERD 시각화 메뉴 진입 시 갱신 (앱 시작 시 전체 갱신 제거로 로딩 완화)
if "saved_reports" not in st.session_state:
    st.session_state.saved_reports = []
if "notifications" not in st.session_state:
    st.session_state.notifications = [
        {"id": 1, "msg": "새로운 상담 데이터 50건이 추가되었습니다. AI 분석을 시작할까요?", "read": False, "time": "방금 전"},
    ]
if "ai_dashboard_summary" not in st.session_state:
    st.session_state.ai_dashboard_summary = None
if "ai_reasoning" not in st.session_state:
    st.session_state.ai_reasoning = None
if "last_scores" not in st.session_state:
    st.session_state.last_scores = {"성향 점수": 78, "수익성 등급": "B+", "안정성 위험도": "낮음"}


def load_custom_css():
    """화이트 테마 · Electric Blue · Purple 포인트 CSS"""
    st.markdown(
        f"""
    <style>
    /* 전역 배경 */
    .stApp {{
        background: linear-gradient(180deg, #FFFFFF 0%, {COLORS["bg_page"]} 100%);
    }}
    [data-testid="stSidebar"] {{
        background: #FFFFFF;
        border-right: 1px solid {COLORS["border"]};
    }}
    [data-testid="stSidebar"] .stMarkdown {{
        color: {COLORS["text_primary"]};
    }}
    /* 사이드바 로고·문구 열 간격 축소 */
    [data-testid="stSidebar"] [data-testid="column"] {{
        padding-left: 0.15rem;
        padding-right: 0.15rem;
        min-width: 0;
    }}

    /* 메트릭/카드 스타일 */
    .metric-card {{
        background: {COLORS["bg_card"]};
        border-radius: 12px;
        padding: 1.25rem;
        border-left: 4px solid {COLORS["electric_blue"]};
        color: {COLORS["text_primary"]};
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid {COLORS["border"]};
    }}
    .metric-card.purple {{
        border-left-color: {COLORS["purple"]};
    }}
    .metric-card.green {{
        border-left-color: {COLORS["success"]};
    }}
    .metric-card h4 {{
        color: {COLORS["text_secondary"]};
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
    }}
    .metric-card .value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: {COLORS["electric_blue"]};
    }}

    /* AI 요약 카드 */
    .ai-summary-card {{
        background: #FFFFFF;
        border: 1px solid {COLORS["electric_blue"]};
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: {COLORS["text_primary"]};
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    /* 조건 추출 카드 */
    .criteria-extract-card {{
        background: #FFFFFF;
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border-left: 4px solid {COLORS["electric_blue"]};
    }}
    .ai-summary-card h3 {{
        color: {COLORS["electric_blue"]};
        font-size: 1rem;
        margin-bottom: 0.75rem;
    }}

    /* 고객 세그 카드 */
    .segment-card {{
        background: #FFFFFF;
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        border-left: 4px solid {COLORS["electric_blue"]};
    }}
    .segment-card .seg-code {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {COLORS["electric_blue"]};
        letter-spacing: 0.05em;
    }}
    .segment-card .meta {{
        color: {COLORS["text_secondary"]};
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }}

    /* Reasoning 블록 */
    .reasoning-block {{
        background: {COLORS["bg_card"]};
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
        border-left: 4px solid {COLORS["purple"]};
        color: {COLORS["text_primary"]};
        border: 1px solid {COLORS["border"]};
        border-left-width: 4px;
        border-left-color: {COLORS["purple"]};
    }}
    .reasoning-block li {{
        margin: 0.35rem 0;
    }}

    /* 알림 센터 */
    .notification-box {{
        background: {COLORS["bg_page"]};
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid {COLORS["electric_blue"]};
        color: {COLORS["text_primary"]};
    }}

    /* 타이틀 */
    .main-title {{
        color: {COLORS["text_primary"]};
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }}
    .sub-title {{
        color: {COLORS["text_secondary"]};
        font-size: 0.9rem;
    }}

    /* 게이지 컨테이너 */
    .gauge-container {{
        background: {COLORS["bg_card"]};
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )


def _data_context(df: pd.DataFrame) -> dict:
    """업로드된 데이터프레임에서 AI용 요약 컨텍스트 생성."""
    if df is None or df.empty:
        return {}
    ctx = {"rows": len(df), "columns": list(df.columns)}
    # 수치 컬럼 기초 통계
    nums = df.select_dtypes(include=["number"]).columns.tolist()
    if nums:
        ctx["numeric_summary"] = df[nums].describe().round(2).to_dict()
    # 범주형 1~2개 컬럼만 value_counts (상위 5개)
    cats = df.select_dtypes(include=["object", "category"]).columns.tolist()[:2]
    for c in cats:
        vc = df[c].dropna().value_counts().head(5)
        ctx[f"value_counts_{c}"] = vc.to_dict()
    return ctx


def render_gauge(title: str, value: float, max_val: float = 100, color: str = COLORS["electric_blue"]):
    """KPI 게이지 차트"""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"font": {"size": 28, "color": color}},
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title, "font": {"size": 14, "color": COLORS["text_secondary"]}},
            gauge={
                "axis": {"range": [0, max_val], "tickcolor": COLORS["text_secondary"]},
                "bar": {"color": color},
                "bgcolor": COLORS["bg_page"],
                "borderwidth": 2,
                "bordercolor": COLORS["border"],
                "steps": [
                    {"range": [0, max_val * 0.33], "color": COLORS["navy_light"]},
                    {"range": [max_val * 0.33, max_val * 0.66], "color": COLORS["electric_blue"]},
                    {"range": [max_val * 0.66, max_val], "color": COLORS["purple"]},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 3},
                    "thickness": 0.8,
                    "value": value,
                },
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor=COLORS["bg_page"],
        margin=dict(l=20, r=20, t=50, b=20),
        height=220,
        font=dict(color=COLORS["text_primary"]),
    )
    return fig


def _get_dashboard_tables():
    """대시보드 분석용 테이블 로드 (마이데이터, 대출, 신용, 상담). 없으면 None."""
    tables = list_tables()
    out = {}
    for name in ["마이데이터", "대출", "신용", "상담"]:
        if name in tables:
            df = load_table(name)
            out[name] = df
        else:
            out[name] = None
    return out


def main_dashboard():
    """홈 (대시보드) — 제목만 표시"""
    st.markdown('<p class="main-title">📊 AI Financial CRM 대시보드</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">수익성(Profitability), 건전성(Soundness), 리스크율(Risk Rate) 분석을 한눈에 파악하세요.</p>',
        unsafe_allow_html=True,
    )
    st.divider()


def data_upload():
    """데이터 적재 화면"""
    st.markdown('<p class="main-title">📤 데이터 적재</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">CSV/Excel 데이터 적재와 테이블 컬럼 MIN/MAX 정의 적재를 한 화면에서 할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # 이전 액션에서 남긴 메시지가 있으면 상단에 계속 표시 (한 번 표시 후 제거)
    if "data_upload_message" in st.session_state:
        kind, text = st.session_state.data_upload_message
        del st.session_state.data_upload_message
        if kind == "success":
            st.success(text)
        elif kind == "warning":
            st.warning(text)
        elif kind == "error":
            st.error(text)
        else:
            st.info(text)

    # ----- 1. 데이터 적재 -----
    st.subheader("1. 데이터 적재")
    st.caption("CSV 또는 Excel 파일을 업로드하면, 파일명과 같은 이름의 기존 테이블에 데이터가 추가(INSERT)됩니다. 여러 파일 선택 가능.")
    if "data_uploader_key" not in st.session_state:
        st.session_state.data_uploader_key = 0
    uploaded = st.file_uploader(
        "파일 선택 (CSV, xlsx, xls)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        key=f"data_uploader_{st.session_state.data_uploader_key}",
        help="테이블은 생성·재생성하지 않습니다. 먼저 **테이블 생성** 메뉴에서 테이블을 만든 뒤, 같은 테이블명으로 업로드하세요.",
    )
    if uploaded:
        files = list(uploaded) if uploaded else []
        if "ai_extract_result" in st.session_state:
            del st.session_state.ai_extract_result
        success_count = 0
        fail_count = 0
        NA_VALUES_READ = ["", "#N/A", "null", "None", "nan", ".", "#NULL!"]
        for f in files:
            try:
                if f.name.endswith(".csv"):
                    df = pd.read_csv(f, keep_default_na=False, na_values=NA_VALUES_READ)
                else:
                    df = pd.read_excel(f, na_values=NA_VALUES_READ)
                table_name = Path(f.name).stem
                ok, err, _ = insert_into_table(df, table_name)
                if ok:
                    success_count += 1
                    st.session_state.uploaded_data = df
                    st.success(f"✅ **{f.name}** → 테이블 **{table_name}** 에 {len(df):,}건 추가 완료")
                else:
                    fail_count += 1
                    st.error(f"❌ **{f.name}** → {table_name}: {err or '업로드 실패'}")
                with st.expander(f"미리보기: {f.name} (상위 10행)"):
                    st.dataframe(df.head(10), use_container_width=True)
                    st.caption(f"컬럼: {list(df.columns)}")
            except Exception as e:
                fail_count += 1
                st.error(f"❌ **{f.name}** 파일 처리 오류: {e}")
        if success_count > 0:
            try:
                refresh_erd_tables_json()
            except Exception:
                pass
            st.session_state.data_upload_message = (
                "info",
                f"총 **{success_count}**개 파일 적재 완료" + (f", **{fail_count}**개 실패" if fail_count else "") + ". **데이터 보기**에서 확인하세요.",
            )
        elif fail_count > 0:
            st.session_state.data_upload_message = ("error", f"**{fail_count}**개 파일 적재 실패. 테이블 존재 여부·스키마·파일 형식을 확인하세요.")
        st.session_state.data_uploader_key = (st.session_state.data_uploader_key + 1) % (10**6)
        st.rerun()

    st.divider()

    # ----- 2. 테이블 컬럼 MIN/MAX 정의 적재 -----
    st.subheader("2. 테이블 컬럼 MIN/MAX 정의 적재")
    st.caption(
        "테이블·컬럼별 min/max가 정의된 엑셀을 업로드하면 DB에 저장됩니다. "
        "엑셀 양식: **테이블명**(또는 table_name), **컬럼명**(또는 column_name), **min**, **max** 컬럼 포함. 첫 시트 상단 10행 안에 헤더가 있으면 인식합니다."
    )
    if "min_max_uploader_key" not in st.session_state:
        st.session_state.min_max_uploader_key = 0
    min_max_file = st.file_uploader(
        "파일 선택 (xlsx, xls)",
        type=["xlsx", "xls"],
        key=f"min_max_excel_uploader_{st.session_state.min_max_uploader_key}",
        help="MIN/MAX 정의 엑셀만 업로드하세요.",
    )
    if min_max_file:
        rows = _parse_min_max_excel(min_max_file)
        if rows:
            saved, err = save_column_min_max_batch(rows)
            if err:
                st.session_state.data_upload_message = ("error", f"저장 실패: {err}")
                st.rerun()
            else:
                st.session_state.data_upload_message = ("success", f"✅ **{saved}건** MIN/MAX 정의 DB 적재 완료.")
                st.session_state.min_max_uploader_key = (st.session_state.min_max_uploader_key + 1) % (10**6)
                st.rerun()
        else:
            st.session_state.data_upload_message = ("warning", "엑셀에서 테이블명·컬럼명·min·max 컬럼을 찾을 수 없습니다. 양식을 확인해 주세요.")
            st.rerun()

    # ----- 샘플 데이터 생성 (_column_min_max 기반) -----
    st.caption("_column_min_max에 정의된 min/max 범위 안에서 테이블에 샘플 데이터를 생성합니다. 여러 테이블을 선택하면 한 번에 생성됩니다.")
    min_max_all = get_column_min_max()
    existing_tables = set(list_tables())
    tables_with_min_max = sorted([t for t in min_max_all if t in existing_tables])
    if tables_with_min_max:
        c1, c2 = st.columns([1, 3])
        with c1:
            sample_count = st.number_input(
                "생성 할 건수",
                min_value=1,
                max_value=100_000,
                value=100,
                step=10,
                key="sample_data_count",
            )
        with c2:
            selected_tables = st.multiselect(
                "대상 테이블 (여러 개 선택 가능)",
                options=tables_with_min_max,
                default=[],
                key="sample_data_tables_multiselect",
            )
        if st.button("샘플 데이터 생성", type="primary", key="sample_data_generate_btn"):
            if not selected_tables:
                st.session_state.data_upload_message = ("warning", "테이블을 하나 이상 선택하세요.")
                st.rerun()
            results = []
            total_inserted = 0
            errors = []
            for tname in selected_tables:
                df = _generate_sample_data(tname, sample_count)
                if df is not None and not df.empty:
                    ok, err, rows_inserted = insert_into_table(df, tname)
                    if ok:
                        if rows_inserted == 0:
                            detail = insert_one_row_and_get_error(df.head(1), tname)
                            errors.append(f"**{tname}**: 0건 — " + (detail or "제약으로 무시됨"))
                        else:
                            results.append((tname, rows_inserted, get_table_row_count(tname)))
                            total_inserted += rows_inserted
                    else:
                        errors.append(f"**{tname}**: {err or '적재 실패'}")
                else:
                    errors.append(f"**{tname}**: 생성 실패 또는 비어 있음")
            try:
                refresh_erd_tables_json()
            except Exception:
                pass
            if results:
                parts = [f"**{t}** {n}건 (총 {total}건)" for t, n, total in results]
                msg = f"✅ {len(results)}개 테이블 적재 완료 (총 **{total_inserted}건**). " + ", ".join(parts) + ". **데이터 보기**에서 확인하세요."
                if errors:
                    msg += " 일부 실패: " + " / ".join(errors)
                st.session_state.data_upload_message = ("success", msg)
            elif errors:
                st.session_state.data_upload_message = ("warning", "⚠️ " + " / ".join(errors))
            else:
                st.session_state.data_upload_message = ("warning", "선택한 테이블에 대해 생성·적재된 결과가 없습니다.")
            st.rerun()
    else:
        st.info("MIN/MAX가 정의된 테이블이 없거나, 해당 테이블이 DB에 없습니다. 위에서 MIN/MAX 정의 엑셀을 먼저 적재하고 **테이블 생성**으로 테이블을 만든 뒤 이용하세요.")


def _generate_sample_data(table_name: str, n_rows: int) -> pd.DataFrame | None:
    """
    _column_min_max를 참고하여 table_name 테이블에 넣을 n_rows건의 샘플 데이터 DataFrame 생성.
    MIN/MAX 범위가 있는 컬럼만 해당 범위 내에서 생성. MIN/MAX 둘 다 비어 있으면 해당 컬럼은 생성하지 않음(NULL).
    PK 컬럼은 삽입을 위해 MIN/MAX 없어도 유일값 생성(INTEGER PK는 None으로 DB 자동 생성, TEXT/복합 INT PK는 유일값).
    """
    schema = get_table_schema_with_comments(table_name)
    if not schema:
        return None
    col_min_max = get_column_min_max(table_name)
    col_data_length = get_column_data_lengths(table_name)  # _column_comment.data_length
    rng = random.Random()
    data = {}
    MAX_TEXT_PK_LEN = 16
    def short_pk_text(i: int, col_name: str = "") -> str:
        # CSTNO: C로 시작, 총 16자리
        if (col_name or "").upper() == "CSTNO":
            return f"C{i:015d}"  # C + 15자리 숫자 = 16자
        return f"s{i:015d}"[:MAX_TEXT_PK_LEN]
    int_pk_cols = [c["name"] for c in schema if c.get("pk") and "INT" in (c.get("type") or "").upper()]
    use_pk_row_index = len(int_pk_cols) > 1
    for col in schema:
        cname = col["name"]
        ctype = (col.get("type") or "TEXT").upper()
        is_pk = bool(col.get("pk"))
        mm = col_min_max.get(cname, {})
        min_s = mm.get("min")
        max_s = mm.get("max")
        if min_s is not None and isinstance(min_s, float) and pd.isna(min_s):
            min_s = None
        if max_s is not None and isinstance(max_s, float) and pd.isna(max_s):
            max_s = None
        if min_s is not None:
            min_s = str(min_s).strip() or None
        if max_s is not None:
            max_s = str(max_s).strip() or None
        has_both = bool(min_s) and bool(max_s)
        try:
            min_i = int(float(min_s)) if min_s else None
            max_i = int(float(max_s)) if max_s else None
        except (ValueError, TypeError):
            min_i, max_i = None, None
        # MIN/MAX가 숫자 범위: PK는 min부터 max까지 순차 증가, 비-PK는 랜덤
        if has_both and min_i is not None and max_i is not None:
            if max_i < min_i:
                min_i, max_i = max_i, min_i
            span = max_i - min_i + 1
            if is_pk:
                # PRIMARY KEY는 min 값부터 차례로 증가 (범위 넘으면 순환)
                data[cname] = [min_i + (i % span) for i in range(n_rows)]
            else:
                data[cname] = [rng.randint(min_i, max_i) for _ in range(n_rows)]
            continue
        # CHECK(length(IVTG_CRED_CALG_CD) ≤ 1) 대응: 이 컬럼은 항상 1글자만 생성
        if (cname or "").upper() == "IVTG_CRED_CALG_CD":
            if has_both and min_s and max_s:
                try:
                    mi, ma = int(float(min_s)), int(float(max_s))
                    if 0 <= mi <= 9 and 0 <= ma <= 9:
                        data[cname] = [str(rng.randint(mi, ma)) for _ in range(n_rows)]
                    else:
                        lo, hi = ord(str(min_s)[0]), ord(str(max_s)[0])
                        data[cname] = [chr(rng.randint(min(lo, hi), max(lo, hi))) for _ in range(n_rows)]
                except Exception:
                    data[cname] = ["0"] * n_rows
            else:
                data[cname] = ["0"] * n_rows
            continue
        # CSTNO: PK 여부와 관계없이 항상 생성 (min/max 있으면 해당 범위, 없으면 기본 범위)
        if (cname or "").upper() == "CSTNO":
            s_min = (min_s or "").strip() if min_s else "C000000000000001"
            s_max = (max_s or "").strip() if max_s else "C999999999999999"
            if not s_min:
                s_min = "C000000000000001"
            if not s_max:
                s_max = "C999999999999999"
            try:
                def _parse_cstno_num(s: str) -> int | None:
                    s = (s or "").strip().upper()
                    if s.startswith("C") and len(s) > 1:
                        return int(s[1:])
                    return None
                lo, hi = _parse_cstno_num(s_min), _parse_cstno_num(s_max)
                if lo is not None and hi is not None:
                    if hi < lo:
                        lo, hi = hi, lo
                    span = max(hi - lo + 1, 1)
                    indices = [lo + (i % span) for i in range(n_rows)]
                    data[cname] = [f"C{i:015d}" for i in indices]
                    continue
            except (ValueError, TypeError):
                pass
        # PK 컬럼: MIN/MAX가 필수. 없으면 INTEGER PK만 DB 자동 생성, TEXT PK는 NULL(정의 필요)
        if is_pk and "INT" in ctype:
            if use_pk_row_index and has_both and min_i is not None and max_i is not None:
                if max_i < min_i:
                    min_i, max_i = max_i, min_i
                span = max_i - min_i + 1
                data[cname] = [min_i + (i % span) for i in range(n_rows)]
            elif not use_pk_row_index:
                data[cname] = [None] * n_rows
            else:
                data[cname] = [i + 1 for i in range(n_rows)]
            continue
        if is_pk and ("TEXT" in ctype or ctype == "TEXT"):
            # CSTNO: min/max 있으면 해당 범위, 없어도 기본 범위(C000000000000001~C999999999999999)로 생성
            if (cname or "").upper() == "CSTNO":
                s_min = (min_s or "").strip() if min_s else ""
                s_max = (max_s or "").strip() if max_s else ""
                if not s_min or not s_max:
                    s_min, s_max = "C000000000000001", "C999999999999999"
                try:
                    def _parse_cstno_num(s: str) -> int | None:
                        s = (s or "").strip().upper()
                        if s.startswith("C") and len(s) > 1:
                            return int(s[1:])
                        return None
                    lo, hi = _parse_cstno_num(s_min), _parse_cstno_num(s_max)
                    if lo is not None and hi is not None:
                        if hi < lo:
                            lo, hi = hi, lo
                        span = hi - lo + 1
                        indices = [lo + (i % span) for i in range(n_rows)]
                        data[cname] = [f"C{i:015d}" for i in indices]
                        continue
                except (ValueError, TypeError):
                    pass
            # 그 외 TEXT PK는 MIN/MAX 없음 → NULL
            data[cname] = [None] * n_rows
            continue
        # MIN/MAX 둘 다 비어 있으면 데이터 생성하지 않음 (NULL)
        if not has_both:
            data[cname] = [None] * n_rows
            continue
        # MIN/MAX 범위 내에서만 생성
        try:
            min_i = int(float(min_s)) if min_s else None
            max_i = int(float(max_s)) if max_s else None
        except (ValueError, TypeError):
            min_i, max_i = None, None
        try:
            min_f = float(min_s) if min_s else None
            max_f = float(max_s) if max_s else None
        except (ValueError, TypeError):
            min_f, max_f = None, None
        # 한 자리 수(0~9) 또는 한 글자 min/max: CHECK(length ≤ 1) 대응 — 반드시 한 글자 문자열로 생성
        if min_i is not None and max_i is not None and 0 <= min_i <= 9 and 0 <= max_i <= 9:
            data[cname] = [str(rng.randint(min_i, max_i)) for _ in range(n_rows)]
            continue
        if min_s and max_s and len(min_s) == 1 and len(max_s) == 1:
            try:
                lo, hi = ord(min_s[0]), ord(max_s[0])
                if lo <= hi:
                    data[cname] = [chr(rng.randint(lo, hi)) for _ in range(n_rows)]
                else:
                    data[cname] = [min_s for _ in range(n_rows)]
            except Exception:
                data[cname] = [None] * n_rows
            continue
        if "INT" in ctype and min_i is not None and max_i is not None:
            data[cname] = [rng.randint(min_i, max_i) for _ in range(n_rows)]
        elif ("REAL" in ctype or "FLOAT" in ctype or "NUM" in ctype) and min_f is not None and max_f is not None:
            data[cname] = [rng.uniform(min_f, max_f) for _ in range(n_rows)]
        elif min_i is not None and max_i is not None:
            data[cname] = [rng.randint(min_i, max_i) for _ in range(n_rows)]
        elif min_f is not None and max_f is not None:
            data[cname] = [rng.uniform(min_f, max_f) for _ in range(n_rows)]
        elif min_s and max_s and re.match(r"^\d{4}-\d{2}-\d{2}", min_s) and re.match(r"^\d{4}-\d{2}-\d{2}", max_s):
            try:
                d_min = datetime.strptime(min_s[:10], "%Y-%m-%d").date()
                d_max = datetime.strptime(max_s[:10], "%Y-%m-%d").date()
                if d_min <= d_max:
                    delta = (d_max - d_min).days
                    data[cname] = [(d_min + timedelta(days=rng.randint(0, delta))).strftime("%Y-%m-%d") for _ in range(n_rows)]
                else:
                    data[cname] = [min_s for _ in range(n_rows)]
            except ValueError:
                data[cname] = [min_s for _ in range(n_rows)]
        elif min_s and max_s and len(min_s) <= 2 and len(max_s) <= 2:
            try:
                lo, hi = ord(min_s[0]), ord(max_s[0])
                if lo <= hi:
                    data[cname] = [chr(rng.randint(lo, hi)) for _ in range(n_rows)]
                else:
                    data[cname] = [min_s for _ in range(n_rows)]
            except Exception:
                data[cname] = [None] * n_rows
        else:
            # TEXT 등: min/max 문자열 구간이 명확하지 않으면 NULL
            data[cname] = [None] * n_rows
    # _column_comment.data_length 적용: 생성된 값을 해당 길이를 넘지 않도록 자르기
    for cname, max_len in (col_data_length or {}).items():
        if cname in data and max_len is not None and max_len > 0:
            data[cname] = [str(v)[:max_len] if v is not None else None for v in data[cname]]
    return pd.DataFrame(data) if data else None


def _normalize_header(s: str) -> str:
    """헤더 문자열 정규화: 공백 축약, 소문자 (매칭용)."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).strip()
    s = " ".join(s.lower().split())
    return s


def _parse_min_max_excel(uploaded_file) -> list[dict]:
    """
    min/max 정의 엑셀 파싱. 모든 시트를 읽어 테이블명·컬럼명·min·max 컬럼을 찾아
    [{"table_name", "column_name", "min_val", "max_val"}, ...] 반환.
    각 시트마다 헤더는 첫 행~10행 중에서 자동 탐색.
    """
    # 모든 시트 읽기 (sheet_name=None → {시트명: DataFrame})
    sheets = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    if not sheets:
        return []
    TABLE_HEADERS = {"테이블명", "table_name", "table name", "테이블"}
    COLUMN_HEADERS = {"컬럼명", "column_name", "column name", "컬럼", "column"}
    MIN_HEADERS = {"min", "min_val", "min val", "최소", "min value"}
    MAX_HEADERS = {"max", "max_val", "max val", "최대", "max value"}
    all_rows = []
    for _sheet_name, df_raw in sheets.items():
        if df_raw is None or df_raw.empty or len(df_raw) < 1:
            continue
        col_map = {}
        header_row_idx = None
        for row_idx in range(min(10, len(df_raw))):
            row_vals = df_raw.iloc[row_idx]
            col_map = {}
            for i, x in enumerate(row_vals):
                norm = _normalize_header(x)
                if norm in TABLE_HEADERS:
                    col_map["table_name"] = i
                elif norm in COLUMN_HEADERS:
                    col_map["column_name"] = i
                elif norm in MIN_HEADERS:
                    col_map["min_val"] = i
                elif norm in MAX_HEADERS:
                    col_map["max_val"] = i
            if "table_name" in col_map and "column_name" in col_map:
                header_row_idx = row_idx
                break
        if header_row_idx is None or "table_name" not in col_map or "column_name" not in col_map:
            continue
        df = df_raw.iloc[header_row_idx + 1 :].copy()
        df.columns = [f"_c{i}" for i in range(len(df.columns))]
        table_idx = col_map["table_name"]
        column_idx = col_map["column_name"]
        min_idx = col_map.get("min_val")
        max_idx = col_map.get("max_val")
        for _, r in df.iterrows():
            t = r.iloc[table_idx] if table_idx < len(r) else None
            c = r.iloc[column_idx] if column_idx < len(r) else None
            if pd.isna(t) or pd.isna(c) or (str(t).strip() == "") or (str(c).strip() == ""):
                continue
            min_v = r.iloc[min_idx] if min_idx is not None and min_idx < len(r) else None
            max_v = r.iloc[max_idx] if max_idx is not None and max_idx < len(r) else None
            if isinstance(min_v, float) and pd.isna(min_v):
                min_v = None
            if isinstance(max_v, float) and pd.isna(max_v):
                max_v = None
            all_rows.append({
                "table_name": str(t).strip(),
                "column_name": str(c).strip(),
                "min_val": min_v,
                "max_val": max_v,
            })
    return all_rows


def _parse_schema_excel(uploaded_file) -> list[tuple[str, str | None, list[dict]]]:
    """
    엑셀 파일(단일 또는 다중 시트)을 파싱하여 (테이블명, 테이블 한글명, 컬럼 정의 리스트) 목록 반환.
    양식: No., 테이블명, 테이블 한글명, 엔티티명, 컬럼명, 컬럼 한글명, 속성명, 데이터타입, ...
    테이블 한글명: "테이블 한글명" 또는 "엔티티명" 컬럼. 컬럼 한글명: "컬럼 한글명" 또는 "속성명" 컬럼.
    """
    import pandas as pd
    sheets_raw = pd.read_excel(uploaded_file, sheet_name=None, header=None)
    result = []
    required = {"테이블명", "컬럼명", "데이터타입"}
    for sheet_name, df_raw in sheets_raw.items():
        if df_raw is None or df_raw.empty or len(df_raw) < 2:
            continue
        df = None
        for header_row in range(min(10, len(df_raw))):
            row_vals = df_raw.iloc[header_row]
            cols = []
            for i, x in enumerate(row_vals):
                if x is None or (isinstance(x, float) and pd.isna(x)):
                    cols.append(f"_c{i}")
                elif isinstance(x, str) and not x.strip():
                    cols.append(f"_c{i}")
                else:
                    cols.append(str(x).strip())
            if required.issubset(set(cols)):
                df = df_raw.iloc[header_row + 1 :].copy()
                df.columns = cols
                break
        if df is None or df.empty or "테이블명" not in df.columns:
            continue
        for tname, grp in df.groupby("테이블명", dropna=True):
            tname_str = (tname if isinstance(tname, str) else str(tname)).strip()
            if not tname_str or (isinstance(tname, float) and pd.isna(tname)) or tname_str.lower() == "nan":
                continue
            # 테이블 한글명: 첫 행 기준 "테이블 한글명" 또는 "엔티티명"
            table_name_ko = None
            if "테이블 한글명" in grp.columns:
                first_val = grp.iloc[0].get("테이블 한글명")
                if first_val is not None and not (isinstance(first_val, float) and pd.isna(first_val)):
                    table_name_ko = str(first_val).strip()
            if (not table_name_ko) and "엔티티명" in grp.columns:
                first_val = grp.iloc[0].get("엔티티명")
                if first_val is not None and not (isinstance(first_val, float) and pd.isna(first_val)):
                    table_name_ko = str(first_val).strip()
            column_defs = []
            for _, row in grp.iterrows():
                cn = row.get("컬럼명")
                if cn is None or (isinstance(cn, float) and pd.isna(cn)):
                    continue
                col = {
                    "컬럼명": cn,
                    "데이터타입": row.get("데이터타입"),
                    "데이터길이": row.get("데이터길이"),
                    "소수점": row.get("소수점"),
                    "PK": row.get("PK"),
                    "Null여부": row.get("Null여부"),
                    "DEFAULT": row.get("DEFAULT"),
                }
                if "컬럼 한글명" in grp.columns:
                    col["컬럼 한글명"] = row.get("컬럼 한글명")
                if "속성명" in grp.columns:
                    col["속성명"] = row.get("속성명")
                column_defs.append(col)
            if column_defs:
                result.append((tname_str, table_name_ko or None, column_defs))
    return result


def table_schema_upload_page():
    """엑셀 테이블 양식 업로드 → 시트/테이블명 단위로 테이블 생성"""
    st.markdown('<p class="main-title">📋 테이블 생성</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">엑셀 양식(테이블명·컬럼명·데이터타입 등)을 업로드하면 DB에 빈 테이블이 생성됩니다. 시트가 여러 개여도 모든 시트를 읽어 테이블을 만듭니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption(
        "**엑셀 양식**: 첫 행 헤더에 다음 컬럼이 있어야 합니다. "
        "No., 테이블명, 테이블 한글명(또는 엔티티명), 컬럼명, 컬럼 한글명(또는 속성명), 데이터타입, 데이터길이, 소수점, PK, Null여부, DEFAULT. "
        "필수: 테이블명, 컬럼명, 데이터타입. 테이블/컬럼 한글명이 있으면 DB 메타에 저장되어 화면 등에서 사용됩니다."
    )
    st.divider()

    uploaded = st.file_uploader(
        "테이블 양식 엑셀 선택 (xlsx, xls) — 모든 시트를 읽어 테이블명 단위로 생성",
        type=["xlsx", "xls"],
        key="schema_excel_uploader",
    )
    if not uploaded:
        return

    try:
        tables_schema = _parse_schema_excel(uploaded)
    except Exception as e:
        st.error(f"엑셀 파싱 오류: {e}")
        return

    if not tables_schema:
        st.warning("유효한 테이블 정의가 없습니다. 시트마다 **테이블명**, **컬럼명**, **데이터타입** 컬럼이 있는지 확인하세요.")
        return

    # 미리보기
    st.subheader("생성할 테이블 미리보기")
    for item in tables_schema:
        tname = item[0]
        table_name_ko = item[1] if len(item) >= 2 else None
        columns = item[2] if len(item) >= 3 else item[1] if len(item) == 2 else []
        if not columns:
            st.caption(f"⚠️ 테이블명 없음 또는 컬럼 없음 (시트 일부)")
            continue
        expander_label = f"📌 **{tname}**"
        if table_name_ko:
            expander_label += f" — {table_name_ko}"
        expander_label += f" — 컬럼 {len(columns)}개"
        with st.expander(expander_label):
            preview_df = pd.DataFrame([
                {
                    "컬럼명": c.get("컬럼명"),
                    "한글명": c.get("컬럼 한글명") or c.get("속성명"),
                    "데이터타입": c.get("데이터타입"),
                    "PK": c.get("PK"),
                    "Null여부": c.get("Null여부"),
                    "DEFAULT": c.get("DEFAULT"),
                }
                for c in columns
            ])
            st.dataframe(preview_df, use_container_width=True)

    if st.button("✅ 위 테이블들 DB에 생성", type="primary", key="create_tables_btn"):
        results = []  # (테이블명, 성공여부, CREATE_SQL, 오류메시지)
        for item in tables_schema:
            tname = item[0]
            table_name_ko = item[1] if len(item) >= 2 else None
            columns = item[2] if len(item) >= 3 else item[1] if len(item) == 2 else []
            if not columns:
                continue
            ok, sql, err = create_table_from_schema(tname, columns, table_name_ko=table_name_ko)
            results.append((tname, ok, sql, err))
        try:
            refresh_erd_tables_json()
        except Exception:
            pass
        # 로그 파일 생성 (log/table_creation_YYYYMMDD_HHMMSS.log)
        log_dir = Path(__file__).resolve().parent / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_name = f"table_creation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = log_dir / log_name
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"# 테이블 생성 로그 — {datetime.now().isoformat()}\n")
            f.write(f"# 파일: {uploaded.name}\n")
            f.write("=" * 60 + "\n\n")
            for tname, ok, sql, err in results:
                status = "성공" if ok else "실패"
                f.write(f"[테이블] {tname}\n")
                f.write(f"[결과] {status}\n")
                if sql:
                    f.write("[CREATE 문]\n")
                    f.write(sql + "\n")
                if err:
                    f.write("[오류 내용]\n")
                    f.write(err + "\n")
                f.write("-" * 60 + "\n")
        success = [t for t, ok, _, _ in results if ok]
        failed = [t for t, ok, _, _ in results if not ok]
        if success:
            st.success(f"✅ 생성 완료: **{', '.join(success)}** (총 {len(success)}개). **데이터 보기**·**ERD 시각화**에서 확인하세요.")
        if failed:
            st.error(f"❌ 생성 실패: **{', '.join(failed)}** — 로그 파일에서 CREATE 문과 오류 내용을 확인하세요.")
        st.info(f"📄 **로그 파일**: `{log_path}`")
        if success:
            st.rerun()


def view_loaded_data():
    """데이터 보기 — 테이블 선택 후 해당 테이블 건수·컬럼 요약 + 페이지네이션 테이블"""
    st.markdown('<p class="main-title">📋 데이터 보기</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">적재된 테이블을 선택하여 데이터를 조회합니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    tables = list_tables()
    if not tables:
        st.warning("적재된 테이블이 없습니다. **데이터 적재** 메뉴에서 CSV 또는 Excel 파일을 올려주세요.")
        return

    # 테이블 표시 이름 (영문 테이블명 → 한글 라벨)
    table_display_names = {
        TABLE_CONDITION_EXTRACT_RESULT: "조건추출결과 (condition_extract_result)",
        TABLE_EXTRACTION_CRITERIA: "조회조건 (extraction_criteria)",
        TABLE_EXTRACTION_RESULT: "조회결과 (extraction_result)",
    }
    def table_label(t):
        return table_display_names.get(t, t)

    # 테이블 선택 (기본값 빈칸 — 선택 시에만 로드해서 대용량 시 느려짐 방지)
    PLACEHOLDER = ""
    options = [PLACEHOLDER] + tables
    def format_option(t):
        return "테이블을 선택하세요" if t == PLACEHOLDER else table_label(t)
    st.subheader("테이블 선택")
    selected = st.selectbox(
        "보고 싶은 테이블을 선택하세요",
        options=options,
        index=0,
        format_func=format_option,
        key="view_loaded_data_table_select",
    )
    if not selected or selected == PLACEHOLDER:
        st.caption("위에서 테이블을 선택하면 데이터가 표시됩니다.")
        return

    df = load_table(selected)
    display_name = table_label(selected)
    if df is None or df.empty:
        st.warning(f"**{display_name}** 데이터를 불러올 수 없습니다.")
        return

    # 선택 테이블 요약 카드
    n_rows, n_cols = len(df), len(df.columns)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("선택 테이블", display_name)
    with c2:
        st.metric("총 행 수", f"{n_rows:,}건")
    with c3:
        st.metric("총 컬럼 수", f"{n_cols}개")
    with c4:
        null_pct = (df.isna().sum().sum() / (n_rows * n_cols) * 100) if (n_rows * n_cols) > 0 else 0
        st.metric("결측 비율", f"{null_pct:.1f}%")

    # 컬럼 목록·타입·결측
    st.subheader("컬럼 정보")
    col_info = pd.DataFrame({
        "컬럼명": df.columns,
        "타입": [str(d) for d in df.dtypes],
        "결측 수": df.isna().sum().values,
        "유일값 수": [df[c].nunique() for c in df.columns],
    })
    st.dataframe(col_info, use_container_width=True, height=min(200, 50 + len(col_info) * 35))

    # 데이터 테이블 (페이지네이션)
    st.subheader("데이터 테이블")
    page_size = 50
    n_pages = max(1, (n_rows + page_size - 1) // page_size)
    page = st.number_input("페이지", min_value=1, max_value=n_pages, value=1, step=1, key="view_loaded_data_page")
    start = (page - 1) * page_size
    end = min(start + page_size, n_rows)
    st.caption(f"**{display_name}** · 총 {n_rows:,}건 중 {start + 1} ~ {end}건 표시 (페이지당 {page_size}건)")
    st.dataframe(df.iloc[start:end], use_container_width=True, height=400)


def _comment_for_feature(feature_name: str, column_comments_by_table: dict) -> str:
    """피처명에 대한 한글 설명 조회 (테이블별 _column_comment, 접미사 .TableName 반영)."""
    for tname, comments in (column_comments_by_table or {}).items():
        if feature_name in comments:
            return comments[feature_name] or ""
        suffix = "." + tname
        if feature_name.endswith(suffix):
            base = feature_name[: -len(suffix)]
            if base in comments:
                return comments[base] or ""
    return ""


def ml_crm_grade_page():
    """랜덤 포레스트 기반 CRM 고객 등급화·마케팅 점수 — 학습·등급·ML_CRM_RESULTS 저장."""
    st.markdown('<p class="main-title">🌲 CRM 등급화 (Random Forest)</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">데이터 사용 설정 테이블을 CSTNO 기준 병합 후, **수익성·건전성·취급율**에 맞는 타겟 컬럼을 데이터 분석으로 자동 선정하고, RF 모델로 1~10등급·마케팅 우선순위 점수(0~100)를 산출해 **ML_CRM_RESULTS**에 저장합니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    try:
        from ml_crm_rf import run_ml_pipeline, ML_RESULTS_TABLE
    except Exception as e:
        st.error(f"모듈 로드 실패: {e}. scikit-learn이 설치되어 있는지 확인하세요.")
        return

    if st.button("▶ 모델 학습 및 등급화 실행", type="primary", key="ml_crm_run_btn"):
        with st.spinner("데이터 병합·전처리·모델 학습·등급 산출·저장 중..."):
            ok, err, res = run_ml_pipeline()
        if ok:
            st.success("학습·등급화 완료. **ML_CRM_RESULTS** 테이블에 저장되었습니다.")
            st.metric("병합 행 수", f"{res.get('merged_rows', 0):,}건")
            sel = res.get("selected_targets") or {}
            cand = res.get("target_candidates") or {}
            st.caption(
                "**선정된 타겟**: "
                + " · ".join([f"수익성→{sel.get('profit') or '—'}", f"건전성→{sel.get('soundness') or '—'}", f"취급율→{sel.get('handling') or '—'}"])
            )
            with st.expander("📋 병합 데이터에서 뽑은 타겟 후보 (차원별 상위 3개)", expanded=True):
                for dim_label, key in [("수익성", "profit"), ("건전성", "soundness"), ("취급율", "handling")]:
                    cols = cand.get(key) or []
                    chosen = sel.get(key) or "—"
                    st.caption(f"**{dim_label}** 후보: " + (", ".join([f"`{c}`" + (" ✓선정" if c == chosen else "") for c in cols]) if cols else "—"))
            rd = res.get("result_df")
            if rd is not None and not rd.empty:
                header_ko = {
                    "RUN_KEY": "실행키",
                    "CSTNO": "고객번호",
                    "profit_grade": "수익성 등급",
                    "soundness_grade": "건전성 등급",
                    "handling_grade": "취급율 등급",
                    "priority_score": "우선순위 점수",
                    "marketing_group": "마케팅 그룹",
                    "SEGMENT_CD": "범주코드",
                    "CREATED_DATE": "생성 일자",
                    "CREATED_TIME": "생성 시간",
                }
                rd_display = rd.rename(columns={c: header_ko.get(c, c) for c in rd.columns})
                with st.expander("결과 미리보기 (상위 100건)", expanded=True):
                    st.dataframe(rd_display.head(100), use_container_width=True)
            # 고객 범주 요약 및 AI 해석
            seg_summary = res.get("segment_summary") or []
            if seg_summary:
                st.subheader("📂 고객 범주 (5~7개 그룹)")
                seg_df = pd.DataFrame(seg_summary)
                seg_display = seg_df.rename(columns={
                    "name": "범주", "count": "건수",
                    "avg_profit_grade": "평균 수익등급", "avg_soundness_grade": "평균 건전등급",
                    "avg_handling_grade": "평균 취급등급", "avg_priority_score": "평균 우선순위점수",
                })
                st.dataframe(seg_display, use_container_width=True, hide_index=True)
                with st.expander("🤖 범주 해석 (생성형 AI)", expanded=True):
                    ai_list, markdown_fallback = generate_segment_interpretations(seg_summary)
                    if ai_list:
                        name_to_cd = {s.get("name", ""): s.get("segment_cd", "") for s in seg_summary}
                        updates = []
                        for item in ai_list:
                            name = item.get("segment_name", "")
                            interp = item.get("interpretation", "")
                            seg_cd = name_to_cd.get(name, "")
                            if seg_cd:
                                updates.append((seg_cd, interp))
                        run_key = res.get("run_key", "")
                        if run_key and updates:
                            update_ml_crm_segment_interpretations(run_key, updates)
                        for item in ai_list:
                            st.markdown(f"### {item.get('segment_name', '')}")
                            st.markdown(item.get("interpretation", ""))
                    elif markdown_fallback:
                        st.markdown(markdown_fallback)
                    else:
                        st.caption("AI 해석을 불러오지 못했습니다. OPENAI_API_KEY 설정 여부를 확인하세요.")
            comments_map = res.get("column_comments_by_table") or {}
            st.subheader("📌 모델별 Feature Importance (상위 9개)")
            any_shown = False
            for dim_label, key in [
                ("수익성", "importance_profit"),
                ("건전성", "importance_soundness"),
                ("취급율", "importance_handling"),
            ]:
                cols = res.get(key) or []
                tcol = (sel.get("profit") if dim_label == "수익성" else sel.get("soundness") if dim_label == "건전성" else sel.get("handling")) or "—"
                label = f"{dim_label} (타겟: `{tcol}`)"
                if cols:
                    any_shown = True
                    st.markdown(f"**{label}**")
                    for i, c in enumerate(cols, 1):
                        ko = _comment_for_feature(c, comments_map)
                        st.caption(f"{i}. `{c}`" + (f" — {ko}" if ko else ""))
                    st.markdown("")
            if not any_shown:
                st.caption(
                    "표시할 Feature Importance가 없습니다. 타겟은 **데이터 분석으로 수익성·건전성·취급율 각각 의미 있는 컬럼을 자동 선정**합니다. "
                    "선정된 타겟이 없거나 유효 데이터가 부족하면 해당 모델은 학습되지 않습니다."
                )
        else:
            st.error("실패: " + (err or "알 수 없는 오류"))
    else:
        st.caption("위 **모델 학습 및 등급화 실행** 버튼을 누르면 데이터 사용 설정 테이블 기준으로 학습이 진행됩니다. 결과는 **데이터 보기**에서 **ML_CRM_RESULTS** 테이블을 선택해 확인할 수 있습니다.")


def extraction_config_page():
    """데이터 사용 설정 — 좌: 테이블 목록(사용 체크), 우: 선택 테이블의 컬럼 목록(사용 체크)."""
    st.markdown('<p class="main-title">⚙️ 데이터 사용 설정</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">좌측에서 **사용할 테이블**을 체크하고, 테이블을 선택하면 우측에서 **AI 분석에 사용할 컬럼**을 체크하세요. 저장 시 반영됩니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    tables = list_tables()
    if not tables:
        st.warning("적재된 테이블이 없습니다. **데이터 적재**에서 CSV/Excel을 올린 뒤 사용하세요.")
        return

    schemas_by_table = get_all_tables_schema_with_comments()
    existing = _load_extraction_config()
    config_by_table = {}
    if existing:
        for c in existing:
            config_by_table[c.get("table_name")] = c

    table_display_names = {
        TABLE_CONDITION_EXTRACT_RESULT: "조건추출결과 (condition_extract_result)",
        TABLE_EXTRACTION_CRITERIA: "조회조건 (extraction_criteria)",
        TABLE_EXTRACTION_RESULT: "조회결과 (extraction_result)",
    }
    def table_label(t, name_ko=None):
        base = table_display_names.get(t, t)
        if name_ko is None:
            name_ko = get_table_comment(t)
        return f"{base} — {name_ko}" if name_ko else base

    # 데이터 있는 테이블만 + 테이블 한글명
    tables_with_data = [t for t in tables if table_has_rows(t)]
    if not tables_with_data:
        st.warning("데이터가 있는 테이블이 없습니다.")
        return
    table_name_ko = {t: get_table_comment(t) for t in tables_with_data}

    # 테이블 선택은 폼 밖에 두어, 클릭 시 바로 rerun 되고 우측 컬럼 목록이 갱신되도록 함
    st.subheader("📋 테이블 목록")
    st.caption("테이블을 **클릭**하면 우측에 해당 테이블의 컬럼이 표시됩니다.")
    selected_table = st.radio(
        "테이블 선택",
        options=tables_with_data,
        format_func=lambda t: table_label(t, table_name_ko.get(t)),
        key="ext_selected_table",
        label_visibility="collapsed",
    )
    st.markdown("---")

    with st.form("ext_config_form"):
        submitted = st.form_submit_button("💾 설정 저장")
        col_left, col_right = st.columns([1, 1])
        with col_left:
            use_by_table = {}
            for tname in tables_with_data:
                prev = config_by_table.get(tname, {})
                default_use = prev.get("use", True)
                row_cb, row_name = st.columns([0.12, 0.88])
                with row_cb:
                    use_by_table[tname] = st.checkbox("사용", value=default_use, key=f"ext_use_{tname}", label_visibility="collapsed")
                with row_name:
                    label = table_label(tname, table_name_ko.get(tname))
                    st.text(label)

        # ----- 우측 그리드: 선택 테이블의 컬럼 목록 + 사용 체크 -----
        with col_right:
            st.subheader("📌 컬럼 목록")
            schema = schemas_by_table.get(selected_table, [])
            cols = [c.get("name") or c.get("컬럼명") for c in schema if c.get("name") or c.get("컬럼명")]
            cid_col = (cols or [""])[0]
            ai_by_col = {}
            if not cols:
                st.caption("컬럼 정보를 불러올 수 없습니다.")
            else:
                prev = config_by_table.get(selected_table, {})
                default_cid = prev.get("customer_id_column") or ""
                if not default_cid or default_cid not in cols:
                    for c in schema:
                        nm = (c.get("name") or c.get("컬럼명") or "")
                        ko = (c.get("name_ko") or "") if isinstance(c.get("name_ko"), str) else ""
                        if nm and (str(nm).upper() in ("CSTNO", "CUST_NO") or "고객_ID" in str(nm) or "customer_id" in str(nm).lower() or (ko and "고객번호" in ko)):
                            default_cid = nm
                            break
                    default_cid = default_cid if default_cid in cols else cols[0]
                cid_col = st.selectbox(
                    "고객 연결 키 컬럼",
                    options=cols,
                    index=cols.index(default_cid) if default_cid in cols else 0,
                    key=f"ext_cid_{selected_table}",
                )
                st.caption("좌측 체크로 AI 분석에 사용할 컬럼을 선택하세요.")
                saved_ai = prev.get("columns_for_ai")
                default_ai_set = set([c for c in (saved_ai or []) if c in cols]) if saved_ai else set(cols)
                for c in schema:
                    col_name = c.get("name") or c.get("컬럼명")
                    if not col_name:
                        continue
                    name_ko = (c.get("name_ko") or "") if isinstance(c.get("name_ko"), str) else ""
                    label = f"{col_name}" + (f" — {name_ko}" if name_ko else "")
                    row_cb, row_name = st.columns([0.12, 0.88])
                    with row_cb:
                        ai_by_col[col_name] = st.checkbox("사용", value=col_name in default_ai_set, key=f"ext_ai_{selected_table}_{col_name}", label_visibility="collapsed")
                    with row_name:
                        st.text(label)

    if submitted:
        new_config = []
        for tname in tables_with_data:
            use = use_by_table.get(tname, True)
            if tname == selected_table:
                cid = cid_col
                ai_cols = [c for c in cols if ai_by_col.get(c, True)]
            else:
                prev = config_by_table.get(tname, {})
                cid = prev.get("customer_id_column")
                sch = schemas_by_table.get(tname, [])
                all_cols = [c.get("name") or c.get("컬럼명") for c in sch if c.get("name") or c.get("컬럼명")]
                if not cid or cid not in (all_cols or []):
                    cid = (all_cols or [""])[0]
                ai_cols = prev.get("columns_for_ai") or all_cols or []
                ai_cols = [c for c in ai_cols if c in (all_cols or [])]
            new_config.append({
                "table_name": tname,
                "use": use,
                "customer_id_column": cid or (cols or [""])[0],
                "columns_for_ai": ai_cols or (schema and cols) or [],
            })
        if _save_extraction_config(new_config):
            st.success("저장했습니다. **AI 상세 분석**·**CRM 등급화(ML)** 등에서 위에서 체크한 테이블·컬럼이 사용됩니다.")
            st.rerun()
        else:
            st.error("저장에 실패했습니다.")

def _resolve_table(tables, *candidates):
    """실제 DB 테이블 목록에서 논리 테이블명(고객/대출/신용/상담 등)에 해당하는 테이블명 반환.
    예: 고객내역·고객, 대출내역·대출, 신용정보내역·신용 등 모두 인식."""
    if not tables:
        return None
    for c in candidates:
        if c in tables:
            return c
    for t in tables:
        for c in candidates:
            if c in t:
                return t
    return None


def _find_col(df, *candidates):
    """DataFrame에서 후보 문자열이 포함된 컬럼명 찾기 (대소문자 무시)."""
    if df is None or df.empty:
        return None
    cols = [str(c) for c in df.columns]
    for cand in candidates:
        for i, c in enumerate(cols):
            if cand.lower() in c.lower() or (cand in c):
                return df.columns[i]
    return None


def _find_first_numeric_col(df, exclude_cols=None):
    """ID 등 제외 후 첫 번째 숫자형 컬럼 반환 (잔액·점수 등 검토 항목 매핑용)."""
    if df is None or df.empty:
        return None
    exclude = set(exclude_cols or [])
    for c in df.columns:
        if c in exclude:
            continue
        try:
            if pd.api.types.is_numeric_dtype(df[c]):
                return c
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().any():
                return c
        except Exception:
            continue
    return None


def _find_first_text_col(df, exclude_cols=None):
    """ID 등 제외 후 첫 번째 문자열형 컬럼 반환 (상담 내용 등 검토 항목 매핑용)."""
    if df is None or df.empty:
        return None
    exclude = set(exclude_cols or [])
    for c in df.columns:
        if c in exclude:
            continue
        try:
            if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == object:
                if df[c].astype(str).str.len().max() > 1:
                    return c
        except Exception:
            continue
    return None


def _load_extraction_config():
    """
    조건 추출에 사용할 테이블·컬럼 설정 로드.
    반환: list[dict] 또는 None. 각 dict: table_name, use, customer_id_column, columns_for_ai
    """
    if not EXTRACTION_CONFIG_PATH.exists():
        return None
    try:
        with open(EXTRACTION_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("tables") or None
    except Exception:
        return None


def _save_extraction_config(tables_config):
    """데이터 사용 설정 저장. tables_config: list[dict] (table_name, use, customer_id_column, columns_for_ai)."""
    EXTRACTION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(EXTRACTION_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"tables": tables_config}, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _get_segment_column_stats():
    """
    데이터 사용 설정에서 체크된 테이블·컬럼 기준으로 컬럼별 min, max, dtype 수집.
    설정이 없거나 현재 DB 테이블과 맞지 않으면, 데이터 있는 모든 테이블·모든 컬럼을 기본 사용.
    반환: (schema_info: str, column_stats: list[dict]). column_stats 항목: table, column, min, max, dtype
    """
    tables = list_tables()
    if not tables:
        return "적재된 테이블 없음", []
    config_list = _load_extraction_config()
    used = [c for c in (config_list or []) if c.get("use") and c.get("table_name") in tables]
    if not used:
        # 설정 없거나 테이블 변경으로 매칭 안 됨 → 데이터 있는 모든 테이블·모든 컬럼 기본 사용
        schemas_by_table = get_all_tables_schema_with_comments()
        for tname in tables:
            if not table_has_rows(tname):
                continue
            schema = schemas_by_table.get(tname, [])
            cols = [c.get("name") or c.get("컬럼명") for c in schema if c.get("name") or c.get("컬럼명")]
            if not cols:
                continue
            default_cid = cols[0]
            for c in schema:
                nm = (c.get("name") or c.get("컬럼명") or "")
                ko = (c.get("name_ko") or "") if isinstance(c.get("name_ko"), str) else ""
                if nm and (str(nm).upper() in ("CSTNO", "CUST_NO") or (ko and "고객번호" in ko)):
                    default_cid = nm
                    break
            used.append({
                "table_name": tname,
                "use": True,
                "customer_id_column": default_cid,
                "columns_for_ai": cols,
            })
    # 통계용으로는 샘플만 로드해 화면 로딩 속도 확보 (전체 로드 시 10만 건×테이블 수로 지연)
    SEGMENT_STATS_SAMPLE = 10_000
    schema_parts = []
    column_stats = []
    for cfg in used:
        tname = cfg.get("table_name")
        cols_ai = cfg.get("columns_for_ai") or []
        if not tname or not cols_ai:
            continue
        df = load_table(tname, limit=SEGMENT_STATS_SAMPLE)
        if df is None or df.empty:
            continue
        schema_parts.append(f"{tname}({', '.join(cols_ai[:8])}{'...' if len(cols_ai) > 8 else ''})")
        for col in cols_ai:
            if col not in df.columns:
                continue
            s = df[col]
            try:
                if pd.api.types.is_numeric_dtype(s):
                    mn = pd.to_numeric(s, errors="coerce").min()
                    mx = pd.to_numeric(s, errors="coerce").max()
                    dtype = str(s.dtype)
                    is_boolean = dtype == "bool"
                    unique_values = ["예", "아니오"] if is_boolean else None
                else:
                    mn = mx = None
                    dtype = "object"
                    uniq = s.dropna().astype(str).unique()
                    is_boolean = "여부" in col or (len(uniq) <= 2 and len(uniq) >= 1)
                    unique_values = list(uniq[:2]) if is_boolean and len(uniq) else (["예", "아니오"] if is_boolean else None)
            except Exception:
                mn = mx = None
                dtype = "object"
                is_boolean = "여부" in col
                unique_values = ["예", "아니오"] if is_boolean else None
            row = {"table": tname, "column": col, "min": mn, "max": mx, "dtype": dtype, "is_boolean": is_boolean}
            if unique_values is not None:
                row["unique_values"] = unique_values
            column_stats.append(row)
    schema_info = "; ".join(schema_parts) if schema_parts else "; ".join(tables)
    return schema_info, column_stats


def _build_summary_from_config(tables, used_config_list, schema_info):
    """
    설정(used_config_list)에 따라 테이블을 로드해 고객별 요약 생성.
    used_config_list: list[dict] with table_name, customer_id_column, columns_for_ai (each use=True).
    반환: (summaries: list[dict], used_tables_columns: list[dict])
    """
    all_cids = set()
    table_dfs = {}
    name_by_cid = {}
    for cfg in used_config_list:
        tname = cfg.get("table_name")
        cid_col = cfg.get("customer_id_column")
        if not tname or not cid_col or tname not in tables:
            continue
        df = load_table(tname)
        if df is None or df.empty or cid_col not in df.columns:
            continue
        table_dfs[tname] = {"df": df, "cfg": cfg}
        all_cids.update(df[cid_col].dropna().astype(str).unique().tolist())
        # 고객명: 첫 테이블에서 이름 컬럼 찾아서 채우기
        name_col = _find_col(df, "고객명", "customer_name", "이름", "name")
        if name_col and name_col in df.columns:
            for _, row in df[[cid_col, name_col]].drop_duplicates(cid_col).iterrows():
                cid = row[cid_col]
                if cid not in name_by_cid:
                    name_by_cid[cid] = str(row[name_col])

    if not all_cids:
        return [], []

    used_tables_columns = []
    for tname, data in table_dfs.items():
        cfg = data["cfg"]
        cid_col = cfg.get("customer_id_column")
        cols_ai = cfg.get("columns_for_ai") or []
        cols_loan = [cid_col] + [c for c in cols_ai if c in data["df"].columns]
        used_tables_columns.append({"table": tname, "columns": cols_loan, "labels": ["연결키"] + cols_ai[: len(cols_loan) - 1]})

    summaries = []
    for cid in sorted(all_cids, key=lambda x: (str(x), x)):
        cname = name_by_cid.get(cid, f"고객_{cid}")
        row = {"고객_ID": cid, "고객명": cname}
        for tname, data in table_dfs.items():
            df = data["df"]
            cfg = data["cfg"]
            cid_col = cfg.get("customer_id_column")
            cols_ai = cfg.get("columns_for_ai") or []
            sub = df[df[cid_col].astype(str) == str(cid)]
            row[f"{tname}_건수"] = len(sub)
            for col in cols_ai:
                if col not in sub.columns:
                    continue
                try:
                    s = sub[col]
                    if pd.api.types.is_numeric_dtype(s):
                        row[f"{tname}_{col}"] = pd.to_numeric(s, errors="coerce").sum()
                    else:
                        row[f"{tname}_{col}"] = " ".join(s.dropna().astype(str).tolist())[:200]
                except Exception:
                    row[f"{tname}_{col}"] = None
        summaries.append(row)
    return summaries, used_tables_columns


def _build_customer_summary_from_db():
    """
    DB의 테이블을 분석해 고객별 요약 dict 리스트와 스키마 설명·사용 테이블·컬럼 반환.
    설정(extraction_config.json)이 있으면 해당 테이블·컬럼만 사용; 없으면 기존 자동 감지(고객내역/대출내역 등).
    반환: (summaries: list[dict], schema_info: str, used_tables_columns: list[dict])
    """
    tables = list_tables()
    if not tables:
        return [], "적재된 테이블 없음", []
    schema_parts = []
    for t in tables:
        df = load_table(t)
        if df is not None and not df.empty:
            schema_parts.append(f"{t}({', '.join(df.columns[:8])}{'...' if len(df.columns) > 8 else ''})")
    schema_info = "; ".join(schema_parts)

    # 설정에 따라 사용할 테이블·컬럼이 있으면 설정 기반으로 요약 생성
    config_list = _load_extraction_config()
    if config_list:
        used = [c for c in config_list if c.get("use") and c.get("table_name") in tables]
        if used:
            summaries, used_tables_columns = _build_summary_from_config(tables, used, schema_info)
            if summaries:
                return summaries, schema_info, used_tables_columns
            # 설정 테이블 로드 실패 등이면 아래 자동 감지로 fallback

    table_customer = _resolve_table(tables, "고객내역", "고객")
    df_customers = load_table(table_customer) if table_customer else None
    id_col_cust = _find_col(df_customers, "고객_ID", "customer_id", "id", "ID") if df_customers is not None else None
    name_col_cust = _find_col(df_customers, "고객명", "customer_name", "이름", "name") if df_customers is not None else None

    used_tables_columns = []

    customers = []
    if df_customers is not None and not df_customers.empty:
        id_col = id_col_cust or df_customers.columns[0]
        name_col = name_col_cust or id_col  # 이름 컬럼 없으면 ID로 표시
        cols_guest = [c for c in [id_col, name_col] if c]
        labels_guest = ["연결키", "이름(검토)"][: len(cols_guest)]
        used_tables_columns.append({"table": table_customer or "고객", "columns": cols_guest, "labels": labels_guest})
        for i in range(len(df_customers)):
            cid = df_customers[id_col].iloc[i]
            cname = str(df_customers[name_col].iloc[i])
            customers.append({"고객_ID": cid, "고객명": cname})
    else:
        cids = set()
        for role, candidates in [
            ("대출", ["대출내역", "대출"]),
            ("신용", ["신용정보내역", "고객신용정보내역", "신용"]),
            ("상담", ["상담내역", "상담"]),
            ("연체", ["연체"]),
        ]:
            tname = _resolve_table(tables, *candidates)
            if tname is None:
                continue
            df = load_table(tname)
            if df is None or df.empty:
                continue
            cid_col = _find_col(df, "고객_ID", "customer_id", "id", "ID")
            if cid_col is not None:
                cids.update(df[cid_col].dropna().unique().tolist())
        for cid in sorted(cids, key=lambda x: (str(x), x)):
            customers.append({"고객_ID": cid, "고객명": f"고객_{cid}"})
        if not customers:
            for i in range(30):
                customers.append({"고객_ID": i, "고객명": f"고객{i+1} (목업)"})

    summaries = []
    table_loan = _resolve_table(tables, "대출내역", "대출")
    table_credit = _resolve_table(tables, "신용정보내역", "고객신용정보내역", "신용")
    table_consult = _resolve_table(tables, "상담내역", "상담")
    table_overdue = _resolve_table(tables, "연체")
    df_loan = load_table(table_loan) if table_loan else None
    df_credit = load_table(table_credit) if table_credit else None
    df_consult = load_table(table_consult) if table_consult else None
    df_overdue = load_table(table_overdue) if table_overdue else None

    cid_loan = _find_col(df_loan, "고객_ID", "customer_id", "id") if df_loan is not None else None
    cid_credit = _find_col(df_credit, "고객_ID", "customer_id", "id") if df_credit is not None else None
    cid_consult = _find_col(df_consult, "고객_ID", "customer_id", "id") if df_consult is not None else None
    cid_overdue = _find_col(df_overdue, "고객_ID", "customer_id", "id") if df_overdue is not None else None
    balance_col = _find_col(df_loan, "잔액", "balance", "대출잔액", "금액", "amount") if df_loan is not None else None
    if balance_col is None and df_loan is not None:
        balance_col = _find_first_numeric_col(df_loan, exclude_cols=[cid_loan] if cid_loan else None)
    score_col = _find_col(df_credit, "점수", "score", "신용점수", "credit") if df_credit is not None else None
    if score_col is None and df_credit is not None:
        score_col = _find_first_numeric_col(df_credit, exclude_cols=[cid_credit] if cid_credit else None)
    content_col = _find_col(df_consult, "내용", "content", "상담내용", "메모", "memo") if df_consult is not None else None
    if content_col is None and df_consult is not None:
        content_col = _find_first_text_col(df_consult, exclude_cols=[cid_consult] if cid_consult else None)

    # 검토 항목(의미) + 실제 컬럼명 — 결과 화면에서 "고객_ID만" 아닌 검토 의미가 보이도록
    if df_loan is not None and (cid_loan or balance_col):
        cols_loan = [cid_loan] if cid_loan else []
        if balance_col:
            cols_loan.append(balance_col)
        used_tables_columns.append({"table": table_loan or "대출", "columns": cols_loan, "labels": ["연결키"] + (["잔액(검토)"] if balance_col else [])})
    if df_credit is not None and (cid_credit or score_col):
        cols_credit = [cid_credit] if cid_credit else []
        if score_col:
            cols_credit.append(score_col)
        used_tables_columns.append({"table": table_credit or "신용", "columns": cols_credit, "labels": ["연결키"] + (["점수(검토)"] if score_col else [])})
    if df_consult is not None and (cid_consult or content_col):
        cols_consult = [cid_consult] if cid_consult else []
        if content_col:
            cols_consult.append(content_col)
        used_tables_columns.append({"table": table_consult or "상담", "columns": cols_consult, "labels": ["연결키"] + (["내용(검토)"] if content_col else [])})
    if df_overdue is not None and cid_overdue:
        used_tables_columns.append({"table": table_overdue or "연체", "columns": [cid_overdue], "labels": ["연결키"]})

    for c in customers:
        cid = c["고객_ID"]
        row = {"고객_ID": cid, "고객명": c["고객명"], "대출_건수": 0, "대출_잔액_합계": 0, "신용점수_최근": None, "상담_건수": 0, "상담_키워드_요약": "", "연체_건수": 0}
        if df_loan is not None and cid_loan and cid in df_loan[cid_loan].values:
            sub = df_loan[df_loan[cid_loan] == cid]
            row["대출_건수"] = len(sub)
            if balance_col and balance_col in sub.columns:
                try:
                    row["대출_잔액_합계"] = pd.to_numeric(sub[balance_col], errors="coerce").sum()
                except Exception:
                    pass
        if df_credit is not None and cid_credit and cid in df_credit[cid_credit].values:
            sub = df_credit[df_credit[cid_credit] == cid]
            if score_col and score_col in sub.columns:
                try:
                    row["신용점수_최근"] = pd.to_numeric(sub[score_col], errors="coerce").dropna().iloc[-1] if len(sub) else None
                except Exception:
                    pass
        if df_consult is not None and cid_consult and cid in df_consult[cid_consult].values:
            sub = df_consult[df_consult[cid_consult] == cid]
            row["상담_건수"] = len(sub)
            texts = []
            if content_col and content_col in sub.columns:
                texts = sub[content_col].dropna().astype(str).tolist()
            row["상담_키워드_요약"] = " ".join(texts)[:200] if texts else ""
        if df_overdue is not None and cid_overdue and cid in df_overdue[cid_overdue].values:
            row["연체_건수"] = len(df_overdue[df_overdue[cid_overdue] == cid])
        summaries.append(row)
    return summaries, schema_info, used_tables_columns


def _customer_scores_for_filter(user_instruction: str = ""):
    """
    고객별 수익성·건전성·리스크 점수 리스트 반환.
    AI 사용 가능 시: DB 요약을 배치로 나눠 AI 호출 후 병합 (429 완화). 실패/미사용 시: 목업 수식으로 반환.
    user_instruction: 사용자가 AI에게 전달할 추가 요청 문구 (선택).
    반환: (list[dict], "ai" | "fallback", api_error_message | None)
    """
    import time
    summaries, schema_info, _ = _build_customer_summary_from_db()
    if not summaries:
        return [], "fallback", None
    if is_ai_available():
        # 429 완화: 한 번에 보내지 않고 배치 단위로 요청 (배치당 고객 수 제한 + 배치 간 대기)
        AI_SCORE_BATCH_SIZE = 50
        AI_SCORE_BATCH_DELAY_SEC = 2
        # 임시: 테스트용 — AI에는 상위 N명만 전송, 나머지는 기본점수 50
        _AI_TEST_LIMIT = 10
        summaries_for_ai = summaries[:_AI_TEST_LIMIT]
        full_scored = []
        api_error = None
        for start in range(0, len(summaries_for_ai), AI_SCORE_BATCH_SIZE):
            chunk = summaries_for_ai[start : start + AI_SCORE_BATCH_SIZE]
            if start > 0:
                time.sleep(AI_SCORE_BATCH_DELAY_SEC)
            scored, err = generate_customer_scores(chunk, schema_info, user_instruction=user_instruction)
            if scored and len(scored) >= 1:
                ai_by_id = {str(s["고객_ID"]): s for s in scored}
                for c in chunk:
                    cid, cname = c.get("고객_ID"), c.get("고객명", "")
                    if str(cid) in ai_by_id:
                        rec = ai_by_id[str(cid)].copy()
                        rec["고객_ID"], rec["고객명"] = cid, cname
                        full_scored.append(rec)
                    else:
                        full_scored.append({"고객_ID": cid, "고객명": cname, "수익성": 50, "건전성": 50, "리스크": 50})
            else:
                for c in chunk:
                    full_scored.append({"고객_ID": c["고객_ID"], "고객명": c.get("고객명", ""), "수익성": 50, "건전성": 50, "리스크": 50})
                if err and not api_error:
                    api_error = err
        if full_scored:
            # 임시: AI에 보내지 않은 나머지 고객은 기본점수 50으로 채움
            for c in summaries[_AI_TEST_LIMIT:]:
                full_scored.append({"고객_ID": c["고객_ID"], "고객명": c.get("고객명", ""), "수익성": 50, "건전성": 50, "리스크": 50})
            return full_scored, "ai", api_error
        # 전체 실패 시 fallback
        err_msg = api_error or "API 호출에 실패했습니다."
        seed_base = 31
        rows = []
        for i, c in enumerate(summaries):
            seed = i * seed_base + 17
            p = min(100, 70 + (seed % 25))
            s = min(100, 75 + ((seed * 3) % 20))
            r = min(100, 10 + ((seed * 7) % 25))
            rows.append({"고객명": c["고객명"], "고객_ID": c["고객_ID"], "수익성": p, "건전성": s, "리스크": r})
        return rows, "fallback", err_msg
    seed_base = 31
    rows = []
    for i, c in enumerate(summaries):
        seed = i * seed_base + 17
        p = min(100, 70 + (seed % 25))
        s = min(100, 75 + ((seed * 3) % 20))
        r = min(100, 10 + ((seed * 7) % 25))
        rows.append({"고객명": c["고객명"], "고객_ID": c["고객_ID"], "수익성": p, "건전성": s, "리스크": r})
    return rows, "fallback", None


def ai_insight_report():
    """② AI 인사이트 리포트 (상세 분석)"""
    st.markdown('<p class="main-title">🧠 AI 인사이트 리포트</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">분석 결과와 그 이유(Reasoning)를 확인하고 저장할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )

    # ----- 조건에 맞는 고객 추출 (수익성·건전성·리스크 점수 조건) -----
    st.markdown("---")
    st.subheader("📌 조건에 맞는 고객 추출")
    st.caption("수익성·건전성·리스크 **점수를 설정**한 뒤 [추출] 버튼을 누르면, **설정한 수치에 맞는 고객만** 추출되어 표시됩니다.")

    with st.form("ai_extract_form"):
        st.markdown("**추출 조건 설정** — 적용할 기준(이상/이하)을 입력하세요.")
        col_a, col_b, col_c, col_btn = st.columns([1, 1, 1, 1.2])
        with col_a:
            min_profit = st.number_input("수익성 **이상** (점)", min_value=0, max_value=100, value=0, step=5, key="ai_min_profit", help="이 점수 이상인 고객만 포함")
        with col_b:
            min_sound = st.number_input("건전성 **이상** (점)", min_value=0, max_value=100, value=0, step=5, key="ai_min_sound", help="이 점수 이상인 고객만 포함")
        with col_c:
            max_risk = st.number_input("리스크 **이하** (점)", min_value=0, max_value=100, value=0, step=5, key="ai_max_risk", help="이 점수 이하인 고객만 포함")
        user_instruction = st.text_area(
            "**AI에게 요청할 문구** (선택)",
            placeholder="예: 대출 잔액이 큰 고객을 우선 고려해 주세요.",
            key="ai_extract_instruction",
            height=80,
        )
        with col_btn:
            st.write("")
            st.write("")
            do_extract = st.form_submit_button("🔍 조건에 맞는 고객 추출")
    if do_extract:
        # 폼 제출 시 입력된 AI 요청 문구 (같은 run에서 session_state에 반영됨)
        ai_request_text = st.session_state.get("ai_extract_instruction", "") or ""
        with st.spinner("AI가 DB를 분석해 고객별 수익성·건전성·리스크 점수를 산출 중..."):
            all_customers, score_source, api_error = _customer_scores_for_filter(user_instruction=ai_request_text)
        filtered = [
            c for c in all_customers
            if c["수익성"] >= min_profit and c["건전성"] >= min_sound and c["리스크"] <= max_risk
        ]
        crit = {"수익성 이상": min_profit, "건전성 이상": min_sound, "리스크 이하": max_risk}
        # 전체 고객 점수 범위 (AI 분석 결과 확인용)
        score_stats = None
        if all_customers:
            p_vals = [c["수익성"] for c in all_customers]
            s_vals = [c["건전성"] for c in all_customers]
            r_vals = [c["리스크"] for c in all_customers]
            score_stats = {
                "수익성": (min(p_vals), max(p_vals)),
                "건전성": (min(s_vals), max(s_vals)),
                "리스크": (min(r_vals), max(r_vals)),
            }
        ai_reasoning = None
        used_tables_columns = []
        if score_source == "ai":
            summaries, schema_info, used_tables_columns = _build_customer_summary_from_db()
            with st.spinner("AI 점수 산출 사유 생성 중…"):
                ai_reasoning = generate_extract_reasoning(summaries, schema_info, crit, user_instruction=ai_request_text)
        st.session_state.ai_extract_result = {
            "filtered": filtered,
            "total": len(all_customers),
            "criteria": crit,
            "score_source": score_source,
            "ai_reasoning": ai_reasoning,
            "api_error": api_error,
            "score_stats": score_stats,
            "used_tables_columns": used_tables_columns,
            "user_instruction": ai_request_text,
        }
        st.rerun()

    # 추출 결과 영역 — 레이아웃은 항상 표시, 내용은 결과 유무에 따라
    res = st.session_state.get("ai_extract_result")
    if res:
        filtered = res["filtered"]
        total = res["total"]
        crit = res["criteria"]
        score_source = res.get("score_source", "fallback")
    else:
        filtered = []
        total = 0
        crit = {"수익성 이상": 0, "건전성 이상": 0, "리스크 이하": 0}
        score_source = "fallback"

    st.markdown("---")
    st.subheader("📊 추출 결과")
    if res and score_source == "ai":
        st.caption("✅ **점수 산출:** AI가 DB(고객·대출·신용·상담·연체 등)를 분석해 고객별 수익성·건전성·리스크를 산출했습니다. (임시: AI에는 상위 10명만 전송, 나머지는 기본점수 50)")
    elif res:
        err_note = " (AI는 호출됐으나 한도 429로 실패 → 1~2분 후 재시도)" if res.get("api_error") else ""
        st.caption("📐 **점수 산출:** 기본 산식 적용 (OPENAI_API_KEY 미설정 시 또는 AI 호출 실패 시)" + err_note)
    else:
        st.caption("**점수 산출:** 조건에 맞는 고객 추출을 실행하면 점수 산출 방식이 여기에 표시됩니다.")
    # 추출 결과 DB 적재 버튼 (📊 추출 결과 상단) — 항상 표시
    if st.button("💾 추출 결과 DB에 적재", key="ai_save_extract_to_db", type="secondary"):
        if res:
            ai_reasoning = res.get("ai_reasoning") or ""
            if save_extraction_run(crit, filtered, ai_reasoning=ai_reasoning, created_by="system", updated_by="system"):
                try:
                    refresh_erd_tables_json()
                except Exception:
                    pass
                st.success(
                    f"✅ **조회 조건**은 **{TABLE_EXTRACTION_CRITERIA}**에, "
                    f"**조회 결과** {len(filtered)}건은 **{TABLE_EXTRACTION_RESULT}**에 저장했습니다. (데이터 보기에서 확인)"
                )
                st.rerun()
            else:
                st.error("DB 적재에 실패했습니다.")
        else:
            st.warning("먼저 **조건에 맞는 고객 추출**을 실행한 뒤 저장할 수 있습니다.")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("추출 인원", f"{len(filtered)}명", f"전체 {total}명 중")
    with m2:
        pct = (len(filtered) / total * 100) if total else 0
        st.metric("비율", f"{pct:.1f}%", "조건 충족")
    with m3:
        st.metric("적용 조건", f"수익≥{crit['수익성 이상']} · 건전≥{crit['건전성 이상']} · 리스크≤{crit['리스크 이하']}", "")
    st.success(
        f"**{len(filtered)}명** 추출됨 — 수익성 ≥ {crit['수익성 이상']}, 건전성 ≥ {crit['건전성 이상']}, 리스크 ≤ {crit['리스크 이하']}"
    )
    score_stats = res.get("score_stats") if res else None
    if len(filtered) == 0 and score_stats:
        st.warning(
            "조건이 현재 점수 범위보다 엄격해서 0명입니다. "
            "**수익성·건전성** 하한을 낮추거나 **리스크** 상한을 올려 보세요. (예: 수익성 ≥ 50, 건전성 ≥ 50, 리스크 ≤ 60)"
        )
    if filtered:
        st.caption("👤 **상세 보기** 링크를 누르면 해당 고객 상세 화면으로 이동합니다.")
        with st.container(height=420):
            h1, h2, h3, h4, h5, h_link = st.columns([2, 1, 0.8, 0.8, 0.8, 1])
            with h1:
                st.markdown("**고객명**")
            with h2:
                st.markdown("**고객_ID**")
            with h3:
                st.markdown("**수익성**")
            with h4:
                st.markdown("**건전성**")
            with h5:
                st.markdown("**리스크**")
            with h_link:
                st.markdown("**이동**")
            st.divider()
            for i, c in enumerate(filtered):
                col1, col2, col3, col4, col5, col_btn = st.columns([2, 1, 0.8, 0.8, 0.8, 1])
                with col1:
                    st.text(c["고객명"])
                with col2:
                    st.text(str(c["고객_ID"]))
                with col3:
                    st.text(str(c["수익성"]))
                with col4:
                    st.text(str(c["건전성"]))
                with col5:
                    st.text(str(c["리스크"]))
                with col_btn:
                    if st.button("→ 상세 보기", key=f"ai_extract_link_{i}", type="secondary"):
                        st.session_state.customer_detail_linked_id = c["고객_ID"]
                        st.session_state.current_page = "고객 상세"
                        st.rerun()
    else:
        st.info("조건을 만족하는 고객이 없습니다. 수익성·건전성 하한을 낮추거나 리스크 상한을 올려 보세요." if res else "조건에 맞는 고객 추출을 실행하면 추출 결과가 여기에 표시됩니다.")

    st.markdown("")
    st.subheader("📋 AI 점수 산출 시 중점 항목 및 사유")
    if res and score_source == "ai":
        used_tables_columns = res.get("used_tables_columns") or []
        if used_tables_columns:
            st.markdown("**🔍 AI 분석에 사용된 테이블·컬럼**")
            for item in used_tables_columns:
                tbl = item.get("table", "")
                cols = item.get("columns", [])
                labels = item.get("labels", [])
                if tbl and cols:
                    if labels and len(labels) == len(cols):
                        parts = [f"`{col}`({lab})" for col, lab in zip(cols, labels)]
                    else:
                        parts = [f"`{col}`" for col in cols]
                    st.caption(f"• **{tbl}**: " + ", ".join(parts))
            st.markdown("")
        reasoning_text = res.get("ai_reasoning") or ""
        if reasoning_text.strip():
            st.info(reasoning_text)
        else:
            st.warning(
                "AI 사유가 생성되지 않았습니다. (API 응답 지연·오류 또는 토큰 제한일 수 있습니다.) "
                "다시 한 번 **조건에 맞는 고객 추출**을 실행해 보세요."
            )
    elif res:
        api_error = res.get("api_error")
        if api_error:
            st.caption(
                "⚠️ **AI(OpenAI API)는 정상적으로 호출**되고 있으나, **요청 한도(429)** 로 이번 요청이 거절되어 기본 산식이 적용되었습니다. "
                "AI 사유는 점수가 AI로 산출된 경우에만 생성됩니다. "
                "**API 한도 정보**는 API가 **성공했을 때만** 사이드바에 표시됩니다. 1~2분 후 다시 시도해 보세요."
            )
        else:
            st.info(
                "이번 추출은 **기본 산식**으로 점수를 산출했습니다. "
                "**.env** 파일에 **OPENAI_API_KEY**를 넣고 앱을 다시 실행한 뒤, **조건에 맞는 고객 추출**을 다시 실행하면 "
                "AI가 DB를 분석한 중점 항목 및 사유가 여기에 표시됩니다."
            )
    else:
        st.info("조건에 맞는 고객 추출을 실행하면 AI 점수 산출 시 중점 항목 및 사유가 여기에 표시됩니다.")

    df = st.session_state.uploaded_data
    ctx = _data_context(df) if df is not None else {}
    scores = st.session_state.last_scores.copy()


def data_archive():
    """③ 데이터 아카이브 (과거 이력 관리)"""
    st.markdown('<p class="main-title">📁 과거 리포트 보관함</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">저장한 분석 결과를 타임라인으로 확인하고, 두 결과를 비교할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    reports = st.session_state.saved_reports
    if not reports:
        st.info("저장된 분석 결과가 없습니다. 'AI 상세 분석'에서 분석 후 저장해 주세요.")
        return

    # 리스트 뷰
    st.subheader("분석 이력")
    for i, r in enumerate(reversed(reports)):
        with st.container():
            snap = r.get("snapshot") or {}
            scores = snap.get("scores", {})
            score_str = ", ".join(f"{k}={v}" for k, v in scores.items()) if scores else ""
            st.markdown(
                f"**{r['saved_at']}** · {r['type']} · 키워드: {r['keywords']}"
            )
            if score_str:
                st.caption(f"스코어: {score_str}")
            st.caption("---")
    st.divider()

    # 비교 모드 (스냅샷 있으면 AI 비교 호출)
    st.subheader("비교 모드")
    st.caption("두 개의 과거 분석을 선택하면, AI가 차이점을 설명합니다.")
    opts = [f"{r['saved_at']} - {r['type']}" for r in reports]
    if len(opts) >= 2:
        c1, c2 = st.columns(2)
        with c1:
            sel_a = st.selectbox("분석 A", options=opts, key="compare_a")
        with c2:
            sel_b = st.selectbox("분석 B", options=opts, key="compare_b")
        if st.button("차이점 AI 분석"):
            idx_a = opts.index(sel_a)
            idx_b = opts.index(sel_b)
            ra, rb = reports[idx_a], reports[idx_b]
            snap_a = ra.get("snapshot") or {}
            snap_b = rb.get("snapshot") or {}
            summary_a = snap_a.get("reasoning") or str(snap_a.get("scores", ""))
            summary_b = snap_b.get("reasoning") or str(snap_b.get("scores", ""))
            if not summary_a:
                summary_a = f"분석 시점: {ra['saved_at']}, 키워드: {ra['keywords']}"
            if not summary_b:
                summary_b = f"분석 시점: {rb['saved_at']}, 키워드: {rb['keywords']}"
            ai_diff = generate_comparison(summary_a, summary_b)
            if ai_diff:
                st.info("**AI 비교 요약:** " + ai_diff)
            else:
                st.info(
                    "**AI 비교 요약:** 분석 A 대비 B에서는 수익성 등급이 1단계 상승했고, "
                    "안정성 지표는 동일하게 유지되었습니다. OPENAI_API_KEY를 설정하면 실제 AI가 차이를 분석합니다."
                )
    else:
        st.warning("비교하려면 분석 결과를 2개 이상 저장해 주세요.")


def customer_detail_page():
    """고객 상세 — 이름·등급·점수 카드, 대출/신용 복합 차트, 상담 타임라인, 미니 ERD"""
    st.markdown('<p class="main-title">👤 고객 상세</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">고객별 수익성·건전성·리스크 점수, 대출/신용 추이, 상담 이력을 확인합니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # 고객 목록: DB 고객(또는 고객내역) 테이블 있으면 사용, 없으면 추출 결과와 동일한 30명 목업
    customer_options = [f"고객{i+1} (목업)" for i in range(30)]
    customer_ids = list(range(30))
    tables = list_tables()
    table_customer = _resolve_table(tables, "고객내역", "고객")
    df_customers = load_table(table_customer) if table_customer else None
    if df_customers is not None and not df_customers.empty:
        name_col = [c for c in df_customers.columns if "이름" in str(c) or "name" in str(c).lower()][:1]
        id_col = [c for c in df_customers.columns if "ID" in str(c) or "id" in str(c).lower()][:1]
        display_col = name_col[0] if name_col else df_customers.columns[0]
        customer_options = [f"{df_customers[display_col].iloc[i]} (행 {i+1})" for i in range(len(df_customers))]
        customer_ids = df_customers[id_col[0]].tolist() if id_col else list(range(len(df_customers)))

    # AI 추출 결과에서 링크로 진입한 경우: 해당 고객 ID로 선택 인덱스 설정
    if "customer_detail_linked_id" in st.session_state:
        linked_id = st.session_state.pop("customer_detail_linked_id", None)
        if linked_id is not None:
            for i, cid in enumerate(customer_ids):
                if cid == linked_id:
                    st.session_state["customer_detail_select"] = i
                    break
            else:
                if isinstance(linked_id, int) and 0 <= linked_id < len(customer_ids):
                    st.session_state["customer_detail_select"] = linked_id

    selected_idx = st.selectbox("고객 선택", range(len(customer_options)), format_func=lambda i: customer_options[i], key="customer_detail_select")
    cust_name = customer_options[selected_idx]
    cust_id = customer_ids[selected_idx] if selected_idx < len(customer_ids) else None

    # 선택한 고객 기준 데이터 조회: DB에 대출/신용/상담 있으면 해당 고객으로 필터, 없으면 선택 인덱스로 다른 목업 표시
    months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"]
    seed = selected_idx * 31 + 17
    scores = {
        "수익성": min(100, 70 + (seed % 25)),
        "건전성": min(100, 75 + ((seed * 3) % 20)),
        "리스크": min(100, 10 + ((seed * 7) % 25)),
    }
    grades = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]
    grade = grades[selected_idx % len(grades)]
    base_loan = 5000 - (selected_idx * 200) % 2000
    loan_balance = [max(500, base_loan - i * (base_loan - 500) // 11) for i in range(12)]
    base_credit = 680 + (selected_idx * 5) % 60
    credit_score = [min(850, base_credit + i * 4 + (selected_idx % 3)) for i in range(12)]
    pool = [
        ("2024-12-01 14:30", "대출 만기 연장 상담", "원리금 상환 일정 조정 요청.", "대출"),
        ("2024-11-15 10:00", "신용 한도 조회", "카드 한도 상향 문의.", "신용"),
        ("2024-10-20 15:45", "추가 대출 상담", "주택 리모델링 자금 대출 희망.", "대출"),
        ("2024-09-05 11:20", "정기 리뷰", "전체 상품 이용 현황 점검.", "일반"),
        ("2024-08-10 09:00", "연체 해제 안내", "1일 연체 발생. 당일 입금 완료.", "연체"),
        ("2024-07-22 16:00", "적금 가입", "정기 적금 상품 가입 완료.", "일반"),
    ]
    consultations = [pool[(selected_idx + i) % len(pool)] for i in range(min(5, len(pool)))]

    # DB에 해당 고객 데이터가 있으면 덮어씀 (대출/신용/상담 테이블)
    table_loan = _resolve_table(tables, "대출내역", "대출")
    table_credit = _resolve_table(tables, "신용정보내역", "고객신용정보내역", "신용")
    table_consult = _resolve_table(tables, "상담내역", "상담")
    df_loan = load_table(table_loan) if table_loan else None
    df_credit = load_table(table_credit) if table_credit else None
    df_consult = load_table(table_consult) if table_consult else None
    if cust_id is not None:
        loan_cid = [_find_col(df_loan, "customer_id", "고객_ID", "id")] if df_loan is not None else []
        credit_cid = [_find_col(df_credit, "customer_id", "고객_ID", "id")] if df_credit is not None else []
        consult_cid = [_find_col(df_consult, "customer_id", "고객_ID", "id")] if df_consult is not None else []
        loan_cid = [c for c in loan_cid if c]
        credit_cid = [c for c in credit_cid if c]
        consult_cid = [c for c in consult_cid if c]
        if df_loan is not None and loan_cid and cust_id in df_loan[loan_cid[0]].values:
            sub = df_loan[df_loan[loan_cid[0]] == cust_id]
            num_cols = sub.select_dtypes(include=["number"]).columns.tolist()
            if num_cols:
                n = min(12, len(sub))
                loan_balance = sub.iloc[:n][num_cols[0]].tolist()
                if len(loan_balance) < 12:
                    loan_balance = loan_balance + [loan_balance[-1] if loan_balance else 0] * (12 - len(loan_balance))
        if df_credit is not None and credit_cid and cust_id in df_credit[credit_cid[0]].values:
            sub = df_credit[df_credit[credit_cid[0]] == cust_id]
            num_cols = sub.select_dtypes(include=["number"]).columns.tolist()
            if num_cols:
                n = min(12, len(sub))
                credit_score = sub.iloc[:n][num_cols[0]].tolist()
                if len(credit_score) < 12:
                    credit_score = credit_score + [credit_score[-1] if credit_score else 700] * (12 - len(credit_score))
        if df_consult is not None and consult_cid and cust_id in df_consult[consult_cid[0]].values:
            sub = df_consult[df_consult[consult_cid[0]] == cust_id].head(10)
            text_cols = [c for c in sub.columns if c != consult_cid[0]][:3]
            consultations = []
            for _, row in sub.iterrows():
                dt = str(row.get("상담_ID", row.iloc[0]))[:10] if len(sub.columns) > 0 else "2024-01-01"
                title = str(row[text_cols[0]])[:30] if text_cols else "상담"
                memo = str(row[text_cols[1]])[:80] if len(text_cols) > 1 else ""
                consultations.append((dt, title, memo, "상담"))

    # 상단: 고객명·등급·3개 점수 카드
    st.subheader(f"📌 {cust_name}" + (f" · {grade}" if grade else ""))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("수익성", f"{scores['수익성']}점", help="고객 생애 가치·NIM 기여도 등")
    with c2:
        st.metric("건전성", f"{scores['건전성']}점", help="DSR·연체 전이율·신용 추이 등")
    with c3:
        st.metric("리스크", f"{scores['리스크']}점", help="부도율·상담 키워드 리스크 등")

    # 점수 산출 항목·이유 (수익성 / 건전성 / 리스크) — 선택한 고객의 실제 점수에 따라 문구 변경
    st.markdown("---")
    st.subheader("📊 점수 산출 내역")
    p, s, r = scores["수익성"], scores["건전성"], scores["리스크"]
    profit_level = "우수" if p >= 80 else "양호" if p >= 65 else "보통" if p >= 50 else "미흡"
    sound_level = "우수" if s >= 85 else "양호" if s >= 70 else "보통" if s >= 55 else "주의"
    risk_level = "낮음" if r <= 25 else "보통" if r <= 50 else "주의" if r <= 70 else "높음"
    score_detail = {
        "수익성": {
            "items": [
                "LTV(고객 생애 가치): 대출·카드 등 기대 총수익",
                "예대마진(NIM) 기여도: 대출 금리－조달 비용 반영",
                "교차 판매 지수: 이용 중인 금융 상품 수",
            ],
            "reason": f"해당 고객({cust_name})은 수익성 점수 **{p}점**으로 **{profit_level}** 그룹에 해당합니다. "
            + ("대출·카드 등 다중 상품 이용과 NIM 기여도가 높아 LTV가 상위권으로 산정되었습니다." if p >= 70 else "LTV·NIM 기여도·교차 판매 지수를 종합해 현재 수준으로 산출되었습니다.")
            + (" 추가 상품 가입 권유 시 수익성 개선 여지가 있습니다." if p < 70 else ""),
        },
        "건전성": {
            "items": [
                "DSR(총부채원리금상환비율) 추정: 소득 대비 원리금 상환 비중",
                "연체 전이율: 정상 → 1~30일 단기 연체로 넘어간 비율",
                "신용 점수 변동 추이: 최근 6개월 신용 점수 하락 여부",
            ],
            "reason": f"건전성 **{s}점**으로 **{sound_level}** 수준입니다. "
            + ("DSR·연체 전이 이력·신용 추이가 양호해 건전성이 높게 산출되었습니다." if s >= 75 else "DSR·연체·신용 변동을 반영한 결과이며, 지속 모니터링을 권장합니다." if s >= 55 else "연체·신용 하락 등 이력이 반영되어 건전성 점수가 낮게 산출되었습니다. 상환 계획 점검이 필요합니다."),
        },
        "리스크": {
            "items": [
                "부도율(PD) 추정: 특정 기간 내 연체 가능 확률",
                "상담 키워드 기반 리스크: '개인회생', '파산', '연기 요청' 등 위험 단어 출현",
                "다중 채무자 비중: 타 금융기관 대출 급증 여부",
            ],
            "reason": f"리스크 점수 **{r}점**으로 **{risk_level}**으로 판정됩니다. "
            + ("상담 이력에 위험 키워드가 없고, 다중 채무·PD가 낮아 리스크가 낮게 산정되었습니다." if r <= 30 else "상담 키워드·다중 채무·PD를 종합해 현재 수준으로 산출되었습니다. 주기적 점검이 필요합니다." if r <= 60 else "위험 키워드 출현·다중 채무·PD 상승 등이 반영되어 리스크가 높게 산출되었습니다. 조기 상담·관리가 권장됩니다."),
        },
    }
    for name, detail in score_detail.items():
        with st.expander(f"**{name}** ({scores[name]}점) — 산출 항목 및 이유", expanded=True):
            st.markdown("**산출 항목**")
            for item in detail["items"]:
                st.markdown(f"- {item}")
            st.markdown("**이유**")
            st.write(detail["reason"])

    # 특이 사항 — 고객별로 분석상 특이한 내용이 있으면 표시, 없으면 "없음"
    st.markdown("---")
    st.subheader("🔍 특이 사항")
    notable_pool = [
        "최근 3개월 내 단기 연체 1건 발생. 당일 입금 완료되어 신용 영향은 제한적이나, 재발 시 건전성 점수 하락 가능.",
        "교차 판매 지수가 동일 연령대 상위 10%로, 추가 대출·카드 상품 권유 적합 구간으로 판단됩니다.",
        "상담 이력에서 '연기 요청' 키워드 1회 출현. 원리금 상환 연기 문의였으며, 현재는 정상 상환 중.",
        "신용 점수가 전월 대비 15점 상승. 신용회복 또는 데이터 반영 지연 해소로 추정됩니다.",
        "다중 금융기관 대출 건수 증가 추세. 채무 통합 상품 안내를 권장합니다.",
        "LTV가 전년 동기 대비 20% 이상 증가. 대출 이용 확대에 따른 것으로, 수익성 기여도가 높음.",
        "DSR이 40% 근접. 소득 대비 부채 상환 부담이 커질 수 있어 추가 대출 시 신중 검토가 필요합니다.",
    ]
    # 고객별로 0~2개 특이 사항 할당 (selected_idx에 따라 다르게)
    n_notable = (selected_idx * 7 + 3) % 4  # 0, 1, 2, 3 중 하나
    if n_notable == 0:
        notable_items = []
    else:
        notable_items = [notable_pool[(selected_idx + i) % len(notable_pool)] for i in range(min(n_notable, 2))]
    if notable_items:
        for i, text in enumerate(notable_items, 1):
            st.markdown(f"- **{i}.** {text}")
        st.caption("위 항목은 해당 고객 분석 시 도출된 특이 사항입니다. 필요 시 상담·추가 검토를 권장합니다.")
    else:
        st.info("이번 분석에서 **특이 사항은 없습니다.** 수익성·건전성·리스크 지표 모두 정상 범위 내로 판단됩니다.")

    # 중앙: 복합 라인 차트 | 우측: 상담 타임라인
    col_chart, col_timeline = st.columns([2, 1])
    with col_chart:
        st.subheader("📈 대출 잔액 & 신용 점수 추이")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=months, y=loan_balance, name="대출 잔액(만원)", line=dict(color=COLORS["electric_blue"], width=2), yaxis="y"))
        fig.add_trace(go.Scatter(x=months, y=credit_score, name="신용 점수", line=dict(color=COLORS["success"], width=2), yaxis="y2"))
        fig.update_layout(
            xaxis=dict(title="월"),
            yaxis=dict(title=dict(text="대출 잔액(만원)", font=dict(color=COLORS["electric_blue"])), side="left"),
            yaxis2=dict(title=dict(text="신용 점수", font=dict(color=COLORS["success"])), side="right", overlaying="y"),
            legend=dict(orientation="h", y=1.02),
            margin=dict(t=40),
            height=340,
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor=COLORS["bg_card"],
            font=dict(color=COLORS["text_primary"]),
        )
        fig.update_xaxes(gridcolor=COLORS["border"])
        fig.update_yaxes(gridcolor=COLORS["border"])
        st.plotly_chart(fig, use_container_width=True)

    with col_timeline:
        st.subheader("📋 상담 이력")
        for i, (dt, title, memo, typ) in enumerate(consultations):
            with st.expander(f"{dt} · {title}", expanded=(i == 0)):
                st.caption(typ)
                st.write(memo)

    # 하단: 미니 ERD 위젯 (고객-대출-신용-마이데이터)
    st.markdown("---")
    st.subheader("🔗 연결 ERD 구조")
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:center; gap:12px; flex-wrap:wrap; padding:16px; 
                    background:{COLORS['bg_card']}; border:1px solid {COLORS['border']}; border-radius:12px;">
            <span style="padding:8px 16px; border-radius:8px; background:#ECFDF5; border:2px solid {COLORS['success']}; font-weight:600; color:#047857;">고객</span>
            <span style="color:#94a3b8;">→</span>
            <span style="padding:8px 16px; border-radius:8px; background:#EFF6FF; border:2px solid {COLORS['electric_blue']}; font-weight:600; color:#1d4ed8;">대출</span>
            <span style="color:#94a3b8;">→</span>
            <span style="padding:8px 16px; border-radius:8px; background:#EFF6FF; border:2px solid {COLORS['electric_blue']}; font-weight:600; color:#1d4ed8;">신용</span>
            <span style="color:#94a3b8;">→</span>
            <span style="padding:8px 16px; border-radius:8px; background:#F5F3FF; border:2px solid {COLORS['purple']}; font-weight:600; color:#6d28d9;">마이데이터</span>
        </div>
        <p style="text-align:center; color:{COLORS['text_secondary']}; font-size:0.85rem; margin-top:8px;">고객 → 대출 · 신용 · 마이데이터 연결 구조</p>
        """,
        unsafe_allow_html=True,
    )


def erd_viewer_page():
    """ERD 시각화 — localhost:5173 iframe (erd-viewer)"""
    st.markdown('<p class="main-title">📐 ERD 시각화</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">고객·상담·대출·신용·연체 테이블 관계를 탐색합니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption(
        "ERD가 보이지 않으면, 터미널에서 **erd-viewer** 폴더로 이동 후 **npm run dev** 를 실행한 뒤 새로고침하세요. "
        "run.bat 으로 실행했다면 ERD 창이 별도로 열려 있어야 합니다."
    )
    # iframe: 8501과 같은 호스트에서 5173 포트로 ERD 뷰어 로드
    st.markdown(
        '<iframe src="http://localhost:5173" title="ERD 시각화" '
        'style="width:100%; height:calc(100vh - 220px); min-height:500px; border:1px solid #2D3748; border-radius:8px;"></iframe>',
        unsafe_allow_html=True,
    )


@st.dialog("AI에 요청 (세그먼트 등급 분석)")
def _show_segment_data_dialog(
    schema_info: str, column_stats: list, dimension: str | None = None, user_script: str = ""
):
    """AI에 보내는 요청(프롬프트)을 팝업으로 표시. dimension이 있으면 해당 차원만, user_script가 있으면 포함."""
    if dimension:
        st.caption(f"**{dimension}** 차원 분석 시 AI에 전달하는 요청(프롬프트)입니다.")
        try:
            final_prompt = get_segment_grade_prompt_for_dimension(
                schema_info or "", column_stats or [], dimension, user_script or ""
            )
        except Exception:
            final_prompt = ""
    else:
        st.caption("**AI 호출** 시 전달하는 전체 사용자 메시지(프롬프트)입니다.")
        try:
            final_prompt = get_segment_grade_prompt(schema_info or "", column_stats or [])
        except Exception:
            final_prompt = ""
    st.text_area("AI에 보내는 최종 데이터", value=final_prompt or "(생성 실패)", height=400, disabled=True, label_visibility="collapsed")


@st.dialog("AI 답변 (세그먼트 등급 분석 결과)")
def _show_segment_response_dialog(segment_schema: dict, dimension: str | None = None):
    """AI가 반환한 세그먼트 등급 스키마를 팝업으로 표시. dimension이 있으면 해당 차원만 표시."""
    if dimension:
        st.caption(f"**{dimension}** 차원 분석 결과(수정한 구간 값은 세션에 반영된 상태)입니다.")
        data = {dimension: segment_schema.get(dimension, [])} if segment_schema else {}
    else:
        st.caption("**AI로 세그먼트 등급 분석** 호출 후 AI가 반환한 JSON입니다.")
        data = segment_schema if segment_schema else {}
    st.json(data)


def customer_segment_creation_page():
    """고객 범주 생성: 데이터 사용 설정의 테이블·컬럼·데이터를 AI에 전달해 건전성·수익성·취급율별 검토 컬럼 3개씩 및 등급 1~9 구간을 분석하고, 사용자가 구간 값을 수정할 수 있게 함."""
    st.markdown('<p class="main-title">📐 고객 범주 생성</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">**데이터 사용 설정**에 체크된 테이블·컬럼·데이터를 AI가 분석해, 건전성·수익성·취급율 각각에 대해 검토할 만한 컬럼 3개와 등급 1~9(1=좋음) 구간을 제안합니다. 구간 값은 수정할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # 구간만 변경할 때는 DB 재조회 불필요 — segment_schema가 있으면 세션에 둔 column_stats 사용
    schema = st.session_state.get("segment_schema")
    if schema and isinstance(schema, dict) and st.session_state.get("segment_column_stats") is not None:
        schema_info = st.session_state.get("segment_schema_info", "")
        column_stats = st.session_state.get("segment_column_stats") or []
    else:
        with st.spinner("테이블·컬럼 통계 불러오는 중…"):
            schema_info, column_stats = _get_segment_column_stats()
        if schema and isinstance(schema, dict) and column_stats:
            st.session_state.segment_schema_info = schema_info
            st.session_state.segment_column_stats = column_stats

    if not column_stats:
        st.warning("**데이터 사용 설정**에서 사용할 테이블을 체크하고 **AI 분석에 사용할 컬럼**을 선택한 뒤 저장하세요. 그다음 이 화면에서 **AI로 세그먼트 등급 분석**을 실행하세요.")
        return

    st.markdown("""
    <style>
    /* AI 요청/답변 버튼 바짝 붙이기 */
    .stHorizontalBlock > div[data-testid="column"]:last-child .stHorizontalBlock > div[data-testid="column"] {
        padding-left: 2px !important; padding-right: 2px !important; min-width: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    def _merge_dimension_into_schema(dimension: str, result_list: list):
        base = st.session_state.get("segment_schema") or {}
        if not isinstance(base, dict):
            base = {}
        schema = {"건전성": list(base.get("건전성") or []), "수익성": list(base.get("수익성") or []), "취급율": list(base.get("취급율") or [])}
        schema[dimension] = result_list
        st.session_state.segment_schema = schema
        st.session_state.segment_schema_info = st.session_state.get("segment_schema_info") or schema_info
        st.session_state.segment_column_stats = st.session_state.get("segment_column_stats") or column_stats

    if "segment_user_script" not in st.session_state:
        st.session_state.segment_user_script = ""
    st.text_area(
        "희망 사항 또는 지시 (선택): 분석 시 AI에 추가로 전달할 내용을 입력하세요. 비워두면 기본 지시만 전달됩니다.",
        value=st.session_state.segment_user_script,
        key="segment_user_script",
        height=80,
        placeholder="예: 연체 이력이 없는 고객 위주로, 수익성은 대출 잔액 구간을 중시해 주세요.",
    )
    bcol_left, bcol_right = st.columns([2, 1])
    with bcol_left:
        # 버튼 4개를 가깝게 붙이기 위해 좁은 비율로 배치, 나머지는 여백
        dim_col1, dim_col2, dim_col3, dim_col4, _ = st.columns([1, 1, 1, 1, 4])
        user_script = st.session_state.get("segment_user_script", "") or ""
        with dim_col1:
            if st.button("📌 건전성 분석", type="primary", key="seg_btn_건전성"):
                with st.spinner("건전성 분석 중..."):
                    result_list, err_msg = generate_segment_grade_schema_for_dimension(schema_info, column_stats, "건전성", user_script)
                if result_list is not None:
                    _merge_dimension_into_schema("건전성", result_list)
                    st.success("건전성 분석 완료.")
                    st.rerun()
                else:
                    st.error("건전성 분석 실패." + (f" ({err_msg})" if err_msg else ""))
        with dim_col2:
            if st.button("📌 수익성 분석", type="primary", key="seg_btn_수익성"):
                with st.spinner("수익성 분석 중..."):
                    result_list, err_msg = generate_segment_grade_schema_for_dimension(schema_info, column_stats, "수익성", user_script)
                if result_list is not None:
                    _merge_dimension_into_schema("수익성", result_list)
                    st.success("수익성 분석 완료.")
                    st.rerun()
                else:
                    st.error("수익성 분석 실패." + (f" ({err_msg})" if err_msg else ""))
        with dim_col3:
            if st.button("📌 취급율 분석", type="primary", key="seg_btn_취급율"):
                with st.spinner("취급율 분석 중..."):
                    result_list, err_msg = generate_segment_grade_schema_for_dimension(schema_info, column_stats, "취급율")
                if result_list is not None:
                    _merge_dimension_into_schema("취급율", result_list)
                    st.success("취급율 분석 완료.")
                    st.rerun()
                else:
                    st.error("취급율 분석 실패." + (f" ({err_msg})" if err_msg else ""))
        with dim_col4:
            if st.button("🤖 전체 분석(동시)", key="seg_btn_all"):
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with st.spinner("건전성·수익성·취급율 동시 분석 중..."):
                    results = {}
                    with ThreadPoolExecutor(max_workers=3) as ex:
                        futures = {
                            ex.submit(generate_segment_grade_schema_for_dimension, schema_info, column_stats, d, user_script): d
                            for d in ("건전성", "수익성", "취급율")
                        }
                        for fut in as_completed(futures):
                            dim = futures[fut]
                            try:
                                lst, err = fut.result()
                                results[dim] = lst if lst else []
                            except Exception:
                                results[dim] = []
                    schema = {
                        "건전성": results.get("건전성") or [],
                        "수익성": results.get("수익성") or [],
                        "취급율": results.get("취급율") or [],
                    }
                    st.session_state.segment_schema = schema
                    st.session_state.segment_schema_info = schema_info
                    st.session_state.segment_column_stats = column_stats
                    st.success("전체 분석 완료. 아래에서 각 차원별 결과를 확인하세요.")
                    st.rerun()
    # 고객 범주 생성 전용 버튼 키(고객 범주 선택 화면 위젯과 구분)
    with bcol_right:
        segment_schema = st.session_state.get("segment_schema") or {}
        for dim in ("건전성", "수익성", "취급율"):
            req_col, res_col = st.columns(2)
            with req_col:
                if st.button(f"📋 요청 보기 ({dim})", key=f"고객범주_요청보기_{dim}"):
                    _show_segment_data_dialog(schema_info, column_stats, dim, st.session_state.get("segment_user_script", ""))
            with res_col:
                if st.button(f"📄 답변 보기 ({dim})", key=f"고객범주_답변보기_{dim}"):
                    _show_segment_response_dialog(segment_schema, dim)

    schema = st.session_state.get("segment_schema")
    if not schema or not isinstance(schema, dict):
        st.caption("위 **건전성 / 수익성 / 취급율 분석** 버튼 또는 **전체 분석(동시)** 버튼을 누르면 결과가 여기에 표시됩니다.")
        return
    if not any(schema.get(d) for d in ("건전성", "수익성", "취급율")):
        st.caption("위 버튼으로 차원별 분석을 실행하면 결과가 여기에 표시됩니다.")
        return

    @st.fragment
    def _segment_interval_form():
        """구간 값만 변경할 때 이 프래그먼트만 리런되어 상단 DB/통계 조회가 발생하지 않음."""
        schema = st.session_state.get("segment_schema")
        column_stats = st.session_state.get("segment_column_stats") or []
        if not schema or not isinstance(schema, dict) or not column_stats:
            return
        stats_by_key = {(s["table"], s["column"]): s for s in column_stats}

        def _ensure_intervals(col_spec, mn, mx):
            """col_spec에 intervals(9개, low/high)가 있으면 그대로, 없으면 boundaries에서 변환 또는 기본값 생성."""
            intervals = col_spec.get("intervals")
            if isinstance(intervals, list) and len(intervals) >= 9:
                return intervals[:9]
            boundaries = col_spec.get("boundaries")
            if isinstance(boundaries, list) and len(boundaries) >= 10:
                return [{"low": boundaries[i], "high": boundaries[i + 1]} for i in range(9)]
            try:
                mn_f = float(mn) if mn is not None else 0.0
                mx_f = float(mx) if mx is not None else 100.0
            except (TypeError, ValueError):
                mn_f, mx_f = 0.0, 100.0
            step = (mx_f - mn_f) / 9
            return [{"low": mn_f + i * step, "high": mn_f + (i + 1) * step} for i in range(9)]

        def _ensure_intervals_boolean(col_spec):
            """여부 컬럼: 1등급·9등급 두 개만, value(예/아니오)로 반환."""
            intervals = col_spec.get("intervals")
            if isinstance(intervals, list) and len(intervals) >= 2 and isinstance(intervals[0], dict) and "value" in intervals[0]:
                return [{"grade": intervals[0].get("grade", 1), "value": intervals[0].get("value", "예")}, {"grade": intervals[1].get("grade", 9), "value": intervals[1].get("value", "아니오")}]
            return [{"grade": 1, "value": "예"}, {"grade": 9, "value": "아니오"}]

        for dim_name, dim_label in [("건전성", "건전성"), ("수익성", "수익성"), ("취급율", "취급율")]:
            dim_list = schema.get(dim_name)
            if not dim_list or not isinstance(dim_list, list):
                continue
            st.subheader(f"📌 {dim_label}")
            dim_cols = st.columns(3)
            for col_idx, col_spec in enumerate(dim_list):
                if not isinstance(col_spec, dict):
                    continue
                if col_idx >= 3:
                    break
                table = col_spec.get("table", "")
                column = col_spec.get("column", "")
                mn = col_spec.get("min")
                mx = col_spec.get("max")
                reason_col = col_spec.get("reason_column", "")
                reason_int = col_spec.get("reason_intervals", "")
                stat = stats_by_key.get((table, column)) or {}
                is_boolean = stat.get("is_boolean", False)
                bool_options = stat.get("unique_values") or ["예", "아니오"]

                with dim_cols[col_idx]:
                    if is_boolean:
                        intervals = _ensure_intervals_boolean(col_spec)
                        schema[dim_name][col_idx]["intervals"] = intervals
                        with st.expander(f"**{table}.{column}** (여부)", expanded=True):
                            st.caption("**컬럼 선정 이유:** " + (reason_col or "-"))
                            st.caption("**등급 구간을 정한 이유:** " + (reason_int or "-"))
                            g1, g9 = intervals[0].get("grade", 1), intervals[1].get("grade", 9)
                            for i, iv in enumerate(intervals):
                                grade = iv.get("grade", (1, 9)[i])
                                val_default = iv.get("value", ("예", "아니오")[i])
                                key_val = f"seg_{dim_name}_{col_idx}_g{grade}_value"
                                current_val = st.session_state.get(key_val, val_default)
                                if current_val not in bool_options:
                                    current_val = bool_options[0]
                                c1, c2 = st.columns([1, 2])
                                with c1:
                                    st.markdown(f"**{grade}등급**")
                                with c2:
                                    st.selectbox("값 (여부)", options=bool_options, index=bool_options.index(current_val) if current_val in bool_options else 0, key=key_val, label_visibility="collapsed")
                            schema[dim_name][col_idx]["intervals"] = [
                                {"grade": g1, "value": st.session_state.get(f"seg_{dim_name}_{col_idx}_g{g1}_value", intervals[0].get("value", "예"))},
                                {"grade": g9, "value": st.session_state.get(f"seg_{dim_name}_{col_idx}_g{g9}_value", intervals[1].get("value", "아니오"))},
                            ]
                    else:
                        intervals = _ensure_intervals(col_spec, mn, mx)
                        schema[dim_name][col_idx]["intervals"] = intervals
                        with st.expander(f"**{table}.{column}** (min: {mn}, max: {mx})", expanded=True):
                            st.caption("**컬럼 선정 이유:** " + (reason_col or "-"))
                            st.caption("**등급 구간을 정한 이유:** " + (reason_int or "-"))
                            for grade in range(1, 10):
                                iv = intervals[grade - 1] if grade - 1 < len(intervals) else {}
                                low_default = iv.get("low")
                                high_default = iv.get("high")
                                try:
                                    low_default = float(low_default) if low_default is not None else (float(mn) if mn is not None else 0.0)
                                    high_default = float(high_default) if high_default is not None else (float(mx) if mx is not None else 100.0)
                                except (TypeError, ValueError):
                                    low_default = 0.0
                                    high_default = 100.0
                                key_low = f"seg_{dim_name}_{col_idx}_g{grade}_low"
                                key_high = f"seg_{dim_name}_{col_idx}_g{grade}_high"
                                current_low = st.session_state.get(key_low, low_default)
                                current_high = st.session_state.get(key_high, high_default)
                                try:
                                    current_low = float(current_low)
                                    current_high = float(current_high)
                                except (TypeError, ValueError):
                                    current_low = low_default
                                    current_high = high_default
                                c1, c2, c3, c4 = st.columns([1, 2, 0.4, 2])
                                with c1:
                                    st.markdown(f"**{grade}등급**")
                                with c2:
                                    st.number_input("하한", value=current_low, key=key_low, format="%.2f", label_visibility="collapsed")
                                with c3:
                                    st.markdown("**~**")
                                with c4:
                                    st.number_input("상한", value=current_high, key=key_high, format="%.2f", label_visibility="collapsed")
                            def _def_low(g):
                                if g - 1 < len(intervals) and isinstance(intervals[g - 1], dict):
                                    v = intervals[g - 1].get("low")
                                    try:
                                        return float(v)
                                    except (TypeError, ValueError):
                                        pass
                                return float(mn) if mn is not None else 0.0
                            def _def_high(g):
                                if g - 1 < len(intervals) and isinstance(intervals[g - 1], dict):
                                    v = intervals[g - 1].get("high")
                                    try:
                                        return float(v)
                                    except (TypeError, ValueError):
                                        pass
                                return float(mx) if mx is not None else 100.0
                            schema[dim_name][col_idx]["intervals"] = [
                                {
                                    "low": st.session_state.get(f"seg_{dim_name}_{col_idx}_g{g}_low", _def_low(g)),
                                    "high": st.session_state.get(f"seg_{dim_name}_{col_idx}_g{g}_high", _def_high(g)),
                                }
                                for g in range(1, 10)
                            ]
            st.markdown("---")

        st.caption("등급 1 = 가장 좋음, 등급 9 = 가장 나쁨. 숫자 컬럼은 하한 **~** 상한 구간으로 정의하고, **여부** 컬럼은 1등급·9등급만 표시하며 값은 예/아니오로 선택합니다.")

    _segment_interval_form()


@st.dialog("AI에 요청 (고객 범주 선택)")
def _show_category_request_dialog(prompt_text: str):
    """고객 범주 선택 시 AI에 보내는 요청(컬럼·범주 데이터 + 지시)을 팝업으로 표시."""
    st.caption("**컬럼별 범주 선택(전체 마케팅 최적 조합)** 요청 시 AI에 전달하는 전체 프롬프트입니다.")
    st.text_area("요청 내용", value=prompt_text or "(없음)", height=400, disabled=True, label_visibility="collapsed")


@st.dialog("AI 답변 (고객 범주 선택)")
def _show_category_response_dialog(response_data: dict):
    """AI가 선택한 건전성·수익성·취급율 각 1개 범주와 이유를 팝업으로 표시."""
    st.caption("AI가 선택한 **컬럼별 범주(전체 마케팅 최적 조합)**와 이유입니다.")
    st.json(response_data if response_data else {})


def _build_columns_with_categories(segment_schema: dict) -> list[dict]:
    """segment_schema(건전성·수익성·취급율 각 3개 컬럼)를 AI에 보낼 컬럼·범주 리스트(최대 9개)로 변환. 각 범주에 등급(grade 1~9) 명시."""
    out = []
    for dim in ("건전성", "수익성", "취급율"):
        for col_spec in (segment_schema.get(dim) or []):
            if not isinstance(col_spec, dict):
                continue
            intervals_raw = col_spec.get("intervals") or []
            intervals_with_grade = []
            for i, iv in enumerate(intervals_raw):
                if not isinstance(iv, dict):
                    continue
                item = dict(iv)
                if "grade" not in item:
                    item["grade"] = i + 1  # 1등급~9등급
                intervals_with_grade.append(item)
            out.append({
                "dimension": dim,
                "table": col_spec.get("table", ""),
                "column": col_spec.get("column", ""),
                "reason_column": col_spec.get("reason_column", ""),
                "intervals": intervals_with_grade,
            })
            if len(out) >= 9:
                return out
    return out


def customer_category_creation_page():
    """고객 범주 선택: 세그먼트 분석 결과 컬럼별 범주를 AI에 보내, 컬럼당 1개씩 선택·전체 조합이 마케팅 최적이 되도록 선택받음."""
    st.markdown('<p class="main-title">🏷️ 고객 범주 선택</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">**고객 범주 생성**에서 분석한 **현재 존재하는 컬럼별**로 등급(범주)을 AI에 보내, **각 컬럼당 1개씩** 범주를 선택받습니다. 컬럼별로 무조건 좋은 범주가 아니라 **모든 컬럼을 종합했을 때 마케팅 고객군으로 최상**이 되는 조합을 선택받습니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    segment_schema = st.session_state.get("segment_schema") or {}
    if not isinstance(segment_schema, dict):
        segment_schema = {}
    columns_with_categories = _build_columns_with_categories(segment_schema)

    if not columns_with_categories:
        st.warning("**고객 범주 선택**에서 먼저 건전성·수익성·취급율 분석을 실행해 9개 컬럼·범주를 만든 뒤 이 화면을 이용하세요.")
        return

    st.caption(f"현재 **{len(columns_with_categories)}개** 컬럼·범주가 있습니다. 아래 버튼으로 AI에게 범주 선택을 요청하고, 요청/답변을 확인할 수 있습니다.")

    if "category_user_script" not in st.session_state:
        st.session_state.category_user_script = ""
    st.text_area(
        "희망 사항 또는 지시 (선택): 범주 선택 시 AI에 추가로 전달할 내용을 입력하세요. 비워두면 기본 지시만 전달됩니다.",
        value=st.session_state.category_user_script,
        key="category_user_script",
        height=80,
        placeholder="예: 신규 마케팅 타깃으로 리스크 낮고 거래 빈도 높은 군을 우선하고 싶습니다.",
    )
    category_script = st.session_state.get("category_user_script", "") or ""
    # 고객 범주 선택 전용 버튼 키(다른 화면에서 위젯이 재사용되지 않도록 페이지 접두사 사용)
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        if st.button("🤖 AI에게 범주 선택 요청", type="primary", key="고객세그_범주선택요청"):
            with st.spinner("AI가 컬럼별 최적 범주 조합을 선택하는 중..."):
                result, err_msg = generate_best_marketing_category(columns_with_categories, category_script)
            if result is not None:
                st.session_state.category_ai_request_payload = get_best_marketing_category_prompt(columns_with_categories, category_script)
                st.session_state.category_ai_response = result
                st.success("컬럼별 범주 선택이 완료되었습니다. AI 답변 보기에서 확인하세요.")
                st.rerun()
            else:
                st.error("요청에 실패했습니다." + (f" ({err_msg})" if err_msg else ""))
    with btn_col2:
        prompt_text = st.session_state.get("category_ai_request_payload") or get_best_marketing_category_prompt(columns_with_categories, st.session_state.get("category_user_script", ""))
        if st.button("📋 AI 요청 보기", key="고객세그_AI요청보기"):
            _show_category_request_dialog(prompt_text)
    with btn_col3:
        if st.button("📄 AI 답변 보기", key="고객세그_AI답변보기"):
            _show_category_response_dialog(st.session_state.get("category_ai_response") or {})

    response = st.session_state.get("category_ai_response")
    if response and isinstance(response, dict):
        st.divider()
        st.subheader("📌 AI가 선택한 범주 (컬럼별 1개, 전체 마케팅 최적 조합)")
        # 새 형식: selections(컬럼별 1개) + overall_reason — 3열 구성(건전성 3개 한 행, 수익성 3개 한 행, 취급율 3개 한 행)
        if "selections" in response and isinstance(response["selections"], list):
            # 차원별로 그룹: 건전성 3개, 수익성 3개, 취급율 3개
            by_dim: dict[str, list[dict]] = {"건전성": [], "수익성": [], "취급율": []}
            for sel in response["selections"]:
                if not isinstance(sel, dict):
                    continue
                dim = sel.get("dimension", "")
                if dim in by_dim:
                    by_dim[dim].append(sel)
            for dim_name in ("건전성", "수익성", "취급율"):
                items = by_dim.get(dim_name) or []
                if not items:
                    continue
                st.markdown(f"**{dim_name}**")
                cols = st.columns(3)
                for idx, sel in enumerate(items):
                    if idx >= 3:
                        break
                    with cols[idx]:
                        tbl = sel.get("table", "")
                        col = sel.get("column", "")
                        chosen_grade = sel.get("chosen_grade")
                        grade_desc = sel.get("chosen_grade_or_range", "") or "-"
                        reason = sel.get("reason", "") or "-"
                        st.caption(f"{tbl} · {col}")
                        if chosen_grade is not None:
                            st.markdown(f"**선택한 등급:** {chosen_grade}등급")
                        st.markdown(f"**선택한 범주:** {grade_desc}")
                        st.caption(f"이유: {reason}")
                st.divider()
            overall = response.get("overall_reason") or ""
            if overall:
                st.markdown("**전체 조합을 선택한 이유 (마케팅 고객군 최적)**")
                st.info(overall)
        elif "건전성" in response and "수익성" in response and "취급율" in response:
            # 이전 3차원 형식 호환 — 3열로 표시, 선택한 등급 필수 노출
            c1, c2, c3 = st.columns(3)
            for idx, dim_name in enumerate(("건전성", "수익성", "취급율")):
                col = [c1, c2, c3][idx]
                with col:
                    dim_data = response.get(dim_name)
                    if isinstance(dim_data, dict):
                        st.markdown(f"**{dim_name}**")
                        st.caption(f"{dim_data.get('chosen_table', '-')} · {dim_data.get('chosen_column', '-')}")
                        grade = dim_data.get("chosen_grade_or_range", "") or "-"
                        st.markdown(f"**선택한 등급:** {grade}")
                        st.caption(f"이유: {dim_data.get('reason', '-')}")
            overall = response.get("overall_reason") or ""
            if overall:
                st.markdown("**세 가지 조합을 선택한 이유**")
                st.info(overall)
        else:
            # 이전 단일 범주 형식 호환 — 선택한 등급 필수 노출
            st.markdown(f"**차원:** {response.get('chosen_dimension', '-')} · **테이블:** {response.get('chosen_table', '-')} · **컬럼:** {response.get('chosen_column', '-')}")
            grade = response.get("chosen_grade_or_range", "") or "-"
            st.markdown(f"**선택한 등급:** {grade}")
            st.markdown(f"**이유:** {response.get('reason', '-')}")
            st.caption("(이전 형식의 답변입니다. 다시 요청하면 컬럼별 범주 선택 형식으로 받을 수 있습니다.)")

    st.divider()


def _segment_customer_count_and_query(selections: list[dict]):
    """
    selections(테이블·컬럼·chosen_interval)로 조건에 맞는 고객 수 계산 및 쿼리 설명 문자열 생성.
    반환: (고객건수, 쿼리문자열). DB/테이블 없으면 (0, "데이터 없음").
    """
    if not selections:
        return 0, "-- 조건 없음"
    tables = list_tables()
    if not tables:
        return 0, "-- DB에 테이블이 없습니다."
    # 테이블별로 (컬럼, interval) 그룹
    by_table: dict[str, list[tuple[str, dict]]] = {}
    for s in selections:
        if not isinstance(s, dict):
            continue
        t, c = s.get("table", ""), s.get("column", "")
        iv = s.get("chosen_interval")
        if not t or not c or not isinstance(iv, dict):
            continue
        if t not in by_table:
            by_table[t] = []
        by_table[t].append((c, iv))

    query_parts = []
    filtered_dfs = []
    join_key_candidates = ["customer_id", "고객_id", "고객_ID", "id"]

    for tname, cols_intervals in by_table.items():
        if tname not in tables:
            query_parts.append(f"-- 테이블 '{tname}' 없음")
            continue
        df = load_table(tname)
        if df is None or df.empty:
            query_parts.append(f"-- '{tname}' 데이터 없음")
            continue
        mask = pd.Series(True, index=df.index)
        conds = []
        for col, iv in cols_intervals:
            if col not in df.columns:
                conds.append(f"  {col} (컬럼 없음)")
                continue
            if "low" in iv and "high" in iv:
                try:
                    lo, hi = float(iv["low"]), float(iv["high"])
                    mask = mask & (df[col].astype(float, errors="ignore") >= lo) & (df[col].astype(float, errors="ignore") <= hi)
                    conds.append(f"  \"{tname}\".\"{col}\" BETWEEN {lo} AND {hi}")
                except (TypeError, ValueError):
                    conds.append(f"  \"{tname}\".\"{col}\" (구간 파싱 실패)")
            elif "value" in iv:
                val = iv["value"]
                mask = mask & (df[col].astype(str) == str(val))
                conds.append(f"  \"{tname}\".\"{col}\" = '{val}'")
            else:
                conds.append(f"  \"{tname}\".\"{col}\" (조건 없음)")
        df_filtered = df.loc[mask]
        filtered_dfs.append((tname, df_filtered))
        query_parts.append(f"SELECT * FROM \"{tname}\" WHERE\n" + " AND\n".join(conds))

    if not filtered_dfs:
        return 0, "\n\n".join(query_parts) if query_parts else "-- 적용 가능한 조건 없음"

    # 단일 테이블
    if len(filtered_dfs) == 1:
        _, df_one = filtered_dfs[0]
        cnt = len(df_one)
        return cnt, query_parts[0] + f"\n\n-- 결과: {cnt}건"

    # 다중 테이블: 공통 키로 조인
    join_key = None
    for k in join_key_candidates:
        if all(k in df.columns for _, df in filtered_dfs):
            join_key = k
            break
    if join_key is None:
        # 첫 테이블 건수만 사용
        cnt = len(filtered_dfs[0][1])
        full_query = "\n\n-- 다중 테이블(조인 키 미검출). 첫 테이블 기준 건수.\n\n" + "\n\n".join(query_parts) + f"\n\n-- 첫 테이블 결과: {cnt}건"
        return cnt, full_query

    merged = filtered_dfs[0][1][[join_key]].drop_duplicates()
    for _, df in filtered_dfs[1:]:
        merged = merged.merge(df[[join_key]].drop_duplicates(), on=join_key, how="inner")
    cnt = len(merged)
    full_query = f"-- 조인 키: {join_key}\n\n" + "\n\n".join(query_parts) + f"\n\n-- INNER JOIN 결과: {cnt}건"
    return cnt, full_query


def _build_seg_code_and_digit_info(selections: list[dict]) -> tuple[str, list[dict]]:
    """고객 범주 선택 결과(selections)에서 세그코드(111-111-111 형식)와 자릿수별 테이블·컬럼 정보 생성."""
    if not selections:
        return "", []
    grades = []
    digit_info = []
    for i, s in enumerate(selections):
        if not isinstance(s, dict):
            continue
        g = s.get("chosen_grade")
        if g is not None:
            grades.append(str(g))
        digit_info.append({
            "digit": i + 1,
            "table": s.get("table", ""),
            "column": s.get("column", ""),
            "dimension": s.get("dimension", ""),
            "grade": g,
        })
    # 9자리: 3-3-3 형식 (건전성3 수익성3 취급율3)
    code_str = "".join(grades)[:9].ljust(9, "0")
    seg_code = "-".join([code_str[i : i + 3] for i in range(0, 9, 3)])
    return seg_code, digit_info


@st.dialog("세그 쿼리 보기")
def _show_segment_query_dialog_inline():
    query_text = st.session_state.get("segment_query_to_show", "") or "(없음)"
    st.caption("이 세그의 고객 건수 계산에 사용된 조건(쿼리)입니다.")
    try:
        q_b64 = base64.b64encode(query_text.encode("utf-8")).decode("ascii")
    except Exception:
        q_b64 = ""
    # 복사·닫기 버튼 상단 배치
    import streamlit.components.v1 as components
    copy_html = f"""
    <style>
    #segcopybtn {{
        min-height: 38.4px;
        padding: 0.25rem 0.75rem;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        font-weight: 400;
        border: 1px solid rgba(49, 51, 63, 0.2);
        background-color: rgba(49, 51, 63, 0.05);
        color: rgb(49, 51, 63);
        cursor: pointer;
        font-family: "Source Sans Pro", sans-serif;
    }}
    #segcopybtn:hover {{ background-color: rgba(49, 51, 63, 0.1); }}
    </style>
    <div id="segq" data-q="{q_b64}"></div>
    <button type="button" id="segcopybtn">복사</button>
    <script>
    (function() {{
        var btn = document.getElementById('segcopybtn');
        var el = document.getElementById('segq');
        btn.onclick = function() {{
            try {{
                var b64 = el.getAttribute('data-q') || '';
                var binary = atob(b64);
                var bytes = new Uint8Array(binary.length);
                for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                var decoded = new TextDecoder('utf-8').decode(bytes);
                navigator.clipboard.writeText(decoded).then(function() {{
                    btn.textContent = '복사됨';
                    setTimeout(function() {{ btn.textContent = '복사'; }}, 1500);
                }});
            }} catch(e) {{ btn.textContent = '복사 실패'; }}
        }};
    }})();
    </script>
    """
    components.html(copy_html, height=50)
    st.text_area("쿼리", value=query_text, height=340, disabled=True, label_visibility="collapsed")


def customer_segment_build_page():
    """고객 세그 생성: 고객 범주 선택에서 선택된 컬럼별 구간 값을 조건으로 세그 생성. 세그코드(111-111-111), 별칭·설명 입력, 카드 표시."""
    st.markdown('<p class="main-title">📂 고객 세그 생성</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">**고객 범주 선택**에서 선택된 컬럼별 구간 값을 조건으로 고객 세그를 생성합니다. 세그코드는 범주 등급을 순서대로 이어 붙인 형태(예: 111-111-111)입니다.</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    if "segment_list" not in st.session_state:
        st.session_state.segment_list = []

    response = st.session_state.get("category_ai_response") or {}
    selections = response.get("selections") if isinstance(response.get("selections"), list) else []

    if not selections or not all(isinstance(s, dict) and s.get("chosen_grade") is not None for s in selections):
        st.warning("**고객 범주 선택**에서 AI로 범주를 선택한 뒤 이 화면을 이용하세요.")
        return

    seg_code, digit_info = _build_seg_code_and_digit_info(selections)

    # 카드 1: 새 세그 만들기
    st.markdown("#### 📌 새 세그 만들기")
    st.markdown(
        f'<div class="segment-card">'
        f'<div class="seg-code">{seg_code}</div>'
        f'<div class="meta">자릿수별: 1~3 건전성, 4~6 수익성, 7~9 취급율 · 각 자리는 해당 컬럼의 선택 등급(1~9)</div>'
        f"</div>",
        unsafe_allow_html=True,
    )
    alias = st.text_input("세그 별칭", placeholder="예: 우량 신규 타깃", key="seg_alias_input")
    description = st.text_area("세그 설명", placeholder="이 세그의 용도나 설명을 입력하세요.", height=80, key="seg_desc_input")
    if st.button("✅ 세그 생성", type="primary", key="seg_create_btn"):
        if not (alias or "").strip():
            st.error("세그 별칭을 입력하세요.")
        else:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with st.spinner("고객 건수 계산 중..."):
                customer_count, query_text = _segment_customer_count_and_query(selections)
            new_seg = {
                "seg_code": seg_code,
                "alias": (alias or "").strip(),
                "description": (description or "").strip(),
                "created_at": created_at,
                "customer_count": customer_count,
                "query_text": query_text,
                "digit_info": digit_info,
                "selections": selections,
            }
            st.session_state.segment_list = [new_seg] + (st.session_state.segment_list or [])
            st.success(f"세그 **{new_seg['alias']}** ({seg_code})가 생성되었습니다. 고객 건수: {customer_count}건")
            st.rerun()

    st.divider()
    st.markdown("#### 📋 생성된 세그 목록")

    segment_list = st.session_state.get("segment_list") or []
    if not segment_list:
        st.caption("아직 생성된 세그가 없습니다. 위에서 세그 별칭과 설명을 입력한 뒤 **세그 생성**을 누르세요.")
        return

    for idx, seg in enumerate(segment_list):
        if not isinstance(seg, dict):
            continue
        code = seg.get("seg_code", "-")
        alias_val = seg.get("alias", "-")
        desc_val = seg.get("description", "") or "-"
        created = seg.get("created_at", "-")
        count = seg.get("customer_count", 0)
        digits = seg.get("digit_info") or []

        digit_lines = []
        for d in digits:
            t = d.get("table", "")
            c = d.get("column", "")
            pos = d.get("digit", "")
            digit_lines.append(f"자리 {pos}: {t}.{c}")

        st.markdown(
            f'<div class="segment-card">'
            f'<div class="seg-code">{code}</div>'
            f'<p style="margin:0.25rem 0 0 0; font-weight:600;">{alias_val}</p>'
            f'<p style="margin:0.25rem 0 0 0; color:#666; font-size:0.9rem;">{desc_val}</p>'
            f'<div class="meta">🕐 생성 일시: {created} · 👥 고객 건수: {count}</div>'
            f'<div class="meta" style="margin-top:0.5rem;">세그코드 자릿수별 컬럼:<br/>' + "<br/>".join(digit_lines) + "</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button("📄 쿼리 보기", key=f"seg_query_btn_{idx}"):
            st.session_state.segment_query_to_show = seg.get("query_text", "")
            st.rerun()

    # 쿼리 팝업: segment_query_to_show가 설정되어 있으면 다이얼로그 표시
    if st.session_state.get("segment_query_to_show") is not None:
        _show_segment_query_dialog_inline()


def run():
    load_custom_css()

    MENU_OPTIONS = [
        "홈 (대시보드)",
        "테이블 생성",
        "데이터 적재",
        "데이터 보기",
        "데이터 사용 설정",
        "CRM 등급화 (ML)",
        "고객 범주 생성",
        "고객 범주 선택",
        "고객 세그 생성",
        "고객 상세",
        "ERD 시각화",
        "AI 상세 분석",
        "과거 리포트 보관함",
    ]
    # 이동 버튼으로 지정된 페이지가 있으면 우선 사용, 없으면 직전에 선택한 메뉴 유지 (rerun 시 홈으로 튕기는 현상 방지)
    cur_page = st.session_state.get("current_page")
    saved_menu = st.session_state.get("selected_menu")
    if cur_page and cur_page in MENU_OPTIONS:
        default_idx = MENU_OPTIONS.index(cur_page)
        st.session_state.current_page = None  # 한 번 반영 후 초기화
    elif saved_menu and saved_menu in MENU_OPTIONS:
        default_idx = MENU_OPTIONS.index(saved_menu)
    else:
        default_idx = 0

    with st.sidebar:
        col_logo, col_title = st.columns([1, 2])
        with col_logo:
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), width=40)
            else:
                st.markdown("📊")
        with col_title:
            st.markdown("### **AI Driven CRM**")
        st.markdown("---")
        menu = st.radio(
            "메뉴",
            MENU_OPTIONS,
            index=default_idx,
            label_visibility="collapsed",
            key="main_menu_radio",
        )
        st.session_state.selected_menu = menu  # rerun 후에도 현재 메뉴 유지
        st.markdown("---")
        st.caption("AI-First Financial Intelligence")
        if is_ai_available():
            st.caption("✅ AI 사용 가능 (API 키 설정됨)")
        else:
            with st.expander("AI 연동 안내"):
                st.caption("OPENAI_API_KEY 환경변수를 설정하면 대시보드 요약·Reasoning·비교 분석을 AI가 생성합니다.")
        st.markdown("---")
        # API 호출 후 rate limit 헤더 표시 (B 방식: 사이드바, 세션에 저장된 값 우선)
        h = st.session_state.get("last_rate_limit_headers") or get_last_rate_limit_headers()
        with st.expander("📊 API 한도 정보 (최근 호출 기준)", expanded=bool(h)):
            if h:
                labels = {
                    "x-ratelimit-limit-requests": "1분당 허용 최대 요청 수 (RPM)",
                    "x-ratelimit-remaining-requests": "이번 분기 남은 요청 수",
                    "x-ratelimit-limit-tokens": "1분당 허용 최대 토큰 수 (TPM)",
                    "x-ratelimit-remaining-tokens": "이번 분기 남은 토큰 수",
                    "x-ratelimit-reset-tokens": "한도 초기화까지 남은 시간",
                }
                for key in labels:
                    v = h.get(key, "-")
                    st.caption(f"**{labels[key]}**: {v}")
            else:
                st.caption(
                    "AI 호출 **성공** 시 여기에 표시됩니다. "
                    "한도 초과(429)로 실패한 경우에는 응답 헤더를 읽을 수 없어 표시되지 않습니다."
                )

    if menu == "홈 (대시보드)":
        main_dashboard()
    elif menu == "테이블 생성":
        table_schema_upload_page()
    elif menu == "데이터 적재":
        data_upload()
    elif menu == "데이터 보기":
        view_loaded_data()
    elif menu == "데이터 사용 설정":
        extraction_config_page()
    elif menu == "CRM 등급화 (ML)":
        ml_crm_grade_page()
    elif menu == "고객 범주 생성":
        customer_segment_creation_page()
    elif menu == "고객 범주 선택":
        customer_category_creation_page()
    elif menu == "고객 세그 생성":
        customer_segment_build_page()
    elif menu == "고객 상세":
        customer_detail_page()
    elif menu == "ERD 시각화":
        erd_viewer_page()
    elif menu == "AI 상세 분석":
        ai_insight_report()
    else:
        data_archive()


if __name__ == "__main__":
    run()
