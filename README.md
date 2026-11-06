# ivan-parity · 对标监督

对标分析只告诉你差在哪，不保证改完。ivan-parity 把每一条差异写成一项能自动检查的清单，逐项检查、逐项修，直到每一项都拿出证据通过；对标方更新了，清单也能发现。

A Claude Code / agent skill for closing the gaps found in a benchmark comparison: write each gap as a checkable item in `parity.json`, run the checker, fix what fails, re-run until every item passes with evidence.

## 安装

把整个文件夹放进 `~/.claude/skills/ivan-parity/`（或你的 agent 的 skills 目录）。只依赖 Python 3 标准库。

## 用法

```sh
python3 scripts/parity_check.py parity.json --out PARITY.md
# 检查对标方的最新数据版本时，可设 GITHUB_TOKEN 避免匿名限流
```

输出一张表：每项 PASS / FAIL / UNKNOWN 和证据。全部通过时退出码为 0。

清单写法、检查类型和工作规则见 [SKILL.md](SKILL.md)。示例：[人选鸟图对标花叔 birdalbum.com](examples/bird-human-picks.parity.json)，10 项全部通过的检查结果见 [bird-human-picks/PARITY.md](https://github.com/flychicken067/bird-human-picks/blob/main/PARITY.md)。

## 授权

MIT
