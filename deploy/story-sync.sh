#!/bin/sh
# 每周同步剧情库：更新 SCTranslationData，再在后端容器里运行 `eidolon story sync`。
# 由主机上的 cron 运行，安装方法见 docs/deploy.md 的「每周自动同步」。需要 git；有 flock（util-linux）时加锁，
# 防止两次同步重叠，没有时（例如 Windows 的 Git Bash）不加锁照常同步。
#
# 输出追加到仓库根目录的 logs/story-sync.log（可用 EIDOLON_SYNC_LOG 改到别处）。
# 默认用 docker-compose.prod.yml；设置了 COMPOSE_FILE 时用它指定的配置。
# 设了 EIDOLON_SYNC_DIRECT=1 时不经过 docker，在 backend/ 下用 uv 同步本地的库（本机直接跑，
# docs/agents/deploying.md「三种跑法」），设置从仓库根目录的 .env 读。
#
# 退出码（含义也写在每次同步的最后一行日志里）：
#   0  完全成功
#   1  同步命令出错：配置错误，或向量化中断（重新运行即可继续）
#   2  镜像或 API 出错，这次没拉到（全部）原文剧情；汉化版已照常导入
#   3  git 没能更新 SCTranslationData：有已下载的数据时照常同步（同步出错时以 1、2 为准），
#      一份都没有时不运行同步
#   4  后端容器没有运行，或无法运行同步命令（直接跑时：找不到 uv）
#   5  上一次同步还没结束，这次没有运行

set -u

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root" || exit 4
PATH=/usr/local/bin:/usr/bin:/bin:$PATH:$HOME/.local/bin # cron 的 PATH 很短；uv 默认装在 ~/.local/bin
export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
log=${EIDOLON_SYNC_LOG:-$root/logs/story-sync.log}
mkdir -p "$root/logs" "$(dirname "$log")"
exec >>"$log" 2>&1

say() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

finish() {
  case $1 in
    0) meaning="完全成功" ;;
    1) meaning="同步命令出错：配置错误，或向量化中断（重新运行即可继续）" ;;
    2) meaning="镜像或 API 出错：汉化版已导入，原文剧情下次同步接着拉取" ;;
    3) meaning="SCTranslationData 没有更新，见上方 git 的输出" ;;
    4) meaning="后端容器没有运行，或无法运行同步命令" ;;
    5) meaning="上一次同步还没结束，这次没有运行" ;;
    *) meaning="未知" ;;
  esac
  say "==== 结束：退出码 $1（$meaning）"
  echo
  exit "$1"
}

say "==== 开始同步剧情库（$root）"

# 首次全量补齐要一到两个小时，手动运行时可能和 cron 撞上
if command -v flock >/dev/null; then
  exec 9>"$root/logs/story-sync.lock"
  if ! flock -n 9; then
    finish 5
  fi
else
  say "找不到 flock（util-linux），不加锁：别同时运行两次"
fi

corpus=corpus/SCTranslationData
git_failed=0
if [ -d "$corpus/.git" ]; then
  say "git pull $corpus"
  if before=$(git -C "$corpus" rev-parse HEAD) && git -C "$corpus" pull --ff-only --quiet; then
    corpus_head=$(git -C "$corpus" log -1 --format='%h（%cs）')
    changed=$(git -C "$corpus" diff --shortstat "$before" HEAD)
    if [ -n "$changed" ]; then
      say "SCTranslationData 更新到 $corpus_head：$changed"
    else
      say "SCTranslationData 没有新提交，仍是 $corpus_head"
    fi
  else
    git_failed=1
  fi
elif [ -e "$corpus" ]; then
  say "$corpus 不是 git 仓库，无法更新；删掉它，下次同步会重新克隆"
  git_failed=1
else
  say "克隆 SCTranslationData 到 $corpus"
  mkdir -p corpus
  git clone --depth 1 https://github.com/ShinyGroup/SCTranslationData.git "$corpus" || git_failed=1
fi
if [ "$git_failed" = 1 ]; then
  if [ -d "$corpus/data/story" ]; then
    say "git 失败，用已有的 SCTranslationData 继续同步"
  else
    say "git 失败，而且没有可用的 SCTranslationData，这次不同步"
    finish 3
  fi
fi
# 游戏目录（ADR-0034）：用 npm run game:login 存过登录态时，先从游戏查一遍卡牌和剧情标题，同步从这里取；没存过时
# 什么也不做。要 Node.js 和 frontend 的依赖（npm --prefix frontend ci），没装就跳过。查不了（登录态失效、维护中）
# 不影响同步：游戏目录 3 天没更新，同步就退回 ShinyColorsDB。12 小时内查过的（立绘同步刚查过）不再查。
if command -v npm >/dev/null && [ -d frontend/node_modules/playwright ]; then
  npm --prefix frontend run --silent game:catalog -- --if-signed-in --if-older-than 12
  catalog_code=$?
  if [ "$catalog_code" != 0 ]; then
    say "npm run game:catalog 以 $catalog_code 结束（2：登录态失效，要重新 npm run game:login；3：游戏或接口出错），照常同步"
  fi
fi

if [ "${EIDOLON_SYNC_DIRECT:-}" = 1 ]; then
  if ! command -v uv >/dev/null; then
    say "找不到 uv（docs/agents/deploying.md 的 2.1 说了怎么装）"
    finish 4
  fi
  env_file=
  if [ -f .env ]; then
    env_file="--env-file=../.env"
  fi
  say "eidolon story sync（不经过 docker）"
  # PYTHONIOENCODING：输出重定向到日志时，Windows 上的 Python 默认用 GBK，和脚本自己写的 UTF-8 混成乱码
  # shellcheck disable=SC2086 # 没有 .env 时 $env_file 为空，不传这个参数
  (cd backend && PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 uv run --quiet $env_file eidolon story sync)
  sync_code=$?
  ran_with="uv run"
else
  # 出错时（例如没有 docker 的权限）docker 自己的错误信息也写进日志
  if [ -z "$(docker compose ps --status running --quiet backend)" ]; then
    say "后端容器没有运行（docker compose ps 里找不到运行中的 backend）"
    finish 4
  fi
  say "docker compose exec backend eidolon story sync"
  # -T：cron 里没有终端；PYTHONUNBUFFERED：进度日志和结果按实际顺序写进日志
  docker compose exec -T -e PYTHONUNBUFFERED=1 backend eidolon story sync
  sync_code=$?
  ran_with="docker compose exec"
fi
case $sync_code in
  0 | 1 | 2) ;;
  *)
    say "$ran_with 以 $sync_code 结束"
    finish 4
    ;;
esac
if [ "$sync_code" = 0 ] && [ "$git_failed" = 1 ]; then
  finish 3
fi
finish "$sync_code"
