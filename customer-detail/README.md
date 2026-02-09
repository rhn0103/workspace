# CRM 고객 상세 페이지

React 기반 고객 상세 뷰 (이름·등급·점수 카드, 대출/신용 복합 차트, 상담 타임라인, 미니 ERD 위젯).

## 실행

```bash
cd customer-detail
npm install
npm run dev
```

브라우저에서 http://localhost:5174 로 접속합니다.

## 구조

- **상단**: 고객 이름, 등급(Gold 등), 수익성/건전성/리스크 3개 점수 카드
- **중앙**: 대출 잔액 변화 + 신용 점수 추이 복합 라인 차트 (Recharts)
- **우측**: 상담 이력 타임라인
- **하단**: 고객-대출-신용-마이데이터 연결 ERD 구조 위젯

현재는 목업 데이터(`src/data/mockCustomer.js`)를 사용합니다. 실제 API 연동 시 해당 데이터를 교체하면 됩니다.
