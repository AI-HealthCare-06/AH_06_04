#!/usr/bin/env bash
# GlowPass 자동 배포 — EC2 안에서 도는 부분
# .github/workflows/deploy.yml 이 직원 통로(EICE)로 ssh 해서 이 파일을 표준입력(bash -s)으로 넘긴다.
#
# 운영 서버의 지금 방식 그대로 한다 (11/3 서버에서 확인):
#   ~/project/glowpass               = 레포를 받아 둔 곳 (main)
#   ~/project/docker-compose.aws.yml = fastapi · chatbot 을 서버에서 빌드 (glowpass-app:local · glowpass-chatbot:local)
#   ~/project/.env                   = 서버 비밀값 (건드리지 않는다)
#
#   MODE=deploy   : 서버 코드를 이 커밋(SHA)으로 앞으로 감기 → fastapi · chatbot 빌드 → 교체
#   MODE=rollback : 이번 실행(RUN_ID)이 바꾼 것만 바로 앞 커밋으로 되돌려 다시 빌드 · 교체
#   MODE=cleanup  : 성공한 뒤 표시 파일을 지우고, 이름 없는(교체돼 남은) 옛 이미지만 정리
set -euo pipefail

MARK=.deploy-in-progress   # 이번 실행이 서버 코드를 바꿨다는 표시 (내용 = "RUN_ID 바로앞커밋")
SERVICES=(fastapi chatbot)

fail() { echo "::error::$*" >&2; exit 1; }

compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

# 컨테이너를 새로 만들면 IP 가 바뀐다 → nginx 가 옛 주소를 붙잡지 않게 설정을 다시 읽힌다
reload_nginx() {
  if compose ps --status running --services 2>/dev/null | grep -qx nginx; then
    compose exec -T nginx nginx -s reload || echo "nginx 다시 읽기 실패 (계속 진행)"
  fi
}

main() {
  local MODE="${MODE:?MODE 가 없습니다 (deploy|rollback|cleanup)}"
  local DEPLOY_DIR="${DEPLOY_DIR:-$HOME/project}"
  local RUN_ID="${RUN_ID:?RUN_ID 가 없습니다}"
  local CODE_DIR="${CODE_DIR:-glowpass}"
  COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.aws.yml}"
  [[ "$RUN_ID" =~ ^[0-9-]+$ ]] || fail "RUN_ID 형식이 이상합니다"
  [[ "$COMPOSE_FILE" =~ ^[A-Za-z0-9._-]+$ ]] || fail "COMPOSE_FILE 형식이 이상합니다"
  [[ "$CODE_DIR" =~ ^[A-Za-z0-9._-]+$ ]] || fail "CODE_DIR 형식이 이상합니다"

  cd "$DEPLOY_DIR" || fail "배포 폴더가 없습니다: $DEPLOY_DIR"
  [[ -f .env ]] || fail "$DEPLOY_DIR/.env 가 없습니다"
  [[ -f "$COMPOSE_FILE" ]] || fail "$DEPLOY_DIR/$COMPOSE_FILE 이 없습니다"
  [[ -d "$CODE_DIR/.git" ]] || fail "$DEPLOY_DIR/$CODE_DIR 에 코드(git)가 없습니다"

  case "$MODE" in
    deploy)
      : "${SHA:?SHA 가 없습니다}"
      [[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA 형식이 이상합니다"

      # 서비스 이름만 본다 (--services 는 값이 아니라 이름만 찍는다)
      local services s prev
      services=$(compose config --services)
      for s in "${SERVICES[@]}"; do
        grep -qx "$s" <<< "$services" || fail "$COMPOSE_FILE 에 $s 서비스가 없습니다"
      done

      # 누가 서버에서 손으로 고친 파일이 있으면 덮어쓰지 않고 멈춘다
      if [[ -n "$(git -C "$CODE_DIR" status --porcelain --untracked-files=no)" ]]; then
        fail "서버 코드($CODE_DIR)에 손으로 고친 파일이 있습니다. 확인 전에는 배포하지 않습니다 (서버는 그대로)"
      fi
      # 지난 실행이 교체 뒤 정리 · 되돌리기 없이 끊겼다면, 지금 서버 버전은 확인되지 않은 버전일 수 있다
      if [[ -f "$MARK" ]]; then
        echo "::warning::지난 배포($(cut -d' ' -f1 "$MARK"))가 끝까지 정리되지 않았습니다. 이번에 실패하면 그 버전으로 되돌아갑니다."
      fi

      prev=$(git -C "$CODE_DIR" rev-parse HEAD)
      echo "서버 코드 받기: ${prev:0:7} → ${SHA:0:7}"
      git -C "$CODE_DIR" fetch --quiet origin \
        || fail "GitHub 에서 코드 받기 실패 (서버의 origin 주소 · 인터넷 확인) — 서버는 그대로"
      git -C "$CODE_DIR" cat-file -e "${SHA}^{commit}" 2>/dev/null \
        || fail "커밋 ${SHA:0:7} 을 서버에서 받을 수 없습니다 (서버는 그대로)"
      # 서버에만 있는 커밋을 지우지 않게: 지금 서버 코드가 새 커밋의 앞 버전일 때만 앞으로 감는다
      git -C "$CODE_DIR" merge-base --is-ancestor "$prev" "$SHA" \
        || fail "서버 코드(${prev:0:7})가 ${SHA:0:7} 의 앞 버전이 아닙니다 (서버에만 있는 커밋?). 확인 전에는 배포하지 않습니다 (서버는 그대로)"

      echo "$RUN_ID $prev" > "$MARK"
      git -C "$CODE_DIR" checkout --quiet main
      git -C "$CODE_DIR" merge --quiet --ff-only "$SHA"

      echo "빌드: ${SERVICES[*]}"
      if ! compose build "${SERVICES[@]}"; then
        # 빌드가 끝나기 전에는 돌고 있는 컨테이너가 그대로다 → 코드만 원래대로
        git -C "$CODE_DIR" reset --quiet --hard "$prev"
        rm -f "$MARK"
        fail "빌드 실패 — 서버 코드를 원래대로 돌려놓았습니다 (돌고 있는 서버는 그대로)"
      fi
      # fastapi 는 켜질 때 마이그레이션을 먼저 한다 (운영 compose 의 command)
      compose up -d --no-deps "${SERVICES[@]}"
      reload_nginx
      echo "교체 끝: ${SERVICES[*]} (${SHA:0:7})"
      ;;

    rollback)
      local run="" prev=""
      [[ -f "$MARK" ]] && read -r run prev < "$MARK"
      if [[ "$run" != "$RUN_ID" ]]; then
        echo "이번 실행이 바꾼 것이 없습니다 — 되돌릴 것 없음 (서버는 그대로)"
        return 0
      fi
      [[ "$prev" =~ ^[0-9a-f]{40}$ ]] || fail "되돌릴 커밋 기록이 이상합니다"
      echo "앞 버전으로 되돌리기: ${prev:0:7}"
      git -C "$CODE_DIR" reset --quiet --hard "$prev"
      compose build "${SERVICES[@]}"
      compose up -d --no-deps "${SERVICES[@]}"
      reload_nginx
      rm -f "$MARK"
      echo "앞 버전으로 되돌렸습니다: ${SERVICES[*]} (${prev:0:7})"
      ;;

    cleanup)
      rm -f "$MARK"
      # 이름 없는 이미지(새로 빌드하면서 이름을 넘겨준 옛 이미지)만 지운다. 이름 있는 이미지는 그대로
      docker image prune -f > /dev/null
      echo "옛 이미지 정리 끝"
      ;;

    *)
      fail "모르는 MODE: $MODE"
      ;;
  esac
}

# bash -s 로 받을 때 docker 가 표준입력을 먹어 스크립트 뒷부분이 사라지지 않게:
# 끝줄에서 한꺼번에 부르고, 안쪽 명령의 표준입력은 /dev/null 로 막는다
main "$@" < /dev/null
