#!/usr/bin/env bash
#
# 统一编译/检查 cmx-workspace 下全部 Rust 后端仓（10 个独立 cargo workspace）。
#
#   用法: scripts/build-all-rust.sh [check|clippy|build|release]   （默认 check）
#
# 约束与约定：
#   - 默认 check —— 对齐 AGENTS.md §四.4「Rust 检查用 cargo check/clippy，禁止 cargo build」。
#   - 共享 target（~/.cargo-shared-target）由全局 ~/.cargo/config.toml 配置，本脚本不覆盖（见 CLAUDE.md）。
#   - cmx-container 先编（公用库，预热共享 target 供 8 个下游 path 引用仓复用）。
#   - cmx-agent 收尾（无特殊处理，与其余仓一致）。
#   - 单仓失败不中断，末尾汇总 OK/FAIL + 耗时；有任一失败则退出码非 0。
#   - 需 Homebrew bash 5+（关联/普通数组 + SECONDS）；shebang 走 env，PATH 已优先 /opt/homebrew/bin。
set -uo pipefail

MODE="${1:-check}"
case "$MODE" in
  check)   CARGO_ARGS=(check   --workspace) ;;
  clippy)  CARGO_ARGS=(clippy  --workspace) ;;
  build)   CARGO_ARGS=(build   --workspace) ;;
  release) CARGO_ARGS=(build   --workspace --release) ;;
  *) echo "未知级别: $MODE（用法: $(basename "$0") [check|clippy|build|release]）" >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 编译顺序：cmx-container 先（预热共享 target）→ 其余按名 → cmx-agent 收尾。
ORDER=()
[ -f "backend/cmx-container/Cargo.toml" ] && ORDER+=(cmx-container)
for d in backend/*/; do
  r="$(basename "$d")"
  case "$r" in cmx-container|cmx-agent) continue ;; esac
  [ -f "$d/Cargo.toml" ] && ORDER+=("$r")
done
[ -f "backend/cmx-agent/Cargo.toml" ] && ORDER+=(cmx-agent)

echo "==== 统一 [$MODE] · ${#ORDER[@]} 个 Rust 仓 · 共享 target=~/.cargo-shared-target ===="
echo "顺序: ${ORDER[*]}"

OK_LIST=(); FAIL_LIST=()
START_ALL=$SECONDS
for r in "${ORDER[@]}"; do
  echo ""
  echo ">>> [$r] cargo ${CARGO_ARGS[*]}"
  t0=$SECONDS
  if ( cd "backend/$r" && cargo "${CARGO_ARGS[@]}" ); then
    el=$((SECONDS - t0)); OK_LIST+=("$r(${el}s)");        echo "<<< [$r] OK  ${el}s"
  else
    rc=$?; el=$((SECONDS - t0)); FAIL_LIST+=("$r(rc=$rc,${el}s)"); echo "<<< [$r] FAIL rc=$rc ${el}s"
  fi
done
TOTAL=$((SECONDS - START_ALL))

echo ""
echo "==== 汇总 [$MODE] · 总耗时 ${TOTAL}s ===="
echo "OK   (${#OK_LIST[@]}): ${OK_LIST[*]:-无}"
echo "FAIL (${#FAIL_LIST[@]}): ${FAIL_LIST[*]:-无}"
[ ${#FAIL_LIST[@]} -eq 0 ]
