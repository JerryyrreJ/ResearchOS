# ResearchOS AIY Hackathon Roadshow

这个分支同时提供可直接发送的单文件 HTML 和可继续修改的源文件。

## 直接发送

- `ResearchOS_AIY_Hackathon_10页路演_可直接打开.html`
- 图片已经 Base64 内嵌，下载后可直接打开，不需要其他文件。

## 继续修改

- `editable-source/index.html`：未内嵌素材的可编辑 HTML。
- `editable-source/assets/`：路演使用的全部图片与 GIF 素材。
- `editable-source/tools/build-standalone-pitch.mjs`：重新生成单文件 HTML 的编译脚本。
- `editable-source/tests/standalone-pitch.test.mjs`：素材内嵌测试。

在仓库根目录运行：

```bash
node editable-source/tools/build-standalone-pitch.mjs \
  editable-source/index.html \
  ResearchOS_AIY_Hackathon_10页路演_可直接打开.html
```

修改时请保持 `index.html` 与 `assets/` 的相对目录关系。
