# -*- coding: utf-8 -*-
"""
AI 분석 연동 (OpenAI 호환 API)
API 키가 없거나 실패 시 None/데모용 반환
"""

import os
from pathlib import Path

# 이 파일과 같은 폴더의 .env 로드 (실행 경로와 무관하게 API 키 적용)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

# API 호출 후 마지막 응답의 rate limit 헤더 (사이드바 표시용)
_last_rate_limit_headers = {}
_RATE_HEADERS = (
    "x-ratelimit-limit-requests",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-tokens",
)


def _save_rate_limit_headers(raw_or_headers):
    """응답 헤더에서 rate limit 5종 추출해 저장 (대소문자 무시). raw 응답 또는 headers 객체 모두 허용."""
    global _last_rate_limit_headers
    headers = None
    if raw_or_headers is not None:
        if hasattr(raw_or_headers, "headers"):
            headers = getattr(raw_or_headers, "headers", None)
        if headers is None and hasattr(raw_or_headers, "response"):
            resp = getattr(raw_or_headers, "response", None)
            if resp is not None:
                headers = getattr(resp, "headers", None)
        if headers is None and (hasattr(raw_or_headers, "items") or hasattr(raw_or_headers, "keys")):
            headers = raw_or_headers
    if headers is None:
        return
    try:
        items = headers.items() if hasattr(headers, "items") else []
        h_lower = {str(k).strip().lower(): (v.decode() if isinstance(v, bytes) else v) for k, v in items}
    except Exception:
        h_lower = {}
    out = {}
    for key in _RATE_HEADERS:
        for k, v in h_lower.items():
            k_norm = k.replace("_", "-")
            key_norm = key.replace("_", "-")
            if k == key or k_norm == key_norm:
                out[key] = v
                break
    # 한 건이라도 있으면 갱신 (빈 dict로 덮어쓰지 않음)
    if out:
        _last_rate_limit_headers = out


def get_last_rate_limit_headers():
    """마지막 AI 호출 응답의 rate limit 헤더 5종 반환 (사이드바 표시용)."""
    return dict(_last_rate_limit_headers)


def _client():
    try:
        from openai import OpenAI
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            return None
        return OpenAI(api_key=key)
    except Exception:
        return None


def generate_dashboard_summary(data_context: dict) -> str | None:
    """대시보드용 한 문단 AI 요약. data_context에는 건수, 컬럼명, 요약 통계 등."""
    client = _client()
    if not client:
        return None
    try:
        import json
        prompt = f"""당신은 금융 CRM의 AI 애널리스트입니다. 아래 고객 데이터 요약을 보고, 
한 문단(2~3문장)으로 비즈니스 상태를 요약해 주세요. 
마케팅 성공 가능 그룹, 상환 안정성, 수익성 관련 인사이트를 자연어로 작성하세요.
데이터 요약:
{json.dumps(data_context, ensure_ascii=False, indent=2)}

요약 (한국어):"""
        raw = client.chat.completions.with_raw_response.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        _save_rate_limit_headers(raw)
        r = raw.parse()
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return None


def generate_reasoning(data_context: dict, scores: dict) -> str | None:
    """스코어링 결과에 대한 이유(Reasoning)를 불릿 포인트로 생성."""
    client = _client()
    if not client:
        return None
    try:
        import json
        prompt = f"""금융 CRM 스코어링 결과에 대한 이유(Reasoning)를 작성해 주세요.
데이터 요약: {json.dumps(data_context, ensure_ascii=False)}
현재 스코어: {json.dumps(scores, ensure_ascii=False)}

다음 형식으로 4~6개 불릿 포인트만 출력하세요. 각 줄은 "• 내용" 형태로.
- 안정성/연체/상환 관련
- 수익성/투자/대출 관련  
- 마케팅/세그먼트/프로필 관련
- 이탈/응답률 등 리스크 관련
한국어로 작성하고, 숫자나 등급을 근거로 언급하세요."""
        raw = client.chat.completions.with_raw_response.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        _save_rate_limit_headers(raw)
        r = raw.parse()
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return None


def generate_comparison(summary_a: str, summary_b: str) -> str | None:
    """두 분석 결과의 차이점을 AI가 설명."""
    client = _client()
    if not client:
        return None
    try:
        prompt = f"""다음은 금융 CRM에서 저장한 두 시점의 분석 요약입니다.
분석 A: {summary_a}
분석 B: {summary_b}

분석 A 대비 B의 차이점을 2~4문장으로 요약해 주세요. 수익성, 안정성, 마케팅 성공률 등 지표 변화를 자연어로 설명하세요. 한국어로 작성."""
        raw = client.chat.completions.with_raw_response.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
        )
        _save_rate_limit_headers(raw)
        r = raw.parse()
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return None


def generate_segment_interpretations(segment_summary: list[dict]) -> tuple[list[dict] | None, str | None]:
    """
    ML로 산출된 고객 범주별 요약을 받아, 생성형 AI가 각 범주의 해석을 한국어로 작성.
    segment_summary: [ {"name": "VIP", "segment_cd": "01", "count": 120, ... }, ... ]
    반환: ( [ {"segment_name": "VIP", "interpretation": "..."}, ... ], None ) 성공 시,
          ( None, 마크다운전체문자열 ) 구조화 실패 시 화면 표시용으로 마크다운 반환,
          ( None, None ) API 실패 시.
    """
    client = _client()
    if not client or not segment_summary:
        return None, None
    try:
        import json
        import re
        names = [s.get("name", "") for s in segment_summary]
        prompt = f"""당신은 금융 CRM의 고객 분석가입니다. 아래는 점수와 등급으로 나눈 고객 범주별 요약입니다.
각 범주가 어떤 고객군인지, 마케팅·리스크·수익성 관점에서 2~3문장으로 해석해 주세요.
반드시 다음 JSON 배열만 출력하세요 (다른 글 없이). 배열 각 항목: "segment_name" (범주명, 아래 name과 동일하게), "interpretation" (해석 문단, 한국어).

범주별 요약:
{json.dumps(segment_summary, ensure_ascii=False, indent=2)}

출력 (JSON 배열만):
[{{"segment_name": "VIP", "interpretation": "해석문장..."}}, ...]"""
        raw = client.chat.completions.with_raw_response.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        _save_rate_limit_headers(raw)
        r = raw.parse()
        text = (r.choices[0].message.content or "").strip()
        if not text:
            return None, None
        # JSON 배열 추출 (```json ... ``` 또는 순수 배열)
        json_match = re.search(r"\[[\s\S]*\]", text)
        if json_match:
            arr = json.loads(json_match.group())
            if isinstance(arr, list) and len(arr) >= 1:
                return arr, None
        # 구조화 실패 시 마크다운으로라도 반환 (화면 표시용)
        return None, text
    except Exception:
        return None, None


def _classify_api_error(exc: Exception) -> str:
    """API 예외를 사용자용 한글 메시지로 분류."""
    msg = str(exc).lower()
    if "insufficient_quota" in msg or "quota" in msg and "exceeded" in msg or "you exceeded your current quota" in msg or "billing" in msg:
        return "크레딧이 부족하거나 결제 한도를 초과했습니다. OpenAI Billing(https://platform.openai.com/account/billing)에서 결제 수단·사용량을 확인해 주세요."
    if "invalid" in msg and "api key" in msg or "incorrect api key" in msg or "invalid_api_key" in msg or "authentication" in msg:
        return "API 키가 올바르지 않습니다. .env의 OPENAI_API_KEY를 확인해 주세요."
    if "rate" in msg or "limit" in msg:
        return "요청 한도 초과입니다. 잠시 후 다시 시도해 주세요."
    if "connection" in msg or "timeout" in msg or "network" in msg:
        return "네트워크 연결을 확인해 주세요."
    return f"API 오류: {str(exc)[:200]}"


def _to_json_safe(obj):
    """numpy/pandas 타입(int64, float64 등)을 JSON 직렬화 가능한 기본 타입으로 변환."""
    try:
        import numpy as np
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj) if obj == obj else None  # NaN -> None
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except Exception:
        pass
    tname = type(obj).__name__
    if tname in ("int64", "int32", "Int64", "Int32"):
        return int(obj)
    if tname in ("float64", "float32", "Float64", "Float32"):
        try:
            f = float(obj)
            return f if f == f else None
        except Exception:
            return None
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    return obj


def _is_rate_limit_error(exc: Exception) -> bool:
    """요청 한도(rate limit) 관련 오류인지 확인."""
    msg = str(exc).lower()
    return "rate" in msg or "limit" in msg or "quota" in msg or "429" in msg


def generate_customer_scores(customer_summaries: list[dict], schema_info: str = "", user_instruction: str = "") -> tuple[list[dict] | None, str | None]:
    """
    DB에서 수집한 고객별 요약 데이터를 바탕으로, 고객별 수익성·건전성·리스크 점수(0~100)를 AI가 산출.
    한도 초과 시 최대 3회 재시도(5초·10초·15초 대기).
    user_instruction: 사용자가 AI에게 전달할 추가 요청 문구 (선택).
    반환: (점수 리스트 또는 None, 오류 메시지 또는 None)
    """
    client = _client()
    if not client:
        return None, "API 키가 설정되지 않았습니다. .env에 OPENAI_API_KEY를 넣어 주세요."
    if not customer_summaries:
        return None, None
    import json
    import time
    safe_summaries = _to_json_safe(customer_summaries)
    extra = f"\n\n**사용자 추가 요청:** {user_instruction.strip()}\n" if (user_instruction and user_instruction.strip()) else ""
    prompt = f"""당신은 금융 CRM의 리스크·수익 분석가입니다. 아래는 DB에서 수집한 고객별 요약 데이터입니다.
스키마/테이블 정보: {schema_info or "없음"}

고객별 데이터 (JSON 배열):
{json.dumps(safe_summaries, ensure_ascii=False, indent=2)}
{extra}
각 고객에 대해 다음 세 가지 점수를 0~100 정수로 산출해 주세요.
- **수익성(Profitability)**: 대출 잔액·이자 수익·상품 가입 등으로 기대 수익이 높을수록 높은 점수
- **건전성(Soundness)**: DSR·신용점수·연체 이력·상환 안정성 등이 양호할수록 높은 점수
- **리스크(Risk)**: 연체·부실 가능성·상담 키워드(연체·파산 등) 등 위험 요인이 있을수록 높은 점수 (위험할수록 높음)

반드시 아래 JSON 배열 형태로만 응답하세요. 다른 설명 없이 JSON만 출력하세요.
[ {{ "고객_ID": 원본_ID, "고객명": "원본이름", "수익성": 0~100, "건전성": 0~100, "리스크": 0~100 }}, ... ]"""
    last_error = None
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(5 * attempt)  # 5초, 10초 대기
            raw = client.chat.completions.with_raw_response.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
            )
            _save_rate_limit_headers(raw)
            r = raw.parse()
            content = (r.choices[0].message.content or "").strip()
            break
        except Exception as e:
            last_error = e
            if not _is_rate_limit_error(e) or attempt >= 2:
                return None, _classify_api_error(e)
    else:
        return None, _classify_api_error(last_error)
    try:
        # JSON 블록만 추출 (```json ... ``` 제거)
        if "```" in content:
            for part in content.split("```"):
                part = part.strip()
                if part.lower().startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    content = part
                    break
        # [ ... ] 구간만 추출 (앞뒤 설명 제거)
        start = content.find("[")
        if start >= 0:
            depth = 0
            end = -1
            for i in range(start, len(content)):
                if content[i] == "[":
                    depth += 1
                elif content[i] == "]":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end >= start:
                content = content[start : end + 1]
        # trailing comma 등 흔한 오류 보정
        content = content.replace(",]", "]").replace(", }", "}").replace(",}", "}")
        arr = None
        try:
            arr = json.loads(content)
        except json.JSONDecodeError:
            # 잘린 응답 복구 시도: 마지막 완성된 }, 뒤까지 자르고 ] 붙이기
            last_pair = content.rfind("},")
            if last_pair > 0:
                try:
                    arr = json.loads(content[: last_pair + 1] + "]")
                except json.JSONDecodeError:
                    pass
        if not arr or not isinstance(arr, list):
            return None, "AI 응답이 잘렸거나 JSON 형식이 올바르지 않습니다. 고객 수가 많으면 일부만 처리되니, 다시 추출하거나 고객 수를 줄여 보세요."
        ai_by_id = {}
        for item in arr:
            if not isinstance(item, dict):
                continue
            gid = item.get("고객_ID", item.get("고객_ID"))
            name = item.get("고객명", item.get("고객명", ""))
            p = max(0, min(100, int(item.get("수익성", 50))))
            s = max(0, min(100, int(item.get("건전성", 50))))
            r = max(0, min(100, int(item.get("리스크", 50))))
            ai_by_id[str(gid)] = {"고객_ID": gid, "고객명": str(name), "수익성": p, "건전성": s, "리스크": r}
        # 입력 순서 유지, AI가 반환하지 않은 고객은 50점으로 채움
        out = []
        for c in customer_summaries:
            cid = c.get("고객_ID")
            cname = c.get("고객명", "")
            if str(cid) in ai_by_id:
                rec = ai_by_id[str(cid)].copy()
                rec["고객_ID"] = cid
                rec["고객명"] = str(cname)
                out.append(rec)
            else:
                out.append({"고객_ID": cid, "고객명": str(cname), "수익성": 50, "건전성": 50, "리스크": 50})
        return out, None
    except Exception as e:
        return None, _classify_api_error(e)


def generate_extract_reasoning(
    customer_summaries: list[dict],
    schema_info: str,
    criteria: dict,
    user_instruction: str = "",
) -> str | None:
    """
    고객 추출 시 AI가 수익성·건전성·리스크 점수 산출에 어떤 항목을 중점적으로 반영했는지 사유·설명 생성.
    criteria: {"수익성 이상": N, "건전성 이상": N, "리스크 이하": N}
    user_instruction: 사용자가 AI에게 전달한 추가 요청 문구 (선택).
    한도 초과 시 최대 3회 재시도(5초·10초·15초 대기) 수행.
    """
    client = _client()
    if not client or not customer_summaries:
        return None
    import json
    import time
    extra = f"\n**사용자 추가 요청:** {user_instruction.strip()}\n" if (user_instruction and user_instruction.strip()) else ""
    prompt = f"""당신은 금융 CRM의 AI 분석가입니다. 방금 DB에서 수집한 고객별 요약 데이터를 바탕으로 수익성·건전성·리스크 점수를 산출했습니다.

DB 스키마: {schema_info or "없음"}

고객별 요약 데이터(일부, 상위 5건만 예시):
{json.dumps(_to_json_safe(customer_summaries[:5]), ensure_ascii=False, indent=2)}

사용자 추출 조건: 수익성 ≥ {criteria.get('수익성 이상', 70)}, 건전성 ≥ {criteria.get('건전성 이상', 75)}, 리스크 ≤ {criteria.get('리스크 이하', 35)}
{extra}
**한국어로** 아래 형식에 맞춰 **상세히** 작성해 주세요. 참고한 컬럼은 **테이블당 최대 5개**만 선택해 설명하세요.

- **수익성:** (1) 어떤 테이블의 어떤 컬럼을 사용했는지 나열 (2) 해당 컬럼에서 참고한 정보(수치·내용) (3) 그 정보를 어떤 방법으로 해석·분석해 수익성 점수에 반영했는지
- **건전성:** (1) 어떤 테이블의 어떤 컬럼을 사용했는지 나열 (2) 해당 컬럼에서 참고한 정보 (3) 그 정보를 어떤 방법으로 분석해 건전성 점수에 반영했는지
- **리스크:** (1) 어떤 테이블의 어떤 컬럼을 사용했는지 나열 (2) 해당 컬럼에서 참고한 정보 (3) 그 정보를 어떤 방법으로 분석해 리스크 점수에 반영했는지"""
    last_error = None
    for attempt in range(3):  # 최대 3회 (첫 시도 + 재시도 2회)
        try:
            if attempt > 0:
                time.sleep(5 * attempt)  # 5초, 10초 대기
            raw = client.chat.completions.with_raw_response.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            _save_rate_limit_headers(raw)
            r = raw.parse()
            return (r.choices[0].message.content or "").strip()
        except Exception as e:
            last_error = e
            if not _is_rate_limit_error(e) or attempt >= 2:
                return None
    return None


def get_segment_grade_prompt(schema_info: str, column_stats: list[dict]) -> str:
    """
    AI 세그먼트 등급 분석 호출 시 실제로 AI에 보내는 최종 프롬프트(단일 트랜잭션의 전체 사용자 메시지)를 반환.
    generate_segment_grade_schema와 동일한 문자열을 사용하며, 팝업 등에서 그대로 노출할 때 사용.
    """
    import json
    stats_str = json.dumps(_to_json_safe((column_stats or [])[:50]), ensure_ascii=False, indent=2)
    return f"""당신은 금융 CRM의 세그먼트 분석가입니다. 아래는 DB 스키마와 컬럼별 데이터 min/max입니다.

DB 스키마: {schema_info or "없음"}

컬럼별 통계 (테이블, 컬럼, min, max, dtype):
{stats_str}

다음 세 가지 항목(건전성, 수익성, 취급율)에 대해, **각 항목당 3개**의 컬럼을 선정해 주세요.
- **건전성**: 신용·연체·상환 안정성 등과 관련해 검토할 만한 컬럼 3개
- **수익성**: 대출 잔액·이자·상품 가입 등 수익과 관련해 검토할 만한 컬럼 3개
- **취급율**: 상담·가입·이용률 등 취급 실적과 관련해 검토할 만한 컬럼 3개

각 컬럼에 대해 **등급 1~9**(1=가장 좋음, 9=가장 나쁨)에 해당하는 **구간 9개**를 정해 주세요.
- 각 등급은 **low(하한)** 와 **high(상한)** 로 표현합니다. 예: 1등급은 1부터 2까지 → low: 1, high: 2 / 2등급은 3부터 4까지 → low: 3, high: 4
- **구간은 서로 겹치지 않게** 하세요. 1등급의 high와 2등급의 low는 같게, 2등급의 high와 3등급의 low는 같게 하는 식으로 연속되게 하거나, 최소한 N등급의 high와 (N+1)등급의 low가 같아서 겹치지 않도록 하세요.
- (예: 부양가족 수가 적을수록 좋다면 1등급 low=0 high=1, 2등급 low=1 high=2, 3등급 low=2 high=3, ... / 건전성 점수는 높을수록 좋다면 1등급 low=90 high=100, 2등급 low=80 high=89, ...)
- **min/max가 없거나 값이 두 개뿐인 컬럼(여부 등)** 은 구간 대신 **1등급·9등급만** 사용하고, 각각 **"grade": 1, "value": "좋은값"** / **"grade": 9, "value": "나쁜값"** 형태로 씁니다. **1등급과 9등급의 value는 반드시 서로 달라야 합니다.** (예: 연체 여부 컬럼이면 1등급 value="N", 9등급 value="Y" 처럼 좋은 쪽·나쁜 쪽을 구분해서 배정)
- **컬럼을 선정한 이유**(reason_column), **해당 구간으로 등급을 정한 이유**(reason_intervals)를 한국어로 한 줄씩 작성해 주세요.

반드시 아래 JSON 형태로만 응답하세요. 다른 설명 없이 JSON만 출력하세요.
{{
  "건전성": [
    {{ "table": "테이블명", "column": "컬럼명", "min": 숫자, "max": 숫자, "reason_column": "선정 이유", "reason_intervals": "구간/등급 정한 이유", "intervals": [ {{ "low": 숫자, "high": 숫자 }}, {{ "low": 숫자, "high": 숫자 }}, ...총 9개 (1등급~9등급) ] }},
    ...총 3개
  ],
  "수익성": [ ...총 3개, 같은 구조 ],
  "취급율": [ ...총 3개, 같은 구조 ]
}}
위 컬럼명·테이블명은 반드시 column_stats에 있는 값만 사용하세요."""


_DIMENSION_DESCRIPTIONS = {
    "건전성": "신용·연체·상환 안정성 등과 관련해 검토할 만한 컬럼 3개",
    "수익성": "대출 잔액·이자·상품 가입 등 수익과 관련해 검토할 만한 컬럼 3개",
    "취급율": "상담·가입·이용률 등 취급 실적과 관련해 검토할 만한 컬럼 3개",
}


def get_segment_grade_prompt_for_dimension(
    schema_info: str, column_stats: list[dict], dimension: str, user_script: str = ""
) -> str:
    """한 차원(건전성/수익성/취급율)만 요청하는 짧은 프롬프트. user_script가 있으면 AI 분석 지시에 추가."""
    import json
    stats_str = json.dumps(_to_json_safe((column_stats or [])[:50]), ensure_ascii=False, indent=2)
    desc = _DIMENSION_DESCRIPTIONS.get(dimension, dimension)
    user_block = ""
    if (user_script or "").strip():
        user_block = f"""
**사용자 희망 사항 (아래 분석 시 반드시 반영해 주세요):**
{user_script.strip()}

"""
    return f"""당신은 금융 CRM의 세그먼트 분석가입니다. 아래는 DB 스키마와 컬럼별 데이터 min/max입니다.

DB 스키마: {schema_info or "없음"}

컬럼별 통계 (테이블, 컬럼, min, max, dtype):
{stats_str}
{user_block}**{dimension}** 항목에 대해, 검토할 만한 컬럼 **3개**를 선정하고, 각 컬럼별 **등급 1~9**(1=가장 좋음, 9=가장 나쁨) 구간을 정해 주세요.
- {desc}
- 각 등급은 **low(하한)** 와 **high(상한)** 로 표현. 구간은 서로 겹치지 않게 연속되게 하세요.
- min/max가 없거나 값이 두 개뿐인 컬럼(여부)은 1등급·9등급만 사용하고, "grade": 1 "value": "좋은값" / "grade": 9 "value": "나쁜값" 형태로 하며, **1등급과 9등급 value는 반드시 서로 달라야 합니다.**
- reason_column, reason_intervals를 한국어로 한 줄씩 작성하세요.

아래 JSON 형태로만 응답하세요. 다른 설명 없이 JSON만 출력하세요.
{{ "{dimension}": [
  {{ "table": "테이블명", "column": "컬럼명", "min": 숫자 또는 null, "max": 숫자 또는 null, "reason_column": "선정 이유", "reason_intervals": "구간 이유", "intervals": [ {{ "low": 숫자, "high": 숫자 }}, ... 9개 ] 또는 여부면 [ {{ "grade": 1, "value": "값" }}, {{ "grade": 9, "value": "값" }} ] }},
  ...총 3개
] }}
위 컬럼명·테이블명은 반드시 column_stats에 있는 값만 사용하세요."""


def _normalize_dimension_result(dimension: str, data: dict, column_stats: list[dict]) -> list | None:
    """한 차원 파싱 결과를 정규화(intervals 변환·여부 보정)."""
    import json
    raw_list = data.get(dimension)
    if not isinstance(raw_list, list) or len(raw_list) < 1:
        return None
    for col_spec in raw_list:
        if not isinstance(col_spec, dict):
            continue
        ivs = col_spec.get("intervals") or []
        if len(ivs) >= 9 or (len(ivs) == 2 and isinstance(ivs[0], dict) and ("low" in ivs[0] or "value" in ivs[0])):
            continue
        boundaries = col_spec.get("boundaries")
        if isinstance(boundaries, list) and len(boundaries) >= 10:
            col_spec["intervals"] = [{"low": boundaries[i], "high": boundaries[i + 1]} for i in range(9)]
        elif len(ivs) < 9:
            mn, mx = col_spec.get("min"), col_spec.get("max")
            try:
                mn = float(mn) if mn is not None else 0.0
                mx = float(mx) if mx is not None else 100.0
            except (TypeError, ValueError):
                mn, mx = 0.0, 100.0
            step = (mx - mn) / 9
            col_spec["intervals"] = [{"low": mn + i * step, "high": mn + (i + 1) * step} for i in range(9)]
    stats_lookup = {(s.get("table"), s.get("column")): s for s in (column_stats or []) if s.get("table") and s.get("column")}
    for col_spec in raw_list:
        if not isinstance(col_spec, dict):
            continue
        ivs = col_spec.get("intervals") or []
        if len(ivs) != 2 or "value" not in (ivs[0] or {}) or "value" not in (ivs[1] or {}):
            continue
        v1, v9 = ivs[0].get("value"), ivs[1].get("value")
        if v1 != v9:
            continue
        table, column = col_spec.get("table"), col_spec.get("column")
        stat = stats_lookup.get((table, column)) or {}
        options = stat.get("unique_values") or (["N", "Y"] if ("yn" in str(column).lower() or "여부" in str(column)) else ["예", "아니오"])
        other = next((x for x in options if x != v1), None)
        if other is not None:
            ivs[1]["value"] = other
    return raw_list


def generate_segment_grade_schema_for_dimension(
    schema_info: str, column_stats: list[dict], dimension: str, user_script: str = ""
) -> tuple[list | None, str | None]:
    """
    한 차원(건전성/수익성/취급율)만 AI에 요청. user_script가 있으면 프롬프트에 포함.
    반환: (해당 차원 리스트 3개 또는 None, 오류 메시지 또는 None).
    """
    client = _client()
    if not client or not column_stats:
        if not column_stats:
            return None, "분석할 컬럼 통계가 없습니다."
        return None, "AI 클라이언트를 사용할 수 없습니다. API 키를 확인하세요."
    if dimension not in ("건전성", "수익성", "취급율"):
        return None, f"지원하지 않는 차원입니다: {dimension}"
    import json
    import time
    prompt = get_segment_grade_prompt_for_dimension(schema_info, column_stats, dimension, user_script or "")
    last_error = None
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(5 * attempt)
            raw = client.chat.completions.with_raw_response.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
            )
            _save_rate_limit_headers(raw)
            r = raw.parse()
            content = (r.choices[0].message.content or "").strip()
            if "```" in content:
                for part in content.split("```"):
                    part = part.strip()
                    if part.lower().startswith("json"):
                        part = part[4:].strip()
                    if part.strip().startswith("{"):
                        content = part
                        break
            start = content.find("{")
            if start >= 0:
                depth = 1
                end = -1
                for i in range(start + 1, len(content)):
                    if content[i] == "{":
                        depth += 1
                    elif content[i] == "}":
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                if end >= start:
                    content = content[start : end + 1]
            data = json.loads(content)
            if not isinstance(data, dict) or dimension not in data:
                return None, f"AI 응답에 '{dimension}' 키가 없거나 형식이 맞지 않습니다."
            result_list = _normalize_dimension_result(dimension, data, column_stats)
            if result_list is None:
                return None, f"AI 응답의 '{dimension}' 리스트를 파싱할 수 없습니다."
            return result_list, None
        except json.JSONDecodeError as e:
            last_error = e
            if attempt >= 2:
                return None, f"AI 응답 JSON 파싱 실패: {e}"
        except Exception as e:
            last_error = e
            if not _is_rate_limit_error(e) or attempt >= 2:
                err_msg = getattr(e, "message", None) or str(e)
                return None, f"API 오류: {err_msg}"
    return None, (f"재시도 후 실패: {last_error}" if last_error else "알 수 없는 오류")


def generate_segment_grade_schema(schema_info: str, column_stats: list[dict]) -> tuple[dict | None, str | None]:
    """
    조건 추출 설정의 테이블·컬럼과 데이터(min/max)를 바탕으로,
    건전성·수익성·취급율 각각에 대해 검토할 만한 컬럼 3개씩 선정하고,
    각 컬럼별 등급 1~9(1=좋음)에 해당하는 구간(low~high) 9개를 AI가 분석해 반환.
    반환: (결과 dict 또는 None, 실패 시 오류 메시지 또는 None)
    """
    client = _client()
    if not client or not column_stats:
        if not column_stats:
            return None, "분석할 컬럼 통계가 없습니다."
        return None, "AI 클라이언트를 사용할 수 없습니다. API 키를 확인하세요."
    import json
    import time
    prompt = get_segment_grade_prompt(schema_info, column_stats)
    last_error = None
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(5 * attempt)
            raw = client.chat.completions.with_raw_response.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500,
            )
            _save_rate_limit_headers(raw)
            r = raw.parse()
            content = (r.choices[0].message.content or "").strip()
            if "```" in content:
                for part in content.split("```"):
                    part = part.strip()
                    if part.lower().startswith("json"):
                        part = part[4:].strip()
                    if part.strip().startswith("{"):
                        content = part
                        break
            start = content.find("{")
            if start >= 0:
                depth = 1
                end = -1
                for i in range(start + 1, len(content)):
                    if content[i] == "{":
                        depth += 1
                    elif content[i] == "}":
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                if end >= start:
                    content = content[start : end + 1]
            data = json.loads(content)
            if not isinstance(data, dict) or "건전성" not in data or "수익성" not in data or "취급율" not in data:
                return None, "AI 응답에 건전성·수익성·취급율 키가 없거나 형식이 맞지 않습니다."
            # 기존 boundaries(10개) 형식이면 intervals(9개, low/high)로 변환
            for dim in ("건전성", "수익성", "취급율"):
                for col_spec in data.get(dim) or []:
                    if not isinstance(col_spec, dict):
                        continue
                    if "intervals" in col_spec and isinstance(col_spec["intervals"], list) and len(col_spec["intervals"]) >= 9:
                        continue
                    boundaries = col_spec.get("boundaries")
                    if isinstance(boundaries, list) and len(boundaries) >= 10:
                        col_spec["intervals"] = [
                            {"low": boundaries[i], "high": boundaries[i + 1]}
                            for i in range(9)
                        ]
                    elif "intervals" not in col_spec or not col_spec["intervals"]:
                        mn = col_spec.get("min", 0)
                        mx = col_spec.get("max", 100)
                        try:
                            mn, mx = float(mn), float(mx)
                        except (TypeError, ValueError):
                            mn, mx = 0.0, 100.0
                        step = (mx - mn) / 9
                        col_spec["intervals"] = [{"low": mn + i * step, "high": mn + (i + 1) * step} for i in range(9)]
            # 여부 컬럼: 1등급·9등급 value가 같으면 9등급을 나머지 값으로 자동 보정
            stats_lookup = {(s.get("table"), s.get("column")): s for s in (column_stats or []) if s.get("table") and s.get("column")}
            for dim in ("건전성", "수익성", "취급율"):
                for col_spec in data.get(dim) or []:
                    if not isinstance(col_spec, dict):
                        continue
                    ivs = col_spec.get("intervals") or []
                    if len(ivs) != 2 or not isinstance(ivs[0], dict) or not isinstance(ivs[1], dict):
                        continue
                    if "value" not in ivs[0] or "value" not in ivs[1]:
                        continue
                    v1, v9 = ivs[0].get("value"), ivs[1].get("value")
                    if v1 != v9:
                        continue
                    table, column = col_spec.get("table"), col_spec.get("column")
                    stat = stats_lookup.get((table, column)) or {}
                    options = stat.get("unique_values") or ["N", "Y"] if "yn" in str(column).lower() or "여부" in str(column) else ["예", "아니오"]
                    other = next((x for x in options if x != v1), None)
                    if other is not None:
                        ivs[1]["value"] = other
            return data, None
        except json.JSONDecodeError as e:
            last_error = e
            if attempt >= 2:
                return None, f"AI 응답 JSON 파싱 실패: {e}"
        except Exception as e:
            last_error = e
            if not _is_rate_limit_error(e) or attempt >= 2:
                err_msg = getattr(e, "message", None) or str(e)
                return None, f"API 오류: {err_msg}"
    return None, (f"재시도 후 실패: {last_error}" if last_error else "알 수 없는 오류")


def is_ai_available() -> bool:
    return _client() is not None


def get_best_marketing_category_prompt(
    columns_with_categories: list[dict], user_script: str = ""
) -> str:
    """
    고객 범주 선택: AI에게 보낼 요청(컬럼·범주 데이터 + 지시). user_script가 있으면 분석 지시에 추가.
    columns_with_categories: [ {"dimension": "건전성", "table": str, "column": str, "reason_column": str, "intervals": [...] }, ... ] 최대 9개
    """
    import json
    data_str = json.dumps(_to_json_safe(columns_with_categories), ensure_ascii=False, indent=2)
    n = len(columns_with_categories)
    user_block = ""
    if (user_script or "").strip():
        user_block = f"""
**사용자 희망 사항 (아래 범주 선택 시 반드시 반영해 주세요):**
{user_script.strip()}

"""
    return f"""당신은 금융 CRM의 마케팅 전략가입니다. 아래는 **{n}개 컬럼**과 각 컬럼의 **등급(범주)** 정의입니다. (건전성·수익성·취급율 등) 각 범주(interval)에는 **grade**(1~9)가 붙어 있습니다.

컬럼·범주 데이터:
{data_str}
{user_block}**요청:** 위 **{n}개 컬럼 각각**에 대해, 그 컬럼의 intervals에 있는 범주(등급/구간) 중 **딱 하나씩** 골라 주세요.
- 각 컬럼의 intervals는 **grade**(1등급~9등급), 그리고 **low/high**(숫자 구간) 또는 **value**(여부 값)로 정의되어 있습니다. 위 데이터에 있는 것만 선택하세요.
- **중요:** 컬럼별로 "그 컬럼만 보면 좋은" 범주를 고르는 게 아니라, **모든 컬럼의 선택을 종합했을 때** 하나의 **마케팅 고객군**으로서 **최상의 조합**이 되도록 선택하세요.
- **필수:** 각 selection에는 (1) **chosen_grade**: 선택한 등급 번호(1~9 정수), (2) **chosen_interval**: 위 데이터에서 선택한 그 컬럼의 interval 객체를 **그대로 복사**한 것(low/high 또는 grade+value 포함), (3) **chosen_grade_or_range**: 사람이 보기 좋은 설명(예: "1등급", "2등급 (0~100만)", "1등급 value N")을 반드시 넣으세요.

아래 JSON 형태로만 응답하세요. 다른 설명 없이 JSON만 출력하세요.
- "selections": 배열은 위 컬럼 순서와 **동일한 순서**로, 각 컬럼에 대해 선택한 범주 1개씩. **chosen_grade**(1~9), **chosen_interval**(위 데이터의 interval 객체 그대로), **chosen_grade_or_range**(설명) 모두 필수.
- "overall_reason": 이 조합 전체가 마케팅 고객군으로 최적인 이유를 2~4문장으로 한국어로 쓰세요.

{{
  "selections": [
    {{
      "table": "해당 컬럼의 테이블명",
      "column": "해당 컬럼명",
      "dimension": "건전성|수익성|취급율",
      "chosen_grade": 1,
      "chosen_interval": {{ "grade": 1, "low": 0, "high": 100 }},
      "chosen_grade_or_range": "1등급 (0~100)",
      "reason": "이 컬럼에서 이 범주를 선택한 이유 (1~2문장)"
    }}
  ],
  "overall_reason": "모든 컬럼의 선택을 합쳤을 때 이 조합이 마케팅 효과가 최적인 이유 (2~4문장)"
}}

chosen_interval은 반드시 위 컬럼·범주 데이터에 있는 해당 컬럼의 intervals 중 하나와 **동일한 형태**(grade, low/high 또는 grade, value)로 넣으세요. selections 배열 길이는 {n}개여야 합니다."""


def generate_best_marketing_category(
    columns_with_categories: list[dict], user_script: str = ""
) -> tuple[dict | None, str | None]:
    """
    컬럼·범주 데이터를 AI에 보내, 컬럼별로 1개씩 범주를 선택받음. user_script가 있으면 프롬프트에 포함.
    반환: ( { "selections": [ ... ], "overall_reason": "..." } 또는 None, 오류 메시지 또는 None )
    """
    client = _client()
    if not client or not columns_with_categories:
        if not columns_with_categories:
            return None, "컬럼·범주 데이터가 없습니다. 고객 범주 선택에서 먼저 분석을 실행하세요."
        return None, "AI 클라이언트를 사용할 수 없습니다. API 키를 확인하세요."
    import json
    import time
    prompt = get_best_marketing_category_prompt(columns_with_categories, user_script or "")
    last_error = None
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(5 * attempt)
            raw = client.chat.completions.with_raw_response.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            _save_rate_limit_headers(raw)
            r = raw.parse()
            content = (r.choices[0].message.content or "").strip()
            if "```" in content:
                for part in content.split("```"):
                    part = part.strip()
                    if part.lower().startswith("json"):
                        part = part[4:].strip()
                    if part.strip().startswith("{"):
                        content = part
                        break
            start = content.find("{")
            if start >= 0:
                depth = 1
                end = -1
                for i in range(start + 1, len(content)):
                    if content[i] == "{":
                        depth += 1
                    elif content[i] == "}":
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                if end >= start:
                    content = content[start : end + 1]
            data = json.loads(content)
            if not isinstance(data, dict):
                return None, "AI 응답 형식이 올바르지 않습니다."
            # chosen_grade, chosen_interval, chosen_grade_or_range 필수 검증
            selections = data.get("selections") or []
            invalid = []
            for i, s in enumerate(selections):
                if not isinstance(s, dict):
                    invalid.append(i)
                    continue
                g = s.get("chosen_grade")
                interval = s.get("chosen_interval")
                desc = (s.get("chosen_grade_or_range") or "").strip()
                if not (isinstance(g, int) and 1 <= g <= 9):
                    invalid.append(i)
                    continue
                if not isinstance(interval, dict) or not interval:
                    invalid.append(i)
                    continue
                if not desc:
                    invalid.append(i)
            if invalid:
                return None, "AI 응답에 일부 항목의 '선택한 등급(chosen_grade)' 또는 '선택한 범주(chosen_interval)'가 없거나 형식이 맞지 않습니다. 다시 요청해 주세요."
            return data, None
        except json.JSONDecodeError as e:
            last_error = e
            if attempt >= 2:
                return None, f"AI 응답 JSON 파싱 실패: {e}"
        except Exception as e:
            last_error = e
            if not _is_rate_limit_error(e) or attempt >= 2:
                err_msg = getattr(e, "message", None) or str(e)
                return None, f"API 오류: {err_msg}"
    return None, (f"재시도 후 실패: {last_error}" if last_error else "알 수 없는 오류")
