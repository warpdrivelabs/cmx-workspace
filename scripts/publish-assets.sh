#!/usr/bin/env bash
# 发布：把 backend/cmx-container/assets/<svc>/ 下的 web/、data/ 同步到对应主应用仓目录。
# 同步粒度（按顶层子目录，不做整个 web/ 镜像替换）：
#   · 真源 web/（data/）下有哪些顶层子目录（如 ui-html/、ui-native/、definitions/），
#     就只对它们逐个「整目录替换」——先删目标同名子目录，再放入新内容（内部完全按真源重建）；
#   · 顶层散文件覆盖拷入；
#   · 目标目录下真源没有的其它内容（README、core/ 等）一律不动、不删。
# 工作区为唯一真源、单向流出；被管理的顶层子目录禁止在服务仓反向手改（下次发布即被替换）。
# 真源撤销某顶层子目录后，目标仓残留的同名目录**不会自动删除**，需人工清理（脚本会提示）。
# 用法: ./scripts/publish-assets.sh <portal|model|mdm|flow|report|rules>
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WS="$ROOT/backend/cmx-container/assets"

declare -A REPO=(
  [portal]=cmx-portalservice [model]=cmx-model [mdm]=cmx-mdm
  [flow]=cmx-flowengine [report]=cmx-report [rules]=cmx-rulesengine
)

svc="${1:?用法: $0 <portal|model|mdm|flow|report|rules>}"
[ -d "$WS/$svc" ] || { echo "工作区不存在: $WS/$svc"; exit 1; }
dst="$ROOT/backend/${REPO[$svc]:-}"
[ -n "$dst" ] && [ -d "$dst" ] || { echo "未知服务或仓库缺失: $svc"; exit 1; }

# 发布前守护：页面归属校验（id 前缀匹配服务目录 / 跨服务去重 / html 业务坐标防污染，全量 ~1s；违规退出码 1 即中止发布）
python3 "$ROOT/scripts/check-asset-ownership.py"

for sub in web data; do
  src="$WS/$svc/$sub"
  [ -d "$src" ] || continue
  mkdir -p "$dst/$sub"
  # 顶层子目录：整目录替换（先删目标同名子目录，再拷入；子目录内部完全按真源重建）。
  for d in "$src"/*/; do
    [ -d "$d" ] || continue
    name="$(basename "$d")"
    rm -rf "${dst:?}/$sub/$name"
    cp -a "$d" "$dst/$sub/$name"
    echo "[$svc] $sub/$name/ → 整目录替换"
  done
  # 顶层散文件：覆盖拷入（目标多余文件不删）。
  while IFS= read -r -d '' f; do
    cp -a "$f" "$dst/$sub/"
    echo "[$svc] $sub/$(basename "$f") 覆盖拷入"
  done < <(find "$src" -mindepth 1 -maxdepth 1 -type f -print0)
  # 提示：目标下不在真源管理范围的顶层条目（不删不改，仅知悉——其中可能有历史残留待人工清理）。
  unmanaged="$(comm -13 <(ls -A "$src" | sort) <(ls -A "$dst/$sub" | sort) | tr '\n' ' ')"
  [ -n "$unmanaged" ] && echo "[$svc] $sub/ 下真源没有、保留不动：$unmanaged"
done
echo "✅ [$svc] 发布完成（注意：各服务 [assets] 已直指工作区，此拷贝仅用于打包/归档一致性）"
