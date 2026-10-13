# assets/fonts —— 汉化所需的字体与文本索引

这些文件是从《乐高印第安纳琼斯 2》正版游戏 DAT 中提取并改写的**二进制素材**，
著作权属于 Traveller's Tales / Warner Bros. Interactive Entertainment 及相关权利方，
**不在 MIT 授权范围内**。放在仓库里只是为了让持有正版的玩家不必自己逆向一遍。

| 文件 | 大小 | SHA-256 (前 16) | 说明 |
|---|---|---|---|
| `font_pc.fnt` | 5,601,432 | `71af70c18b5f9166` | NFNT 主字体：拉丁+中文字形位图与度量（PS2_FONT_J_pc.fnt 内容与本文件完全相同） |
| `FONT_NXG.FT2` | 4,217,874 | `c43a586b730e0c7e` | FT2 字体：字形表 + 内嵌 2048x2048 DXT5 图集（与 FONT3_NXG.FT2 内容相同） |
| `FONT2_NXG.FT2` | 8,412,178 | `bbe75e4ac24d443d` | FT2 字体：变体 B（含更多中文字形） |
| `font.txt` | 1,826 | `08344800a78541c8` | 字体键名与回退链 |
| `PS2_FONT_J.txt` | 1,838 | `a5fe808afc0e4693` | 同上，另一处引用 |
| `english.txt` | 26,821 | `6f9390d1fda26e61` | 英文文本索引 |
| `american.txt` | 323 | `bf76d4a3e48a536c` | 美式文本索引 |
| `japanese.txt` | 27,680 | `677f3fae3ba2c038` | 日文文本索引（保持原样，未汉化） |
| `charset_full.txt` | 4,112 | `fcc4b24c998b33cb` | 本项目用到的完整字符集清单 |

合计 18,294,084 字节（17.4 MB）。

## 装到哪里

这些文件是**重建用的原料**，不是成品。跑 `tools/build_font.py` 与
`tools/build_text.py` 会把它们打进你本机的 `GAME.dat` / `GAME2.dat`。

两个 DAT 本身（约 981 MB / 925 MB）不入库 —— 它们 99.5% 是原版素材，
且远超 GitHub 单文件 100 MB 硬限制。
