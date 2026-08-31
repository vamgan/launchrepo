import os, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import render

PROFILE = {"facts": {"name": {"value": "declutter", "source": "git remote"},
                     "license": {"value": "MIT", "source": "LICENSE"}},
           "unavailable": {"tagline": "not declared"}}


class TestFill(unittest.TestCase):
    def test_replaces_one_placeholder(self):
        self.assertEqual(render.fill("hello {{name}}", PROFILE, {}), "hello declutter")

    def test_replaces_several_placeholders(self):
        self.assertEqual(
            render.fill("{{name}} is {{license}}", PROFILE, {}),
            "declutter is MIT",
        )

    def test_extras_override_facts(self):
        self.assertEqual(
            render.fill("{{name}}", PROFILE, {"name": "override"}),
            "override",
        )

    def test_unknown_key_raises_and_names_it(self):
        with self.assertRaises(SystemExit) as ctx:
            render.fill("{{nope}}", PROFILE, {})
        self.assertIn("nope", str(ctx.exception))

    def test_unavailable_key_raises_with_reason(self):
        with self.assertRaises(SystemExit) as ctx:
            render.fill("{{tagline}}", PROFILE, {})
        message = str(ctx.exception)
        self.assertIn("tagline", message)
        self.assertIn("not declared", message)

    def test_html_special_characters_are_escaped(self):
        extras = {"tagline": "<script>&\"'"}
        result = render.fill("{{tagline}}", PROFILE, extras)
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_text_with_no_placeholders_is_unchanged(self):
        self.assertEqual(render.fill("plain text", PROFILE, {}), "plain text")


if __name__ == "__main__":
    unittest.main()
