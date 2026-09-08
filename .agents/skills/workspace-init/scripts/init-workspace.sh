#!/usr/bin/env bash
# 初始化 CMX 工作区：把 15 个子仓按 backend/ + frontend/ + cmx-launcher/ 三分结构克隆到位（完整克隆，不浅克）。
# 幂等：已存在的 Git 仓默认跳过；非 Git 目录视为冲突报错（不自动覆盖，人工处理）。
# 本脚本的 REPOS 清单是子仓清单唯一真源——新增/下线子仓时改这里，并同步 AGENTS.md §六。
# 用法: bash .agents/skills/workspace-init/scripts/init-workspace.sh [--update] [--dry-run]
#   --update    已存在的仓顺带 git pull --ff-only 更新（默认跳过不动）
#   --dry-run   只打印将执行的动作，不实际 clone/pull
set -euo pipefail

# 脚本位于 <根>/.agents/skills/workspace-init/scripts/，向上 4 层即工作区根
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
[ -f "$ROOT/AGENTS.md" ] || { echo "定位工作区根失败: $ROOT（缺少 AGENTS.md，请确认脚本位于 cmx-workspace 工作区内）" >&2; exit 2; }
ORG="https://gitee.com/warpdrivelabs"

UPDATE=0
DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --update)  UPDATE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    *) echo "未知参数: $1（用法: $0 [--update] [--dry-run]）" >&2; exit 2 ;;
  esac
done

# 清单：工作区相对路径 -> 仓库名（clone 用各仓默认分支：除 mega-sheet 为 master 外均为 main）
declare -A REPOS=(
  [backend/cmx-container]=cmx-container
  [backend/cmx-portalservice]=cmx-portalservice
  [backend/cmx-agent]=cmx-agent
  [backend/cmx-flowengine]=cmx-flowengine
  [backend/cmx-report]=cmx-report
  [backend/cmx-rulesengine]=cmx-rulesengine
  [backend/cmx-model]=cmx-model
  [backend/cmx-mdm]=cmx-mdm
  [backend/cmx-ontology]=cmx-ontology
  [backend/cmx-data-auth]=cmx-data-auth
  [frontend/cmx-enterprise-portal]=cmx-enterprise-portal
  [frontend/cmx-mega-sheet]=cmx-mega-sheet
  [frontend/cmx-ontology-graph]=cmx-ontology-graph
  [frontend/cmx-decision-graph]=cmx-decision-graph
  [cmx-launcher]=cmx-launcher
)

ok=0; skipped=0; updated=0; failed=0; conflicted=0
fail_list=""; conflict_list=""

for path in $(printf '%s\n' "${!REPOS[@]}" | sort); do
  name="${REPOS[$path]}"
  dst="$ROOT/$path"
  url="$ORG/$name.git"

  if [ -d "$dst/.git" ]; then
    if [ "$UPDATE" -eq 1 ]; then
      echo "⟳ update  $path"
      if [ "$DRY" -eq 1 ]; then updated=$((updated+1)); continue; fi
      if git -C "$dst" pull --ff-only; then updated=$((updated+1)); else failed=$((failed+1)); fail_list="$fail_list $path(pull)"; fi
    else
      echo "– skip    $path（已存在）"
      skipped=$((skipped+1))
    fi
  elif [ -e "$dst" ]; then
    echo "✗ 冲突    $path 已存在但不是 Git 仓（人工处理后再跑，本脚本不覆盖）" >&2
    conflicted=$((conflicted+1)); conflict_list="$conflict_list $path"
  else
    echo "+ clone   $path  ←  $url"
    if [ "$DRY" -eq 1 ]; then ok=$((ok+1)); continue; fi
    if git clone "$url" "$dst"; then ok=$((ok+1)); else failed=$((failed+1)); fail_list="$fail_list $path"; fi
  fi
done

echo
echo "===== 汇总 ====="
echo "新克隆 $ok · 跳过 $skipped · 更新 $updated · 失败 $failed · 冲突 $conflicted / 共 ${#REPOS[@]} 仓"
[ -n "$fail_list" ]    && echo "失败:$fail_list（网络问题可重跑本脚本，已克隆的会自动跳过）"
[ -n "$conflict_list" ] && echo "冲突:$conflict_list（目录存在但非 Git 仓，请人工确认）"

if [ "$failed" -gt 0 ] || [ "$conflicted" -gt 0 ]; then
  exit 1
fi

echo "✅ 工作区初始化完成。后续步骤见技能 workspace-init（前端 npm install 等）。"
