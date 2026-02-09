# DB 테이블·컬럼 네이밍 규칙 (메타화)

앞으로 **모든 테이블명·컬럼명은 영문**으로 하며, 아래 규칙으로 **인식성**을 높입니다.

## 규칙

| 항목 | 규칙 | 예시 |
|------|------|------|
| **테이블명** | snake_case, 영문, 의미 단위 | `condition_extract_result`, `customer`, `loan` |
| **컬럼명** | snake_case, 영문, entity_attribute 또는 measure_name | `customer_id`, `profitability_score`, `extracted_at` |
| **인식성** | 약어보다 풀네임 권장, 복수는 단수 테이블명 | `customer` (O), `customers` (X) |

## 앱에서 사용하는 표준 이름 (db_storage.py 상수)

- **테이블**: `TABLE_CONDITION_EXTRACT_RESULT` = `"condition_extract_result"`
- **컬럼**:  
  `COL_CUSTOMER_ID`, `COL_CUSTOMER_NAME`,  
  `COL_PROFITABILITY_SCORE`, `COL_SOUNDNESS_SCORE`, `COL_RISK_SCORE`,  
  `COL_EXTRACTED_AT`, `COL_CRITERIA_PROFITABILITY_MIN`, `COL_CRITERIA_SOUNDNESS_MIN`, `COL_CRITERIA_RISK_MAX`

신규 테이블/컬럼 추가 시 위 패턴을 따르고, `db_storage.py`에 상수를 정의해 두는 것을 권장합니다.
