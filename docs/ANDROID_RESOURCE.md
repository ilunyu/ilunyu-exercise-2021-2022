# Android 资源包发布

本仓库可构建为 Android 应用通过 GitHub URL 下载的学年题库资源。应用支持粘贴仓库地址、Release 地址或 `resource.ilunyupack` 下载地址。

## 资源元数据

仓库根目录的 `resource.json` 定义资源身份和发布版本：

```json
{
  "packageId": "exercise.2026-2027",
  "kind": "exercise",
  "year": "2026-2027",
  "name": "2026—2027 学年试题",
  "versionName": "0.1.0",
  "versionCode": 1,
  "minAppVersionCode": 1,
  "sourceRepository": "https://github.com/ilunyu/ilunyu-exercise-2026-2027",
  "license": "All rights reserved"
}
```

新建年度仓库时，将 `packageId`、`year` 和名称改为该学年；每次发布时递增 `versionCode`，并更新面向用户展示的 `versionName`。年度题目 JSON 的 `year` 必须与 `resource.json.year` 一致。

## 本地构建

先校验题目，再构建资源包：

```bash
python3 tools/validate_exercises.py
python3 tools/build_resource_package.py \
  --source-repository https://github.com/ilunyu/ilunyu-exercise-2026-2027
```

构建产物位于 `dist/`：

- `resource.ilunyupack`：Android 可安装资源包；
- `release.json`：包标识、版本、大小和 SHA-256；
- `resource.ilunyupack.sha256`：资源包哈希文件。

资源包包含 `manifest.json`、题目列表与搜索索引、以及每道题目的完整 JSON。Android 应用安装时校验包内清单与文件哈希。

## GitHub Release

`.github/workflows/release-resource.yml` 会在 Pull Request、推送 main 分支和手动运行时校验并构建资源包。推送形如 `v0.1.0` 的版本标签时，工作流将三个构建产物发布到对应 GitHub Release。

发布完成后，用户可在 Android 应用的“资源与题库管理”页面点击“添加”，粘贴仓库或 Release 链接进行安装。官方资源还可由官方注册表列出。
