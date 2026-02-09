# -*- coding: utf-8 -*-
"""
적재용 샘플 데이터 생성 (메타 기준: 영문 snake_case 컬럼, 고객번호 키로 조인 가능)
- 고객내역, 대출내역, 상담내역, 심사내역, 신용정보내역, 마이데이터내역
- 각 1000행 이상, 모든 테이블에 customer_id 포함
"""
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

Faker.seed(42)
random.seed(42)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_ROWS = 1_050
fake = Faker("ko_KR")

# 공통: 고객번호 풀 (조인 키)
CUSTOMER_IDS = [f"C{10000 + i}" for i in range(N_ROWS)]


def _date_str(days_ago_min=0, days_ago_max=3650):
    d = fake.date_between(
        start_date=datetime.now() - timedelta(days=days_ago_max),
        end_date=datetime.now() - timedelta(days=days_ago_min),
    )
    return d.strftime("%Y-%m-%d") if d else ""


def _datetime_str(days_ago_max=365):
    dt = fake.date_time_between(
        start_date=datetime.now() - timedelta(days=days_ago_max),
        end_date=datetime.now(),
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


def _numeric(min_val=0, max_val=10000000, decimals=0):
    v = random.uniform(min_val, max_val)
    return round(v, decimals) if decimals else int(v)


# ----- 고객내역 -----
# 인적: 성별, 연령대, 거주지역코드, 주거형태, 거주주택시세, 거주년수, 결혼여부, 부양가족수
# 직장: 직업군분류, 고용형태, 직장명, 사업자번호, 업종코드, 직위, 근속연수
# 소득: 연소득구분, 연소득금액, 건강보험료납부액, 국민연금납부액, 기타소득금액
def generate_customer_detail():
    cols = [
        "customer_id",
        "gender",
        "age_group",
        "residence_region_code",
        "housing_type",
        "residence_market_value",
        "years_of_residence",
        "marriage_yn",
        "dependents_count",
        "occupation_classification",
        "employment_type",
        "employer_name",
        "business_registration_number",
        "industry_code",
        "job_position",
        "tenure_years",
        "annual_income_type",
        "annual_income_amount",
        "health_insurance_premium",
        "national_pension_premium",
        "other_income_amount",
    ]
    rows = []
    for i in range(N_ROWS):
        rows.append({
            "customer_id": CUSTOMER_IDS[i],
            "gender": random.choice(["M", "F"]),
            "age_group": random.choice(["20대", "30대", "40대", "50대", "60대이상"]),
            "residence_region_code": f"R{random.randint(1, 20):02d}",
            "housing_type": random.choice(["자가", "전세", "월세", "기타"]),
            "residence_market_value": _numeric(0, 800000, 0),
            "years_of_residence": _numeric(0, 30, 0),
            "marriage_yn": random.choice(["Y", "N"]),
            "dependents_count": _numeric(0, 6, 0),
            "occupation_classification": random.choice(["전문직", "사무직", "서비스", "자영업", "기타"]),
            "employment_type": random.choice(["정규직", "비정규직", "자영업", "프리랜서", "무직"]),
            "employer_name": fake.company() if random.random() > 0.3 else "",
            "business_registration_number": f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10000, 99999)}" if random.random() > 0.7 else "",
            "industry_code": f"IND{random.randint(1, 50):02d}",
            "job_position": random.choice(["임원", "부장", "과장", "대리", "사원", "기타"]),
            "tenure_years": _numeric(0, 25, 0),
            "annual_income_type": random.choice(["DECLARED", "ESTIMATED"]),  # 신고/추정
            "annual_income_amount": _numeric(2000, 150000, 0),
            "health_insurance_premium": _numeric(50, 2000, 0),
            "national_pension_premium": _numeric(100, 3000, 0),
            "other_income_amount": _numeric(0, 30000, 0),
        })
    return pd.DataFrame(rows, columns=cols)


# ----- 대출내역 -----
# 요청: 신청상품코드, 희망금액, 희망금리, 희망기간, 상환방식, 거치기간설정(월)
# 자금용도: 자금용도대분류, 세부용도내용, 타사대출대환여부, 대환대상기관명, 대환금액
# 담보: 담보유형, 담보물주소, 담보물시세, 설정액, 선순위채권액, 담보평가일자
# 부수: 우대금리적용여부, 프로모션코드, 제휴처코드, 카드발급동시신청여부
def generate_loan_detail():
    cols = [
        "loan_id",
        "customer_id",
        "applied_product_code",
        "desired_amount",
        "desired_interest_rate",
        "desired_term_months",
        "repayment_method",
        "grace_period_months",
        "fund_usage_category",
        "detail_usage_content",
        "other_loan_refinance_yn",
        "refinance_institution_name",
        "refinance_amount",
        "collateral_type",
        "collateral_address",
        "collateral_market_value",
        "collateral_set_amount",
        "senior_debt_amount",
        "collateral_appraisal_date",
        "preferential_rate_yn",
        "promotion_code",
        "partner_code",
        "card_issue_with_application_yn",
    ]
    rows = []
    for i in range(N_ROWS):
        cid = random.choice(CUSTOMER_IDS)
        rows.append({
            "loan_id": f"L{20000 + i}",
            "customer_id": cid,
            "applied_product_code": random.choice(["PL", "HL", "CL", "VL", "BL"]),
            "desired_amount": _numeric(1000, 500000, 0),
            "desired_interest_rate": round(random.uniform(2.0, 12.0), 2),
            "desired_term_months": random.choice([12, 24, 36, 48, 60, 84, 120]),
            "repayment_method": random.choice(["EQUAL_PRINCIPAL", "EQUAL_INSTALLMENT", "BULLET"]),
            "grace_period_months": _numeric(0, 12, 0),
            "fund_usage_category": random.choice(["HOUSING", "CONSUMER", "BUSINESS", "REFINANCE", "OTHER"]),
            "detail_usage_content": fake.sentence()[:80] if random.random() > 0.5 else "",
            "other_loan_refinance_yn": random.choice(["Y", "N"]),
            "refinance_institution_name": fake.company() if random.random() > 0.7 else "",
            "refinance_amount": _numeric(0, 200000, 0) if random.random() > 0.7 else 0,
            "collateral_type": random.choice(["REAL_ESTATE", "CAR", "DEPOSIT", "NONE"]),
            "collateral_address": fake.address()[:100] if random.random() > 0.5 else "",
            "collateral_market_value": _numeric(0, 800000, 0),
            "collateral_set_amount": _numeric(0, 500000, 0),
            "senior_debt_amount": _numeric(0, 300000, 0),
            "collateral_appraisal_date": _date_str(0, 365) if random.random() > 0.4 else "",
            "preferential_rate_yn": random.choice(["Y", "N"]),
            "promotion_code": f"PM{random.randint(1, 99):02d}" if random.random() > 0.5 else "",
            "partner_code": f"PT{random.randint(1, 30):02d}" if random.random() > 0.6 else "",
            "card_issue_with_application_yn": random.choice(["Y", "N"]),
        })
    return pd.DataFrame(rows, columns=cols)


# ----- 상담내역 -----
# 식별자: 상담번호, 고객번호, 상담원사번, 부서코드, 지점코드
# 시간: 상담일자, 상담시작시간, 상담종료시간, 총상담소요시간(초), 대기시간
# 채널: 상담채널구분(전화/방문/앱), 인입경로(광고/검색/추천), 기기정보(OS/모델), IP주소
# 상태: 상담진행상태(완료/진행/예약), 재통화예약일시, 통화품질점수, 상담녹취여부, STT변환여부, 고객감정상태코드
def generate_consultation_detail():
    cols = [
        "consultation_no",
        "customer_id",
        "consultant_emp_no",
        "dept_code",
        "branch_code",
        "consultation_date",
        "consultation_start_time",
        "consultation_end_time",
        "total_consultation_duration_seconds",
        "wait_time_seconds",
        "consultation_channel_type",
        "inbound_path",
        "device_info",
        "ip_address",
        "consultation_status",
        "callback_reservation_datetime",
        "call_quality_score",
        "recording_yn",
        "stt_conversion_yn",
        "customer_emotion_code",
    ]
    rows = []
    for i in range(N_ROWS):
        st = _datetime_str(365)
        dur = _numeric(60, 3600, 0)
        rows.append({
            "consultation_no": f"CS{30000 + i}",
            "customer_id": random.choice(CUSTOMER_IDS),
            "consultant_emp_no": f"E{random.randint(1000, 9999)}",
            "dept_code": f"D{random.randint(1, 20):02d}",
            "branch_code": f"BR{random.randint(1, 100):03d}",
            "consultation_date": st[:10],
            "consultation_start_time": st,
            "consultation_end_time": _datetime_str(0),
            "total_consultation_duration_seconds": dur,
            "wait_time_seconds": _numeric(0, 600, 0),
            "consultation_channel_type": random.choice(["PHONE", "VISIT", "APP"]),
            "inbound_path": random.choice(["AD", "SEARCH", "RECOMMEND"]),
            "device_info": random.choice(["iOS/iPhone14", "Android/Galaxy S23", "Windows/PC", "Web"]),
            "ip_address": fake.ipv4(),
            "consultation_status": random.choice(["COMPLETED", "IN_PROGRESS", "RESERVED"]),
            "callback_reservation_datetime": _datetime_str(30) if random.random() > 0.6 else "",
            "call_quality_score": _numeric(1, 5, 0),
            "recording_yn": random.choice(["Y", "N"]),
            "stt_conversion_yn": random.choice(["Y", "N"]),
            "customer_emotion_code": random.choice(["POSITIVE", "NEUTRAL", "NEGATIVE", "ANGRY"]),
        })
    return pd.DataFrame(rows, columns=cols)


# ----- 심사내역 -----
# 판정: 심사판정코드(승인/거절/보류), 거절사유코드, 거절상세내용, 심사전략코드, 심사역의견
# 최종조건: 최종승인한도, 최종결정금리, 가산금리, 우대금리항목, 월예상상환액, 중도상환수수료율
# 스코어: 내부신용등급, 외부KCB점수, 외부NICE점수, 심사스코어점수, 부도확률(PD)값
# 한도산출: DSR계산값, DTI계산값, LTV계산값, 소득대비부채비율
def generate_review_detail():
    cols = [
        "review_id",
        "customer_id",
        "loan_id",
        "review_judgment_code",
        "rejection_reason_code",
        "rejection_detail",
        "review_strategy_code",
        "reviewer_remark",
        "final_approval_limit",
        "final_interest_rate",
        "add_on_rate",
        "preferential_rate_items",
        "monthly_expected_repayment",
        "early_repayment_fee_rate",
        "internal_credit_grade",
        "external_kcb_score",
        "external_nice_score",
        "review_score",
        "pd_value",
        "dsr_value",
        "dti_value",
        "ltv_value",
        "debt_to_income_ratio",
    ]
    rows = []
    loan_ids = [f"L{20000 + i}" for i in range(N_ROWS)]
    for i in range(N_ROWS):
        cid = random.choice(CUSTOMER_IDS)
        lid = random.choice(loan_ids)
        judgment = random.choice(["APPROVED", "REJECTED", "PENDING"])
        rows.append({
            "review_id": f"RV{40000 + i}",
            "customer_id": cid,
            "loan_id": lid,
            "review_judgment_code": judgment,
            "rejection_reason_code": f"R{random.randint(1, 20):02d}" if judgment == "REJECTED" else "",
            "rejection_detail": fake.sentence()[:100] if judgment == "REJECTED" else "",
            "review_strategy_code": f"ST{random.randint(1, 10):02d}",
            "reviewer_remark": fake.sentence()[:80] if random.random() > 0.5 else "",
            "final_approval_limit": _numeric(0, 500000, 0) if judgment == "APPROVED" else 0,
            "final_interest_rate": round(random.uniform(2.0, 12.0), 2) if judgment == "APPROVED" else 0,
            "add_on_rate": round(random.uniform(0, 2.0), 2),
            "preferential_rate_items": fake.sentence()[:50] if random.random() > 0.6 else "",
            "monthly_expected_repayment": _numeric(50, 5000, 0),
            "early_repayment_fee_rate": round(random.uniform(0, 0.05), 4),
            "internal_credit_grade": random.choice(["A", "B", "C", "D", "E"]),
            "external_kcb_score": _numeric(300, 900, 0),
            "external_nice_score": _numeric(300, 900, 0),
            "review_score": _numeric(300, 900, 0),
            "pd_value": round(random.uniform(0.001, 0.2), 4),
            "dsr_value": round(random.uniform(0.1, 0.5), 2),
            "dti_value": round(random.uniform(0.1, 0.6), 2),
            "ltv_value": round(random.uniform(0.3, 0.9), 2),
            "debt_to_income_ratio": round(random.uniform(0.1, 0.5), 2),
        })
    return pd.DataFrame(rows, columns=cols)


# ----- 신용정보내역 -----
# 부채: 타사대출총건수, 타사대출총잔액, 1금융권대출잔액, 2금융권대출잔액, 대부업이용건수
# 연체: 현재연체여부, 최근3개월연체건수, 최대연체일수, 최근연체해제일, 채무불이행경험여부
# 신용카드: 카드보유개수, 최근6개월카드사용액, 현금서비스잔액, 카드론잔액, 리볼빙사용여부
# 조회: 최근1개월신용조회건수, 최근7일이내조회건수, 다중채무자여부
def generate_credit_info_detail():
    cols = [
        "credit_info_id",
        "customer_id",
        "report_date",
        "other_loan_count",
        "other_loan_total_balance",
        "first_tier_loan_balance",
        "second_tier_loan_balance",
        "loan_shark_count",
        "current_delinquency_yn",
        "delinquency_count_3m",
        "max_delinquency_days",
        "latest_delinquency_clear_date",
        "default_experience_yn",
        "card_count",
        "card_spend_6m",
        "cash_service_balance",
        "card_loan_balance",
        "revolving_yn",
        "inquiry_count_1m",
        "inquiry_count_7d",
        "multi_debtor_yn",
    ]
    rows = []
    for i in range(N_ROWS):
        rows.append({
            "credit_info_id": f"CR{50000 + i}",
            "customer_id": CUSTOMER_IDS[i],
            "report_date": _date_str(0, 365),
            "other_loan_count": _numeric(0, 10, 0),
            "other_loan_total_balance": _numeric(0, 300000, 0),
            "first_tier_loan_balance": _numeric(0, 200000, 0),
            "second_tier_loan_balance": _numeric(0, 100000, 0),
            "loan_shark_count": _numeric(0, 3, 0),
            "current_delinquency_yn": random.choice(["Y", "N"]),
            "delinquency_count_3m": _numeric(0, 5, 0),
            "max_delinquency_days": _numeric(0, 90, 0),
            "latest_delinquency_clear_date": _date_str(0, 365) if random.random() > 0.6 else "",
            "default_experience_yn": random.choice(["Y", "N"]),
            "card_count": _numeric(0, 8, 0),
            "card_spend_6m": _numeric(0, 50000, 0),
            "cash_service_balance": _numeric(0, 10000, 0),
            "card_loan_balance": _numeric(0, 30000, 0),
            "revolving_yn": random.choice(["Y", "N"]),
            "inquiry_count_1m": _numeric(0, 15, 0),
            "inquiry_count_7d": _numeric(0, 5, 0),
            "multi_debtor_yn": random.choice(["Y", "N"]),
        })
    return pd.DataFrame(rows, columns=cols)


# ----- 마이데이터내역 -----
# 자산: 타행예적금잔액, 투자자산규모, 보유보험건수, 월평균보험료, 월평균통신비
# 소비: 주소비업종, 월평균카드소비액, 할부결제비중, 연간해외결제금액
# 행동: 앱최근접속일, 최근7일접속횟수, 상담전페이지체류시간, 마케팅동의여부, 앱푸시수신여부
def generate_my_data_detail():
    cols = [
        "record_id",
        "customer_id",
        "other_bank_deposit_balance",
        "investment_asset_size",
        "insurance_count",
        "monthly_avg_insurance_premium",
        "monthly_avg_communication_expense",
        "main_spending_industry",
        "monthly_avg_card_spend",
        "installment_ratio",
        "annual_overseas_payment_amount",
        "app_last_access_date",
        "access_count_7d",
        "consultation_page_dwell_time_seconds",
        "marketing_consent_yn",
        "app_push_yn",
    ]
    rows = []
    for i in range(N_ROWS):
        rows.append({
            "record_id": f"MD{60000 + i}",
            "customer_id": CUSTOMER_IDS[i],
            "other_bank_deposit_balance": _numeric(0, 500000, 0),
            "investment_asset_size": _numeric(0, 300000, 0),
            "insurance_count": _numeric(0, 5, 0),
            "monthly_avg_insurance_premium": _numeric(0, 500, 0),
            "monthly_avg_communication_expense": _numeric(30, 200, 0),
            "main_spending_industry": random.choice(["RETAIL", "FOOD", "TRAVEL", "EDUCATION", "HEALTH"]),
            "monthly_avg_card_spend": _numeric(100, 3000, 0),
            "installment_ratio": round(random.uniform(0, 0.5), 2),
            "annual_overseas_payment_amount": _numeric(0, 20000, 0),
            "app_last_access_date": _date_str(0, 90),
            "access_count_7d": _numeric(0, 30, 0),
            "consultation_page_dwell_time_seconds": _numeric(0, 600, 0),
            "marketing_consent_yn": random.choice(["Y", "N"]),
            "app_push_yn": random.choice(["Y", "N"]),
        })
    return pd.DataFrame(rows, columns=cols)


def main():
    configs = [
        ("고객내역.csv", generate_customer_detail, "고객내역"),
        ("대출내역.csv", generate_loan_detail, "대출내역"),
        ("상담내역.csv", generate_consultation_detail, "상담내역"),
        ("심사내역.csv", generate_review_detail, "심사내역"),
        ("신용정보내역.csv", generate_credit_info_detail, "신용정보내역"),
        ("마이데이터내역.csv", generate_my_data_detail, "마이데이터내역"),
    ]
    for filename, fn, label in configs:
        df = fn()
        path = OUT_DIR / filename
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"{label}: {path} - rows={len(df)}, cols={len(df.columns)}")
    print("Done. All tables include customer_id for join. Saved to", OUT_DIR)


if __name__ == "__main__":
    main()
