# 샘플 데이터 생성

## 실행 방법

```bash
# 프로젝트 루트에서
pip install faker
python scripts/generate_sample_data.py
```

또는 (이미 requirements.txt 설치 후):

```bash
python scripts/generate_sample_data.py
```

## 생성 파일

`data/sample/` 폴더에 다음 CSV가 생성됩니다.

| 파일 | 행 수 | 주요 컬럼 | 연결 |
|------|--------|-----------|------|
| 고객.csv | 1,000 | 고객_ID, 속성001~속성100 | PK: 고객_ID |
| 상담.csv | 1,000 | 상담_ID, 고객_ID, 속성001~속성100 | 고객_ID → 고객 |
| 대출.csv | 1,000 | 대출_ID, 고객_ID, 속성001~속성100 | 고객_ID → 고객 |
| 신용.csv | 1,000 | 신용_ID, 고객_ID, 속성001~속성100 | 고객_ID → 고객 |
| 마이데이터.csv | 1,000 | 마이데이터_ID, 고객_ID, 속성001~속성100 | 고객_ID → 고객 |

각 테이블은 **고객_ID**로 조인 가능합니다.
