# 发布检查清单

发版前逐项勾选；任一项不通过，不打 Release、不上传分卷。

## 产物齐全

- [ ] `tools/build_dist.py` 已在本机正版游戏目录上跑完，产出完整汉化包两个分卷 + SaveFix 独立包。
- [ ] 分卷命名与 `patch/payload/lib/Common.ps1` 的 `$script:PatchVersion` 一致。
- [ ] 两个分卷解到同一目录后，`安装.ps1`、`卸载.ps1`、`lib/Common.ps1`、README、`data/GAME.dat`、`data/GAME2.dat`、`data/d3d9.dll`、`data/Audio/_VO/` 齐备。
- [ ] SaveFix 包内含 `dinput8.dll` 与对应安装/卸载脚本。

## 校验通过

- [ ] `python tools/verify_dist.py` 全部通过（分卷齐备、未超 2 GB 上限、顶层目录一致、内容完整、BOM/CRLF 合规、无残留 `.bat`）。
- [ ] 包内 `.ps1` / `.txt` 带 UTF-8 BOM 且纯 CRLF。
- [ ] 未把构建缓存、临时解压目录、本机备份带进分发包。

## 文档与版本对齐

- [ ] README 与 `docs/release-and-rollback.md` 登记的版本、分卷内容一致。
- [ ] `CHANGELOG.md` 的 `[Unreleased]` 已整理为本次发版条目并补上日期。
- [ ] 未核对的游戏版本/系统兼容性不写「兼容」结论。

## 回滚路径可用

- [ ] `卸载.ps1` 与 `卸载-仅存档修复.ps1` 可还原原版文件。
- [ ] 原版备份带校验，不会把汉化版误当原版沿用。

## 门禁

- [ ] `release-check.yml` 工作流通过；本地未跑通的步骤不写入 CI。
