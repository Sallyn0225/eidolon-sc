# 06: 她的手写签名

**What to build:** 信末是她的手写签名，从左到右写出来。はづき没有签名图，信末用信上的字体写她的名字。

见 spec「签名」。

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] 旧版 28 张签名图（CDN `stand.hmhnk.top` 的 `letters/signatures/` 下，文件名带哈希；对照 `last-letter` 分支 `letters.json` 里的 `signature_image` 找）下载回仓库的 `characters/signatures/`，按角色 id 命名。
- [ ] `characters.toml` 每位加一个可选的签名字段；角色接口带签名图地址（没有时为空）。
- [ ] 照头像的写法提供签名图接口（带 ETag，304）。
- [ ] 读一封带签名图地址或替代文字（她的名字）；前端信末有图时从左到右显出（旧版的 `sign` 动效，1.6 秒），没有图时照字写。
- [ ] 后端测试照头像接口的测试；角色加载测试覆盖签名字段可选。

## Comments

### 票 01 交接

- 读一封的 `signature` 已经是 `{"image": null, "text": 她的名字}`，前端 `LetterLayer` 的 `Signature` 有图时用图（`letter-signature` 三行高、`animate-sign`），取不到时退回照字写。后端只要填 `image`。
