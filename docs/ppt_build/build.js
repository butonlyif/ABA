const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const Fa = require("react-icons/fa");

// ---------- palette ----------
// 通用 + 教练（绿）+ ABA（蓝，匹配主应用界面 #4A90D9 / #3A7BC8）
const C = {
  teal: "0F766E", tealDk: "0B4F4A", seafoam: "5EC4B6", mint: "CFEDE8",
  blue: "3A7BC8", blueMid: "4A90D9", blueDk: "1C3D5E", blueLight: "E3EEFA",
  cream: "FBF7F0", ink: "1F2A2E", slate: "5A6B6E", coral: "F0805A",
  gold: "F2B441", white: "FFFFFF",
};
// 统一中文字体，避免标题(Georgia)与正文(Calibri)的中文被系统替换成忽黑忽宋
const HF = "Noto Sans SC", BF = "Noto Sans SC";

async function icon(IconComponent, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(IconComponent, { color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}
const mkShadow = () => ({ type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.14 });

async function main() {
  const p = new pptxgen();
  p.layout = "LAYOUT_WIDE";
  p.author = "ABA智能助手";
  p.title = "ABA智能助手 + 人生教练 — 产品介绍";
  const W = 13.33, H = 7.5;

  const ic = {
    seedling: await icon(Fa.FaSeedling, "#" + C.white),
    childW: await icon(Fa.FaChild, "#" + C.white),
    handW: await icon(Fa.FaHandHoldingHeart, "#" + C.white),
    book: await icon(Fa.FaBookOpen, "#" + C.blue),
  };

  // ---- helpers ----
  function lightHeader(slide, kicker, title, accent = C.teal) {
    slide.background = { color: C.cream };
    slide.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.18, fill: { color: accent } });
    slide.addText(kicker.toUpperCase(), { x: 0.7, y: 0.46, w: 11.9, h: 0.35, fontFace: BF, fontSize: 13, bold: true, color: C.coral, charSpacing: 3, margin: 0 });
    slide.addText(title, { x: 0.7, y: 0.78, w: 11.9, h: 0.8, fontFace: HF, fontSize: 30, bold: true, color: C.ink, margin: 0 });
  }
  async function chapterDivider(label, title, subtitle, iconData, bg, circle) {
    const s = p.addSlide();
    s.background = { color: bg };
    s.addShape(p.shapes.OVAL, { x: 9.6, y: -2.2, w: 6.5, h: 6.5, fill: { color: circle } });
    s.addShape(p.shapes.OVAL, { x: 11.2, y: 3.8, w: 4.0, h: 4.0, fill: { color: circle, transparency: 45 } });
    s.addShape(p.shapes.OVAL, { x: 0.75, y: 2.0, w: 1.5, h: 1.5, fill: { color: C.coral } });
    s.addImage({ data: iconData, x: 1.1, y: 2.35, w: 0.8, h: 0.8 });
    s.addText(label.toUpperCase(), { x: 0.78, y: 3.7, w: 9, h: 0.4, fontFace: BF, fontSize: 15, bold: true, color: C.gold, charSpacing: 4, margin: 0 });
    s.addText(title, { x: 0.75, y: 4.1, w: 10.5, h: 1.1, fontFace: HF, fontSize: 44, bold: true, color: C.white, margin: 0 });
    s.addText(subtitle, { x: 0.78, y: 5.35, w: 10.4, h: 0.9, fontFace: BF, fontSize: 17, color: C.white, lineSpacingMultiple: 1.25, margin: 0 });
    return s;
  }

  // ===== S1 Title =====
  let s = p.addSlide();
  s.background = { color: C.tealDk };
  s.addShape(p.shapes.OVAL, { x: 9.4, y: -2.2, w: 6.5, h: 6.5, fill: { color: C.teal } });
  s.addShape(p.shapes.OVAL, { x: 11.0, y: 3.6, w: 4.2, h: 4.2, fill: { color: C.seafoam, transparency: 35 } });
  s.addShape(p.shapes.OVAL, { x: -1.6, y: 4.6, w: 4.0, h: 4.0, fill: { color: C.teal, transparency: 30 } });
  s.addShape(p.shapes.OVAL, { x: 0.75, y: 0.7, w: 0.95, h: 0.95, fill: { color: C.coral } });
  s.addImage({ data: ic.seedling, x: 0.97, y: 0.92, w: 0.5, h: 0.5 });
  s.addText("ABA 智能助手", { x: 1.85, y: 0.78, w: 6, h: 0.8, fontFace: HF, fontSize: 22, bold: true, color: C.white, valign: "middle", margin: 0 });
  s.addText("陪孩子成长，也照顾好你自己", { x: 0.78, y: 2.35, w: 10, h: 0.5, fontFace: BF, fontSize: 18, color: C.seafoam, charSpacing: 1, margin: 0 });
  s.addText("一个账号，两个助手", { x: 0.75, y: 2.78, w: 11, h: 1.4, fontFace: HF, fontSize: 50, bold: true, color: C.white, margin: 0 });
  s.addText([
    { text: "ABA 智能助手", options: { bold: true, color: C.white } }, { text: " —— 面向孩子的科学干预    ·    ", options: { color: C.mint } },
    { text: "人生教练", options: { bold: true, color: C.white } }, { text: " —— 面向家长自己的成长", options: { color: C.mint } },
  ], { x: 0.78, y: 4.35, w: 11.5, h: 0.6, fontFace: BF, fontSize: 17, margin: 0 });
  s.addText("基于 ABA（应用行为分析）+ ACT（接纳与承诺疗法）专业知识库，浏览器打开即用。", { x: 0.78, y: 5.15, w: 11, h: 0.6, fontFace: BF, fontSize: 15, color: C.mint, margin: 0 });
  s.addText("面向自闭症儿童家庭 · 网页访问 · v1.4.0", { x: 0.78, y: 6.78, w: 9, h: 0.4, fontFace: BF, fontSize: 13, color: C.seafoam, charSpacing: 1, margin: 0 });

  // ===== S2 为什么（双面）=====
  s = p.addSlide();
  lightHeader(s, "为什么需要它", "确诊之后，孩子和家长都需要支持", C.teal);
  const cols = [
    { x: 0.7, head: "孩子这边", icon: Fa.FaChild, color: C.blue,
      rows: [["知识门槛高", "刚接触 ABA，不知道从何学起、目标怎么定"], ["记录负担重", "训练数据靠手记，难统计、难看趋势"], ["缺即时指导", "孩子突发行为问题，身边没人能立刻问"]] },
    { x: 6.95, head: "家长这边", icon: Fa.FaHeart, color: C.coral,
      rows: [["长期高压", "自闭症家长焦虑、抑郁、压力水平显著偏高"], ["容易耗竭", "把全部精力给孩子，丢了自己、濒临 burnout"], ["孤立无援", "「身边都是人，却没人真正理解我」"]] },
  ];
  for (const col of cols) {
    s.addShape(p.shapes.RECTANGLE, { x: col.x, y: 1.75, w: 5.68, h: 4.95, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.RECTANGLE, { x: col.x, y: 1.75, w: 5.68, h: 0.12, fill: { color: col.color } });
    s.addShape(p.shapes.OVAL, { x: col.x + 0.35, y: 2.1, w: 0.8, h: 0.8, fill: { color: col.color } });
    s.addImage({ data: await icon(col.icon, "#" + C.white), x: col.x + 0.55, y: 2.3, w: 0.4, h: 0.4 });
    s.addText(col.head, { x: col.x + 1.3, y: 2.18, w: 4, h: 0.6, fontFace: HF, fontSize: 22, bold: true, color: C.ink, valign: "middle", margin: 0 });
    let ry = 3.15;
    for (const [t, d] of col.rows) {
      s.addText("•", { x: col.x + 0.4, y: ry, w: 0.3, h: 0.4, fontFace: BF, fontSize: 18, bold: true, color: col.color, margin: 0 });
      s.addText([{ text: t + "  ", options: { bold: true, color: C.ink } }, { text: d, options: { color: C.slate } }], { x: col.x + 0.7, y: ry, w: 4.75, h: 1.0, fontFace: BF, fontSize: 14, lineSpacingMultiple: 1.15, margin: 0 });
      ry += 1.12;
    }
  }

  // ===== S3 产品全景 =====
  s = p.addSlide();
  lightHeader(s, "产品全景", "一个账号，两个助手，免登录互跳", C.teal);
  s.addText("登录一次，在「帮孩子」和「顾自己」之间一键整页切换，数据互通、账号共享。", { x: 0.7, y: 1.6, w: 11.9, h: 0.5, fontFace: BF, fontSize: 15, color: C.slate, margin: 0 });
  const apps = [
    { x: 0.9, name: "ABA 智能助手", port: "蓝色界面 · 网页 8501", who: "面向孩子", iconData: ic.childW, color: C.blue, pts: ["AI 问答 · 孩子档案 · 个案记忆", "训练记录闭环：评估→任务→试次→报告", "数据看板 · 自动周/月报告"] },
    { x: 7.05, name: "人生教练", port: "绿色界面 · 网页 8503", who: "面向家长本人", iconData: ic.handW, color: C.teal, pts: ["ACT 教练对话 · 八种情绪识别", "议题驱动的个性化成长路径（5 类模板）", "情绪追踪 · AI 周报 · 心理知识库"] },
  ];
  for (const a of apps) {
    s.addShape(p.shapes.RECTANGLE, { x: a.x, y: 2.3, w: 5.4, h: 3.7, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.RECTANGLE, { x: a.x, y: 2.3, w: 5.4, h: 0.12, fill: { color: a.color } });
    s.addShape(p.shapes.OVAL, { x: a.x + 0.35, y: 2.65, w: 1.0, h: 1.0, fill: { color: a.color } });
    s.addImage({ data: a.iconData, x: a.x + 0.6, y: 2.9, w: 0.5, h: 0.5 });
    s.addText(a.name, { x: a.x + 1.5, y: 2.66, w: 3.7, h: 0.45, fontFace: HF, fontSize: 20, bold: true, color: C.ink, margin: 0 });
    s.addText([{ text: a.who + "  ", options: { bold: true, color: a.color } }, { text: a.port, options: { color: C.slate } }], { x: a.x + 1.5, y: 3.12, w: 3.7, h: 0.4, fontFace: BF, fontSize: 12, margin: 0 });
    s.addText(a.pts.map(t => ({ text: t, options: { bullet: { indent: 14 }, breakLine: true, color: C.slate } })), { x: a.x + 0.45, y: 3.9, w: 4.8, h: 1.9, fontFace: BF, fontSize: 13.5, lineSpacingMultiple: 1.2, paraSpaceAfter: 6, margin: 0 });
  }
  s.addShape(p.shapes.OVAL, { x: 6.31, y: 3.8, w: 0.9, h: 0.9, fill: { color: C.gold } });
  s.addText("⇄", { x: 6.31, y: 3.8, w: 0.9, h: 0.9, align: "center", valign: "middle", fontFace: HF, fontSize: 26, bold: true, color: C.white, margin: 0 });
  s.addText("免登录互跳", { x: 5.91, y: 4.73, w: 1.7, h: 0.35, align: "center", fontFace: BF, fontSize: 11, bold: true, color: C.teal, margin: 0 });
  s.addShape(p.shapes.RECTANGLE, { x: 0.9, y: 6.25, w: 11.55, h: 0.62, fill: { color: C.mint } });
  s.addText([{ text: "数据安全： ", options: { bold: true, color: C.teal } }, { text: "可本地单机运行，也可私有服务器部署；孩子档案与家长记录按账号隔离，可查看/导出/删除。", options: { color: C.ink } }], { x: 1.1, y: 6.25, w: 11.2, h: 0.62, valign: "middle", fontFace: BF, fontSize: 13, margin: 0 });

  // ===== S4 第一章封面（蓝）=====
  await chapterDivider("第一章", "ABA 智能助手", "面向孩子的科学干预——把专业的 ABA 知识与训练记录，装进每天的陪伴里。", ic.childW, C.blueDk, C.blue);

  // ===== S5 六大功能（蓝）=====
  s = p.addSlide();
  lightHeader(s, "第一章 · 功能", "六大功能，覆盖陪伴干预全程", C.blue);
  const feats = [
    [Fa.FaCommentDots, "智能问答助手", "自然语言提问，回答分级（通用建议 / 需咨询治疗师），标注知识来源。", "例：「孩子超市哭闹要玩具？」→ 理解+预防+应对+教学"],
    [Fa.FaUserShield, "个案记忆系统", "记住孩子年龄、诊断、目标、强化物偏好与历史，回答越来越个性化。", "例：记得「小明在练表达、爱汽车」，建议自动贴合"],
    [Fa.FaShieldAlt, "回答安全边界", "识别自伤/攻击等危机信号，超出能力范围时引导联系专业人员。", "例：描述自伤行为 → 立即引导就医 + 注意事项"],
    [Fa.FaClipboardCheck, "训练记录闭环", "按试次记录 I/V/M/P/E，自动算正确率与掌握状态。", "例：6 个按钮点一下完成一次试次录入"],
    [Fa.FaSitemap, "课程与技能树", "122 项技能、4 大领域结构化进阶；20 题入门评估一键推荐起点。", "例：评估后自动生成今日任务清单"],
    [Fa.FaChartLine, "进展与报告", "数据看板（正确率/频次/辅助趋势）+ 自动生成周/月报告。", "例：一键导出结构化 Markdown 报告"],
  ];
  const fW = 3.92, fH = 1.72, fgx = 0.27, fgy = 0.25, fx0 = 0.7, fy0 = 1.85;
  for (let i = 0; i < feats.length; i++) {
    const cx = i % 3, ry = Math.floor(i / 3), x = fx0 + cx * (fW + fgx), y = fy0 + ry * (fH + fgy);
    const [Ic, t, d, eg] = feats[i];
    s.addShape(p.shapes.RECTANGLE, { x, y, w: fW, h: fH, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.RECTANGLE, { x, y, w: 0.1, h: fH, fill: { color: C.blue } });
    s.addShape(p.shapes.OVAL, { x: x + 0.28, y: y + 0.26, w: 0.62, h: 0.62, fill: { color: C.blueLight } });
    s.addImage({ data: await icon(Ic, "#" + C.blue), x: x + 0.43, y: y + 0.41, w: 0.32, h: 0.32 });
    s.addText(t, { x: x + 1.05, y: y + 0.26, w: fW - 1.2, h: 0.6, fontFace: HF, fontSize: 16, bold: true, color: C.ink, valign: "middle", margin: 0 });
    s.addText(d, { x: x + 0.3, y: y + 0.86, w: fW - 0.55, h: 0.55, fontFace: BF, fontSize: 11.5, color: C.slate, lineSpacingMultiple: 1.1, margin: 0 });
    s.addText(eg, { x: x + 0.3, y: y + 1.4, w: fW - 0.55, h: 0.28, fontFace: BF, fontSize: 10, italic: true, color: C.blue, margin: 0 });
  }

  // ===== S6 实操流程（蓝）=====
  s = p.addSlide();
  s.background = { color: C.blueDk };
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.18, fill: { color: C.coral } });
  s.addText("第一章 · 怎么操作", { x: 0.7, y: 0.5, w: 8, h: 0.35, fontFace: BF, fontSize: 13, bold: true, color: C.gold, charSpacing: 3, margin: 0 });
  s.addText("实操流程：从建档到一份报告", { x: 0.7, y: 0.85, w: 12, h: 0.7, fontFace: HF, fontSize: 28, bold: true, color: C.white, margin: 0 });
  const flow = [
    [Fa.FaUserPlus, "① 建档", "填孩子年龄、诊断、目标、强化物偏好"],
    [Fa.FaClipboardCheck, "② 入门评估", "20 题评估 → 领域评分 + 推荐起点技能"],
    [Fa.FaListUl, "③ 生成任务", "122 技能课程树自动排出今日任务"],
    [Fa.FaPenFancy, "④ 训练记录", "技能卡 + 6 按钮按试次记 I/V/M/P/E"],
    [Fa.FaLightbulb, "⑤ 实时建议", "自动算正确率，达标自动推进下一技能"],
    [Fa.FaFileAlt, "⑥ 看报告", "数据看板看趋势 + 一键周/月报告"],
  ];
  const cW = 3.84, cgx = 0.26, cgy = 0.3, cx0 = 0.7, cy0 = 1.95, cH = 1.95;
  for (let i = 0; i < flow.length; i++) {
    const cx = i % 3, ry = Math.floor(i / 3), x = cx0 + cx * (cW + cgx), y = cy0 + ry * (cH + cgy);
    const [Ic, t, d] = flow[i];
    s.addShape(p.shapes.RECTANGLE, { x, y, w: cW, h: cH, fill: { color: C.blue }, shadow: mkShadow() });
    s.addShape(p.shapes.OVAL, { x: x + 0.3, y: y + 0.32, w: 0.85, h: 0.85, fill: { color: C.blueDk } });
    s.addImage({ data: await icon(Ic, "#" + C.white), x: x + 0.51, y: y + 0.53, w: 0.43, h: 0.43 });
    s.addText(t, { x: x + 1.3, y: y + 0.34, w: cW - 1.5, h: 0.5, fontFace: HF, fontSize: 19, bold: true, color: C.white, valign: "middle", margin: 0 });
    s.addText(d, { x: x + 0.35, y: y + 1.25, w: cW - 0.6, h: 0.6, fontFace: BF, fontSize: 12.5, color: C.blueLight, lineSpacingMultiple: 1.1, margin: 0 });
  }

  // ===== S7 案例分享 ABA（蓝）=====
  s = p.addSlide();
  lightHeader(s, "第一章 · 案例分享", "小宇的两周：从「不会要」到「主动说」", C.blue);
  // 背景条
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 1.7, w: 11.95, h: 0.9, fill: { color: C.blueLight } });
  s.addText([{ text: "背景： ", options: { bold: true, color: C.blue } }, { text: "小宇，4 岁，刚确诊；妈妈是新手，目标「用语言表达需求」，过去全靠手记、看不清进展。", options: { color: C.ink } }], { x: 1.0, y: 1.7, w: 11.4, h: 0.9, valign: "middle", fontFace: BF, fontSize: 13.5, margin: 0 });
  const story = [
    ["第 1 天", "建档 + 20 题评估 → 系统推荐从「仿说单字」起步，自动生成今日任务"],
    ["第 1 周", "每天 3 个技能、按试次记录；「仿说」正确率从 40% → 65%"],
    ["遇到卡点", "孩子一直不配合 → 问 AI 助手 → 拿到「换更高偏好强化物 + 缩短回合」的具体建议"],
    ["第 2 周", "「仿说」达标自动推进到「主动提要求」；周报显示正确率稳定上升"],
  ];
  let yy = 2.85;
  for (let i = 0; i < story.length; i++) {
    const [t, d] = story[i];
    s.addShape(p.shapes.OVAL, { x: 0.8, y: yy + 0.05, w: 0.4, h: 0.4, fill: { color: C.blue } });
    s.addText(`${i + 1}`, { x: 0.8, y: yy + 0.05, w: 0.4, h: 0.4, align: "center", valign: "middle", fontFace: HF, fontSize: 14, bold: true, color: C.white, margin: 0 });
    if (i < story.length - 1) s.addShape(p.shapes.RECTANGLE, { x: 0.985, y: yy + 0.45, w: 0.03, h: 0.45, fill: { color: C.blueMid } });
    s.addText(t, { x: 1.4, y: yy, w: 2.0, h: 0.5, fontFace: HF, fontSize: 15, bold: true, color: C.blue, valign: "middle", margin: 0 });
    s.addText(d, { x: 3.4, y: yy, w: 5.0, h: 0.55, fontFace: BF, fontSize: 13, color: C.slate, valign: "middle", lineSpacingMultiple: 1.1, margin: 0 });
    yy += 0.9;
  }
  // 结果卡
  s.addShape(p.shapes.RECTANGLE, { x: 8.75, y: 2.85, w: 3.9, h: 3.55, fill: { color: C.blueDk }, shadow: mkShadow() });
  s.addText("结果", { x: 9.05, y: 3.1, w: 3.3, h: 0.4, fontFace: HF, fontSize: 18, bold: true, color: C.gold, margin: 0 });
  s.addText([
    { text: "妈妈第一次「看见」进步曲线", options: { bullet: { characterCode: "2713" }, breakLine: true } },
    { text: "永远知道「下一步该练什么」", options: { bullet: { characterCode: "2713" }, breakLine: true } },
    { text: "卡点当场能问，不必等机构", options: { bullet: { characterCode: "2713" }, breakLine: true } },
    { text: "两周记录全自动汇成一份报告", options: { bullet: { characterCode: "2713" } } },
  ], { x: 9.05, y: 3.65, w: 3.4, h: 2.6, fontFace: BF, fontSize: 13.5, color: C.white, lineSpacingMultiple: 1.6, margin: 0 });

  // ===== S8 专业知识库（蓝；122 技能 + 仅 MiniMax）=====
  s = p.addSlide();
  lightHeader(s, "第一章 · 专业底盘", "可信，来自扎实的 ABA 知识库", C.blue);
  const stats = [
    ["6", "个知识分册", "安全·概念·QA·循证·活动·场景"],
    ["11,400+", "行专业内容", "约 256 KB，完成度 100%"],
    ["122", "项训练技能", "4 大领域结构化进阶"],
    ["100+", "条高频问答", "覆盖沟通/社交/行为/生活"],
  ];
  const kW = 2.85, kGap = 0.27, kX0 = 0.7, kY = 2.0, kH = 2.5;
  for (let i = 0; i < stats.length; i++) {
    const x = kX0 + i * (kW + kGap);
    const [num, lab, sub] = stats[i];
    s.addShape(p.shapes.RECTANGLE, { x, y: kY, w: kW, h: kH, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.RECTANGLE, { x, y: kY + kH - 0.12, w: kW, h: 0.12, fill: { color: i % 2 ? C.coral : C.blue } });
    s.addText(num, { x: x + 0.2, y: kY + 0.32, w: kW - 0.4, h: 0.95, align: "center", fontFace: HF, fontSize: num.length > 4 ? 34 : 44, bold: true, color: C.blue, margin: 0 });
    s.addText(lab, { x: x + 0.2, y: kY + 1.32, w: kW - 0.4, h: 0.4, align: "center", fontFace: BF, fontSize: 15, bold: true, color: C.ink, margin: 0 });
    s.addText(sub, { x: x + 0.2, y: kY + 1.74, w: kW - 0.4, h: 0.6, align: "center", fontFace: BF, fontSize: 11, color: C.slate, lineSpacingMultiple: 1.1, margin: 0 });
  }
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 5.0, w: 11.95, h: 1.55, fill: { color: C.blueLight } });
  s.addImage({ data: ic.book, x: 1.05, y: 5.3, w: 0.5, h: 0.5 });
  s.addText("权威来源 · AI 由 MiniMax 大模型驱动", { x: 1.7, y: 5.25, w: 10.5, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: C.blue, margin: 0 });
  s.addText("BACB Task List · Cooper《应用行为分析》· VB-MAPP / ABLLS-R 评估体系，专业顾问审核。AI 问答与报告由 MiniMax 大模型生成；回答区分「通用建议」与「需专业指导」并标注依据。", { x: 1.7, y: 5.62, w: 10.7, h: 0.85, fontFace: BF, fontSize: 13, color: C.ink, lineSpacingMultiple: 1.25, margin: 0 });

  // ===== S9 安全与隐私（蓝）=====
  s = p.addSlide();
  s.background = { color: C.cream };
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.18, fill: { color: C.blue } });
  s.addShape(p.shapes.RECTANGLE, { x: 8.3, y: 0, w: W - 8.3, h: H, fill: { color: C.blueDk } });
  s.addShape(p.shapes.OVAL, { x: 9.0, y: 4.8, w: 3.6, h: 3.6, fill: { color: C.blue, transparency: 30 } });
  s.addShape(p.shapes.OVAL, { x: 9.9, y: 1.5, w: 1.5, h: 1.5, fill: { color: C.coral } });
  s.addImage({ data: await icon(Fa.FaUserShield, "#" + C.white), x: 10.26, y: 1.86, w: 0.78, h: 0.78 });
  s.addText("辅助，\n而非替代", { x: 8.75, y: 3.5, w: 4.0, h: 1.4, fontFace: HF, fontSize: 30, bold: true, color: C.white, lineSpacingMultiple: 1.0, margin: 0 });
  s.addText("选择权和决策权\n始终留给家长。", { x: 8.75, y: 5.1, w: 4.0, h: 1.0, fontFace: BF, fontSize: 15, color: C.blueLight, lineSpacingMultiple: 1.25, margin: 0 });
  s.addText("第一章 · 安全与隐私", { x: 0.7, y: 0.5, w: 7, h: 0.4, fontFace: BF, fontSize: 13, bold: true, color: C.coral, charSpacing: 2, margin: 0 });
  s.addText("让家长放心托付", { x: 0.7, y: 0.85, w: 7.4, h: 0.7, fontFace: HF, fontSize: 28, bold: true, color: C.ink, margin: 0 });
  const safety = [
    [Fa.FaShieldAlt, "危机信号识别", "自伤、攻击强度上升等 → 立即引导联系专业人员/就医"],
    [Fa.FaHeart, "透明的能力边界", "明确告知能做什么、不能做什么；区分通用建议与专业指导"],
    [Fa.FaHome, "数据本地/私有", "可单机运行或私有服务器部署，孩子信息不强制上云"],
    [Fa.FaLock, "家长掌控数据", "档案可查看、编辑、导出、删除，隐私优先"],
  ];
  let sy2 = 1.85;
  for (const [Ic, t, d] of safety) {
    s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: sy2, w: 7.25, h: 1.08, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.OVAL, { x: 0.95, y: sy2 + 0.27, w: 0.58, h: 0.58, fill: { color: C.blueLight } });
    s.addImage({ data: await icon(Ic, "#" + C.blue), x: 1.08, y: sy2 + 0.4, w: 0.32, h: 0.32 });
    s.addText(t, { x: 1.78, y: sy2 + 0.14, w: 6.0, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: C.blue, margin: 0 });
    s.addText(d, { x: 1.78, y: sy2 + 0.54, w: 6.05, h: 0.45, fontFace: BF, fontSize: 12.5, color: C.slate, lineSpacingMultiple: 1.1, margin: 0 });
    sy2 += 1.2;
  }

  // ===== S10 第二章封面（绿）=====
  await chapterDivider("第二章", "人生教练", "照顾好自己，才能照顾好孩子——一个面向家长本人的 AI 心理成长教练。", ic.handW, C.tealDk, C.teal);

  // ===== S11 为什么家长需要（绿）=====
  s = p.addSlide();
  lightHeader(s, "第二章 · 为什么", "被忽视的那个人：家长自己", C.teal);
  s.addText("主产品照顾孩子，人生教练照顾家长——基于 ACT、正念与积极心理学，温暖、非评判、可操作。", { x: 0.7, y: 1.58, w: 11.9, h: 0.5, fontFace: BF, fontSize: 15, color: C.slate, margin: 0 });
  const facts = [
    ["焦虑 / 抑郁", "自闭症家长的焦虑、抑郁、压力水平显著高于其他家长"],
    ["影响干预", "家长心理状态直接影响干预效果：压力越高、自我效能越低，成果越弱"],
    ["资源稀缺", "时间、经济、地域限制，多数家长拿不到持续的心理 coaching"],
  ];
  const aW = 3.85, aGap = 0.3, ax0 = 0.7, aY = 2.3, aH = 2.2;
  for (let i = 0; i < facts.length; i++) {
    const x = ax0 + i * (aW + aGap);
    s.addShape(p.shapes.RECTANGLE, { x, y: aY, w: aW, h: aH, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.RECTANGLE, { x, y: aY, w: aW, h: 0.1, fill: { color: C.coral } });
    s.addText(facts[i][0], { x: x + 0.3, y: aY + 0.3, w: aW - 0.6, h: 0.5, fontFace: HF, fontSize: 19, bold: true, color: C.coral, margin: 0 });
    s.addText(facts[i][1], { x: x + 0.3, y: aY + 0.95, w: aW - 0.6, h: 1.1, fontFace: BF, fontSize: 13.5, color: C.slate, lineSpacingMultiple: 1.25, margin: 0 });
  }
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 4.85, w: 11.95, h: 1.6, fill: { color: C.tealDk } });
  s.addText("人生教练做什么", { x: 1.05, y: 5.05, w: 11, h: 0.4, fontFace: HF, fontSize: 17, bold: true, color: C.gold, margin: 0 });
  s.addText("陪家长处理情绪、找回自我、明确价值观、迈出小行动——不是说教，是陪伴；不替代心理治疗，遇到临床问题引导寻求专业帮助。", { x: 1.05, y: 5.45, w: 11.2, h: 0.9, fontFace: BF, fontSize: 14, color: C.white, lineSpacingMultiple: 1.3, margin: 0 });

  // ===== S12 人生教练能为你做什么（绿）=====
  s = p.addSlide();
  lightHeader(s, "第二章 · 能帮你什么", "人生教练具体能为家长做的 8 件事", C.teal);
  const caps = [
    [Fa.FaCommentMedical, "情绪即时急救", "崩溃、焦虑、自责的那一刻有人接住、陪你过去"],
    [Fa.FaShieldAlt, "危机识别 + 热线", "出现「撑不下去」等信号，立即给危机资源，最坏时刻不孤单"],
    [Fa.FaRoute, "议题驱动成长路径", "围绕一个具体议题，走 ACT 六阶段——每个议题都有专属个性化练习"],
    [Fa.FaSmile, "情绪追踪", "记录心情+触发+强度+身体感受，看见自己的情绪模式与进步"],
    [Fa.FaChartLine, "AI 周报", "按周自动汇总情绪、记录、任务数据，生成趋势分析与个性化建议"],
    [Fa.FaBookReader, "心理知识库", "9 大领域、34 篇文章，读得懂、用得上；教练结合处境延展"],
    [Fa.FaTasks, "教练任务", "8 种情绪各配专属练习任务，完成即可得具体下一步"],
    [Fa.FaProjectDiagram, "任务快速跳转", "成长任务一键跳转到知识库、记录、情绪追踪，练习无缝衔接"],
  ];
  const pW = 2.85, pH = 1.72, pgx = 0.2, pgy = 0.22, px0 = 0.7, py0 = 1.85;
  for (let i = 0; i < caps.length; i++) {
    const cx = i % 4, ry = Math.floor(i / 4), x = px0 + cx * (pW + pgx), y = py0 + ry * (pH + pgy);
    const [Ic, t, d] = caps[i];
    s.addShape(p.shapes.RECTANGLE, { x, y, w: pW, h: pH, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.OVAL, { x: x + 0.25, y: y + 0.3, w: 0.72, h: 0.72, fill: { color: C.teal } });
    s.addImage({ data: await icon(Ic, "#" + C.white), x: x + 0.43, y: y + 0.49, w: 0.35, h: 0.35 });
    s.addText(t, { x: x + 0.35, y: y + 1.1, w: pW - 0.6, h: 0.28, fontFace: HF, fontSize: 14, bold: true, color: C.ink, margin: 0 });
    s.addText(d, { x: x + 0.25, y: y + 1.38, w: pW - 0.5, h: 0.32, fontFace: BF, fontSize: 10.5, color: C.slate, lineSpacingMultiple: 1.1, margin: 0 });
  }
  // ===== S13 ACT 六阶段（绿）=====
  s = p.addSlide();
  lightHeader(s, "第二章 · 方法", "议题驱动的个性化成长路径", C.teal);
  s.addText("选择一个具体困扰你的议题（如「孩子发脾气时的焦虑」），系统自动识别类型，生成专属的 6 阶段练习。", { x: 0.7, y: 1.58, w: 11.9, h: 0.5, fontFace: BF, fontSize: 14, color: C.slate, margin: 0 });
  const stages = [
    [Fa.FaEye, "焦虑类模板", "焦虑身体地图 · 4-7-8呼吸 · 安全锚", "着陆练习 / 焦虑冲浪 / 广播解离"],
    [Fa.FaHandHoldingHeart, "自责类模板", "给批评家取名 · 慈悲朋友视角 · 写慈悲信", "自我关怀冥想 / 足够好标准"],
    [Fa.FaBatteryQuarter, "疲惫类模板", "精力地图 · 氧气面罩法则 · 微型休息菜单", "支持网络地图 / 精力保护规则"],
    [Fa.FaUsers, "社交类模板", "聚光灯效应检验 · 暴露练习 · 找同类", "正念社交 / 有意义vs消耗社交"],
    [Fa.FaChild, "亲子类模板", "情绪触发链 · 暂停-呼吸-回应 · 正念亲子", "换位感受 / 价值观导向互动"],
    [Fa.FaStar, "通用模板", "固定 ACT 六阶段（觉察→解离→当下→自我→价值观→行动）", "28 个通用练习，适合任何议题"],
  ];
  const gW = 3.92, gH = 1.75, ggx = 0.27, ggy = 0.15, gx0 = 0.7, gy0 = 2.15;
  for (let i = 0; i < stages.length; i++) {
    const cx = i % 3, ry = Math.floor(i / 3), x = gx0 + cx * (gW + ggx), y = gy0 + ry * (gH + ggy);
    const [Ic, t, d, eg] = stages[i];
    s.addShape(p.shapes.RECTANGLE, { x, y, w: gW, h: gH, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.OVAL, { x: x + 0.28, y: y + 0.32, w: 0.78, h: 0.78, fill: { color: i < 5 ? C.teal : C.slate } });
    s.addImage({ data: await icon(Ic, "#" + C.white), x: x + 0.47, y: y + 0.51, w: 0.4, h: 0.4 });
    s.addText(t, { x: x + 1.2, y: y + 0.28, w: gW - 1.35, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: C.ink, margin: 0 });
    s.addText(d, { x: x + 1.2, y: y + 0.7, w: gW - 1.35, h: 0.4, fontFace: BF, fontSize: 11.5, color: C.slate, margin: 0 });
    s.addText(eg, { x: x + 0.3, y: y + 1.15, w: gW - 0.5, h: 0.32, fontFace: BF, fontSize: 10.5, italic: true, color: C.teal, margin: 0 });
    if (i < 5) s.addText("个性化", { x: x + gW - 0.85, y: y + 0.28, w: 0.7, h: 0.28, align: "right", fontFace: BF, fontSize: 9, bold: true, color: C.gold, margin: 0 });
  }

  // ===== S14 三层引擎 + 对话（绿）=====
  s = p.addSlide();
  s.background = { color: C.tealDk };
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: 0.18, fill: { color: C.coral } });
  s.addText("第二章 · 怎么工作", { x: 0.7, y: 0.5, w: 8, h: 0.35, fontFace: BF, fontSize: 13, bold: true, color: C.gold, charSpacing: 2, margin: 0 });
  s.addText("教练对话引擎：三层把关", { x: 0.7, y: 0.85, w: 12, h: 0.7, fontFace: HF, fontSize: 28, bold: true, color: C.white, margin: 0 });
  const layers = [
    [Fa.FaShieldAlt, C.coral, "① 安全分流（最高优先级）", "每句话先做风险识别。出现自伤/绝望/「带孩子一起走」等信号 → 立即给危机回应 + 心理援助热线，不进入普通对话。"],
    [Fa.FaRobot, C.gold, "② ACT 教练（MiniMax 大模型）", "反映式倾听 + 苏格拉底式提问。明确边界：不诊断、不开药、不替代治疗。简短、共情、以一个开放问题或一个小行动收尾。"],
    [Fa.FaCommentDots, C.seafoam, "③ 脚本兜底", "没有 AI 额度或调用失败时，自动回退到情绪策略库的暖心回应，保证离线也能用、不会崩。"],
  ];
  let ly = 1.95;
  for (const [Ic, col, t, d] of layers) {
    s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: ly, w: 7.55, h: 1.35, fill: { color: C.teal }, shadow: mkShadow() });
    s.addShape(p.shapes.OVAL, { x: 0.95, y: ly + 0.36, w: 0.62, h: 0.62, fill: { color: col } });
    s.addImage({ data: await icon(Ic, "#" + C.white), x: 1.1, y: ly + 0.51, w: 0.32, h: 0.32 });
    s.addText(t, { x: 1.75, y: ly + 0.14, w: 6.3, h: 0.4, fontFace: HF, fontSize: 15.5, bold: true, color: C.white, margin: 0 });
    s.addText(d, { x: 1.75, y: ly + 0.52, w: 6.35, h: 0.8, fontFace: BF, fontSize: 11.5, color: C.mint, lineSpacingMultiple: 1.12, margin: 0 });
    ly += 1.5;
  }
  s.addShape(p.shapes.RECTANGLE, { x: 8.5, y: 1.95, w: 4.15, h: 4.4, fill: { color: C.cream }, shadow: mkShadow() });
  s.addText("一段真实风格的回应", { x: 8.75, y: 2.15, w: 3.7, h: 0.4, fontFace: HF, fontSize: 14, bold: true, color: C.teal, margin: 0 });
  s.addText("家长：陪孩子训练他一直不配合，我又急又愧疚。", { x: 8.75, y: 2.6, w: 3.65, h: 0.7, fontFace: BF, fontSize: 11.5, bold: true, color: C.ink, lineSpacingMultiple: 1.15, margin: 0 });
  s.addText("教练：今天陪孩子训练已经不容易了……你先允许自己有这个情绪——它不是「错的」，你只是个想做好、却暂时卡住的家长。\n\n我想问你一句：那个「急」里面，有没有一部分是在担心自己「做错了什么」？", { x: 8.75, y: 3.35, w: 3.65, h: 2.8, fontFace: BF, fontSize: 11.5, color: C.slate, lineSpacingMultiple: 1.2, margin: 0 });

  // ===== S15 八情绪 × 任务（绿）=====
  s = p.addSlide();
  lightHeader(s, "第二章 · 情绪支持", "认得出情绪，给得出具体的下一步", C.teal);
  s.addText("说出此刻的感受，教练识别情绪类型并给出对应策略 + 一个此刻就能做的小任务。", { x: 0.7, y: 1.56, w: 11.9, h: 0.5, fontFace: BF, fontSize: 14, color: C.slate, margin: 0 });
  const emos = [
    ["😟 焦虑", "接纳+解离+当下锚定", "5-4-3-2-1 着陆练习（2 分钟）"], ["😢 悲伤", "接纳+允许+温暖陪伴", "安静坐 5 分钟，不改变任何感受"],
    ["😤 愤怒", "探索需求+建设性表达", "非暴力沟通四步法写一段"], ["😩 疲惫", "确认+自我关怀+设边界", "列 3 件可以请人帮忙的事"],
    ["😔 自责", "认知解离+自我关怀", "「我注意到我有…的想法」"], ["🫂 孤独", "确认+连接行动", "给一个朋友发一句「最近还好吗」"],
    ["🤔 困惑", "苏格拉底提问+价值观锚定", "写下：不考虑别人看法你会怎么选"], ["🌟 感恩", "放大积极+意义构建", "记录今天 3 件好事"],
  ];
  const eW = 2.95, eH = 1.5, egx = 0.13, egy = 0.18, ex0 = 0.7, ey0 = 2.2;
  for (let i = 0; i < emos.length; i++) {
    const cx = i % 4, ry = Math.floor(i / 4), x = ex0 + cx * (eW + egx), y = ey0 + ry * (eH + egy);
    s.addShape(p.shapes.RECTANGLE, { x, y, w: eW, h: eH, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.RECTANGLE, { x, y, w: eW, h: 0.09, fill: { color: ry === 0 ? C.teal : C.coral } });
    s.addText(emos[i][0], { x: x + 0.2, y: y + 0.18, w: eW - 0.4, h: 0.4, fontFace: HF, fontSize: 15, bold: true, color: C.ink, margin: 0 });
    s.addText(emos[i][1], { x: x + 0.2, y: y + 0.6, w: eW - 0.4, h: 0.35, fontFace: BF, fontSize: 10.5, bold: true, color: C.teal, margin: 0 });
    s.addText("→ " + emos[i][2], { x: x + 0.2, y: y + 0.95, w: eW - 0.4, h: 0.45, fontFace: BF, fontSize: 10.5, italic: true, color: C.slate, lineSpacingMultiple: 1.05, margin: 0 });
  }

  // ===== S16 知识库阅读体验（绿）=====
  s = p.addSlide();
  lightHeader(s, "第二章 · 知识库", "读得懂、用得上的心理成长知识", C.teal);
  s.addText("9 大领域、34 篇文章（持续扩充），每篇都能让教练结合你的处境延展。", { x: 0.7, y: 1.58, w: 11.9, h: 0.5, fontFace: BF, fontSize: 14, color: C.slate, margin: 0 });
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 2.25, w: 5.5, h: 4.2, fill: { color: C.white }, shadow: mkShadow() });
  s.addText("覆盖领域", { x: 1.0, y: 2.45, w: 5, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: C.teal, margin: 0 });
  s.addText(["核心方法论（ACT 六过程）", "情绪与心理管理（8 类情绪）", "自我认知与成长 · 心理韧性", "关系经营（伴侣 / 边界沟通）", "健康（睡眠 / 运动）· 时间与习惯", "养育支持 · 正念练习库"].map(t => ({ text: t, options: { bullet: { indent: 15 }, breakLine: true, color: C.slate } })), { x: 1.0, y: 2.95, w: 5.0, h: 3.3, fontFace: BF, fontSize: 13.5, lineSpacingMultiple: 1.2, paraSpaceAfter: 8, margin: 0 });
  s.addShape(p.shapes.RECTANGLE, { x: 6.45, y: 2.25, w: 6.2, h: 4.2, fill: { color: C.tealDk }, shadow: mkShadow() });
  s.addText("「点进去不傻」的阅读体验", { x: 6.75, y: 2.45, w: 5.7, h: 0.4, fontFace: HF, fontSize: 16, bold: true, color: C.gold, margin: 0 });
  const reads = [
    ["💡 结合我的情况举个例子", "把文章正文交给教练，按你的处境延展"],
    ["🧘 带我做一次这个练习", "教练一步步带你做文章里的练习"],
    ["🔄 没太懂，换个说法讲", "用更口语的方式重讲核心意思"],
    ["🔖 收藏 / ✓ 已读 / 📎 相关文章", "标记与跳转，越读越成体系"],
  ];
  let ry2 = 3.0;
  for (const [t, d] of reads) {
    s.addText(t, { x: 6.75, y: ry2, w: 5.7, h: 0.35, fontFace: BF, fontSize: 13.5, bold: true, color: C.white, margin: 0 });
    s.addText(d, { x: 6.75, y: ry2 + 0.34, w: 5.7, h: 0.4, fontFace: BF, fontSize: 11.5, color: C.mint, margin: 0 });
    ry2 += 0.86;
  }

  // ===== S17 案例分享 教练（绿）=====
  s = p.addSlide();
  lightHeader(s, "第二章 · 案例分享", "一位妈妈的两周：从深夜崩溃到睡个好觉", C.teal);
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 1.7, w: 11.95, h: 0.9, fill: { color: C.mint } });
  s.addText([{ text: "背景： ", options: { bold: true, color: C.teal } }, { text: "一位妈妈，长期失眠、反复自责「我不是个好妈妈」，身边没人能说，越夜越崩。", options: { color: C.ink } }], { x: 1.0, y: 1.7, w: 11.4, h: 0.9, valign: "middle", fontFace: BF, fontSize: 13.5, margin: 0 });
  const story2 = [
    ["那一夜", "深夜打下「我撑不下去了」→ 安全分流先给陪伴 + 心理援助热线，没有被一句鸡汤打发"],
    ["开始成长", "创建议题「我对自己的自责」，系统自动匹配「自责类」模板——每个练习都围绕自责设计"],
    ["第 1 周", "用「慈悲朋友视角」练习、写「给自己的慈悲信」；情绪追踪发现焦虑集中在傍晚训练时段"],
    ["第 2 周", "AI 周报显示「自责频率下降 40%」；睡前用清空法，自评心情从 😢 慢慢回到 🙂"],
  ];
  let yy2 = 2.85;
  for (let i = 0; i < story2.length; i++) {
    const [t, d] = story2[i];
    s.addShape(p.shapes.OVAL, { x: 0.8, y: yy2 + 0.05, w: 0.4, h: 0.4, fill: { color: C.teal } });
    s.addText(`${i + 1}`, { x: 0.8, y: yy2 + 0.05, w: 0.4, h: 0.4, align: "center", valign: "middle", fontFace: HF, fontSize: 14, bold: true, color: C.white, margin: 0 });
    if (i < story2.length - 1) s.addShape(p.shapes.RECTANGLE, { x: 0.985, y: yy2 + 0.45, w: 0.03, h: 0.45, fill: { color: C.seafoam } });
    s.addText(t, { x: 1.4, y: yy2, w: 2.0, h: 0.5, fontFace: HF, fontSize: 15, bold: true, color: C.teal, valign: "middle", margin: 0 });
    s.addText(d, { x: 3.4, y: yy2, w: 5.0, h: 0.55, fontFace: BF, fontSize: 13, color: C.slate, valign: "middle", lineSpacingMultiple: 1.1, margin: 0 });
    yy2 += 0.9;
  }
  s.addShape(p.shapes.RECTANGLE, { x: 8.75, y: 2.85, w: 3.9, h: 3.55, fill: { color: C.tealDk }, shadow: mkShadow() });
  s.addText("结果", { x: 9.05, y: 3.1, w: 3.3, h: 0.4, fontFace: HF, fontSize: 18, bold: true, color: C.gold, margin: 0 });
  s.addText([
    { text: "最崩溃的一刻有人接住", options: { bullet: { characterCode: "2713" }, breakLine: true } },
    { text: "议题路径完全贴合自责", options: { bullet: { characterCode: "2713" }, breakLine: true } },
    { text: "不再把消极想法当成事实", options: { bullet: { characterCode: "2713" }, breakLine: true } },
    { text: "AI 周报看到自责频率下降 40%", options: { bullet: { characterCode: "2713" }, breakLine: true } },
    { text: "睡眠与心情都在好转", options: { bullet: { characterCode: "2713" } } },
  ], { x: 9.05, y: 3.6, w: 3.4, h: 2.7, fontFace: BF, fontSize: 12.5, color: C.white, lineSpacingMultiple: 1.4, margin: 0 });

  // ===== S18 一天的使用场景 =====
  s = p.addSlide();
  lightHeader(s, "怎么用", "一天里，两个助手怎么陪着你", C.teal);
  const day = [
    [Fa.FaSun, "早晨", C.gold, "人生教练记录今天心情（触发+强度+身体感受），做一次 3 分钟呼吸空间。"],
    [Fa.FaShoppingCart, "白天", C.blue, "超市孩子闹情绪 → ABA 助手问「怎么处理」，顺手记一次试次。"],
    [Fa.FaComments, "傍晚", C.coral, "训练受挫、心里发堵 → 找人生教练聊两句，做成长任务的小练习。"],
    [Fa.FaMoon, "睡前", C.teal, "ABA 看今天数据看板；人生教练看 AI 周报，了解本周情绪趋势。"],
  ];
  const dW = 2.85, dGap = 0.27, dx0 = 0.7, dY = 2.15, dH = 4.0;
  for (let i = 0; i < day.length; i++) {
    const x = dx0 + i * (dW + dGap);
    const [Ic, t, col, d] = day[i];
    s.addShape(p.shapes.RECTANGLE, { x, y: dY, w: dW, h: dH, fill: { color: C.white }, shadow: mkShadow() });
    s.addShape(p.shapes.OVAL, { x: x + dW / 2 - 0.62, y: dY + 0.45, w: 1.24, h: 1.24, fill: { color: col } });
    s.addImage({ data: await icon(Ic, "#" + C.white), x: x + dW / 2 - 0.32, y: dY + 0.75, w: 0.64, h: 0.64 });
    s.addText(t, { x, y: dY + 1.9, w: dW, h: 0.5, align: "center", fontFace: HF, fontSize: 22, bold: true, color: C.ink, margin: 0 });
    s.addText(d, { x: x + 0.3, y: dY + 2.5, w: dW - 0.6, h: 1.3, align: "center", fontFace: BF, fontSize: 13, color: C.slate, lineSpacingMultiple: 1.3, margin: 0 });
    if (i < day.length - 1) s.addText("›", { x: x + dW - 0.02, y: dY + 0.9, w: dGap, h: 0.6, align: "center", valign: "middle", fontFace: HF, fontSize: 26, bold: true, color: C.gold, margin: 0 });
  }

  // ===== S19 如何开始 =====
  s = p.addSlide();
  lightHeader(s, "如何开始", "打开网页，三步就能用", C.teal);
  const use = [
    [Fa.FaUserPlus, C.blue, "注册账号", "浏览器打开主应用，注册自己的账号——孩子档案、家长记录都按账号隔离。"],
    [Fa.FaChild, C.blue, "给孩子建档", "填入孩子基本情况与目标，做一次 20 题入门评估，自动生成训练任务。"],
    [Fa.FaSeedling, C.teal, "照顾好自己", "点「进入人生教练」，描述一个困扰你的议题，系统自动为你生成个性化成长路径。"],
  ];
  const uW = 3.85, uGap = 0.3, uX0 = 0.7, uY = 2.25, uH = 3.4;
  for (let i = 0; i < use.length; i++) {
    const x = uX0 + i * (uW + uGap);
    const [Ic, col, t, d] = use[i];
    s.addShape(p.shapes.RECTANGLE, { x, y: uY, w: uW, h: uH, fill: { color: C.white }, shadow: mkShadow() });
    s.addText(`${i + 1}`, { x: x + uW - 1.5, y: uY + 0.05, w: 1.4, h: 1.4, align: "right", fontFace: HF, fontSize: 56, bold: true, color: i < 2 ? C.blueLight : C.mint, margin: 0 });
    s.addShape(p.shapes.OVAL, { x: x + 0.4, y: uY + 0.5, w: 1.1, h: 1.1, fill: { color: col } });
    s.addImage({ data: await icon(Ic, "#" + C.white), x: x + 0.66, y: uY + 0.76, w: 0.58, h: 0.58 });
    s.addText(t, { x: x + 0.4, y: uY + 1.8, w: uW - 0.8, h: 0.5, fontFace: HF, fontSize: 21, bold: true, color: C.ink, margin: 0 });
    s.addText(d, { x: x + 0.42, y: uY + 2.35, w: uW - 0.8, h: 0.95, fontFace: BF, fontSize: 13, color: C.slate, lineSpacingMultiple: 1.25, margin: 0 });
  }
  s.addShape(p.shapes.RECTANGLE, { x: 0.7, y: 6.0, w: 11.95, h: 0.62, fill: { color: C.tealDk } });
  s.addText([{ text: "无需安装： ", options: { bold: true, color: C.gold } }, { text: "浏览器访问即可；支持单机绿色包（双击启动）与私有服务器部署两种方式。", options: { color: C.white } }], { x: 0.9, y: 6.0, w: 11.6, h: 0.62, valign: "middle", fontFace: BF, fontSize: 13, margin: 0 });

  // ===== S20 结语 =====
  s = p.addSlide();
  s.background = { color: C.tealDk };
  s.addShape(p.shapes.OVAL, { x: -2.0, y: -2.2, w: 6.5, h: 6.5, fill: { color: C.teal, transparency: 20 } });
  s.addShape(p.shapes.OVAL, { x: 10.3, y: 3.8, w: 5.0, h: 5.0, fill: { color: C.teal } });
  s.addShape(p.shapes.OVAL, { x: 11.7, y: 5.3, w: 2.2, h: 2.2, fill: { color: C.coral, transparency: 20 } });
  s.addShape(p.shapes.OVAL, { x: 0.78, y: 1.3, w: 1.0, h: 1.0, fill: { color: C.coral } });
  s.addImage({ data: ic.seedling, x: 1.0, y: 1.52, w: 0.56, h: 0.56 });
  s.addText("陪孩子成长，\n也别弄丢了你自己。", { x: 0.78, y: 2.7, w: 11, h: 2.0, fontFace: HF, fontSize: 44, bold: true, color: C.white, lineSpacingMultiple: 1.05, margin: 0 });
  s.addText("让专业的 ABA 干预与温暖的 ACT 陪伴触手可及——孩子的每一点进步，家长的每一次喘息，都有人懂、有据可循。", { x: 0.8, y: 4.95, w: 10.6, h: 1.0, fontFace: BF, fontSize: 17, color: C.mint, lineSpacingMultiple: 1.3, margin: 0 });
  s.addShape(p.shapes.RECTANGLE, { x: 0.8, y: 6.3, w: 0.5, h: 0.06, fill: { color: C.gold } });
  s.addText("ABA 智能助手 + 人生教练  ·  一个账号，两个助手", { x: 0.8, y: 6.5, w: 11, h: 0.4, fontFace: BF, fontSize: 14, bold: true, color: C.seafoam, charSpacing: 1, margin: 0 });

  await p.writeFile({ fileName: "ABA智能助手_产品介绍.pptx" });
  console.log("done");
}
main().catch((e) => { console.error(e); process.exit(1); });
