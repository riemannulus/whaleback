# API 서버 가이드

Whaleback REST API 사용 설명서

## 목차

1. [개요](#개요)
2. [서버 시작 방법](#서버-시작-방법)
3. [API 문서 접근](#api-문서-접근)
4. [엔드포인트 목록](#엔드포인트-목록)
5. [캐시 설정](#캐시-설정)
6. [분석 알고리즘](#분석-알고리즘)
7. [환경 변수](#환경-변수)

## 개요

Whaleback API는 FastAPI 기반의 RESTful 웹 서비스로, 한국 주식시장 데이터 및 퀀트 분석 결과를 제공합니다.

### 주요 특징

- **비동기 처리**: asyncpg를 활용한 고성능 비동기 데이터베이스 쿼리
- **자동 캐싱**: Redis 기반 응답 캐싱 (TTL: 300초)
- **자동 문서화**: Swagger UI 및 ReDoc 제공
- **CORS 지원**: 프론트엔드 통합 간편화
- **타입 안전성**: Pydantic 스키마 기반 요청/응답 검증

### 기술 스택

- FastAPI 0.110+
- Uvicorn (ASGI 서버)
- SQLAlchemy 2.x (비동기 ORM)
- asyncpg (PostgreSQL 비동기 드라이버)
- Redis 5+ (캐싱)

## 서버 시작 방법

### 개발 모드

```bash
# 자동 재시작 활성화
whaleback serve --reload

# 특정 호스트/포트 지정
whaleback serve --host 127.0.0.1 --port 8080 --reload
```

### 프로덕션 모드

```bash
# 기본 설정 (0.0.0.0:8000)
whaleback serve

# Uvicorn 직접 실행 (고급)
uvicorn whaleback.web.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 4
```

### Docker 배포

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["whaleback", "serve"]
```

### systemd 서비스 (Linux)

`/etc/systemd/system/whaleback-api.service`:

```ini
[Unit]
Description=Whaleback API Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=whaleback
WorkingDirectory=/opt/whaleback
Environment="PATH=/opt/whaleback/venv/bin"
ExecStart=/opt/whaleback/venv/bin/whaleback serve
Restart=always

[Install]
WantedBy=multi-user.target
```

## API 문서 접근

### Swagger UI (인터랙티브 문서)

```
http://localhost:8000/docs
```

- 모든 엔드포인트 탐색
- 직접 API 호출 테스트 가능
- 요청/응답 스키마 확인

### ReDoc (읽기 전용 문서)

```
http://localhost:8000/redoc
```

- 깔끔한 문서 레이아웃
- 검색 기능
- 다운로드 가능

## 엔드포인트 목록

Base URL: `http://localhost:8000/api/v1`

### System (시스템 상태)

#### GET /health

**설명**: API 서버 헬스 체크

**응답 예시**:

```json
{
  "status": "ok",
  "version": "0.2.0",
  "cache_type": "redis"
}
```

#### GET /health/pipeline

**설명**: 데이터 파이프라인 수집 상태 확인

**응답 예시**:

```json
{
  "data": {
    "collections": [
      {
        "collection_type": "ohlcv",
        "target_date": "2024-02-20",
        "status": "success",
        "record_count": 2543,
        "created_at": "2024-02-20T18:35:12"
      }
    ]
  },
  "meta": {
    "cached": false
  }
}
```

---

### Stocks (종목 정보)

#### GET /stocks

**설명**: 종목 목록 조회 (페이지네이션)

**쿼리 파라미터**:
- `market` (optional): "KOSPI" 또는 "KOSDAQ"
- `search` (optional): 종목명 또는 티커 검색
- `is_active` (optional): 활성 종목 필터 (기본값: true)
- `page` (optional): 페이지 번호 (기본값: 1)
- `size` (optional): 페이지 크기 (기본값: 50, 최대: 200)

**응답 예시**:

```json
{
  "data": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "market": "KOSPI",
      "is_active": true
    }
  ],
  "meta": {
    "total": 2543,
    "page": 1,
    "size": 50
  }
}
```

#### GET /stocks/{ticker}

**설명**: 종목 상세 정보 (최신 가격 + 재무 데이터)

**경로 파라미터**:
- `ticker`: 종목 코드 (예: "005930")

**응답 예시**:

```json
{
  "data": {
    "ticker": "005930",
    "name": "삼성전자",
    "market": "KOSPI",
    "is_active": true,
    "latest_price": {
      "trade_date": "2024-02-20",
      "close": 72500,
      "open": 72000,
      "high": 73000,
      "low": 71800,
      "volume": 15234567,
      "change_rate": 1.23
    },
    "latest_fundamentals": {
      "trade_date": "2024-02-20",
      "bps": 45230,
      "per": 12.34,
      "pbr": 1.60,
      "eps": 5876,
      "div": 2.5,
      "roe": 13.21
    }
  },
  "meta": {
    "cached": true
  }
}
```

#### GET /stocks/{ticker}/price

**설명**: 종목 가격 히스토리 (OHLCV)

**쿼리 파라미터**:
- `start_date` (optional): 시작일 (YYYY-MM-DD, 기본값: 180일 전)
- `end_date` (optional): 종료일 (YYYY-MM-DD, 기본값: 오늘)

**응답 예시**:

```json
{
  "data": [
    {
      "trade_date": "2024-02-20",
      "open": 72000,
      "high": 73000,
      "low": 71800,
      "close": 72500,
      "volume": 15234567,
      "trading_value": 1105678900000,
      "change_rate": 1.23
    }
  ]
}
```

#### GET /stocks/{ticker}/investors

**설명**: 투자자별 매매 동향 히스토리

**쿼리 파라미터**:
- `start_date` (optional): 시작일 (기본값: 60일 전)
- `end_date` (optional): 종료일 (기본값: 오늘)

**응답 예시**:

```json
{
  "data": [
    {
      "trade_date": "2024-02-20",
      "institution_net": 123456789,
      "foreign_net": -45678901,
      "individual_net": -77777888,
      "pension_net": 12345678
    }
  ]
}
```

---

### Quant Analysis (퀀트 분석)

#### GET /analysis/quant/valuation/{ticker}

**설명**: RIM 밸류에이션 및 안전마진

**응답 예시**:

```json
{
  "data": {
    "ticker": "005930",
    "name": "삼성전자",
    "as_of_date": "2024-02-20",
    "current_price": 72500,
    "rim_value": 95230.45,
    "safety_margin_pct": 23.91,
    "is_undervalued": true,
    "grade": "A",
    "grade_label": "매수"
  }
}
```

#### GET /analysis/quant/fscore/{ticker}

**설명**: Modified F-Score 상세 분석

**응답 예시**:

```json
{
  "data": {
    "ticker": "005930",
    "total_score": 7,
    "max_score": 9,
    "data_completeness": 1.0,
    "criteria": [
      {
        "name": "positive_eps",
        "score": 1,
        "value": 5876,
        "label": "당기순이익 > 0"
      },
      {
        "name": "positive_roe",
        "score": 1,
        "value": 13.21,
        "label": "자기자본이익률 > 0"
      },
      {
        "name": "roe_increasing",
        "score": 1,
        "value": 2.15,
        "label": "ROE 증가"
      }
    ]
  }
}
```

#### GET /analysis/quant/grade/{ticker}

**설명**: 투자등급 조회

**응답 예시**:

```json
{
  "data": {
    "ticker": "005930",
    "grade": "A",
    "label": "매수",
    "fscore": 7,
    "safety_margin": 23.91,
    "data_completeness": 1.0
  }
}
```

#### GET /analysis/quant/rankings

**설명**: 퀀트 종목 랭킹

**쿼리 파라미터**:
- `market` (optional): "KOSPI" 또는 "KOSDAQ"
- `min_fscore` (optional): 최소 F-Score (0-9)
- `grade` (optional): 투자등급 필터 (예: "A+", "A", "B+")
- `sort_by` (optional): 정렬 기준 (기본값: "safety_margin")
  - "safety_margin": 안전마진 높은 순
  - "fscore": F-Score 높은 순
  - "rim_value": 내재가치 높은 순
- `page`, `size`: 페이지네이션

**응답 예시**:

```json
{
  "data": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "market": "KOSPI",
      "current_price": 72500,
      "rim_value": 95230.45,
      "safety_margin": 23.91,
      "fscore": 7,
      "grade": "A"
    }
  ],
  "meta": {
    "total": 145,
    "page": 1,
    "size": 50
  }
}
```

---

### Whale Analysis (수급 분석)

#### GET /analysis/whale/score/{ticker}

**설명**: 고래 점수 조회

**응답 예시**:

```json
{
  "data": {
    "ticker": "005930",
    "name": "삼성전자",
    "as_of_date": "2024-02-20",
    "lookback_days": 20,
    "whale_score": 73.45,
    "signal": "strong_accumulation",
    "signal_label": "강한 매집",
    "components": {
      "institution_net": {
        "net_total": 12345678900,
        "consistency": 0.85
      },
      "foreign_net": {
        "net_total": 9876543210,
        "consistency": 0.75
      },
      "pension_net": {
        "net_total": 2345678901,
        "consistency": 0.65
      }
    }
  }
}
```

#### GET /analysis/whale/accumulation/{ticker}

**설명**: 일별 매집 타임라인

**쿼리 파라미터**:
- `start_date`, `end_date`: 조회 기간 (기본값: 최근 40일)

**응답 예시**:

```json
{
  "data": [
    {
      "trade_date": "2024-02-20",
      "institution_net": 123456789,
      "foreign_net": -45678901,
      "pension_net": 12345678
    }
  ]
}
```

#### GET /analysis/whale/top

**설명**: 고래 점수 상위 종목 랭킹

**쿼리 파라미터**:
- `market` (optional): "KOSPI" 또는 "KOSDAQ"
- `min_score` (optional): 최소 고래 점수 (0-100)
- `page`, `size`: 페이지네이션 (기본 size: 20)

**응답 예시**:

```json
{
  "data": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "market": "KOSPI",
      "whale_score": 73.45,
      "signal": "strong_accumulation",
      "institution_net_20d": 12345678900,
      "foreign_net_20d": 9876543210
    }
  ],
  "meta": {
    "total": 87,
    "page": 1,
    "size": 20
  }
}
```

---

### Trend Analysis (추세 분석)

#### GET /analysis/trend/sector-ranking

**설명**: 섹터 성과 랭킹

**쿼리 파라미터**:
- `market` (optional): "KOSPI" 또는 "KOSDAQ"

**응답 예시**:

```json
{
  "data": [
    {
      "sector": "반도체",
      "stock_count": 87,
      "avg_change_rate": 5.23,
      "median_change_rate": 4.87,
      "avg_rs": 1.0523,
      "momentum_rank": 1,
      "top_performer": {
        "ticker": "005930",
        "name": "삼성전자",
        "change_rate": 8.45
      }
    }
  ]
}
```

#### GET /analysis/trend/relative-strength/{ticker}

**설명**: 상대강도(RS) 분석

**쿼리 파라미터**:
- `benchmark` (optional): "KOSPI" 또는 "KOSDAQ" (기본값: "KOSPI")
- `days` (optional): 조회 기간 (기본값: 120, 범위: 20-365)

**응답 예시**:

```json
{
  "data": {
    "ticker": "005930",
    "name": "삼성전자",
    "benchmark": "KOSPI",
    "current_rs": 1.0523,
    "rs_percentile": 78,
    "rs_change_pct": 5.23,
    "series": [
      {
        "date": "2024-02-20",
        "stock_indexed": 105.23,
        "index_indexed": 100.00,
        "rs_ratio": 1.0523
      }
    ]
  }
}
```

#### GET /analysis/trend/sector-rotation

**설명**: 섹터 로테이션 4분면 분석

**응답 예시**:

```json
{
  "data": [
    {
      "sector": "반도체",
      "avg_rs_20d": 1.0523,
      "avg_rs_change": 0.0523,
      "stock_count": 87,
      "quadrant": "leading"
    },
    {
      "sector": "은행",
      "avg_rs_20d": 0.9876,
      "avg_rs_change": -0.0124,
      "stock_count": 23,
      "quadrant": "lagging"
    }
  ]
}
```

**Quadrant 분류**:
- `leading`: 높은 RS + 상승 모멘텀
- `weakening`: 높은 RS + 하락 모멘텀
- `lagging`: 낮은 RS + 하락 모멘텀
- `improving`: 낮은 RS + 상승 모멘텀

#### GET /analysis/trend/sector/{sector_name}

**설명**: 특정 섹터 내 종목 목록 (RS 순위)

**응답 예시**:

```json
{
  "data": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "market": "KOSPI",
      "rs_vs_kospi_20d": 1.0523,
      "rs_percentile": 78,
      "sector": "반도체"
    }
  ],
  "meta": {
    "total": 87,
    "page": 1,
    "size": 50
  }
}
```

## 캐시 설정

### Redis 캐싱 (권장)

Redis가 설치되어 있으면 자동으로 Redis 캐시 사용:

```ini
# .env
WB_REDIS_URL=redis://localhost:6379/0
WB_CACHE_TTL=300  # 5분
```

**캐시되는 엔드포인트**:
- `/stocks/{ticker}` (종목 상세)
- `/analysis/quant/valuation/{ticker}`
- `/analysis/quant/rankings`
- `/analysis/whale/score/{ticker}`
- `/analysis/whale/top`
- `/analysis/trend/sector-ranking`

### Fallback: 메모리 캐시

Redis 연결 실패 시 자동으로 메모리 캐시로 대체:

```python
# 로그 출력
WARNING: Redis connection failed, using in-memory cache
```

메모리 캐시는 프로세스 재시작 시 초기화됨.

### 캐시 확인

응답 메타데이터에서 캐시 사용 여부 확인:

```json
{
  "data": {...},
  "meta": {
    "cached": true  // Redis에서 캐시된 응답
  }
}
```

## 분석 알고리즘

### 1. RIM 밸류에이션 (Residual Income Model)

**공식**:

```
내재가치 = BPS + (ROE - r) × BPS / (r - g)
```

**변수**:
- `BPS`: 주당순자산 (Book value Per Share)
- `ROE`: 자기자본이익률 (%) - DB에서 가져온 값을 100으로 나눔
- `r`: 요구수익률 = 무위험수익률 + 주식위험프리미엄
  - 무위험수익률 (기본값): 3.5% (한국 10년물 국채)
  - 주식위험프리미엄 (기본값): 6.5%
  - **r = 0.035 + 0.065 = 0.10 (10%)**
- `g`: 영구성장률 (기본값: 0%)

**안전마진**:

```
안전마진(%) = (내재가치 - 현재가) / 내재가치 × 100
```

- 양수: 저평가 (매수 기회)
- 음수: 고평가 (주의)

**예시**:

```
BPS = 45,230원
ROE = 13.21% (→ 0.1321)
현재가 = 72,500원

내재가치 = 45,230 + (0.1321 - 0.10) × 45,230 / (0.10 - 0)
         = 45,230 + 14,509
         = 59,739원

안전마진 = (59,739 - 72,500) / 59,739 × 100 = -21.4% (고평가)
```

### 2. Modified F-Score (9개 시그널)

한국 시장에 맞춰 수정된 Piotroski F-Score:

| # | 시그널 | 기준 | 점수 |
|---|--------|------|------|
| 1 | 당기순이익 | EPS > 0 | 1 |
| 2 | 자기자본이익률 | ROE > 0 | 1 |
| 3 | ROE 증가 | ROE > 전년 ROE | 1 |
| 4 | EPS 증가 | EPS > 전년 EPS | 1 |
| 5 | 자본축적 | BPS > 전년 BPS | 1 |
| 6 | 상대 밸류에이션 | PBR < 섹터 중앙값 | 1 |
| 7 | 배당 | DIV > 0 | 1 |
| 8 | 수익 밸류에이션 | PER < 섹터 중앙값 AND PER > 0 | 1 |
| 9 | 거래량 증가 | 현재 거래량 > 전년 거래량 | 1 |

**총점**: 0-9점
- **8-9점**: 매우 우수한 재무 건전성
- **6-7점**: 양호한 재무 상태
- **4-5점**: 보통
- **0-3점**: 취약한 재무 상태

### 3. 투자등급 (A+ ~ F)

F-Score와 안전마진을 결합한 종합 등급:

| 등급 | 조건 | 라벨 | 설명 |
|------|------|------|------|
| A+ | F-Score ≥ 8 AND 안전마진 ≥ 30% | 강력 매수 | 재무 우수 + 고안전마진 |
| A | F-Score ≥ 7 AND 안전마진 ≥ 20% | 매수 | 재무 양호 + 적정 안전마진 |
| B+ | F-Score ≥ 6 AND 안전마진 ≥ 10% | 매수 검토 | 양호한 재무 + 소폭 저평가 |
| B | F-Score ≥ 5 AND 안전마진 ≥ 0% | 보유 | 적정 재무 + 적정 가치 |
| C+ | F-Score ≥ 4 | 관망 | 보통 재무 상태 |
| C | F-Score ≥ 3 | 주의 | 재무 취약 신호 |
| D | F-Score < 3 | 위험 | 재무 건전성 심각 우려 |
| F | 데이터 완전성 < 50% | 데이터 부족 | 분석 불가 |

### 4. 고래 점수 (Whale Score)

기관/외국인/연기금의 매집 강도를 0-100점으로 수치화:

**각 투자자별 서브 점수 계산**:

```
일관성(consistency) = 순매수일 / 전체 영업일
강도(intensity) = |평균 순매수액| / 평균 거래대금
서브점수 = consistency × 60 + min(intensity × 40, 40)
```

**종합 고래 점수**:

```
whale_score = max(서브점수들) × 0.5 + avg(서브점수들) × 0.5
```

**신호 분류**:
- **70-100**: 강한 매집 (strong_accumulation)
- **50-69**: 완만한 매집 (mild_accumulation)
- **30-49**: 중립 (neutral)
- **0-29**: 매도 우위 (distribution, 순매수액 < 0)

**기간**: 최근 20 영업일 (기본값)

### 5. 상대강도 (Relative Strength)

개별 종목의 시장 지수 대비 성과:

**RS Ratio 계산**:

```
종목_인덱스 = (현재가 / 기준가) × 100
지수_인덱스 = (현재 지수 / 기준 지수) × 100
RS Ratio = 종목_인덱스 / 지수_인덱스
```

**해석**:
- RS > 1.0: 시장 대비 아웃퍼폼
- RS = 1.0: 시장과 동일한 성과
- RS < 1.0: 시장 대비 언더퍼폼

**RS 백분위(Percentile)**:
- 전체 종목 중 상대적 순위 (0-100)
- 100 = 최강 상대강도

### 6. 섹터 로테이션

섹터별 RS와 모멘텀을 4분면으로 분류:

```
          모멘텀 상승
              |
   Improving  |  Leading
   (개선 중)  |  (주도)
              |
--------------+-------------- RS 중앙값
              |
   Lagging    |  Weakening
   (낙후)     |  (약화 중)
              |
          모멘텀 하락
```

**투자 전략**:
- **Leading**: 매수 유지 (강세 지속)
- **Weakening**: 차익 실현 검토 (고점 인근)
- **Lagging**: 회피 (약세 지속)
- **Improving**: 신규 진입 검토 (저점 탈출)

## 환경 변수

API 서버 관련 환경 변수:

```ini
# 서버 설정
WB_API_HOST=0.0.0.0
WB_API_PORT=8000

# CORS (프론트엔드 통합)
WB_CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]

# 캐시
WB_REDIS_URL=redis://localhost:6379/0
WB_CACHE_TTL=300  # 초 단위

# 데이터베이스 (비동기)
WB_DB_HOST=localhost
WB_DB_PORT=5432
WB_DB_NAME=whaleback
WB_DB_USER=whaleback
WB_DB_PASSWORD=changeme

# 분석 파라미터
WB_RISK_FREE_RATE=0.035        # 3.5%
WB_EQUITY_RISK_PREMIUM=0.065   # 6.5%
WB_WHALE_LOOKBACK_DAYS=20      # 20 영업일
```

---

**API 서버 가이드 끝**
