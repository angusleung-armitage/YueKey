# 標點對照表 · Punctuation reference

YueKey 0.6.5 補齊 75 個傳統 `z` 符號。輸入兩字碼後按數字選字；下表是全新設定的候選次序，個人學習可能改變排序。三個平台共用同一份字典。

YueKey 0.6.5 includes all 75 traditional Z-code symbols. Enter the two-letter code and choose a numbered candidate. This is the default order in a fresh profile; personal learning can change it. Ubuntu, Kubuntu and Windows share this dictionary.

`，` / `。` 和 `﹐` / `﹒` 是不同 Unicode 字元；小形、全形及直排符號會保留各自字形，不會自動合併。

Small, full-width and vertical forms are distinct Unicode characters and remain separate candidates.

| 碼 · Code | 1 | 2 | 3 |
|---|---|---|---|
| `za` | 全形空白 · Space | ︳ | 〉 |
| `zb` | ， | ╴ | ︿ |
| `zc` | 、 | ︴ | ﹀ |
| `zd` | 。 | ﹏ | 「 |
| `ze` | ． | （ | 」 |
| `zf` | ‧ | ） | ﹁ |
| `zg` | ； | ︵ | ﹂ |
| `zh` | ： | ︶ | 『 |
| `zi` | ？ | ｛ | 』 |
| `zj` | ！ | ｝ | ﹃ |
| `zk` | ︰ | ︷ | ﹄ |
| `zl` | … | ︸ | ﹙ |
| `zm` | ‥ | 〔 | ﹚ |
| `zn` | ﹐ | 〕 | ﹛ |
| `zo` | ﹑ | ︹ | ﹜ |
| `zp` | ﹒ | ︺ | ﹝ |
| `zq` | · | 【 | ﹞ |
| `zr` | ﹔ | 】 | ‘ |
| `zs` | ﹕ | ︻ | ’ |
| `zt` | ﹖ | ︼ | “ |
| `zu` | ﹗ | 《 | ” |
| `zv` | ｜ | 》 | 〝 |
| `zw` | – | ︽ | 〞 |
| `zx` | ︱ | ︾ | ‵ |
| `zy` | — | 〈 | ′ |

## 取碼與來源 · Mapping and references

傳統倉頡 `ZXAA`–`ZXCY` 是三組各 25 個碼，對應 Big5 `A140`–`A1AC` 的 75 個位置。速成取首尾碼，例如 `ZXAF` → `ZF`。建置程式用 Python 的 CP950 編碼對應 Unicode，保留 `A145 → ‧`、`A14E → ﹑`。沒有使用會合併小形及直排符號的相容正規化。

Traditional Cangjie ZXAA–ZXCY comprises three groups of 25 positions in Big5 A140–A1AC. Quick uses the first and last letters. The build decodes these positions with Python's CP950 codec, preserving small and vertical forms instead of applying compatibility normalization. The earlier libcangjie subset contained only 38 entries; ZXBB also incorrectly repeated the wavy low line instead of ╴.

- [倉頡之友：輸入法作者發佈的傳統符號碼表 / Cangjie input-method publisher's symbol table](https://www.chinesecj.com/forum/forum.php?mod=viewthread&tid=247)
- [Unicode：Microsoft CP950 → Unicode mapping](https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WINDOWS/CP950.TXT)
- [香港速成教材：常用符號 / Hong Kong Quick-input teaching reference](https://www.wyjjmps.edu.hk/computer/chineseinput/process.htm)

各種輸入法可能採用不同字形或候選排序；回報差異時，請註明輸入碼、實際符號及預期符號。此表說明 YueKey 的映射，不表示每個輸入法的字形與排序都相同。

Input methods can differ in glyph choice and ranking. When reporting a difference, include the code, actual symbol and expected symbol. This table documents YueKey's mappings; it does not assert identical behavior in every other input method.
