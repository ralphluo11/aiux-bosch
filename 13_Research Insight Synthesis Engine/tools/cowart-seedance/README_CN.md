# Cowart × Seedance 视频 POC

状态：`POC / Product Hypothesis`。它没有修改 Research Copilot，也不会把密钥写进 Cowart。

## 能做什么

1. 接收由 Cowart HTML 页面渲染得到的 PNG/JPEG 首帧。
2. 调用火山方舟视频生成任务 API。
3. 轮询异步任务。
4. 将生成的 MP4 下载到当前 Cowart 页面的 `assets/` 目录。

当前 Cowart MCP 没有原生视频 shape 写入工具，因此最后一步先保存文件。要让视频直接出现在画布上，需要在 Cowart 插件源码中增加 `insert_cowart_video`，或增加能读取本地 MP4 的视频预览组件。

## 配置

```bash
export ARK_API_KEY='你的方舟 API Key'
export SEEDANCE_MODEL='doubao-seedance-1-5-pro-251215'
```

模型 ID 以你在火山方舟控制台实际开通的版本为准。不要提交真实 Key。

## 使用

先将目标 Cowart 页渲染成图片，然后运行：

```bash
python3 tools/cowart-seedance/seedance_adapter.py \
  --image canvas/pages/page/assets/slide-01-frame.png \
  --prompt '保持所有文字、品牌色和版式不变。评分条从左向右展开，关键数字轻微上浮，镜头缓慢推进；不要重绘或扭曲文字。' \
  --duration 5 \
  --ratio 16:9 \
  --output canvas/pages/page/assets/slide-01-seedance.mp4
```

如果只想提交任务而不等待：

```bash
python3 tools/cowart-seedance/seedance_adapter.py ... --submit-only
```

## Cowart 插件接线建议

插件侧的“生成视频”动作应：

1. 读取当前页或当前选中 HTML draft。
2. 用浏览器截图能力渲染为 1024 × 576 PNG。
3. 让用户确认提示词、时长、比例与模型。
4. 在服务端调用本适配器逻辑；前端永远不接触 `ARK_API_KEY`。
5. 显示 `queued / running / succeeded / failed`。
6. 成功后调用待新增的 `insert_cowart_video`，或在旁边插入本地视频预览卡。

## 已知限制

- 生成模型可能重绘文字。对信息密集型 PPT，推荐只生成背景/产品运动，再用 Remotion 或 HTML 将原始文字和图表叠回视频。
- 视频 URL 通常是临时地址，因此成功后立即下载到项目资源目录。
- 真实人物素材必须满足平台授权和合规要求。
