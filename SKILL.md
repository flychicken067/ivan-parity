---
name: ivan-parity
description: 对标监督：把“我们和对标产品差在哪”写成一张可自动检查的清单，逐项检查、逐项修，直到每一项都拿出证据通过。用于：做完一轮对标分析之后，要求“按差异全部改完”“盯着这几项完成”“对标验收”“检查和 XX 还差什么”；也用于每次发布前复查。Use when a benchmark comparison has produced a list of gaps and the user wants them closed and verified, or before each release to re-check parity.
---

# ivan-parity · 对标监督

对标分析只说明差在哪，不保证改完。这个 skill 把差异变成一份 `parity.json` 清单，每一项都有能自动跑的检查，改完以检查结果为准，不以“我觉得改好了”为准。

## 规则

1. **一项一个可检查的结论。** 每条差异都要写成能用文件内容判断的检查：某个链接存在、某段旧文案不再出现、页面数达到数据行数、数据版本等于对标方的最新版本。写不成检查的差异，标为“人工检查”，写清楚怎么看。
2. **没有证据不算完成。** 只有 `parity_check.py` 输出 PASS 的项才能说已完成。UNKNOWN（比如没网查不到对标方的最新版本）要如实报告，不能当成通过。
3. **先修失败项，再重跑全部。** 每轮修完都重跑整张清单，防止修一项坏一项。
4. **不改检查去迁就结果。** 检查写错了可以改，但要在清单的 `changes` 里记下改了什么、为什么。
5. **对标方会变。** 对标方更新后，至少有一项检查要能发现（`upstream` 类型），并重新做一轮对标。

## 流程

1. **写清单。** 按对标分析的结论写 `parity.json`（格式见下），放在被检查项目的根目录。每项写明：标题、来自对标方的哪一点、检查。
2. **跑检查。**
   ```sh
   python3 scripts/parity_check.py parity.json --out PARITY.md
   ```
   退出码 0 表示全部通过，1 表示有失败项。
3. **逐项修。** 从 FAIL 的项开始，一次改一项，改完重跑。
4. **人工项。** 清单里 `manual` 的项（比如手机上有没有横向滚动、图片是否加载），在浏览器里实际看，结果写进 `PARITY.md` 的末尾，写明看了哪个页面、什么尺寸。
5. **交付。** 把最终的 `PARITY.md` 连同改动一起提交。汇报时列出：通过几项、失败几项、未知几项、人工检查结果。

## 清单格式

```json
{
  "title": "人选鸟图 对标花叔 birdalbum.com",
  "benchmark": "https://birdalbum.com（2026-11-06 抓取）",
  "items": [
    {
      "id": "report-link",
      "title": "每种鸟都有报错入口",
      "from": "birdalbum 每页都有 Report a mistake on GitHub",
      "checks": [
        {"type": "each", "glob": "docs/birds/*/index.html", "pattern": "issues/new\\?template=wrong-photo"}
      ]
    }
  ],
  "manual": ["手机宽度 375px 下首页和物种页没有横向滚动"],
  "changes": []
}
```

检查类型：`exists`、`contains`、`absent`、`each`（每个匹配文件都要有）、`none`（任何匹配文件都不能有）、`count`（文件数至少多少，或至少等于某个 CSV 的行数）、`json`（比较 JSON 字段）、`upstream`（对标方 GitHub 文件的最新提交是否就是我们构建时用的那个）。详细参数见 `scripts/parity_check.py` 开头的说明。

## 示例

`examples/bird-human-picks.parity.json` 是人选鸟图对标花叔 birdalbum.com 的清单，共 12 项。
