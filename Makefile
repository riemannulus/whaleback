.PHONY: help
help: ## 도움말 표시
	@grep -E '^[a-zA-Z_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ─── Docker 빌드 ─────────────────────────────────────────

.PHONY: build build-no-cache
build: ## Docker 이미지 빌드
	docker compose build

build-no-cache: ## Docker 이미지 클린 빌드 (캐시 무시)
	docker compose build --no-cache

# ─── Docker 서비스 ────────────────────────────────────────

.PHONY: up down restart logs logs-scheduler ps
up: ## 전체 서비스 시작 (백그라운드)
	docker compose up -d

down: ## 전체 서비스 중지
	docker compose down

restart: ## 전체 서비스 재시작
	docker compose restart

logs: ## 전체 로그 (실시간)
	docker compose logs -f

logs-scheduler: ## 스케줄러 로그 (실시간)
	docker compose logs -f scheduler

ps: ## 서비스 상태 확인
	docker compose ps

# ─── Docker DB 관리 ───────────────────────────────────────

.PHONY: docker.init docker.migrate docker.stamp docker.db-shell
docker.init: ## [Docker] DB 초기화 (테이블 + 파티션 + alembic stamp)
	docker compose run --rm whaleback init

docker.migrate: ## [Docker] Alembic 마이그레이션 실행 (upgrade head)
	docker compose run --rm whaleback migrate

docker.stamp: ## [Docker] Alembic stamp (예: make docker.stamp REV=004)
	docker compose run --rm whaleback alembic stamp $(REV)

docker.db-shell: ## [Docker] PostgreSQL 셸 접속
	docker compose exec db psql -U $${WB_DB_USER:-whaleback} -d $${WB_DB_NAME:-whaleback}

# ─── Docker 데이터 수집/분석 ──────────────────────────────

.PHONY: docker.run-once docker.compute docker.backfill docker.safe-backfill
docker.run-once: ## [Docker] 데이터 수집 (예: make docker.run-once DATE=20260226)
	docker compose run --rm whaleback run-once $(if $(DATE),-d $(DATE),)

docker.compute: ## [Docker] 분석 실행 (예: make docker.compute DATE=20260226)
	docker compose run --rm whaleback compute-analysis $(if $(DATE),-d $(DATE),)

docker.backfill: ## [Docker] 백필 (예: make docker.backfill START=20260101 END=20260220)
	docker compose run --rm whaleback backfill -s $(START) $(if $(END),-e $(END),)

docker.safe-backfill: ## [Docker] 안전 백필 - 월 단위 + KRX 차단 방지 (예: make docker.safe-backfill START=20250301)
	docker compose exec backend bash /app/scripts/safe_backfill.sh $(START) $(END)

# ─── 로컬 DB 관리 ────────────────────────────────────────

.PHONY: local.init local.migrate local.stamp
local.init: ## [로컬] DB 초기화
	whaleback init-db

local.migrate: ## [로컬] Alembic 마이그레이션 실행
	alembic upgrade head

local.stamp: ## [로컬] Alembic stamp (예: make local.stamp REV=004)
	alembic stamp $(REV)

# ─── 로컬 데이터 수집/분석 ────────────────────────────────

.PHONY: local.run-once local.compute local.backfill local.safe-backfill
local.run-once: ## [로컬] 데이터 수집 (예: make local.run-once DATE=20260226)
	whaleback run-once $(if $(DATE),-d $(DATE),)

local.compute: ## [로컬] 분석 실행 (예: make local.compute DATE=20260226)
	whaleback compute-analysis $(if $(DATE),-d $(DATE),)

local.backfill: ## [로컬] 백필 (예: make local.backfill START=20260101 END=20260220)
	whaleback backfill -s $(START) $(if $(END),-e $(END),)

local.safe-backfill: ## [로컬] 안전 백필 (예: make local.safe-backfill START=20250301)
	bash scripts/safe_backfill.sh $(START) $(END)

# ─── 로컬 서버 ───────────────────────────────────────────

.PHONY: local.serve local.dev
local.serve: ## [로컬] API 서버 시작
	whaleback serve --reload

local.dev: ## [로컬] 개발 환경 시작 (API + Frontend)
	bash scripts/run_dev.sh

# ─── 로컬 설치/테스트 ────────────────────────────────────

.PHONY: install install-news install-dev test lint
install: ## [로컬] 기본 패키지 설치
	pip install -e .

install-news: ## [로컬] 뉴스 감성 분석 포함 설치 (anthropic, torch, transformers)
	pip install -e ".[news]"

install-dev: ## [로컬] 개발 의존성 포함 전체 설치
	pip install -e ".[news,dev]"

test: ## [로컬] 테스트 실행
	python -m pytest tests/ -v --tb=short

lint: ## [로컬] 코드 린트
	python -m ruff check src/ tests/

# ─── 프론트엔드 ──────────────────────────────────────────

.PHONY: frontend.install frontend.dev frontend.build
frontend.install: ## [Frontend] npm 의존성 설치
	cd frontend && npm install

frontend.dev: ## [Frontend] 개발 서버 시작
	cd frontend && npm run dev

frontend.build: ## [Frontend] 프로덕션 빌드
	cd frontend && npm run build

# ─── 정리 ────────────────────────────────────────────────

.PHONY: clean docker.clean
clean: ## [로컬] 캐시/빌드 파일 정리
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info

docker.clean: ## [Docker] 볼륨 포함 전체 정리 (DB 데이터 삭제!)
	@echo "⚠ DB 데이터가 삭제됩니다. 계속하려면 Enter, 취소는 Ctrl+C"
	@read _
	docker compose down -v --remove-orphans
