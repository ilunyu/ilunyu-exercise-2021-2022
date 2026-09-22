# 试题资源维护说明

本仓库保存一个学年的《论语》试题资源。你的职责是维护资源内容与年度 README；不要修改 Flutter 页面或主程序功能，除非用户明确要求。

## 工作范围

- 新增、修订与核对题目 JSON；维护年度 README 中的统计、考察矩阵与说明。
- 新建年度仓库时，从 `ilunyu-exercise-template` 创建；删除模板样例并更新学年、统计和矩阵。
- 维护根目录 `resource.json` 的学年、包标识、版本和仓库地址；发布标签前递增 `versionCode`。
- 每次操作前分别检查年度仓库与主项目的 Git 状态；不要混淆它们。
- 不覆盖、重置或删除未确认的资源。只有用户明确要求时才 commit、push、删除或修改远端。

## 编辑题目

优先使用 `res/utils/exercise-editor` 编辑富文本：

```bash
cd /home/lucasct/code/lunyu/res/utils/exercise-editor
conda run -n lunyu python app.py --root /绝对路径/某个学年目录 --port 8090
```

不要手工修改 `format.marks` 的 UTF-16 区间。题目 JSON 的现行规范以编辑器 README 和本仓库的 `docs/SCHEMA.md` 为准：

- 文件位于年度仓库根目录，文件名必须等于 `id`（`<id>.json`）。
- 顶层使用扁平字段：`id`、`title`、`year`、`month`、`source`、`grade`、`type`、`number`、`score`、`question`、`answer`；不得使用旧版 `metadata` 包装或字符串 DSL。
- 块类型仅为 `regular`、`material`、`note`。
- `sourceid` 为正数时必须确认为正确的《论语》章节；无法关联时只能使用 `-1`。

## 校验与交付

运行：

```bash
python3 tools/validate_exercises.py
```

发布 Android 资源包时，继续运行：

```bash
python3 tools/build_resource_package.py --source-repository https://github.com/ilunyu/[仓库名]
```

`resource.json` 不属于题目文件；生成器只读取仓库根目录中除 `resource.json` 外的题目 JSON。推送 `v<versionName>` 标签会由 GitHub Actions 创建含 `resource.ilunyupack`、`release.json` 与哈希文件的 GitHub Release。

需要验证主程序兼容性或资源更新时，在主项目根目录运行：

```bash
python3 -m unittest tools.test_build_flutter_content
python3 tools/build_flutter_content.py
```

生成器只读取每个年度仓库根目录的 JSON；`examples/` 下的模板样例不会成为正式题库。`flutter_app/assets/content/` 是可再生缓存，不提交到主项目。仅在用户要求时构建或部署 Flutter Web。

每次完成后报告：修改的年度仓库与题目、README 更新、校验结果、Git 提交/推送状态，以及是否需要重新生成资源或部署。
