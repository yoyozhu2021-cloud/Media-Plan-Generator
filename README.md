# Media Plan Generator

这是一个可直接分享的网页工具：用户打开网址，粘贴 Strategy JSON，点击生成，就能看到 Media Plan 表格并下载 CSV。

## 分享版部署

本项目已支持 GitHub Pages。部署后，别人只需要打开 GitHub Pages 网址即可使用，不需要安装 Python，也不需要本地服务器。

## 本地预览

直接双击 `index.html`，或用浏览器打开它即可。

## 输出字段

- Market
- Channel
- Campaign Name
- Funnel Stage
- Audience
- Budget
- KPI Target
- Creative Angle
- Expected CPL Range
- Notes

## 转换规则

工具只按结构化 JSON 转换，不自由发挥：

- `market_insight` 生成 Market 和 Notes
- `funnel` 分配 Funnel Stage 和 Channel
- `budget_split` 生成 Budget
- `kpi_forecast` 生成 KPI Target 和 Expected CPL Range
- `creative_strategy` 生成 Creative Angle
- `channel_strategy` 生成 Notes
