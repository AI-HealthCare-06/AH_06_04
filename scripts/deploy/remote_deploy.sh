#!/usr/bin/env bash
# GlowPass 자동 배포 — EC2 안에서 도는 부분
# .github/workflows/deploy.yml 이 직원 통로(EICE)로 ssh 해서 이 파일을 표준입력(bash -s)으로 넘긴다.
#
#   MODE=deploy   : .env 를 백업하고 이미지 주소·버전을 바꾼 뒤 fastapi·chatbot 만 교체
#   MODE=rollback : 이번 실행(RUN_ID)이 바꾼 것만 백업으로 되돌린다 (다른 실행의 옛 백업은 쓰지 않는다)
#   MODE=cleanup  : 성공한 뒤 표시 파일을 지우고 안 쓰는 옛 이미지 정리
#
# .env 값은 화면에 찍지 않는다 (키 이름만 쓴다).
set -euo pipefail

BACKUP=.env.before-deploy
MARK=.deploy-in-progress   # 이번 실행이 .env 를 바꿨다는 표시 (내용 = RUN_ID)
SERVICES=(fastapi chatbot)

fail() { echo "::error::$*" >&2; exit 1; }

# .env 의 KEY=값 한 줄을 바꾸거나, 없으면 끝에 붙인다 (파일 권한은 그대로)
set_env() {
  local key=$1 val=$2 tmp
  tmp=$(mktemp)
  awk -v k="$key" -v v="$val" '
    index($0, k "=") == 1 { print k "=" v; done = 1; next }
    { print }
    END { if (!done) print k "=" v }
  ' .env > "$tmp"
  cat "$tmp" > .env
  rm -f "$tmp"
}

# .env 에서 KEY 의 값을 꺼낸다 (화면에 찍지 않고 변수로만 쓴다 · 같은 키가 여럿이면 마지막 것)
get_env() {
  awk -v k="$1" 'index($0, k "=") == 1 { v = substr($0, length(k) + 2); sub(/\r$/, "", v) } END { print v }' "$2"
}

# 컨테이너를 새로 만들면 IP 가 바뀐다 → nginx 가 옛 주소를 붙잡지 않게 설정을 다시 읽힌다
reload_nginx() {
  if docker compose ps --status running --services 2>/dev/null | grep -qx nginx; then
    docker compose exec -T nginx nginx -s reload || echo "nginx 다시 읽기 실패 (계속 진행)"
  fi
}

swap_services() {
  docker compose up -d --no-deps "${SERVICES[@]}"
  reload_nginx
}

main() {
  local MODE="${MODE:?MODE 가 없습니다 (deploy|rollback|cleanup)}"
  local DEPLOY_DIR="${DEPLOY_DIR:-$HOME/project}"
  local RUN_ID="${RUN_ID:?RUN_ID 가 없습니다}"
  [[ "$RUN_ID" =~ ^[0-9-]+$ ]] || fail "RUN_ID 형식이 이상합니다"

  cd "$DEPLOY_DIR" || fail "배포 폴더가 없습니다: $DEPLOY_DIR"
  [[ -f .env ]] || fail "$DEPLOY_DIR/.env 가 없습니다 (처음 한 번은 손으로 배포해 두어야 합니다)"
  [[ -f docker-compose.yml ]] || fail "$DEPLOY_DIR/docker-compose.yml 이 없습니다"

  case "$MODE" in
    deploy)
      : "${REGISTRY:?REGISTRY 가 없습니다}" "${REPOSITORY:?REPOSITORY 가 없습니다}" "${VERSION:?VERSION 이 없습니다}"
      [[ "$REGISTRY" =~ ^[a-z0-9.-]+(:[0-9]+)?$ ]] || fail "REGISTRY 형식이 이상합니다"
      [[ "$REPOSITORY" =~ ^[a-z0-9._/-]+$ ]] || fail "REPOSITORY 형식이 이상합니다"
      [[ "$VERSION" =~ ^[A-Za-z0-9._-]+$ ]] || fail "VERSION 형식이 이상합니다"

      # 서비스 이름만 본다 (--services 는 값이 아니라 이름만 찍는다)
      local services s
      services=$(docker compose config --services)
      for s in "${SERVICES[@]}"; do
        grep -qx "$s" <<< "$services" || fail "docker-compose.yml 에 $s 서비스가 없습니다"
      done

      # 지난 실행이 교체 뒤 정리·되돌리기 없이 끊겼다면, 지금 서버 버전은 확인되지 않은 버전일 수 있다
      if [[ -f "$MARK" ]]; then
        echo "::warning::지난 배포($(cat "$MARK"))가 끝까지 정리되지 않았습니다. 이번에 실패하면 그 버전으로 되돌아갑니다."
      fi
      cp -p .env "$BACKUP"
      echo "$RUN_ID" > "$MARK"
      set_env DOCKER_USER "$REGISTRY"
      set_env DOCKER_REPOSITORY "$REPOSITORY"
      set_env APP_VERSION "$VERSION"
      set_env CHATBOT_VERSION "$VERSION"

      echo "새 이미지 받기: ${SERVICES[*]} ($VERSION)"
      if ! docker compose pull "${SERVICES[@]}"; then
        cp -p "$BACKUP" .env
        rm -f "$MARK"
        fail "이미지 받기 실패 — .env 를 원래대로 돌려놓았습니다 (서버는 그대로)"
      fi
      # fastapi 는 켜질 때 aerich upgrade 를 먼저 한다 (운영 compose 의 command)
      swap_services
      echo "교체 끝: ${SERVICES[*]}"
      ;;

    rollback)
      if [[ ! -f "$MARK" || "$(cat "$MARK")" != "$RUN_ID" ]]; then
        echo "이번 실행이 바꾼 것이 없습니다 — 되돌릴 것 없음 (서버는 그대로)"
        return 0
      fi
      [[ -f "$BACKUP" ]] || fail "되돌릴 백업($BACKUP)이 없습니다"
      cp -p "$BACKUP" .env
      rm -f "$MARK"
      swap_services
      echo "앞 버전으로 되돌렸습니다: ${SERVICES[*]}"
      ;;

    cleanup)
      rm -f "$MARK"
      # 우리 저장소 이미지만 지운다. 지금 버전과 바로 앞 버전(손으로 되돌릴 때 쓸 것)은 남긴다.
      # (예전 prune -af 는 서버의 다른 이미지와 앞 버전까지 모두 지웠다)
      local reg repo keep tag removed=0
      reg=$(get_env DOCKER_USER .env)
      repo=$(get_env DOCKER_REPOSITORY .env)
      keep=" app-$(get_env APP_VERSION .env) chatbot-$(get_env CHATBOT_VERSION .env) "
      if [[ -f "$BACKUP" ]]; then
        keep+="app-$(get_env APP_VERSION "$BACKUP") chatbot-$(get_env CHATBOT_VERSION "$BACKUP") "
      fi
      if [[ -z "$reg" || -z "$repo" ]]; then
        echo "이미지 이름을 몰라 정리를 건너뜁니다"
        return 0
      fi
      while read -r tag; do
        [[ -z "$tag" || "$tag" == "<none>" || "$keep" == *" $tag "* ]] && continue
        # < /dev/null: docker 가 목록(표준입력)을 먹어 다음 줄을 건너뛰지 않게
        if docker image rm "$reg/$repo:$tag" < /dev/null > /dev/null 2>&1; then
          removed=$((removed + 1))
        fi
      done < <(docker image ls "$reg/$repo" --format '{{.Tag}}')
      echo "옛 이미지 정리 끝: ${removed}개 지움 (지금 버전 · 바로 앞 버전은 남김)"
      ;;

    *)
      fail "모르는 MODE: $MODE"
      ;;
  esac
}

# bash -s 로 받을 때 docker 가 표준입력을 먹어 스크립트 뒷부분이 사라지지 않게:
# 끝줄에서 한꺼번에 부르고, 안쪽 명령의 표준입력은 /dev/null 로 막는다
main "$@" < /dev/null
