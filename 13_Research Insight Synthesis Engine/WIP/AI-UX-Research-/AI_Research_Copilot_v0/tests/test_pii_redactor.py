import tempfile
import unittest
from pathlib import Path

from tools.pii_redactor import Redactor, literal_rules, main


class RedactorTests(unittest.TestCase):
    def test_redacts_common_chinese_pii_and_keeps_labels(self):
        text = "姓名：张三，手机 13812345678，邮箱 zhang.san@example.com，身份证 11010519900101123X"
        result = Redactor().redact(text)
        self.assertIn("姓名：[姓名_001]", result)
        self.assertIn("[手机号_001]", result)
        self.assertIn("[邮箱_001]", result)
        self.assertIn("[身份证_001]", result)
        self.assertNotIn("张三", result)
        self.assertNotIn("13812345678", result)

    def test_same_value_gets_stable_token(self):
        redactor = Redactor()
        result = redactor.redact("13812345678 和 138-1234-5678")
        self.assertEqual(result, "[手机号_001] 和 [手机号_001]")
        self.assertEqual(redactor.report()["detected_occurrences"], 2)

    def test_detects_names_in_common_natural_language_contexts(self):
        result = Redactor().redact("我叫李小明，是这次受访者。\n王芳：我平时每天开车。")
        self.assertEqual(result, "我叫[姓名_001]，是这次受访者。\n[姓名_002]：我平时每天开车。")

    def test_custom_name_and_term(self):
        rules = literal_rules(["李小明"], ["公司=示例科技有限公司"])
        result = Redactor((*rules,)).redact("李小明在示例科技有限公司工作")
        self.assertEqual(result, "[姓名_001]在[公司_001]工作")

    def test_cli_never_overwrites_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "访谈.txt"
            source.write_text("电话：13900001111", encoding="utf-8")
            self.assertEqual(main([str(source)]), 0)
            target = Path(folder) / "访谈.redacted.txt"
            self.assertEqual(source.read_text(encoding="utf-8"), "电话：13900001111")
            self.assertEqual(target.read_text(encoding="utf-8"), "电话：[手机号_001]")


if __name__ == "__main__":
    unittest.main()
