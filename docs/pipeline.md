# 데이터 파이프라인 가이드

Whaleback 데이터 파이프라인 사용 설명서

## 목차

1. [개요](#개요)
2. [수집 대상](#수집-대상)
3. [수집 주기 및 스케줄](#수집-주기-및-스케줄)
4. [CLI 명령어 상세](#cli-명령어-상세)
5. [환경 변수 설정](#환경-변수-설정)
6. [백필 가이드](#백필-가이드)
7. [트러블슈팅](#트러블슈팅)

## 개요

Whaleback 데이터 파이프라인은 pykrx 라이브러리를 활용하여 KRX(한국거래소)의 공개 데이터를 수집하고 PostgreSQL 데이터베이스에 저장합니다. 모든 수집 작업은 멱등성(idempotency)을 보장하며, 동일한 날짜에 대한 재수집 시 기존 데이터를 업데이트합니다.

### 주요 특징

- **자동화**: APScheduler를 통한 자동 수집 스케줄링
- **안정성**: 재시도 로직 및 오류 처리
- **유연성**: 특정 날짜, 기간, 데이터 타입 선택 가능
- **추적성**: 모든 수집 작업은 `collection_log` 테이블에 기록

## 수집 대상

### 1. stock_sync (종목 정보 동기화)

**Collector**: `StockListCollector`

**수집 내용**:
- KOSPI/KOSDAQ 상장 종목 전체 목록
- 종목 코드(ticker), 종목명(name), 시장 구분(market)
- 상장/폐지 상태(is_active)

**데이터베이스 테이블**: `stocks`

**특징**:
- 신규 상장 종목 자동 추가
- 폐지 종목은 `is_active=false`로 업데이트
- 기준일: 수집 당일

### 2. ohlcv (일별 가격 데이터)

**Collector**: `OHLCVCollector`

**수집 내용**:
- 시가(open), 고가(high), 저가(low), 종가(close)
- 거래량(volume), 거래대금(trading_value)
- 시가총액(market_cap), 상장주식수(shares_outstanding)
- 등락률(change_rate)

**데이터베이스 테이블**: `daily_ohlcv` (연도별 파티션)

**특징**:
- 활성 종목 대상 (is_active=true)
- 휴장일은 데이터 없음 (자동 스킵)

### 3. fundamentals (재무 데이터)

**Collector**: `FundamentalsCollector`

**수집 내용**:
- BPS (주당순자산), PER (주가수익비율), PBR (주가순자산비율)
- EPS (주당순이익), DIV (배당수익률), DPS (주당배당금)
- ROE (자기자본이익률)

**데이터베이스 테이블**: `fundamentals` (연도별 파티션)

**특징**:
- KRX에서 제공하는 일별 스냅샷 데이터
- 일부 지표는 null 가능 (예: 적자 기업의 PER)

### 4. investor (투자자별 매매 동향)

**Collector**: `InvestorTradingCollector`

**수집 내용**:
- 기관(institution_net)
- 외국인(foreign_net)
- 개인(individual_net)
- 연기금(pension_net)
- 각 투자자별 매수/매도/순매수 금액

**데이터베이스 테이블**: `investor_trading` (연도별 파티션)

**특징**:
- 순매수 금액(net) = 매수 - 매도
- 단위: 원(KRW)

### 5. sector (섹터 매핑)

**Collector**: `SectorCollector`

**수집 내용**:
- 종목별 업종 분류
- 업종 코드 및 업종명

**데이터베이스 테이블**: `sector_mapping`

**특징**:
- 참조 데이터 (종종 변경되지 않음)
- 섹터 분석의 기준

### 6. market_index (시장 지수)

**Collector**: `IndexCollector`

**수집 내용**:
- KOSPI (코드: 1001)
- KOSDAQ (코드: 2001)
- 각 지수의 OHLCV 및 거래량

**데이터베이스 테이블**: `market_index` (연도별 파티션)

**특징**:
- 상대강도(RS) 계산의 벤치마크
- 시장 전체 추세 파악

## 수집 주기 및 스케줄

### 자동 스케줄

기본 스케줄 (`.env`에서 설정 가능):

```ini
WB_SCHEDULE_HOUR=18        # 18시
WB_SCHEDULE_MINUTE=30      # 30분
WB_TIMEZONE=Asia/Seoul     # KST
```

**실행 시점**: 월~금요일 18:30 KST (장 마감 후)

**실행 순서**:
1. `sector` (섹터 매핑) - 참조 데이터 우선 수집
2. `market_index` (시장 지수)
3. `stock_sync` (종목 정보 동기화)
4. `ohlcv` (가격 데이터)
5. `fundamentals` (재무 데이터)
6. `investor` (투자자별 매매 동향)

**분석 계산**: 19:00 KST (데이터 수집 완료 후)

### 수동 실행

필요 시 CLI 명령어로 수동 실행 가능 (아래 참조)

## CLI 명령어 상세

### 1. init-db (데이터베이스 초기화)

**용도**: 데이터베이스 테이블 및 파티션 생성

**사용법**:

```bash
whaleback init-db
```

**동작**:
- SQLAlchemy 모델 기반 테이블 생성
- 2020년부터 현재+2년까지 연도별 파티션 생성
- 인덱스 생성 (ticker, trade_date 등)

**주의사항**:
- 이미 존재하는 테이블/파티션은 스킵
- 데이터 손실 없음

### 2. run-once (1회 수집)

**용도**: 단일 수집 사이클 실행

**사용법**:

```bash
# 오늘 날짜 데이터 수집
whaleback run-once

# 특정 날짜 데이터 수집
whaleback run-once -d 20240220

# 상세 로그 출력
whaleback run-once --verbose
```

**옵션**:
- `-d, --date YYYYMMDD`: 수집 대상 날짜 (기본값: 오늘)
- `-v, --verbose`: 디버그 로그 활성화

**출력 예시**:

```
  sector: collection complete
  market_index: collection complete
  stock_sync: 2543 records
  ohlcv: 2543 records
  fundamentals: 2543 records
  investor: 2543 records
Collection complete.
```

### 3. schedule (스케줄러 시작)

**용도**: 자동 수집 스케줄러 실행 (장기 실행)

**사용법**:

```bash
whaleback schedule
```

**동작**:
- 설정된 시간(기본: 18:30 KST)에 매일 자동 수집
- 월~금요일만 실행 (주말 스킵)
- Ctrl+C로 종료

**출력 예시**:

```
Starting scheduler: daily at 18:30 KST (Mon-Fri)
Press Ctrl+C to stop.
```

**프로덕션 배포**:
- systemd 서비스로 실행 권장
- 또는 Docker 컨테이너로 백그라운드 실행

### 4. backfill (과거 데이터 백필)

**용도**: 특정 기간의 과거 데이터 일괄 수집

**사용법**:

```bash
# 기본: 시작일부터 어제까지 전체 데이터
whaleback backfill -s 20200101

# 특정 기간 지정
whaleback backfill -s 20230101 -e 20231231

# 특정 데이터 타입만 수집
whaleback backfill -s 20230101 -t ohlcv -t fundamentals

# 기존 데이터 덮어쓰기 (기본: 스킵)
whaleback backfill -s 20230101 --no-skip-existing
```

**옵션**:
- `-s, --start YYYYMMDD`: 시작 날짜 (필수)
- `-e, --end YYYYMMDD`: 종료 날짜 (기본값: 어제)
- `-t, --type`: 수집 타입 (여러 번 지정 가능)
  - `stock_sync`, `ohlcv`, `fundamentals`, `investor`, `sector`, `market_index`
  - 기본값: `stock_sync`, `ohlcv`, `fundamentals`, `investor`
- `--skip-existing`: 이미 수집된 날짜 스킵 (기본값: true)

**주말 처리**: 토요일/일요일 자동 스킵 (증시 휴장)

**출력 예시**:

```
Backfilling ohlcv, fundamentals from 2023-01-02 to 2023-12-29

[2023-01-02]
  ohlcv: 2512 records
  fundamentals: 2512 records

[2023-01-03]
  ohlcv: 2515 records
  fundamentals: 2515 records

...

Backfill complete. Processed 248 trading days.
```

### 5. compute-analysis (분석 계산)

**용도**: 수집된 데이터를 기반으로 퀀트/수급/추세 분석 실행

**사용법**:

```bash
# 오늘 날짜 기준 분석
whaleback compute-analysis

# 특정 날짜 분석
whaleback compute-analysis -d 20240220
```

**계산 대상**:
- **Quant**: RIM 밸류에이션, F-Score, 투자등급
- **Whale**: 고래 점수, 매집 신호
- **Trend**: 상대강도, 섹터 랭킹, RS 백분위

**결과 저장 테이블**:
- `analysis_quant_snapshot`
- `analysis_whale_snapshot`
- `analysis_trend_snapshot`

### 6. serve (API 서버 시작)

**용도**: FastAPI REST API 서버 실행

**사용법**:

```bash
# 프로덕션 모드
whaleback serve

# 개발 모드 (자동 재시작)
whaleback serve --reload

# 호스트/포트 지정
whaleback serve --host 0.0.0.0 --port 8080
```

**API 문서**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 환경 변수 설정

`.env` 파일에서 설정 가능한 환경 변수 (모두 `WB_` 접두사):

### 데이터베이스

```ini
WB_DB_HOST=localhost          # PostgreSQL 호스트
WB_DB_PORT=5432              # PostgreSQL 포트
WB_DB_NAME=whaleback         # 데이터베이스 이름
WB_DB_USER=whaleback         # 사용자명
WB_DB_PASSWORD=changeme      # 비밀번호
WB_DB_POOL_SIZE=5            # 커넥션 풀 크기
WB_DB_MAX_OVERFLOW=10        # 최대 오버플로우
```

### API 요청 제어

```ini
WB_KRX_REQUEST_DELAY=1.0     # 요청 간 지연 시간 (초)
WB_KRX_MAX_RETRIES=3         # 최대 재시도 횟수
WB_KRX_RETRY_BACKOFF=2.0     # 재시도 백오프 시간 (초)
```

### 스케줄러

```ini
WB_SCHEDULE_HOUR=18          # 수집 시간 (시)
WB_SCHEDULE_MINUTE=30        # 수집 시간 (분)
WB_TIMEZONE=Asia/Seoul       # 타임존
WB_ANALYSIS_SCHEDULE_HOUR=19     # 분석 실행 시간 (시)
WB_ANALYSIS_SCHEDULE_MINUTE=0    # 분석 실행 시간 (분)
```

### 분석 파라미터

```ini
WB_RISK_FREE_RATE=0.035      # 무위험 수익률 (한국 10년물 국채 ~3.5%)
WB_EQUITY_RISK_PREMIUM=0.065 # 주식 위험 프리미엄 (~6.5%)
WB_WHALE_LOOKBACK_DAYS=20    # 고래 분석 기간 (영업일)
```

### Redis 캐시

```ini
WB_REDIS_URL=redis://localhost:6379/0  # Redis 연결 URL
WB_CACHE_TTL=300                        # 캐시 유효 시간 (초)
```

### API 서버

```ini
WB_API_HOST=0.0.0.0                     # API 서버 호스트
WB_API_PORT=8000                        # API 서버 포트
WB_CORS_ORIGINS=["http://localhost:3000"]  # CORS 허용 오리진
```

## 백필 가이드

### 최초 설정 시 전체 백필

```bash
# 1단계: 데이터베이스 초기화
whaleback init-db

# 2단계: 참조 데이터 수집 (섹터)
whaleback backfill -s 20200101 -e 20200101 -t sector

# 3단계: 전체 데이터 백필 (2020년 1월부터)
whaleback backfill -s 20200101

# 4단계: 분석 계산 (최신 날짜)
whaleback compute-analysis
```

**예상 소요 시간**: 약 5-10시간 (KRX API 속도 제한 고려)

### 특정 기간 추가 수집

```bash
# 누락된 기간 수집
whaleback backfill -s 20230515 -e 20230520
```

### 데이터 타입별 선택 수집

```bash
# OHLCV만 재수집
whaleback backfill -s 20230101 -e 20231231 -t ohlcv

# 재무데이터 + 투자자 동향만 수집
whaleback backfill -s 20230101 -t fundamentals -t investor
```

### 기존 데이터 덮어쓰기

```bash
# 모든 날짜 강제 재수집 (collection_log 무시)
whaleback backfill -s 20230101 -e 20230131 --no-skip-existing
```

## 트러블슈팅

### 1. 수집 실패: "No data available"

**원인**: 휴장일 또는 KRX API에 데이터 없음

**해결**:
- 휴장일은 정상 동작 (스킵)
- 평일인데 실패하면 KRX API 점검 여부 확인

### 2. 수집 실패: "Connection timeout"

**원인**: KRX API 서버 응답 지연

**해결**:
```bash
# 재시도 설정 증가
export WB_KRX_MAX_RETRIES=5
export WB_KRX_RETRY_BACKOFF=5.0
whaleback run-once
```

### 3. 데이터베이스 연결 오류

**원인**: PostgreSQL 접속 정보 오류

**해결**:
```bash
# .env 파일 확인
cat .env | grep WB_DB

# PostgreSQL 연결 테스트
psql -h localhost -U whaleback -d whaleback
```

### 4. 파티션 누락 오류

**증상**: `no partition of relation "daily_ohlcv" found for row`

**원인**: 해당 연도 파티션 미생성

**해결**:
```bash
# init-db 재실행 (기존 데이터 보존)
whaleback init-db
```

### 5. 메모리 부족 (대량 백필 시)

**증상**: 백필 중 프로세스 종료

**해결**:
```bash
# 기간을 분할하여 수집
whaleback backfill -s 20200101 -e 20201231
whaleback backfill -s 20210101 -e 20211231
whaleback backfill -s 20220101 -e 20221231
```

### 6. 스케줄러 시간 확인

```bash
# 로그에서 다음 실행 시간 확인
whaleback schedule
# 출력: "Next run scheduled for: 2024-02-21 18:30:00 KST"
```

### 7. 수집 로그 확인

```sql
-- 최근 수집 상태 확인
SELECT target_date, collection_type, status, record_count, created_at
FROM collection_log
ORDER BY created_at DESC
LIMIT 20;

-- 실패한 수집 확인
SELECT *
FROM collection_log
WHERE status = 'failed'
ORDER BY created_at DESC;
```

## 모범 사례

1. **정기 백업**: PostgreSQL 데이터베이스 정기 백업 설정
2. **모니터링**: 수집 실패 알림 설정 (collection_log 모니터링)
3. **로그 보관**: `logs/` 디렉토리 정기 아카이빙
4. **분석 갱신**: 데이터 수집 후 항상 `compute-analysis` 실행
5. **시간대 주의**: 모든 시간은 KST (Asia/Seoul) 기준

---

**데이터 파이프라인 가이드 끝**
