# CRM ERD 시각화

React Flow를 사용한 인터랙티브 고객 데이터 ERD 시각화 화면입니다.

## 실행 방법

```bash
cd erd-viewer
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 으로 접속합니다.

## 기능

- **노드**: 고객, 상담, 대출, 신용, 연체 테이블 카드 (헤더 + 컬럼·타입)
- **엣지**: FK 관계를 Bezier 곡선으로 연결
- **호버**: 테이블에 마우스를 올리면 연결된 노드·선만 하이라이트, 나머지는 흐리게
- **미리보기**: 노드의 보기(눈) 아이콘에 마우스를 올리면 샘플 데이터 3건 툴팁
- **미니맵·줌**: 우측 하단 미니맵, 좌측 하단 Zoom In/Out 컨트롤
- **그룹 색상**: 기본 정보(고객, 상담) = 초록, 금융(대출, 신용, 연체) = 파랑

## 데이터 수정

`src/data/erdData.js` 에서 다음만 수정하면 됩니다.

- **TABLE_DEFINITIONS**: 테이블 id, 이름, 그룹, 컬럼 목록, 샘플 데이터
- **FK_RELATIONS**: source → target 관계
- **NODE_POSITIONS**: 노드 초기 위치 (선택)

`initialNodes` / `initialEdges` 는 위 상수로부터 자동 생성됩니다.
