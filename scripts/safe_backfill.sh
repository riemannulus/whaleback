#!/bin/bash
# safe_backfill.sh - KRX 차단 방지를 위한 월 단위 백필 스크립트
#
# 사용법:
#   # Docker 서버에서 실행
#   docker compose exec backend bash /app/scripts/safe_backfill.sh 20250301
#
#   # 또는 호스트에서 직접 실행 (docker compose exec 자동 사용)
#   ./scripts/safe_backfill.sh 20250301
#   ./scripts/safe_backfill.sh 20250301 20260220
#
# 동작:
#   - 시작일부터 종료일까지 1개월 단위로 백필
#   - 각 월 완료 후 60초 대기 (KRX 차단 방지)
#   - 실패 시 자동 중단 + 재개 가능 (이미 수집된 날짜는 skip)

set -euo pipefail

# ─── 설정 ───────────────────────────────────────────────
PAUSE_SECONDS=300       # 월 간 대기 시간 (초) - KRX 차단 방지 권장값
# ────────────────────────────────────────────────────────

if [ $# -lt 1 ]; then
    echo "Usage: $0 START_DATE [END_DATE]"
    echo "  START_DATE: YYYYMMDD (예: 20250301)"
    echo "  END_DATE:   YYYYMMDD (기본값: 어제)"
    exit 1
fi

START_DATE="$1"
shift

# 두 번째 인자가 YYYYMMDD 형식이면 END_DATE, 아니면 추가 옵션으로 취급
if [ $# -ge 1 ] && [[ "$1" =~ ^[0-9]{8}$ ]]; then
    END_DATE="$1"
    shift
else
    END_DATE="$(date -d 'yesterday' +%Y%m%d 2>/dev/null || date -v-1d +%Y%m%d)"
fi

# 나머지 인자를 whaleback backfill에 패스스루 (예: -t investor --no-skip-existing)
EXTRA_ARGS=("$@")

# 날짜 유효성 검사
validate_date() {
    local d="$1"
    if ! [[ "$d" =~ ^[0-9]{8}$ ]]; then
        echo "ERROR: 날짜 형식이 올바르지 않습니다: $d (YYYYMMDD 형식 필요)"
        exit 1
    fi
}

validate_date "$START_DATE"
validate_date "$END_DATE"

# whaleback 명령어 존재 확인 (Docker 내부 vs 외부)
if command -v whaleback &>/dev/null; then
    BACKFILL_CMD="whaleback backfill"
else
    BACKFILL_CMD="docker compose exec -T backend whaleback backfill"
fi

# 날짜 계산 함수 (GNU date)
next_month() {
    local y="${1:0:4}"
    local m="${1:4:2}"
    local d="${1:6:2}"

    # 다음 달 1일
    m=$((10#$m + 1))
    if [ "$m" -gt 12 ]; then
        m=1
        y=$((y + 1))
    fi
    printf "%04d%02d01" "$y" "$m"
}

# 월말 계산 (다음달 1일 - 1일)
end_of_month() {
    local y="${1:0:4}"
    local m="${1:4:2}"

    local nm=$((10#$m + 1))
    local ny=$y
    if [ "$nm" -gt 12 ]; then
        nm=1
        ny=$((ny + 1))
    fi

    # 다음달 1일에서 하루 빼기
    local next_first
    next_first=$(printf "%04d-%02d-01" "$ny" "$nm")
    date -d "$next_first - 1 day" +%Y%m%d 2>/dev/null || \
        date -j -v-1d -f "%Y-%m-%d" "$next_first" +%Y%m%d
}

# ─── 메인 루프 ──────────────────────────────────────────

echo "=============================================="
echo " Whaleback Safe Backfill"
echo "=============================================="
echo " 시작일: $START_DATE"
echo " 종료일: $END_DATE"
echo " 추가 옵션: ${EXTRA_ARGS[*]:-(기본 6개 타입)}"
echo " 월 간 대기: ${PAUSE_SECONDS}초"
echo " 명령어: $BACKFILL_CMD"
echo "=============================================="
echo ""

CHUNK_START="$START_DATE"
CHUNK_NUM=0
TOTAL_START=$(date +%s)

while [ "$CHUNK_START" -le "$END_DATE" ]; do
    CHUNK_NUM=$((CHUNK_NUM + 1))

    # 이번 청크의 끝: 해당 월 말일 또는 END_DATE 중 작은 값
    MONTH_END=$(end_of_month "$CHUNK_START")
    if [ "$MONTH_END" -gt "$END_DATE" ]; then
        CHUNK_END="$END_DATE"
    else
        CHUNK_END="$MONTH_END"
    fi

    echo "──────────────────────────────────────────"
    echo " Chunk #${CHUNK_NUM}: ${CHUNK_START} ~ ${CHUNK_END}"
    echo " 시작: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "──────────────────────────────────────────"

    CHUNK_TS=$(date +%s)

    # 백필 실행 (추가 인자가 없으면 기본 6개 타입 전부, 있으면 패스스루)
    if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
        BACKFILL_ARGS=("${EXTRA_ARGS[@]}")
    else
        BACKFILL_ARGS=(-t stock_sync -t ohlcv -t fundamentals -t investor -t sector -t market_index)
    fi
    if ! $BACKFILL_CMD -s "$CHUNK_START" -e "$CHUNK_END" "${BACKFILL_ARGS[@]}"; then
        echo ""
        echo "ERROR: Chunk #${CHUNK_NUM} 실패! (${CHUNK_START} ~ ${CHUNK_END})"
        echo "재개하려면: $0 $CHUNK_START $END_DATE"
        exit 1
    fi

    CHUNK_ELAPSED=$(( $(date +%s) - CHUNK_TS ))
    echo ""
    echo "  Chunk #${CHUNK_NUM} 완료 (${CHUNK_ELAPSED}초)"

    # 다음 청크 시작일 = 다음 달 1일
    CHUNK_START=$(next_month "$CHUNK_START")

    # 아직 남은 청크가 있으면 대기
    if [ "$CHUNK_START" -le "$END_DATE" ]; then
        echo "  KRX 차단 방지: ${PAUSE_SECONDS}초 대기 중..."
        sleep "$PAUSE_SECONDS"
        echo ""
    fi
done

TOTAL_ELAPSED=$(( $(date +%s) - TOTAL_START ))
TOTAL_MIN=$((TOTAL_ELAPSED / 60))
TOTAL_SEC=$((TOTAL_ELAPSED % 60))

echo ""
echo "=============================================="
echo " 백필 완료!"
echo " 총 ${CHUNK_NUM}개 청크, ${TOTAL_MIN}분 ${TOTAL_SEC}초 소요"
echo "=============================================="
