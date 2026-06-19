// 商业计划书 · 路演版 pitch deck
// 定位：面向自闭症儿童家长的 AI 包裹式支撑平台
// 立论：一个自闭症孩子冲击整个家庭 —— 市场只治孩子，没人接住家长
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const Fa = require("react-icons/fa");

const C = {
  teal: "0F766E", tealDk: "0B4F4A", seafoam: "5EC4B6", mint: "CFEDE8",
  blue: "3A7BC8", blueMid: "4A90D9", blueDk: "1C3D5E", blueLight: "E3EEFA",
  cream: "FBF7F0", ink: "1F2A2E", slate: "5A6B6E", coral: "F0805A",
  gold: "F2B441", white: "FFFFFF", red: "E2674A", zebra: "F2F6F9",
};
// 统一中文字体，避免标题(Georgia)与正文(Calibri)的中文被系统替换成忽黑忽宋
const HF = "Noto Sans SC", BF = "Noto Sans SC";

async function icon(IconComponent, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(IconComponent, { color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}
const shadow = () => ({ type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.14 });

async function main() {
  const p = new pptxgen();
  p.layout = "LAYOUT_WIDE";
  p.author = "星星家庭支撑平台";
  p.title = "商业计划书 · 路演版";
  const W = 13.33, H = 7.5;

  function header(s, kicker, title, accent = C.blue) {
    s.background = { color: C.cream };
    s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.18, fill: { color: accent } });
    s.addText(kicker.toUpperCase(), { x: 0.7, y: 0.46, w: 11.9, h: 0.35, fontFace: BF, fontSize: 13, bold: true, color: C.coral, charSpacing: 3, margin: 0 });
    s.addText(title, { x: 0.7, y: 0.78, w: 11.9, h: 0.8, fontFace: HF, fontSize: 30, bold: true, color: C.ink, margin: 0 });
  }
  function pageNum(s, n) {
    s.addText(String(n).padStart(2, "0"), { x: 12.5, y: 7.0, w: 0.6, h: 0.3, align: "right", fontFace: BF, fontSize: 10, color: C.slate, margin: 0 });
  }
  // 大数字卡片
  function metric(s, x, y, w, big, small, color) {
    s.addShape(p.shapes.RECTANGLE, { x, y, w, h: 1.55, fill: { color: C.white }, shadow: shadow() });
    s.addShape(p.shapes.RECTANGLE, { x, y, w: 0.09, h: 1.55, fill: { color } });
    s.addText(big, { x: x + 0.1, y: y + 0.18, w: w - 0.2, h: 0.7, align: "center", fontFace: HF, fontSize: 30, bold: true, color, margin: 0 });
    s.addText(small, { x: x + 0.1, y: y + 0.95, w: w - 0.2, h: 0.5, align: "center", fontFace: BF, fontSize: 13, color: C.slate, margin: 0 });
  }

  const ic = {
    seed: await icon(Fa.FaSeedling, "#" + C.white),
    child: await icon(Fa.FaChild, "#" + C.white),
    heart: await icon(Fa.FaHandHoldingHeart, "#" + C.white),
  };

  // ===== S1 封面 =====
  let s = p.addSlide();
  s.background = { color: C.blueDk };
  s.addShape(p.shapes.OVAL, { x: 9.6, y: -2.4, w: 7.0, h: 7.0, fill: { color: C.blue, transparency: 30 } });
  s.addShape(p.shapes.OVAL, { x: -2.2, y: 3.8, w: 6.5, h: 6.5, fill: { color: C.teal, transparency: 25 } });
  s.addShape(p.shapes.OVAL, { x: 11.4, y: 4.6, w: 2.4, h: 2.4, fill: { color: C.coral, transparency: 30 } });
  s.addShape(p.shapes.RECTANGLE, { x: 0.78, y: 1.0, w: 2.7, h: 0.5, fill: { color: C.white, transparency: 84 } });
  s.addText("BUSINESS PLAN", { x: 0.95, y: 1.04, w: 3, h: 0.42, valign: "middle", fontFace: BF, fontSize: 13, bold: true, color: C.white, charSpacing: 3, margin: 0 });
  s.addText("让每一个", { x: 0.78, y: 2.35, w: 11, h: 0.85, fontFace: HF, fontSize: 34, color: C.mint, margin: 0 });
  s.addText("「星星家庭」都被稳稳接住", { x: 0.78, y: 3.1, w: 12, h: 1.1, fontFace: HF, fontSize: 46, bold: true, color: C.white, margin: 0 });
  s.addText("面向自闭症儿童家长的 AI 包裹式支撑平台", { x: 0.8, y: 4.4, w: 11, h: 0.5, fontFace: BF, fontSize: 18, color: C.seafoam, margin: 0 });
  // 双 chip
  s.addShape(p.shapes.RECTANGLE, { x: 0.8, y: 5.25, w: 3.4, h: 1.0, fill: { color: C.blue } });
  s.addText([{ text: "ABA 智能助手\n", options: { bold: true, fontSize: 16, color: C.white } }, { text: "帮孩子 · 科学干预", options: { fontSize: 11, color: C.blueLight } }], { x: 0.95, y: 5.35, w: 3.1, h: 0.8, fontFace: BF, lineSpacingMultiple: 1.2, margin: 0 });
  s.addShape(p.shapes.RECTANGLE, { x: 4.35, y: 5.25, w: 3.4, h: 1.0, fill: { color: C.teal } });
  s.addText([{ text: "人生教练\n", options: { bold: true, fontSize: 16, color: C.white } }, { text: "顾家长 · 心理支撑", options: { fontSize: 11, color: C.mint } }], { x: 4.5, y: 5.35, w: 3.1, h: 0.8, fontFace: BF, lineSpacingMultiple: 1.2, margin: 0 });
  s.addText("2026  ·  对外融资 / 政府公益合作", { x: 0.8, y: 6.7, w: 11, h: 0.4, fontFace: BF, fontSize: 13, color: C.seafoam, charSpacing: 1, margin: 0 });

  // ===== S2 问题：一个孩子，冲击整个家庭 =====
  s = p.addSlide();
  header(s, "我们看到的问题", "一个自闭症孩子，冲击的是整个家庭", C.coral);
  const impacts = [
    [Fa.FaYenSign, C.coral, "经济重担", "年均康复支出 5–6 万，常需一方辞职陪训"],
    [Fa.FaBatteryQuarter, C.red, "照护耗竭", "每周 20–40h 高强度干预，全年无休"],
    [Fa.FaHeartBroken, C.gold, "心理危机", "家长焦虑、抑郁检出率远高于普通人群"],
    [Fa.FaUserFriends, C.teal, "婚姻压力", "分歧、指责，离异风险上升"],
    [Fa.FaUserSlash, C.blueDk, "社交孤立", "被误解、回避社交，支持网络萎缩"],
    [Fa.FaBriefcase, C.blue, "职业中断", "晋升停滞、收入下降、返岗困难"],
  ];
  const cW = 3.85, cH = 1.65, gx = 0.25, gy = 0.28, x0 = 0.7, y0 = 1.95;
  for (let i = 0; i < impacts.length; i++) {
    const col = i % 3, row = Math.floor(i / 3);
    const x = x0 + col * (cW + gx), y = y0 + row * (cH + gy);
    const [Ic, color, t, d] = impacts[i];
    s.addShape(p.shapes.RECTANGLE, { x, y, w: cW, h: cH, fill: { color: C.white }, shadow: shadow() });
    s.addShape(p.shapes.OVAL, { x: x + 0.3, y: y + 0.32, w: 0.95, h: 0.95, fill: { color } });
    s.addImage({ data: await icon(Ic, "#" + C.white), x: x + 0.55, y: y + 0.57, w: 0.45, h: 0.45 });
    s.addText(t, { x: x + 1.45, y: y + 0.3, w: cW - 1.6, h: 0.45, fontFace: HF, fontSize: 18, bold: true, color: C.ink, margin: 0 });
    s.addText(d, { x: x + 1.45, y: y + 0.78, w: cW - 1.6, h: 0.75, fontFace: BF, fontSize: 12, color: C.slate, lineSpacingMultiple: 1.2, margin: 0 });
  }
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 6.55, w: 11.95, h: 0.6, fill: { color: C.coral } });
  s.addText("现有市场几乎只服务「孩子的康复」——而家长，长期无人接住。", { x: 0.7, y: 6.55, w: 11.95, h: 0.6, align: "center", valign: "middle", fontFace: BF, fontSize: 15, bold: true, color: C.white, margin: 0 });
  pageNum(s, 2);

  // ===== S3 解决方案：包裹式 =====
  s = p.addSlide();
  header(s, "我们的解法", "包裹式家庭支撑：一个平台，托住整个家", C.blue);
  // 外框
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 1.9, w: 11.95, h: 4.7, fill: { color: C.zebra } });
  s.addText("自闭症孩子的家庭", { x: 0.7, y: 2.0, w: 11.95, h: 0.4, align: "center", fontFace: BF, fontSize: 14, bold: true, color: C.slate, margin: 0 });
  // 左轮 ABA
  s.addShape(p.shapes.RECTANGLE, { x: 1.3, y: 2.6, w: 5.0, h: 3.6, fill: { color: C.blue }, shadow: shadow() });
  s.addShape(p.shapes.OVAL, { x: 3.45, y: 2.85, w: 0.9, h: 0.9, fill: { color: C.blueDk } });
  s.addImage({ data: ic.child, x: 3.67, y: 3.07, w: 0.46, h: 0.46 });
  s.addText("帮孩子 · ABA 智能助手", { x: 1.4, y: 3.85, w: 4.8, h: 0.5, align: "center", fontFace: HF, fontSize: 18, bold: true, color: C.white, margin: 0 });
  s.addText("· 122 项技能评估与训练\n· DTT 标准记录 + 数据看板\n· AI 问答 + 自动训练计划\n· 结构化进展报告", { x: 1.7, y: 4.4, w: 4.3, h: 1.7, fontFace: BF, fontSize: 14, color: C.blueLight, lineSpacingMultiple: 1.4, margin: 0 });
  // 右轮 教练
  s.addShape(p.shapes.RECTANGLE, { x: 7.05, y: 2.6, w: 5.0, h: 3.6, fill: { color: C.teal }, shadow: shadow() });
  s.addShape(p.shapes.OVAL, { x: 9.2, y: 2.85, w: 0.9, h: 0.9, fill: { color: C.tealDk } });
  s.addImage({ data: ic.heart, x: 9.42, y: 3.07, w: 0.46, h: 0.46 });
  s.addText("顾家长 · 人生教练（ACT）", { x: 7.15, y: 3.85, w: 4.8, h: 0.5, align: "center", fontFace: HF, fontSize: 18, bold: true, color: C.white, margin: 0 });
  s.addText("· 24h AI 教练对话\n· 情绪追踪 + 危机识别\n· 个性化成长路径\n· 10 大主题知识库", { x: 7.45, y: 4.4, w: 4.3, h: 1.7, fontFace: BF, fontSize: 14, color: C.mint, lineSpacingMultiple: 1.4, margin: 0 });
  // 中间联结
  s.addShape(p.shapes.OVAL, { x: 6.36, y: 3.9, w: 0.9, h: 0.9, fill: { color: C.gold } });
  s.addText("SSO", { x: 6.36, y: 4.05, w: 0.9, h: 0.6, align: "center", fontFace: BF, fontSize: 12, bold: true, color: C.white, margin: 0 });
  pageNum(s, 3);

  // ===== S4 市场规模 =====
  s = p.addSlide();
  header(s, "市场规模", "千亿康复市场，千万级家长支持需求", C.blue);
  metric(s, 0.7, 2.0, 2.85, "1300万+", "孤独症患者", C.blue);
  metric(s, 3.75, 2.0, 2.85, "200–300万", "0–14 岁儿童", C.teal);
  metric(s, 6.8, 2.0, 2.85, "20万/年", "新增患者", C.coral);
  metric(s, 9.85, 2.0, 2.8, "30万", "康复师缺口", C.gold);
  // 市场层
  s.addText("康复市场规模（亿元 / 年）", { x: 0.7, y: 3.9, w: 11.9, h: 0.4, fontFace: BF, fontSize: 14, bold: true, color: C.ink, margin: 0 });
  const mk = [["小龄康复 0–6 岁", 600, C.blueLight, C.blue], ["0–18 岁孤独症康复", 1800, C.blue, C.white], ["三项发展障碍康复", 9600, C.blueDk, C.white]];
  const barY = [4.45, 5.35, 6.25];
  mk.forEach((row, i) => {
    const [t, v, fill, tc] = row;
    const w = 1.6 + (v / 9600) * 9.8;
    s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: barY[i], w, h: 0.6, fill: { color: fill } });
    s.addText(`${t}    ${v.toLocaleString()} 亿`, { x: 0.85, y: barY[i], w: w - 0.2, h: 0.6, valign: "middle", fontFace: BF, fontSize: 13, bold: true, color: tc, margin: 0 });
  });
  s.addText("数据来源：北大医疗脑健康《2020 年度儿童发展障碍康复报告》、中国残联 2023 普查", { x: 0.7, y: 7.0, w: 11.9, h: 0.3, fontFace: BF, fontSize: 10, italic: true, color: C.slate, margin: 0 });
  pageNum(s, 4);

  // ===== S5 TAM / SAM / SOM（原生矢量漏斗）=====
  s = p.addSlide();
  header(s, "市场空间", "从整体市场到我们可获取的市场", C.blue);
  // 漏斗：三段梯形居中堆叠，宽度自上而下递减
  const fc = 3.6;          // 漏斗中心 x
  const fyTop = 2.05, tierH = 1.45, fgap = 0.06;
  const hwTop = 2.7, hwBot = 0.75;
  const hwAt = (k) => hwTop - (hwTop - hwBot) * (k / 3);  // k=0..3
  const tiers = [
    ["TAM", "整体市场", "约 1800 亿/年", C.blueDk, "0–18 岁孤独症康复 + 千万级家长心理支持需求"],
    ["SAM", "可服务市场", "数字化 + SaaS", C.blue, "数字化干预与家长支持 SaaS，2025 数字疗法破 10 亿且高增长"],
    ["SOM", "可获取市场", "5–8 万付费家庭", C.teal, "3 年内聚焦 6 城 + 政府购买（基于渗透率假设）"],
  ];
  const cardX = 7.1, cardW = 5.5, cardH = 1.3;
  for (let i = 0; i < 3; i++) {
    const yTier = fyTop + i * (tierH + fgap);
    const hwT = hwAt(i), hwB = hwAt(i + 1);
    const [tag, name, big, col, desc] = tiers[i];
    // 梯形：用四点自定义几何（pptxgen custGeom 通过 points）
    const x = fc - hwT, w = hwT * 2;
    s.addShape("custGeom", {
      x, y: yTier, w, h: tierH, fill: { color: col },
      points: [
        { x: 0, y: 0 },
        { x: w, y: 0 },
        { x: hwT + hwB, y: tierH },
        { x: hwT - hwB, y: tierH },
        { close: true },
      ],
    });
    const ymid = yTier + tierH / 2;
    s.addText(tag, { x: fc - hwT, y: ymid - 0.42, w: hwT * 2, h: 0.5, align: "center", fontFace: HF, fontSize: 22, bold: true, color: C.white, margin: 0 });
    s.addText(name, { x: fc - hwT, y: ymid + 0.05, w: hwT * 2, h: 0.35, align: "center", fontFace: BF, fontSize: 12, color: C.white, margin: 0 });
    // 右侧数值卡片
    const cy = yTier + (tierH - cardH) / 2;
    s.addShape(p.shapes.RECTANGLE, { x: cardX, y: cy, w: cardW, h: cardH, fill: { color: C.white }, line: { color: col, width: 1.25 }, shadow: shadow() });
    s.addShape(p.shapes.RECTANGLE, { x: cardX, y: cy, w: 0.12, h: cardH, fill: { color: col } });
    s.addText([{ text: tag + "  ·  ", options: { bold: true, color: col, fontSize: 16 } }, { text: big, options: { bold: true, color: C.ink, fontSize: 16 } }], { x: cardX + 0.35, y: cy + 0.18, w: cardW - 0.6, h: 0.5, fontFace: HF, margin: 0 });
    s.addText(desc, { x: cardX + 0.35, y: cy + 0.68, w: cardW - 0.6, h: 0.55, fontFace: BF, fontSize: 12, color: C.slate, lineSpacingMultiple: 1.15, margin: 0 });
  }
  pageNum(s, 5);

  // ===== S6 政策红利 =====
  s = p.addSlide();
  header(s, "为什么是现在", "政策红利：从「鼓励」到「政府购买」", C.teal);
  s.addText("2024 年 7 月，七部门联合印发《孤独症儿童关爱促进行动实施方案（2024—2028 年）》，其中「家庭暖心行动」与我们高度契合：", { x: 0.7, y: 1.95, w: 11.9, h: 0.7, fontFace: BF, fontSize: 15, color: C.ink, lineSpacingMultiple: 1.3, margin: 0 });
  const pol = [
    [Fa.FaHandHoldingUsd, "家长送训补贴", "拓展救助内容，确保「应救尽救」"],
    [Fa.FaHandsHelping, "政府购买服务", "心理疏导、托养、喘息、社区支持"],
    [Fa.FaBook, "家长培训", "编写家长手册，普遍开展家长培训"],
    [Fa.FaNotesMedical, "纳入医保", "29 项医疗康复项目纳入医保支付"],
  ];
  const pW = 2.85, pgx = 0.22, px0 = 0.7, pY = 2.85, pH = 2.9;
  for (let i = 0; i < pol.length; i++) {
    const x = px0 + i * (pW + pgx);
    const [Ic, t, d] = pol[i];
    s.addShape(p.shapes.RECTANGLE, { x, y: pY, w: pW, h: pH, fill: { color: C.white }, shadow: shadow() });
    s.addShape(p.shapes.OVAL, { x: x + pW / 2 - 0.55, y: pY + 0.45, w: 1.1, h: 1.1, fill: { color: C.teal } });
    s.addImage({ data: await icon(Ic, "#" + C.white), x: x + pW / 2 - 0.28, y: pY + 0.72, w: 0.56, h: 0.56 });
    s.addText(t, { x: x + 0.2, y: pY + 1.7, w: pW - 0.4, h: 0.5, align: "center", fontFace: HF, fontSize: 16, bold: true, color: C.ink, margin: 0 });
    s.addText(d, { x: x + 0.25, y: pY + 2.2, w: pW - 0.5, h: 0.65, align: "center", fontFace: BF, fontSize: 12, color: C.slate, lineSpacingMultiple: 1.2, margin: 0 });
  }
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 6.1, w: 11.95, h: 0.62, fill: { color: C.tealDk } });
  s.addText("政策正把「支持家长」变为可付费的公共服务采购项 —— 这是我们 G 端收入与公益申报的政策抓手。", { x: 0.7, y: 6.1, w: 11.95, h: 0.62, align: "center", valign: "middle", fontFace: BF, fontSize: 14, color: C.white, margin: 0 });
  pageNum(s, 6);

  // ===== S7 竞争格局 =====
  s = p.addSlide();
  header(s, "竞争格局", "所有人都在「教孩子」，没人接住家长", C.blue);
  const rows = [
    ["代表机构", "模式", "融资 / 规模", "服务对象"],
    ["大米和小米", "线下连锁 + RICE 体系", "融资 1.4 亿+，30+ 中心", "孩子"],
    ["东方启音", "语言康复连锁", "累计约 2.8 亿美元", "孩子"],
    ["恩启 / 五彩鹿", "互联网/连锁康复", "数千万元级 / 未融资", "孩子"],
    ["ALSOLIFE", "数字化干预 + AI", "AI 成本降至数元/节", "孩子"],
    ["本项目", "AI 包裹式家庭支撑", "—", "孩子 + 家长"],
  ];
  const colW = [2.6, 3.6, 3.6, 2.15], tx = 0.7; let ty = 2.1;
  rows.forEach((r, ri) => {
    let cx = tx;
    const isH = ri === 0, isUs = ri === rows.length - 1;
    const rh = 0.72;
    for (let ci = 0; ci < r.length; ci++) {
      const fill = isH ? C.blue : isUs ? C.mint : (ri % 2 ? C.white : C.zebra);
      const tc = isH ? C.white : C.ink;
      s.addShape(p.shapes.RECTANGLE, { x: cx, y: ty, w: colW[ci], h: rh, fill: { color: fill }, line: { color: C.cream, width: 1 } });
      s.addText(r[ci], { x: cx + 0.15, y: ty, w: colW[ci] - 0.3, h: rh, valign: "middle", fontFace: BF, fontSize: 13, bold: isH || isUs || ci === 0, color: tc, margin: 0 });
      cx += colW[ci];
    }
    ty += rh;
  });
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 6.55, w: 11.95, h: 0.6, fill: { color: C.blueDk } });
  s.addText("它们以重资产线下连锁服务「孩子」；我们以 AI 轻资产服务「家长」—— 互补而非竞争，它们的客户正是我们的客户。", { x: 0.7, y: 6.55, w: 11.95, h: 0.6, align: "center", valign: "middle", fontFace: BF, fontSize: 13, color: C.white, margin: 0 });
  pageNum(s, 7);

  // ===== S8 商业模式 =====
  s = p.addSlide();
  header(s, "商业模式", "C / B / G 三条收入线协同", C.blue);
  const biz = [
    [C.blue, "C 端家庭订阅", "自闭症儿童家庭", "会员订阅 + 增值\n约 599–999 元/年", "验证需求与口碑"],
    [C.teal, "B 端机构合作", "康复机构 / 医院", "SaaS 授权 + 分成\n约 200–500 元/家庭/年", "借机构家庭放量"],
    [C.gold, "G 端政府购买", "残联 / 政府 / 公益", "政府购买服务\n按项目打包", "降低付费门槛"],
  ];
  const bW = 3.85, bgx = 0.28, bx0 = 0.7, bY = 2.1, bH = 4.0;
  for (let i = 0; i < biz.length; i++) {
    const x = bx0 + i * (bW + bgx);
    const [col, t, who, form, role] = biz[i];
    s.addShape(p.shapes.RECTANGLE, { x, y: bY, w: bW, h: bH, fill: { color: C.white }, shadow: shadow() });
    s.addShape(p.shapes.RECTANGLE, { x, y: bY, w: bW, h: 0.85, fill: { color: col } });
    s.addText(t, { x, y: bY, w: bW, h: 0.85, align: "center", valign: "middle", fontFace: HF, fontSize: 19, bold: true, color: C.white, margin: 0 });
    s.addText([{ text: "客户\n", options: { bold: true, color: col, fontSize: 12 } }, { text: who, options: { color: C.ink, fontSize: 14 } }], { x: x + 0.3, y: bY + 1.05, w: bW - 0.6, h: 0.9, fontFace: BF, lineSpacingMultiple: 1.2, margin: 0 });
    s.addText([{ text: "形态\n", options: { bold: true, color: col, fontSize: 12 } }, { text: form, options: { color: C.ink, fontSize: 14 } }], { x: x + 0.3, y: bY + 2.0, w: bW - 0.6, h: 1.1, fontFace: BF, lineSpacingMultiple: 1.2, margin: 0 });
    s.addShape(p.shapes.RECTANGLE, { x: x + 0.3, y: bY + 3.25, w: bW - 0.6, h: 0.55, fill: { color: C.zebra } });
    s.addText(role, { x: x + 0.3, y: bY + 3.25, w: bW - 0.6, h: 0.55, align: "center", valign: "middle", fontFace: BF, fontSize: 13, bold: true, color: col, margin: 0 });
  }
  pageNum(s, 8);

  // ===== S9 落地路径 =====
  s = p.addSlide();
  header(s, "落地路径", "三步走：打磨验证 → 复制合作 → 规模壁垒", C.blue);
  const phases = [
    [C.blue, "第 1 年 · 打磨验证", ["双 App 数据闭环", "3 城试点 1–2 万家庭", "签约 2–3 家头部机构"]],
    [C.teal, "第 2 年 · 复制合作", ["扩展至 6 城", "接入政府购买项目", "B 端 SaaS 标准化"]],
    [C.gold, "第 3 年 · 规模壁垒", ["全国 15+ 城覆盖", "数据/算法壁垒成型", "家长社区生态"]],
  ];
  const fW = 3.85, fgx = 0.28, fx0 = 0.7, fY = 2.3, fH = 3.7;
  for (let i = 0; i < phases.length; i++) {
    const x = fx0 + i * (fW + fgx);
    const [col, t, items] = phases[i];
    s.addShape(p.shapes.RECTANGLE, { x, y: fY, w: fW, h: fH, fill: { color: C.white }, shadow: shadow() });
    s.addShape(p.shapes.RECTANGLE, { x, y: fY, w: fW, h: 0.85, fill: { color: col } });
    s.addText(t, { x, y: fY, w: fW, h: 0.85, align: "center", valign: "middle", fontFace: HF, fontSize: 16, bold: true, color: C.white, margin: 0 });
    s.addText(items.map(it => ({ text: "· " + it + "\n", options: {} })), { x: x + 0.35, y: fY + 1.1, w: fW - 0.6, h: 2.4, fontFace: BF, fontSize: 14, color: C.ink, lineSpacingMultiple: 1.6, margin: 0 });
    if (i < phases.length - 1) s.addText("›", { x: x + fW - 0.02, y: fY + 1.4, w: fgx, h: 0.6, align: "center", fontFace: HF, fontSize: 26, bold: true, color: C.gold, margin: 0 });
  }
  pageNum(s, 9);

  // ===== S10 财务预测 =====
  s = p.addSlide();
  header(s, "财务预测（基于假设）", "三年营收预测 · 单位：万元", C.blue);
  // 堆叠柱
  const yrs = ["第 1 年", "第 2 年", "第 3 年"];
  const cRev = [180, 720, 2100], bRev = [120, 520, 1500], gRev = [200, 600, 1600];
  const tot = [500, 1840, 5200];
  const chX = 1.6, chBase = 6.2, chTop = 2.4, maxV = 5200, colWb = 1.7, gap = 1.9;
  yrs.forEach((yr, i) => {
    const x = chX + i * (colWb + gap);
    let yb = chBase;
    [[cRev[i], C.blue], [bRev[i], C.teal], [gRev[i], C.gold]].forEach(([v, col]) => {
      const h = (v / maxV) * (chBase - chTop);
      s.addShape(p.shapes.RECTANGLE, { x, y: yb - h, w: colWb, h, fill: { color: col } });
      yb -= h;
    });
    s.addText(tot[i].toLocaleString() + " 万", { x: x - 0.3, y: yb - 0.45, w: colWb + 0.6, h: 0.4, align: "center", fontFace: HF, fontSize: 15, bold: true, color: C.ink, margin: 0 });
    s.addText(yr, { x: x - 0.3, y: chBase + 0.1, w: colWb + 0.6, h: 0.4, align: "center", fontFace: BF, fontSize: 14, bold: true, color: C.ink, margin: 0 });
  });
  // 图例
  const leg = [["C 端家庭订阅", C.blue], ["B 端机构合作", C.teal], ["G 端政府购买", C.gold]];
  leg.forEach(([t, col], i) => {
    const ly = 2.6 + i * 0.6;
    s.addShape(p.shapes.RECTANGLE, { x: 9.2, y: ly, w: 0.35, h: 0.35, fill: { color: col } });
    s.addText(t, { x: 9.7, y: ly - 0.05, w: 3, h: 0.45, valign: "middle", fontFace: BF, fontSize: 14, color: C.ink, margin: 0 });
  });
  s.addText("假设：付费家庭 0.3 万 → 3–5 万；C 端年客单价约 600 元；G 端按地方购买服务打包。", { x: 0.7, y: 6.9, w: 11.9, h: 0.4, fontFace: BF, fontSize: 11, italic: true, color: C.slate, margin: 0 });
  pageNum(s, 10);

  // ===== S11 融资计划 =====
  s = p.addSlide();
  header(s, "融资计划", "本轮融资用途", C.blue);
  s.addText("本轮拟引入战略 / 财务投资，用于产品打磨、试点城市落地与政府 / 机构合作拓展。具体融资额与估值待与投资方沟通确定。", { x: 0.7, y: 1.95, w: 11.9, h: 0.7, fontFace: BF, fontSize: 15, color: C.ink, lineSpacingMultiple: 1.3, margin: 0 });
  const use = [
    [40, C.blue, "产品与研发", "AI 引擎、安全层、数据平台与合规"],
    [30, C.teal, "市场与渠道", "B 端机构、G 端政府、家长社群"],
    [20, C.gold, "团队建设", "心理/ABA 专业、算法与产品人才"],
    [10, C.coral, "运营储备", "试点城市落地与日常运营"],
  ];
  let uy = 2.95;
  use.forEach(([pct, col, t, d]) => {
    s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: uy, w: 0.9, h: 0.9, fill: { color: col } });
    s.addText(pct + "%", { x: 0.7, y: uy, w: 0.9, h: 0.9, align: "center", valign: "middle", fontFace: HF, fontSize: 17, bold: true, color: C.white, margin: 0 });
    s.addShape(p.shapes.RECTANGLE, { x: 1.75, y: uy, w: (pct / 40) * 9.5, h: 0.9, fill: { color: col, transparency: 70 } });
    s.addText([{ text: t + "    ", options: { bold: true, color: C.ink, fontSize: 16 } }, { text: d, options: { color: C.slate, fontSize: 13 } }], { x: 1.95, y: uy, w: 9.5, h: 0.9, valign: "middle", fontFace: BF, margin: 0 });
    uy += 1.05;
  });
  pageNum(s, 11);

  // ===== S12 结语 =====
  s = p.addSlide();
  s.background = { color: C.blueDk };
  s.addShape(p.shapes.OVAL, { x: -2.0, y: -2.2, w: 6.5, h: 6.5, fill: { color: C.teal, transparency: 20 } });
  s.addShape(p.shapes.OVAL, { x: 10.3, y: 3.8, w: 5.0, h: 5.0, fill: { color: C.blue, transparency: 15 } });
  s.addShape(p.shapes.OVAL, { x: 0.78, y: 1.3, w: 1.0, h: 1.0, fill: { color: C.coral } });
  s.addImage({ data: ic.seed, x: 1.0, y: 1.52, w: 0.56, h: 0.56 });
  s.addText("市场只治孩子，\n我们接住整个家庭。", { x: 0.78, y: 2.7, w: 11.5, h: 2.0, fontFace: HF, fontSize: 42, bold: true, color: C.white, lineSpacingMultiple: 1.08, margin: 0 });
  s.addText("用 AI 把专业的 ABA 干预与温暖的 ACT 陪伴规模化、可负担——\n让每一个「星星家庭」都被稳稳接住。", { x: 0.8, y: 5.0, w: 11, h: 1.0, fontFace: BF, fontSize: 17, color: C.mint, lineSpacingMultiple: 1.3, margin: 0 });
  s.addShape(p.shapes.RECTANGLE, { x: 0.8, y: 6.4, w: 0.5, h: 0.06, fill: { color: C.gold } });
  s.addText("星星家庭支撑平台  ·  ABA 智能助手 + 人生教练", { x: 0.8, y: 6.55, w: 11, h: 0.4, fontFace: BF, fontSize: 14, bold: true, color: C.seafoam, charSpacing: 1, margin: 0 });

  await p.writeFile({ fileName: "星星家庭_商业计划书_路演版.pptx" });
  console.log("done");
}
main().catch((e) => { console.error(e); process.exit(1); });
