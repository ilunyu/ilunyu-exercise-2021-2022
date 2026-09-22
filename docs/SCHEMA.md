# 试题 JSON 格式

每个文件代表一道题目，位于仓库根目录，且文件名必须等于 `id`：`<id>.json`。所有题目使用 UTF-8 JSON；不使用旧的顶层 `metadata` 包装，也不使用旧版字符串 DSL。

```jsonc
{
  "id": "202611-example",
  "title": "2026·示例区高三期中",
  "year": "2026-2027",
  "month": 202611,
  "source": "示例区",
  "grade": 3,
  "type": "期中",
  "number": 11,
  "score": 10,
  "question": [],
  "answer": []
}
```

## 顶层字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | 非空字符串 | 全局唯一题目 ID，且与文件名一致。 |
| `title` | 非空字符串 | 卡片与题目页展示标题。 |
| `year` | `YYYY-YYYY` | 所属学年，后一年必须是前一年加一。 |
| `month` | 整数 `YYYYMM` | 考试年月，月份为 01–12。 |
| `source` | 非空字符串 | 地区或考试来源。 |
| `grade` | 1–3 的整数 | 高一年级为 1，高三为 3。 |
| `type` | 非空字符串 | 例如“真题”“期中”“期末”“一模”“二模”。 |
| `number` | 正整数 | 试卷中的题号。 |
| `score` | 非负数字 | 本题分值。 |
| `question` | 块数组 | 题干、材料、设问与备注。 |
| `answer` | 块数组 | 答案、评分说明与解析。 |

## 块

`question` 与 `answer` 按页面显示顺序存放以下三种块：

| `type` | 必填字段 | 用途 |
| --- | --- | --- |
| `regular` | `text`、`format` | 常规正文。 |
| `note` | `text`、`format` | 评分说明、备注、解析。 |
| `material` | `sourceid`、`paragraphs` | 引用材料；可含多个段落。 |

`sourceid` 为正整数时关联《论语》原文章节；不能关联时必须写 `-1`。不要使用其他负数。

普通块示例：

```json
{ "type": "regular", "text": "阅读下面材料，完成各题。", "format": {} }
```

材料块示例：

```json
{
  "type": "material",
  "sourceid": 209,
  "paragraphs": [
    { "text": "①子曰：学而时习之，不亦说乎？", "format": {} }
  ]
}
```

## 格式

每个普通块、备注块和材料段落均有 `format` 对象；无格式必须写 `{}`。

缩进写在 `format.indent`：

```json
{ "indent": { "kind": "hanging", "level": 1 } }
```

- `kind` 只能为 `hanging`、`firstLine` 或 `paragraph`；
- `level` 是 1–8 的整数。

下划线、着重点写在 `format.marks`：

```json
{
  "marks": {
    "underline": [{ "start": 1, "end": 4 }],
    "emphasis": [{ "start": 2, "end": 5 }]
  }
}
```

区间为左闭右开 `[start, end)`，按 UTF-16 code unit 计数。请通过编辑器维护这些区间，不要手工调整。
