# AI-First Financial Intelligence CRM

고객의 다양한 정보를 대량으로 적재하고, AI가 분석하며, 사용자가 관리할 수 있는 CRM 대시보드입니다.

## 디자인 컨셉

- **컨셉**: AI-First Financial Intelligence
- **메인 컬러**: Deep Navy `#1A202C`
- **포인트**: Electric Blue `#3182CE`, Purple `#805AD5`
- **레이아웃**: 왼쪽 네비게이션 + 상단/중앙 카드형 콘텐츠

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

## 주요 화면

1. **홈 (대시보드)**  
   - AI 요약 카드, 수익성/안정성/마케팅 성공률 KPI 게이지  
   - 데이터 흐름 라인 차트, 성향 분포 파이 차트  
   - 알림 센터 (예: 새 상담 데이터 50건 → “AI 분석 시작” 버튼)

2. **데이터 업로드**  
   - CSV/Excel 대량 업로드, 미리보기

3. **AI 상세 분석**  
   - 스코어링 보드(성향 점수, 수익성 등급, 안정성 위험도)  
   - “왜 이런 결과가 나왔나요?” Reasoning 블록  
   - “이 분석 결과 저장하기” 버튼

4. **과거 리포트 보관함**  
   - 저장한 분석 결과 리스트  
   - 비교 모드: 두 분석 선택 후 “차이점 AI 분석”

## AI 연동 (선택)

- **OpenAI API**: `OPENAI_API_KEY` 환경변수를 설정하면 다음 기능이 실제 AI로 동작합니다.
  - **대시보드**: 「AI 요약 새로고침」으로 업로드 데이터 기반 한 문단 요약 생성
  - **AI 상세 분석**: 「AI 분석 실행」으로 스코어에 대한 Reasoning(이유) 생성
  - **과거 리포트 보관함**: 두 분석 선택 후 「차이점 AI 분석」으로 차이 설명 생성
- API 키가 없어도 데모 문구로 모든 화면 이용 가능합니다.

```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-..."

# Linux / macOS
export OPENAI_API_KEY="sk-..."
streamlit run app.py
```

## 기술 스택

- **Python** 3.10+
- **Streamlit** — UI
- **Pandas** — 데이터 처리
- **Plotly** — 게이지/라인/파이 차트
- **OpenAI** — AI 요약·Reasoning·비교 (선택)
