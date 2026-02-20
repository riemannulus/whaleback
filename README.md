# Whaleback

한국 주식시장(KOSPI/KOSDAQ) 데이터 파이프라인 및 퀀트 분석 플랫폼

## 프로젝트 소개

Whaleback은 한국 주식시장의 데이터를 자동으로 수집하고, 퀀트 분석 지표를 계산하며, 웹 인터페이스를 통해 시각화하는 통합 플랫폼입니다. pykrx를 활용하여 KRX(한국거래소) 데이터를 수집하고, 재무제표 기반 밸류에이션, 기관 수급 추적, 섹터 로테이션 분석 등을 제공합니다.

## 주요 기능

### 1. 데이터 파이프라인
- **자동 수집**: 월~금 18:30 KST 자동 실행 (스케줄러)
- **수집 대상**:
  - 종목 정보 (KOSPI/KOSDAQ 전 종목)
  - 일별 OHLCV (가격, 거래량)
  - 재무 데이터 (BPS, PER, PBR, EPS, ROE, DIV 등)
  - 투자자별 매매 동향 (기관, 외국인, 연기금)
  - 섹터 매핑 (업종 분류)
  - 시장 지수 (KOSPI, KOSDAQ)
- **백필 지원**: 과거 데이터 일괄 수집 기능

### 2. 퀀트 분석
- **RIM 밸류에이션**: 잔여이익모델(Residual Income Model) 기반 내재가치 계산
- **Modified F-Score**: 한국 시장에 최적화된 9개 시그널 재무건전성 점수 (0-9점)
- **투자등급**: A+~F 등급 분류 (F-Score + 안전마진 조합)
- **종목 랭킹**: 안전마진, F-Score 기준 정렬 및 필터링

### 3. 수급 분석
- **고래 점수**: 기관/외국인/연기금 매집 강도 점수 (0-100)
- **매집 신호**: 강한 매집, 완만한 매집, 중립, 매도 우위
- **일별 타임라인**: 투자자별 순매수 추이 시각화

### 4. 추세 분석
- **상대강도(RS)**: 개별 종목 vs 시장 지수 성과 비교
- **섹터 랭킹**: 업종별 평균 수익률 및 모멘텀 순위
- **섹터 로테이션**: 4분면 분석 (Leading, Weakening, Lagging, Improving)

### 5. REST API
- FastAPI 기반 17개 엔드포인트
- Redis 캐싱 (TTL 300초)
- Swagger UI 문서 자동 생성

### 6. 웹 인터페이스
- Next.js 14 기반 SPA
- Apache ECharts를 활용한 차트 시각화
- 대시보드, 종목 스크리너, 종목 상세, 분석 페이지

## 기술 스택

### Backend
- **Python**: 3.11+
- **Web Framework**: FastAPI, Uvicorn
- **Database**: PostgreSQL 15+ (파티셔닝), asyncpg, SQLAlchemy 2.x
- **Cache**: Redis 5+
- **Data Collection**: pykrx (KRX 공식 API 래퍼)
- **Scheduler**: APScheduler
- **Analysis**: NumPy, Pandas

### Frontend
- **Framework**: Next.js 14, React 18
- **Language**: TypeScript 5
- **Data Fetching**: TanStack Query v5
- **Charts**: Apache ECharts 5
- **Styling**: Tailwind CSS 3

### Database
- **PostgreSQL 15+**: 시계열 데이터 파티셔닝 (연도별)
- **테이블**: stocks, daily_ohlcv, fundamentals, investor_trading, sector_mapping, market_index, analysis_*_snapshot

## 빠른 시작

### 요구사항

- Python 3.11 이상
- Node.js 18 이상
- PostgreSQL 15 이상
- Redis 5 이상 (선택사항, 없으면 메모리 캐시 사용)

### 설치 및 설정

#### 1. 저장소 클론

```bash
git clone <repository-url>
cd Whaleback
```

#### 2. Python 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -e ".[dev]"
```

#### 3. 환경 변수 설정

`.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일 편집 (데이터베이스 정보 입력):

```ini
WB_DB_HOST=localhost
WB_DB_PORT=5432
WB_DB_NAME=whaleback
WB_DB_USER=whaleback
WB_DB_PASSWORD=changeme

WB_REDIS_URL=redis://localhost:6379/0
WB_CORS_ORIGINS=["http://localhost:3000"]
```

#### 4. 데이터베이스 초기화

```bash
# PostgreSQL에서 데이터베이스 생성
createdb whaleback

# 테이블 및 파티션 생성
whaleback init-db
```

### 데이터 수집

#### 최신 데이터 수집 (1회 실행)

```bash
whaleback run-once
```

특정 날짜 수집:

```bash
whaleback run-once -d 20240220
```

#### 과거 데이터 백필

```bash
# 2020년 1월 1일부터 어제까지 전체 데이터 수집
whaleback backfill -s 20200101

# 특정 기간 수집
whaleback backfill -s 20230101 -e 20231231

# 특정 데이터만 수집
whaleback backfill -s 20230101 -t ohlcv -t fundamentals
```

#### 자동 스케줄러 실행

```bash
# 평일 18:30 KST 자동 수집, 19:00 분석 계산
whaleback schedule
```

### 분석 실행

```bash
# 오늘 날짜 기준 분석 실행
whaleback compute-analysis

# 특정 날짜 분석
whaleback compute-analysis -d 20240220
```

### API 서버 시작

```bash
# 프로덕션 모드
whaleback serve

# 개발 모드 (자동 재시작)
whaleback serve --reload

# API 문서 접근
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### 프론트엔드 실행

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 시작
npm run dev

# 접속: http://localhost:3000
```

프로덕션 빌드:

```bash
npm run build
npm start
```

## 프로젝트 구조

```
Whaleback/
├── src/whaleback/           # 백엔드 소스
│   ├── __main__.py          # CLI 진입점
│   ├── config.py            # 설정 관리
│   ├── api/                 # KRX API 클라이언트
│   │   └── krx_client.py
│   ├── collectors/          # 데이터 수집기
│   │   ├── stock_list.py
│   │   ├── ohlcv.py
│   │   ├── fundamentals.py
│   │   ├── investor.py
│   │   ├── sector.py
│   │   └── index.py
│   ├── db/                  # 데이터베이스 레이어
│   │   ├── models.py        # SQLAlchemy 모델
│   │   ├── engine.py        # DB 엔진
│   │   ├── repositories.py  # 동기 레포지토리
│   │   └── async_repositories.py  # 비동기 레포지토리
│   ├── analysis/            # 분석 엔진 (순수 계산)
│   │   ├── compute.py       # 분석 실행 오케스트레이터
│   │   ├── quant.py         # RIM, F-Score, 투자등급
│   │   ├── whale.py         # 고래 점수, 매집 신호
│   │   └── trend.py         # 상대강도, 섹터 로테이션
│   ├── scheduler/           # APScheduler 작업
│   │   └── jobs.py
│   └── web/                 # FastAPI 애플리케이션
│       ├── app.py           # 앱 팩토리
│       ├── cache.py         # 캐시 서비스
│       ├── schemas.py       # Pydantic 스키마
│       └── routers/         # API 라우터
│           ├── stocks.py
│           ├── quant.py
│           ├── whale.py
│           ├── trend.py
│           └── system.py
├── frontend/                # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/             # App Router 페이지
│   │   │   ├── page.tsx     # 대시보드
│   │   │   ├── stocks/      # 종목 관련 페이지
│   │   │   └── analysis/    # 분석 페이지
│   │   ├── components/      # React 컴포넌트
│   │   ├── lib/             # API 클라이언트, 유틸
│   │   └── types/           # TypeScript 타입 정의
│   └── package.json
├── tests/                   # 테스트 파일
├── migrations/              # Alembic 마이그레이션
├── pyproject.toml           # Python 프로젝트 설정
├── .env.example             # 환경 변수 템플릿
└── README.md                # 본 파일
```

## 상세 문서

프로젝트의 각 구성 요소에 대한 상세한 문서는 `docs/` 폴더를 참조하세요:

- **[데이터 파이프라인](docs/pipeline.md)**: 데이터 수집 상세 가이드
- **[API 서버](docs/api.md)**: REST API 엔드포인트 및 분석 알고리즘 설명
- **[프론트엔드](docs/frontend.md)**: 웹 인터페이스 사용 및 개발 가이드

## 라이선스

이 프로젝트는 개인 프로젝트입니다.

## 기여

이슈 및 풀 리퀘스트는 환영합니다.

---

**Whaleback** - 한국 주식시장 퀀트 분석 플랫폼
