# 附加说明（不放入 LICENSE 的部分）

`LICENSE` 只保留 MIT 许可证的标准全文，未作任何增删。
本仓库特有的授权范围划分与第三方权利声明集中在本文件。

## 关于游戏素材的额外声明

MIT 许可**仅适用于本仓库中的源代码、文档与译文表**，即：

- `src/` `tools/` `patch/` `docs/`
- `translations/translations*.py`
- `translations/text.csv`（本项目生成的汉化文本表）

以下内容**不在 MIT 授权范围内**，其著作权属于 Traveller's Tales / Warner Bros. Interactive Entertainment 及相关权利方：

- `GAME.dat` / `GAME2.dat` 及其任何派生文件（**未入库**，见下）
- `assets/fonts/` 下的字体与文本索引文件 —— 这些是从正版游戏 DAT 中提取并改写的二进制素材，入库仅为方便持有正版的玩家，省去重做格式逆向
- 游戏的商标、Logo、剧情文本、美术资源与角色配音

完整的 `GAME.dat`（约 981 MB）与 `GAME2.dat`（约 925 MB）**不在本仓库中**，既因为它们几乎全部是原版素材，也因为远超 GitHub 单文件 100 MB 上限。请在你自己的正版副本上运行工具生成，不要期待从本仓库获取成品 DAT。

使用本项目的工具前，请自行通过 Steam 购买正版游戏。工具的作用是在你已合法拥有的游戏副本上生成中文本地化。
