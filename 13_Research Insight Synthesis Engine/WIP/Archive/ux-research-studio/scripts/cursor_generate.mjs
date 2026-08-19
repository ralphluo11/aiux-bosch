#!/usr/bin/env node
/**
 * Cursor Agent SDK 桥接：从 stdin 读 JSON，stdout 返回 { content } 或 { error }。
 * 需在 ux-research-studio 目录执行 npm install。
 */
import { readFileSync } from "node:fs";

async function main() {
  const raw = readFileSync(0, "utf8");
  const input = JSON.parse(raw);
  const apiKey = process.env.CURSOR_API_KEY;
  if (!apiKey) {
    console.log(JSON.stringify({ error: "CURSOR_API_KEY 未设置" }));
    process.exit(1);
  }

  try {
    const { Agent } = await import("@cursor/sdk");
    const prompt = [
      "【系统规则】",
      input.system,
      "",
      "【用户任务】",
      input.user,
      "",
      "请只输出模块正文 Markdown，不要解释生成过程。",
    ].join("\n");

    const result = await Agent.prompt(prompt, {
      apiKey,
      model: { id: input.model || "composer-2" },
      local: { cwd: input.cwd || process.cwd() },
    });

    const text =
      typeof result.result === "string"
        ? result.result
        : JSON.stringify(result.result ?? result);
    console.log(JSON.stringify({ content: text }));
  } catch (e) {
    console.log(JSON.stringify({ error: String(e.message || e) }));
    process.exit(1);
  }
}

main();
