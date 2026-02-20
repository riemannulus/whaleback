# 프론트엔드 가이드

Whaleback 웹 인터페이스 사용 및 개발 설명서

## 목차

1. [개요](#개요)
2. [설치 및 실행](#설치-및-실행)
3. [페이지별 기능 설명](#페이지별-기능-설명)
4. [개발 환경 설정](#개발-환경-설정)
5. [프록시 설정](#프록시-설정)
6. [환경 변수](#환경-변수)
7. [빌드 및 배포](#빌드-및-배포)

## 개요

Whaleback 프론트엔드는 Next.js 14 기반의 싱글 페이지 애플리케이션(SPA)으로, 한국 주식시장 데이터와 퀀트 분석 결과를 시각화합니다.

### 주요 특징

- **서버 사이드 렌더링 (SSR)**: Next.js App Router 활용
- **타입 안전성**: TypeScript 5로 전체 코드베이스 작성
- **효율적 데이터 페칭**: TanStack Query v5 (React Query)
  - 자동 캐싱 및 리페칭
  - Stale-while-revalidate 전략
  - 낙관적 업데이트 지원
- **차트 시각화**: Apache ECharts 5
  - 인터랙티브 캔들스틱 차트
  - 라인 차트, 바 차트, 산점도
  - 반응형 디자인
- **현대적 UI**: Tailwind CSS 3
  - 유틸리티 우선 스타일링
  - 다크 모드 지원 준비
- **성능 최적화**:
  - 코드 스플리팅
  - 이미지 최적화 (Next.js Image)
  - 동적 임포트

### 기술 스택

| 분류 | 기술 | 버전 |
|------|------|------|
| Framework | Next.js | 14.2.0 |
| Language | TypeScript | 5.4 |
| UI Library | React | 18.3 |
| Data Fetching | TanStack Query | 5.50.0 |
| Charts | ECharts | 5.5.0 |
| Styling | Tailwind CSS | 3.4.0 |
| Icons | Lucide React | 0.380.0 |
| Utils | date-fns | 3.6.0 |

## 설치 및 실행

### 요구사항

- Node.js 18 이상
- npm 또는 yarn

### 설치

```bash
cd frontend

# 의존성 설치
npm install

# 또는 yarn
yarn install
```

### 개발 서버 실행

```bash
# 개발 모드 (Hot Module Replacement 지원)
npm run dev

# 특정 포트로 실행
PORT=3001 npm run dev
```

개발 서버: http://localhost:3000

### 타입 체크

```bash
# TypeScript 타입 체크 (컴파일 없이)
npm run type-check
```

### 린팅

```bash
# ESLint 실행
npm run lint
```

## 페이지별 기능 설명

### 1. 대시보드 (`/`)

**경로**: `/`
**파일**: `src/app/page.tsx`

**주요 기능**:

1. **시장 개요**
   - KOSPI/KOSDAQ 지수 현황
   - 전일 대비 등락률
   - 거래량 및 거래대금

2. **TOP 종목 섹션**
   - 고래 점수 TOP 10
   - 안전마진 TOP 10 (퀀트)
   - F-Score 높은 종목

3. **섹터 현황**
   - 섹터별 평균 수익률
   - 모멘텀 순위
   - 탑 퍼포머 종목

4. **최근 업데이트**
   - 데이터 수집 상태
   - 마지막 분석 시간

**사용 데이터**:
- `GET /api/v1/analysis/whale/top`
- `GET /api/v1/analysis/quant/rankings`
- `GET /api/v1/analysis/trend/sector-ranking`
- `GET /api/v1/health/pipeline`

**주요 컴포넌트**:
```tsx
<Dashboard>
  <MarketOverview />
  <TopStocksCarousel />
  <SectorHeatmap />
  <PipelineStatus />
</Dashboard>
```

### 2. 종목 스크리너 (`/stocks`)

**경로**: `/stocks`
**파일**: `src/app/stocks/page.tsx`

**주요 기능**:

1. **필터링**
   - 시장 구분: KOSPI, KOSDAQ, 전체
   - 검색: 종목명 또는 티커로 검색
   - 활성 종목만 표시 (상장 종목)

2. **정렬**
   - 종목명 (가나다순)
   - 티커 (오름차순/내림차순)
   - 최신 업데이트 순

3. **페이지네이션**
   - 페이지당 50개 종목 (기본값)
   - 사이즈 조절: 20, 50, 100, 200
   - 전체 결과 수 표시

**사용 예시**:

```tsx
// 필터 상태 관리
const [filters, setFilters] = useState({
  market: null,
  search: '',
  isActive: true,
  page: 1,
  size: 50,
});

// TanStack Query로 데이터 페칭
const { data, isLoading } = useStocksList(filters);
```

**테이블 컬럼**:
| 컬럼 | 내용 |
|------|------|
| 티커 | 종목 코드 (클릭 시 상세 페이지 이동) |
| 종목명 | 한글 종목명 |
| 시장 | KOSPI/KOSDAQ |
| 최신가 | 현재 종가 |
| 등락률 | 전일 대비 % |

### 3. 종목 상세 (`/stocks/[ticker]`)

**경로**: `/stocks/005930` (예시)
**파일**: `src/app/stocks/[ticker]/page.tsx`

**탭 구성**:

#### 탭 1: 가격 (Price)

**차트**:
- 캔들스틱 차트 (OHLC)
- 거래량 바 차트 (하단)
- 기간 선택: 1개월, 3개월, 6개월, 1년, 전체

**기능**:
- 줌/팬 인터랙션
- 툴팁으로 상세 정보 표시
- 데이터 포인트 하이라이트

**ECharts 옵션 예시**:

```typescript
const option = {
  xAxis: { type: 'category', data: dates },
  yAxis: [
    { type: 'value', name: '가격' },
    { type: 'value', name: '거래량' }
  ],
  series: [
    {
      name: 'OHLC',
      type: 'candlestick',
      data: ohlcData, // [[open, close, low, high], ...]
    },
    {
      name: '거래량',
      type: 'bar',
      yAxisIndex: 1,
      data: volumes,
    }
  ],
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
};
```

#### 탭 2: 퀀트 (Quant)

**섹션**:

1. **밸류에이션 카드**
   - 현재가 vs 내재가치
   - 안전마진 % (게이지 차트)
   - 저평가/고평가 표시
   - 투자등급 배지 (A+, A, B+, etc.)

2. **F-Score 상세**
   - 9개 시그널 체크리스트
   - 각 시그널별 통과/실패 아이콘
   - 총점 진행바 (0-9)
   - 데이터 완전성 표시

3. **재무 지표**
   - BPS, PER, PBR
   - EPS, ROE, DIV
   - 전년 대비 변화율

**컴포넌트 구조**:

```tsx
<QuantTab>
  <ValuationCard
    rimValue={data.rim_value}
    currentPrice={data.current_price}
    safetyMargin={data.safety_margin_pct}
    grade={data.grade}
  />
  <FScoreBreakdown criteria={fscoreData.criteria} />
  <FundamentalsTable fundamentals={data.latest_fundamentals} />
</QuantTab>
```

#### 탭 3: 수급 (Supply/Demand)

**차트**:

1. **고래 점수 게이지**
   - 0-100 점수 시각화
   - 신호 라벨 표시 (강한 매집, 중립 등)
   - 색상 코딩 (녹색, 노랑, 빨강)

2. **매집 타임라인 (스택 영역 차트)**
   - X축: 날짜 (최근 40일)
   - Y축: 순매수액 (억 원)
   - 시리즈: 기관(파랑), 외국인(초록), 연기금(보라)
   - 누적 표시 (stacked area chart)

3. **투자자별 통계 테이블**
   - 최근 20일 순매수 합계
   - 매수일/매도일 수
   - 일관성 점수 (consistency)

**데이터 페칭**:

```typescript
const { data: whaleScore } = useQuery({
  queryKey: ['whale', 'score', ticker],
  queryFn: () => api.getWhaleScore(ticker),
});

const { data: accumulation } = useQuery({
  queryKey: ['whale', 'accumulation', ticker],
  queryFn: () => api.getWhaleAccumulation(ticker),
});
```

#### 탭 4: 펀더멘털 (Fundamentals)

**테이블**:
- 최근 30일 재무 데이터 변화 추이
- BPS, PER, PBR, EPS, ROE, DIV 일별 히스토리
- 증감 화살표 표시
- 평균값 및 중앙값 표시

**차트**:
- ROE 추이 라인 차트
- PER/PBR 듀얼 축 차트
- 배당수익률 변화

### 4. 퀀트 분석 (`/analysis/quant`)

**경로**: `/analysis/quant`
**파일**: `src/app/analysis/quant/page.tsx`

**주요 기능**:

1. **종목 랭킹 테이블**
   - 전체 종목 퀀트 점수 순위
   - 정렬 옵션: 안전마진, F-Score, 내재가치
   - 필터: 시장, 최소 F-Score, 투자등급
   - 페이지네이션 (50개씩)

2. **안전마진 분포 차트**
   - 히스토그램: 안전마진 구간별 종목 수
   - 색상: 저평가(녹색), 적정(노랑), 고평가(빨강)

3. **등급별 통계**
   - 파이 차트: A+/A/B+/B/C+/C/D/F 분포
   - 각 등급별 종목 수 및 비율

**테이블 컬럼**:
| 컬럼 | 설명 |
|------|------|
| 순위 | 안전마진 기준 순위 |
| 티커 | 종목 코드 (링크) |
| 종목명 | 한글명 |
| 시장 | KOSPI/KOSDAQ |
| 현재가 | 종가 |
| 내재가치 | RIM 모델 계산값 |
| 안전마진 | % (양수=저평가) |
| F-Score | 0-9점 |
| 등급 | A+ ~ F |

### 5. 수급 분석 (`/analysis/whale`)

**경로**: `/analysis/whale`
**파일**: `src/app/analysis/whale/page.tsx`

**주요 기능**:

1. **고래 점수 TOP 20**
   - 고래 점수 높은 순 정렬
   - 필터: 시장, 최소 점수
   - 카드 레이아웃 또는 테이블 뷰

2. **매집 강도 히트맵**
   - 2D 차트: 일관성 vs 강도
   - 버블 크기: 시가총액
   - 색상: 신호 (강한 매집=녹색)

3. **투자자별 순위**
   - 기관 순매수 TOP 10
   - 외국인 순매수 TOP 10
   - 연기금 순매수 TOP 10

**카드 컴포넌트**:

```tsx
<WhaleCard>
  <StockInfo ticker={item.ticker} name={item.name} />
  <WhaleScoreGauge score={item.whale_score} />
  <SignalBadge signal={item.signal} />
  <NetBuyingStats
    institution={item.institution_net_20d}
    foreign={item.foreign_net_20d}
    pension={item.pension_net_20d}
  />
</WhaleCard>
```

### 6. 추세 분석 (`/analysis/trend`)

**경로**: `/analysis/trend`
**파일**: `src/app/analysis/trend/page.tsx`

**주요 기능**:

1. **섹터 순위**
   - 평균 수익률 높은 순 정렬
   - 모멘텀 랭크 표시
   - 탑 퍼포머 종목 표시
   - 클릭 시 해당 섹터 종목 목록으로 이동

2. **섹터 로테이션 차트**
   - 산점도 (Scatter Plot)
   - X축: RS Ratio
   - Y축: RS 변화율
   - 4분면 표시: Leading, Weakening, Lagging, Improving
   - 버블 라벨: 섹터명

3. **상위 RS 종목**
   - RS 백분위 90 이상 종목
   - 상대강도 추이 미니 차트
   - 섹터별 필터링

**로테이션 차트 구현**:

```typescript
const option = {
  xAxis: { name: 'RS Ratio', axisLine: { onZero: true } },
  yAxis: { name: 'RS Change %', axisLine: { onZero: true } },
  series: [{
    type: 'scatter',
    data: sectors.map(s => [s.avg_rs_20d, s.avg_rs_change]),
    itemStyle: {
      color: (params) => getQuadrantColor(params.data),
    },
    label: { show: true, formatter: '{@sector}' },
  }],
  visualMap: {
    dimension: 'quadrant',
    categories: ['leading', 'weakening', 'lagging', 'improving'],
    inRange: {
      color: ['#22c55e', '#eab308', '#ef4444', '#3b82f6'],
    },
  },
};
```

## 개발 환경 설정

### 프로젝트 구조

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router 페이지
│   │   ├── layout.tsx          # 루트 레이아웃
│   │   ├── page.tsx            # 대시보드 (/)
│   │   ├── globals.css         # 전역 스타일
│   │   ├── stocks/             # 종목 관련 페이지
│   │   │   ├── page.tsx        # 스크리너
│   │   │   ├── layout.tsx      # 종목 레이아웃
│   │   │   └── [ticker]/       # 동적 라우팅
│   │   │       └── page.tsx    # 종목 상세
│   │   └── analysis/           # 분석 페이지
│   │       ├── quant/
│   │       ├── whale/
│   │       └── trend/
│   ├── components/             # 재사용 가능 컴포넌트
│   │   ├── charts/             # ECharts 래퍼 컴포넌트
│   │   │   ├── CandlestickChart.tsx
│   │   │   ├── LineChart.tsx
│   │   │   └── ScatterChart.tsx
│   │   ├── ui/                 # UI 프리미티브
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Table.tsx
│   │   └── layout/             # 레이아웃 컴포넌트
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Footer.tsx
│   ├── lib/                    # 유틸리티 및 헬퍼
│   │   ├── api.ts              # API 클라이언트
│   │   ├── queries.ts          # TanStack Query hooks
│   │   └── utils.ts            # 공통 유틸리티
│   ├── types/                  # TypeScript 타입 정의
│   │   └── api.ts              # API 응답 타입
│   └── providers/              # React Context Providers
│       └── query-provider.tsx  # TanStack Query Provider
├── public/                     # 정적 파일
│   ├── images/
│   └── favicon.ico
├── next.config.js              # Next.js 설정
├── tailwind.config.ts          # Tailwind 설정
├── tsconfig.json               # TypeScript 설정
└── package.json
```

### API 클라이언트 구현

**파일**: `src/lib/api.ts`

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

export const api = {
  // Stocks
  getStocks: async (params: StocksParams) => {
    const res = await fetch(`${API_BASE_URL}/stocks?${new URLSearchParams(params)}`);
    return res.json();
  },

  getStockDetail: async (ticker: string) => {
    const res = await fetch(`${API_BASE_URL}/stocks/${ticker}`);
    return res.json();
  },

  // Quant
  getQuantValuation: async (ticker: string) => {
    const res = await fetch(`${API_BASE_URL}/analysis/quant/valuation/${ticker}`);
    return res.json();
  },

  // Whale
  getWhaleScore: async (ticker: string) => {
    const res = await fetch(`${API_BASE_URL}/analysis/whale/score/${ticker}`);
    return res.json();
  },

  // ... 기타 엔드포인트
};
```

### TanStack Query Hooks

**파일**: `src/lib/queries.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { api } from './api';

export const useStocksList = (params: StocksParams) => {
  return useQuery({
    queryKey: ['stocks', params],
    queryFn: () => api.getStocks(params),
    staleTime: 5 * 60 * 1000, // 5분
  });
};

export const useStockDetail = (ticker: string) => {
  return useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => api.getStockDetail(ticker),
    enabled: !!ticker,
  });
};

export const useQuantValuation = (ticker: string) => {
  return useQuery({
    queryKey: ['quant', 'valuation', ticker],
    queryFn: () => api.getQuantValuation(ticker),
    enabled: !!ticker,
  });
};
```

### TypeScript 타입 정의

**파일**: `src/types/api.ts`

```typescript
export interface Stock {
  ticker: string;
  name: string;
  market: 'KOSPI' | 'KOSDAQ';
  is_active: boolean;
}

export interface PriceData {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change_rate: number;
}

export interface QuantValuation {
  ticker: string;
  name: string;
  current_price: number;
  rim_value: number;
  safety_margin_pct: number;
  is_undervalued: boolean;
  grade: string;
  grade_label: string;
}

// ... 기타 타입 정의
```

## 프록시 설정

### next.config.js

API 서버로의 프록시 설정 (개발 환경):

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
```

**동작**:
- 프론트엔드에서 `/api/v1/stocks` 호출
- Next.js가 `http://localhost:8000/api/v1/stocks`로 프록시
- CORS 문제 회피

### 프로덕션 환경

프로덕션에서는 실제 API URL 사용:

```bash
# .env.production
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

## 환경 변수

### .env.local

개발 환경 설정:

```ini
# API 서버 URL (프록시 대상)
NEXT_PUBLIC_API_URL=http://localhost:8000

# 기타 공개 환경 변수 (브라우저에서 접근 가능)
NEXT_PUBLIC_APP_NAME=Whaleback
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

**중요**: `NEXT_PUBLIC_` 접두사가 있는 변수만 클라이언트 사이드에서 접근 가능

### .env.production

프로덕션 환경:

```ini
NEXT_PUBLIC_API_URL=https://api.whaleback.com
NEXT_PUBLIC_SITE_URL=https://whaleback.com
```

## 빌드 및 배포

### 프로덕션 빌드

```bash
# 최적화된 빌드 생성
npm run build

# 빌드 결과: .next/ 디렉토리
```

### 프로덕션 서버 실행

```bash
# 빌드된 앱 실행
npm start

# 또는 포트 지정
PORT=3000 npm start
```

### Docker 배포

**Dockerfile**:

```dockerfile
FROM node:18-alpine AS base

# 의존성 설치
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# 빌드
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# 프로덕션 이미지
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["node", "server.js"]
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WB_DB_HOST=db
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=whaleback
```

### Vercel 배포

1. **GitHub 연동**
   - Vercel 계정에서 GitHub 저장소 연결

2. **환경 변수 설정**
   - Vercel 대시보드에서 환경 변수 추가
   - `NEXT_PUBLIC_API_URL`: API 서버 URL

3. **자동 배포**
   - `main` 브랜치 푸시 시 자동 배포
   - 프리뷰 배포: PR별 고유 URL

### Nginx 정적 호스팅

```nginx
server {
    listen 80;
    server_name whaleback.com;

    root /var/www/whaleback/out;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 프록시
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

**프론트엔드 가이드 끝**
