#!/bin/sh
# 同步立绘素材：为配了 idol_id 的角色拉取新卡（eidolon stand fetch，ADR-0011；存过游戏的登录态时卡牌和衣装的列表
# 先用 npm run game:catalog 从游戏查，ADR-0034，ShinyColorsDB 补上它没有的）、整理衣装清单
# （eidolon stand outfits）、渲染缩略图（frontend 的 npm run stand:thumbnails），再上传到 S3 兼容的存储桶
# （eidolon stand upload）。适合每周用 cron 跑一次，没有新卡时几乎不花时间。
# 在服务器或自己的电脑上运行都行，不经过 docker；步骤和要装的东西见
# docs/deploy.md 的「立绘素材」。需要 uv、Node.js（22.18 以上）和 Playwright 的 Chromium；有 flock（util-linux）时
# 加锁，防止两次同步重叠，没有时（例如 Windows 的 Git Bash）不加锁照常同步。
#
# 设置从仓库根目录的 .env 读（环境变量里已有的优先）：EIDOLON_STAND_S3_*、EIDOLON_STAND_BUILD_PATH 等。
# 设了 EIDOLON_STAND_FETCH_ONLY=1 时只做第一步拉取，只要 uv、不要存储桶：本机体验用本地的静态服务器
# 提供拉到的立绘（docs/agents/deploying.md「立绘」）。
# 输出追加到仓库根目录的 logs/stand-sync.log（可用 EIDOLON_STAND_SYNC_LOG 改到别处）。
#
# 退出码（含义也写在每次同步的最后一行日志里）：
#   0  完全成功
#   1  配置出错：缺存储桶的设置、角色配置有误等，没有上传
#   2  存储桶出错，这次没传完；已上传的不会重复上传，重新运行即可继续
#   3  有衣装的缩略图没渲染出来：其余照常上传，下次同步再渲染
#   4  缺少运行环境：uv、Node.js、frontend 的依赖或 Playwright 的 Chromium
#   5  上一次同步还没结束，这次没有运行
#   6  没能拉取完新卡（ShinyColorsDB 或官方资源服务器出错）：已拉取的和以前的照常上传，下次同步再拉剩下的

set -u

root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root" || exit 4
PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH # cron 的 PATH 很短；uv 默认装在 ~/.local/bin
export PYTHONIOENCODING=utf-8 # 输出重定向到日志时，Windows 上的 Python 默认用 GBK，和脚本自己写的 UTF-8 混在一起成了乱码
log=${EIDOLON_STAND_SYNC_LOG:-$root/logs/stand-sync.log}
mkdir -p "$root/logs" "$(dirname "$log")"
exec >>"$log" 2>&1

say() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

finish() {
  case $1 in
    0) meaning="完全成功" ;;
    1) meaning="配置出错，没有上传，见上方的错误" ;;
    2) meaning="存储桶出错，这次没传完；重新运行即可继续" ;;
    3) meaning="有衣装的缩略图没渲染出来，其余已上传；下次同步再渲染" ;;
    4) meaning="缺少运行环境，见上方的说明" ;;
    5) meaning="上一次同步还没结束，这次没有运行" ;;
    6) meaning="没能拉取完新卡，其余照常同步；下次同步再拉" ;;
    *) meaning="未知" ;;
  esac
  say "==== 结束：退出码 $1（$meaning）"
  echo
  exit "$1"
}

say "==== 开始同步立绘素材（$root）"

tools="uv node npm"
if [ "${EIDOLON_STAND_FETCH_ONLY:-}" = 1 ]; then
  tools=uv
fi
for tool in $tools; do
  if ! command -v "$tool" >/dev/null; then
    say "找不到 $tool（docs/deploy.md「立绘素材」列出了要装的东西）"
    finish 4
  fi
done
# 首次上传几百 MB，手动运行时可能和 cron 撞上
if command -v flock >/dev/null; then
  exec 9>"$root/logs/stand-sync.lock"
  if ! flock -n 9; then
    finish 5
  fi
else
  say "找不到 flock（util-linux），不加锁：别同时运行两次"
fi

if [ "${EIDOLON_STAND_FETCH_ONLY:-}" != 1 ] && [ ! -d frontend/node_modules/playwright ]; then
  say "npm ci（frontend 的依赖，渲染缩略图要用）"
  if ! npm --prefix frontend ci --no-audit --no-fund; then
    finish 4
  fi
fi

# eidolon 在 backend 目录里运行：角色配置、整理目录的默认位置都相对于它
env_file=
if [ -f .env ]; then
  env_file="--env-file=../.env"
fi

# 游戏目录（ADR-0034）：用 npm run game:login 存过登录态时，先从游戏查一遍卡牌和衣装，拉取从这里取；没存过时什么
# 也不做。查不了（登录态失效、维护中）不影响同步：ShinyColorsDB 照样会问，游戏目录 3 天没更新就只问它。
# 两天内查过的（剧情同步刚查过）不再查。
if command -v npm >/dev/null && [ -d frontend/node_modules/playwright ]; then
  npm --prefix frontend run --silent game:catalog -- --if-signed-in --if-older-than 48
  catalog_code=$?
  if [ "$catalog_code" != 0 ]; then
    say "npm run game:catalog 以 $catalog_code 结束（2：登录态失效，要重新 npm run game:login；3：游戏或接口出错），照常同步"
  fi
fi

say "eidolon stand fetch"
# shellcheck disable=SC2086 # 没有 .env 时 $env_file 为空，不传这个参数
(cd backend && PYTHONUNBUFFERED=1 uv run --quiet $env_file eidolon stand fetch)
fetch_code=$?
case $fetch_code in
  0) fetch_failed=0 ;;
  1) finish 1 ;;
  2) fetch_failed=1 ;; # ShinyColorsDB 或官方资源服务器连不上、接口变了：用已有的素材照常同步
  *)
    say "eidolon stand fetch 以 $fetch_code 结束"
    finish 1
    ;;
esac

if [ "${EIDOLON_STAND_FETCH_ONLY:-}" = 1 ]; then
  if [ "$fetch_failed" = 1 ]; then
    finish 6
  fi
  finish 0
fi

say "eidolon stand outfits"
# shellcheck disable=SC2086 # 没有 .env 时 $env_file 为空，不传这个参数
if ! (cd backend && PYTHONUNBUFFERED=1 uv run --quiet $env_file eidolon stand outfits); then
  finish 1
fi

say "npm run stand:thumbnails"
npm --prefix frontend run --silent stand:thumbnails
thumbnails_code=$?
case $thumbnails_code in
  0) thumbnails_failed=0 ;;
  1) finish 1 ;;
  2) thumbnails_failed=1 ;;
  3) finish 4 ;; # 打不开 Chromium 时上面会提示 npx playwright install --with-deps chromium
  *)
    say "npm run stand:thumbnails 以 $thumbnails_code 结束"
    finish 4
    ;;
esac

say "eidolon stand upload"
# shellcheck disable=SC2086
(cd backend && PYTHONUNBUFFERED=1 uv run --quiet $env_file eidolon stand upload)
upload_code=$?
case $upload_code in
  0) ;;
  1) finish 1 ;;
  2) finish 2 ;;
  *)
    say "eidolon stand upload 以 $upload_code 结束"
    finish 1
    ;;
esac
if [ "$thumbnails_failed" = 1 ]; then
  finish 3
fi
if [ "$fetch_failed" = 1 ]; then
  finish 6
fi
finish 0
