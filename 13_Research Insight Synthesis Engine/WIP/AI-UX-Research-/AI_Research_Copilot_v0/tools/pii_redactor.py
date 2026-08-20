#!/usr/bin/env python3
"""Offline, dependency-free PII redaction for research text files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Match, Pattern


SUPPORTED_SUFFIXES = {".txt", ".md", ".csv", ".json", ".srt", ".vtt"}


@dataclass(frozen=True)
class Rule:
    label: str
    pattern: Pattern[str]
    value_group: str | int = 0


def _rule(label: str, expression: str, value_group: str | int = 0, flags: int = 0) -> Rule:
    return Rule(label, re.compile(expression, flags), value_group)


# Ordered from specific to broad. Boundaries intentionally accept Chinese text around numbers.
DEFAULT_RULES = (
    _rule("邮箱", r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", flags=re.I),
    _rule("身份证", r"(?<![0-9A-Za-z])(?:[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx])(?![0-9A-Za-z])"),
    _rule("护照", r"(?<![0-9A-Za-z])(?:[EeGgPpSsDd]\d{7,8}|[HhMm]\d{8,10})(?![0-9A-Za-z])"),
    _rule("手机号", r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d(?:[- ]?\d{4}){2}(?!\d)"),
    _rule("座机", r"(?<!\d)(?:\+?86[- ]?)?(?:0\d{2,3}[- ]?)?\d{7,8}(?:[-转 ]\d{1,6})?(?!\d)"),
    _rule("银行卡", r"(?<!\d)(?:\d[ -]?){15,18}\d(?!\d)"),
    _rule("车牌", r"(?<![\u4e00-\u9fffA-Z0-9])[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{5,6}(?![A-Z0-9])", flags=re.I),
    _rule("IPv4", r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?!\d)"),
    _rule("QQ号", r"(?P<prefix>(?:QQ(?:号|号码)?)[：:\s]*)(?P<value>[1-9]\d{4,11})", "value", re.I),
    _rule("微信号", r"(?P<prefix>(?:微信(?:号|号码)?|WeChat)[：:\s]*)(?P<value>[a-z][-_a-z0-9]{5,19})", "value", re.I),
    _rule("姓名", r"(?P<prefix>(?:姓名|联系人|受访者|参与者|客户姓名|用户姓名)[：:\s]*)(?P<value>[\u3400-\u9fff·]{2,6})", "value"),
    _rule("姓名", r"(?P<prefix>(?:我叫|本人叫|名字是|称呼是|联系人是|受访者是|参与者是)[：:\s]*)(?P<value>(?:欧阳|司马|上官|诸葛|夏侯|东方|皇甫|尉迟|公孙|慕容|令狐|宇文|长孙|司徒|司空|端木|独孤|南宫|万俟|闻人|[赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵汪祁毛禹狄米贝明臧计伏成戴宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万柯卢莫房裘缪干解应宗丁宣邓郁单杭洪包诸左石崔吉龚程嵇邢裴陆荣翁荀羊甄曲封芮储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全班仰秋仲伊宫宁仇栾暴甘厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰鄂索咸籍赖卓蔺屠蒙池乔阴郁胥能苍双闻莘党翟谭贡劳姬申扶堵冉宰郦雍郤璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公晋楚闫])(?:[\u3400-\u9fff]{1,3}|[\u3400-\u9fff]+·[\u3400-\u9fff]+))", "value"),
    _rule("姓名", r"(?m)^(?P<value>(?:欧阳|司马|上官|诸葛|夏侯|东方|皇甫|尉迟|公孙|慕容|令狐|宇文|长孙|司徒|司空|端木|独孤|南宫|万俟|闻人|[赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹苏潘葛范彭鲁韦马方任袁柳史唐薛雷贺倪汤罗郝安常傅齐康伍余顾孟黄萧姚邵汪毛戴宋庞熊纪舒项祝董梁杜蓝席季麻贾江童颜郭梅林钟徐邱高夏蔡田樊胡霍万卢莫房解宗丁宣邓单洪左石崔龚程邢裴陆翁甄段富焦侯全班仲宁仇甘厉祖武符刘景詹龙叶白蒲鄂赖卓谭申冉牛温庄晏柴瞿阎连艾向古易廖聂辛简饶曾关查游权益])[\u3400-\u9fff]{1,3})(?=[：:])", "value"),
    _rule("地址", r"(?P<prefix>(?:家庭?住址|居住地址|通讯地址|地址)[：:\s]*)(?P<value>[^\n,，;；]{4,100})", "value"),
)


class Redactor:
    def __init__(self, rules: Iterable[Rule] = DEFAULT_RULES) -> None:
        self.rules = tuple(rules)
        self.tokens: dict[tuple[str, str], str] = {}
        self.counts: Counter[str] = Counter()

    def _token(self, label: str, value: str) -> str:
        canonical = re.sub(r"[\s-]", "", value).lower()
        key = (label, canonical)
        if key not in self.tokens:
            number = sum(1 for existing_label, _ in self.tokens if existing_label == label) + 1
            self.tokens[key] = f"[{label}_{number:03d}]"
        self.counts[label] += 1
        return self.tokens[key]

    def redact(self, text: str) -> str:
        result = text
        for rule in self.rules:
            def replace(match: Match[str], current_rule: Rule = rule) -> str:
                value = match.group(current_rule.value_group)
                token = self._token(current_rule.label, value)
                if current_rule.value_group == 0:
                    return token
                start, end = match.span(current_rule.value_group)
                whole_start = match.start(0)
                relative_start, relative_end = start - whole_start, end - whole_start
                whole = match.group(0)
                return whole[:relative_start] + token + whole[relative_end:]

            result = rule.pattern.sub(replace, result)
        return result

    def report(self) -> dict[str, object]:
        return {
            "offline": True,
            "detected_occurrences": sum(self.counts.values()),
            "unique_values": len(self.tokens),
            "by_type": dict(sorted(self.counts.items())),
            "contains_original_values": False,
        }


def literal_rules(names: Iterable[str], terms: Iterable[str]) -> tuple[Rule, ...]:
    rules: list[Rule] = []
    for name in names:
        clean = name.strip()
        if clean:
            rules.append(_rule("姓名", re.escape(clean)))
    for entry in terms:
        if "=" not in entry:
            raise ValueError(f"自定义词条必须使用 类型=原文 格式：{entry}")
        label, value = (part.strip() for part in entry.split("=", 1))
        if not label or not value:
            raise ValueError(f"自定义词条类型和原文不能为空：{entry}")
        rules.append(_rule(label, re.escape(value)))
    return tuple(rules)


def output_path(source: Path, output_dir: Path | None) -> Path:
    destination = output_dir or source.parent
    return destination / f"{source.stem}.redacted{source.suffix}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="完全离线的研究文本个人信息脱敏工具")
    parser.add_argument("files", nargs="+", type=Path, help="待处理文件或目录")
    parser.add_argument("-o", "--output-dir", type=Path, help="输出目录；默认与原文件同目录")
    parser.add_argument("--name", action="append", default=[], help="补充姓名，可重复使用")
    parser.add_argument("--term", action="append", default=[], help="自定义 类型=原文，可重复使用")
    parser.add_argument("--report", type=Path, help="写出不含原值的 JSON 汇总报告")
    return parser.parse_args(argv)


def collect_files(inputs: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        if item.is_dir():
            files.extend(
                path for path in sorted(item.rglob("*"))
                if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
                and ".redacted" not in path.stem
            )
        elif item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(item)
        else:
            raise ValueError(f"不存在或格式不支持：{item}")
    return files


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        extras = literal_rules(args.name, args.term)
        sources = collect_files(args.files)
        if not sources:
            raise ValueError("没有找到可处理的文件")
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=True)

        redactor = Redactor((*extras, *DEFAULT_RULES))
        written: list[str] = []
        for source in sources:
            target = output_path(source, args.output_dir)
            if source.resolve() == target.resolve():
                raise ValueError(f"拒绝覆盖原文件：{source}")
            text = source.read_text(encoding="utf-8-sig")
            target.write_text(redactor.redact(text), encoding="utf-8")
            written.append(str(target))

        report = {**redactor.report(), "processed_files": len(sources), "outputs": written}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
